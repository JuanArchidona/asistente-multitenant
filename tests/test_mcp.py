"""Pruebas de la rama de datos estructurados.

Estas sí levantan el servidor MCP como proceso, a diferencia del resto de la
suite, que no toca nada externo. Es deliberado: lo que hay que comprobar aquí es
justamente que el proceso arranca, negocia el protocolo y cierra limpio, y un
doble de prueba no comprobaría nada de eso. No hay llamadas a APIs de pago, así
que sigue valiendo como puerta de CI.
"""
import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent import system_datos
from src.mcp_cliente import ClienteMCP
from src.tenant import Tenant, cargar_tenant

RAIZ = Path(__file__).resolve().parents[1]
TENANTS = RAIZ / "tenants"

AGENCIA = cargar_tenant("agencia_inmobiliaria", raiz=TENANTS)
EMPRESA = cargar_tenant("empresa_servicios", raiz=TENANTS)


@pytest.fixture(scope="module")
def cliente():
    with ClienteMCP(AGENCIA) as c:
        yield c


# --- Contrato del servidor ---

def test_el_servidor_publica_sus_herramientas(cliente):
    nombres = {h.nombre for h in cliente.herramientas}
    assert {
        "buscar_inmuebles",
        "detalle_inmueble",
        "estadisticas_cartera",
        "agenda_comercial",
        "estado_operacion",
    } <= nombres


def test_las_herramientas_van_prefijadas_por_su_servidor(cliente):
    """Sin prefijo, dos servidores con herramientas homónimas serían ambiguos."""
    for herramienta in cliente.herramientas:
        assert herramienta.nombre_expuesto == f"crm__{herramienta.nombre}"


def test_toda_herramienta_llega_con_descripcion_y_esquema(cliente):
    """Lo que el modelo no puede leer, no lo puede usar bien."""
    for esquema in cliente.esquemas_anthropic():
        assert esquema["description"].strip(), f"{esquema['name']} sin descripción"
        assert esquema["input_schema"]["type"] == "object"


# --- Ejecución ---

def test_una_consulta_de_cartera_devuelve_datos(cliente):
    bruto = cliente.invocar("crm__estadisticas_cartera", {"zona": "Delicias"})
    datos = json.loads(bruto)
    assert datos["inmuebles"] > 0
    assert datos["precio_m2_medio_eur"] > 0


def test_el_filtro_de_inmuebles_estancados_funciona(cliente):
    bruto = cliente.invocar(
        "crm__buscar_inmuebles", {"dias_publicado_min": 91, "solo_sin_ofertas": True}
    )
    datos = json.loads(bruto)
    for inmueble in datos["inmuebles"]:
        assert inmueble["dias_publicado"] >= 91
        assert inmueble["ofertas_recibidas"] == 0


def test_una_referencia_inexistente_devuelve_error_explicito(cliente):
    """No se inventa una ficha ni se devuelve vacío: el modelo tiene que saberlo."""
    datos = json.loads(cliente.invocar("crm__detalle_inmueble", {"referencia": "INM-0000-000"}))
    assert "error" in datos


def test_invocar_una_herramienta_inexistente_falla_ruidosamente(cliente):
    with pytest.raises(KeyError, match="no publicada"):
        cliente.invocar("crm__inventada", {})


def test_la_operacion_expone_datos_personales(cliente):
    """Superficie de fuga declarada.

    Si este test se pusiera en verde por dejar de devolver datos personales, la
    capa de gobernanza estaría midiéndose contra un sistema que ya no tiene nada
    que proteger. El control correcto va en el sistema, no en el servidor.
    """
    datos = json.loads(cliente.invocar("crm__estado_operacion", {"referencia": "OP-2026-110"}))
    assert {"dni", "telefono", "ingresos_netos_mensuales_eur"} <= set(datos["parte_compradora"])


# --- Inquilinos sin rama estructurada ---

def test_un_inquilino_sin_servidores_no_levanta_nada():
    """El inquilino documental no puede pagar el arranque de procesos que no usa."""
    with ClienteMCP(EMPRESA) as c:
        assert c.herramientas == []
        assert c.esquemas_anthropic() == []


def test_usar_el_cliente_sin_abrir_falla_en_vez_de_colgarse():
    cliente = ClienteMCP(AGENCIA)
    with pytest.raises(RuntimeError, match="no está abierto"):
        cliente.invocar("crm__estadisticas_cartera", {})


# --- Coherencia del manifiesto ---

def test_una_categoria_estructurada_sin_servidor_se_rechaza():
    """Enrutaría a la nada y parecería un corpus incompleto."""
    with pytest.raises(ValidationError, match="ningún servidor MCP"):
        Tenant.model_validate({
            "id": "rota",
            "nombre": "Sin servidor",
            "contexto_enrutador": "una prueba",
            "categorias": [
                {"nombre": "datos", "descripcion": "x", "destino": "estructurado"}
            ],
        })


def test_una_categoria_estructurada_no_puede_declarar_fuente():
    with pytest.raises(ValidationError, match="no puede declarar fuente"):
        Tenant.model_validate({
            "id": "rota",
            "nombre": "Con fuente de más",
            "contexto_enrutador": "una prueba",
            "categorias": [
                {
                    "nombre": "datos",
                    "descripcion": "x",
                    "destino": "estructurado",
                    "fuente": "datos",
                }
            ],
            "servidores_mcp": [{"nombre": "crm", "comando": "python", "args": []}],
        })


def test_la_agencia_enruta_cartera_a_la_rama_estructurada():
    assert AGENCIA.destino_de("cartera") == "estructurado"
    assert AGENCIA.destino_de("procesos") == "documental"
    with pytest.raises(KeyError, match="no tiene fuente documental"):
        AGENCIA.fuente_de("cartera")


# --- Prompt de la rama ---

def test_el_prompt_de_datos_lleva_la_fecha():
    """Sin fecha, 'esta semana' no se puede resolver y el modelo pide aclaración."""
    assert "2026-09-20" in system_datos(date(2026, 9, 20))
