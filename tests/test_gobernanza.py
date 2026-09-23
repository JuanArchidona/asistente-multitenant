"""Pruebas del control de acceso.

Lo que estas pruebas vigilan no es que el sistema sepa decir que no, sino que el
dato **no llegue** al modelo. Un control que recupera y luego calla deja el
documento en la ventana de contexto, donde una inyección lo saca y donde queda
en los registros del proveedor.

Y vigilan también lo contrario: que quien tiene el rol siga recibiendo el dato.
Un control que bloquea a todo el mundo saca un pleno en confidencialidad y deja
el producto sin valor.
"""
import json
from dataclasses import replace

import pytest

from src.gobernanza import (
    MARCA_RESTRINGIDO,
    SIN_RESTRICCION,
    USUARIO_ANONIMO,
    PoliticaAcceso,
    Usuario,
    redactar,
    redactar_json,
)
from src.tenant import cargar_tenant

AGENCIA = cargar_tenant("agencia_inmobiliaria")
EMPRESA = cargar_tenant("empresa_servicios")

DIRECCION = Usuario(id="direccion", roles=["direccion"])
COMERCIAL = Usuario(id="comercial", roles=[])

OPERACION = {
    "referencia": "OP-2026-110",
    "estado": "reserva firmada",
    "importe_eur": 170000,
    "parte_compradora": {
        "nombre": "Marta Iribarren Sanz",
        "dni": "40.345.146-K",
        "telefono": "637 00 66 21",
        "correo": "marta@example.com",
        "ingresos_netos_mensuales_eur": 1980,
    },
}


# --- Redacción de resultados de herramienta ---

def test_los_campos_sensibles_se_redactan_aunque_esten_anidados():
    """Los datos personales viven dentro de `parte_compradora`, no en el primer
    nivel. Una redacción que solo mirase las claves de arriba no vería nada."""
    limpio, redactados = redactar(OPERACION, AGENCIA.politica, COMERCIAL)
    compradora = limpio["parte_compradora"]
    assert compradora["dni"] == MARCA_RESTRINGIDO
    assert compradora["telefono"] == MARCA_RESTRINGIDO
    assert compradora["correo"] == MARCA_RESTRINGIDO
    assert compradora["ingresos_netos_mensuales_eur"] == MARCA_RESTRINGIDO
    assert set(redactados) >= {
        "parte_compradora.dni",
        "parte_compradora.ingresos_netos_mensuales_eur",
    }


def test_lo_que_no_es_sensible_sobrevive_a_la_redaccion():
    """Redactar no puede dejar la herramienta inservible."""
    limpio, _ = redactar(OPERACION, AGENCIA.politica, COMERCIAL)
    assert limpio["estado"] == "reserva firmada"
    assert limpio["importe_eur"] == 170000
    assert limpio["parte_compradora"]["nombre"] == "Marta Iribarren Sanz"


def test_quien_tiene_el_rol_recibe_los_datos_intactos():
    limpio, redactados = redactar(OPERACION, AGENCIA.politica, DIRECCION)
    assert redactados == []
    assert limpio == OPERACION


def test_la_redaccion_recorre_las_listas():
    datos = {"operaciones": [{"parte_compradora": {"dni": "X"}}]}
    limpio, redactados = redactar(datos, AGENCIA.politica, COMERCIAL)
    assert limpio["operaciones"][0]["parte_compradora"]["dni"] == MARCA_RESTRINGIDO
    assert redactados == ["operaciones[0].parte_compradora.dni"]


def test_una_salida_no_estructurada_se_retiene_si_la_politica_exige_redactar():
    """No se intenta redactar texto libre con expresiones regulares.

    Un filtro que acierta a veces es peor que no tenerlo: el banco lo daría por
    bueno y la fuga aparecería en producción. Y desde el 23-09-2026 (§41)
    tampoco se deja pasar con una marca al lado: con campos sensibles
    declarados, lo que no se puede redactar no llega al modelo.
    """
    from src.gobernanza import MARCA_RETENIDA, TEXTO_RETENIDO

    bruto = "La compradora es Marta, DNI 40.345.146-K"
    salida, redactados = redactar_json(bruto, AGENCIA.politica, COMERCIAL)
    assert salida == TEXTO_RETENIDO
    assert "40.345.146-K" not in salida
    assert redactados == [MARCA_RETENIDA]


def test_una_salida_no_estructurada_pasa_con_marca_si_no_hay_nada_que_redactar():
    """Sin campos sensibles en la política no hay filtro que aplicar: el texto
    pasa, y se deja constancia de que no era JSON."""
    from src.gobernanza import MARCA_NO_ESTRUCTURADA, PoliticaAcceso

    bruto = "Texto libre de una herramienta"
    salida, redactados = redactar_json(bruto, PoliticaAcceso(), COMERCIAL)
    assert salida == bruto
    assert redactados == [MARCA_NO_ESTRUCTURADA]


def test_redactar_json_devuelve_json_valido():
    salida, _ = redactar_json(json.dumps(OPERACION), AGENCIA.politica, COMERCIAL)
    assert json.loads(salida)["parte_compradora"]["dni"] == MARCA_RESTRINGIDO


# --- Política y usuarios ---

def test_un_documento_sin_restriccion_declarada_es_publico():
    assert EMPRESA.politica.requisito_de_documento("convenio_colectivo.md") == SIN_RESTRICCION
    assert (
        EMPRESA.politica.requisito_de_documento("anexo_confidencial_plantilla.md")
        == "rrhh_direccion"
    )


def test_el_usuario_por_defecto_no_tiene_ningun_privilegio():
    """El escenario a medir es el del empleado que pide lo que no le toca."""
    assert USUARIO_ANONIMO.roles == []
    assert USUARIO_ANONIMO.niveles_visibles == [SIN_RESTRICCION]
    assert USUARIO_ANONIMO.puede(SIN_RESTRICCION)
    assert not USUARIO_ANONIMO.puede("direccion")


def test_los_niveles_visibles_incluyen_lo_publico_y_los_roles():
    assert DIRECCION.niveles_visibles == [SIN_RESTRICCION, "direccion"]


# --- El filtro entra en la búsqueda, no después ---

def test_el_permiso_viaja_dentro_del_where_de_chroma(cfg, monkeypatch):
    """El punto exacto donde el control es o no es real.

    Si el filtro se aplicase después de la búsqueda, el texto restringido habría
    salido del índice y estaría en memoria del proceso. Aquí se comprueba que va
    en la consulta.
    """
    from src import retriever as modulo

    llamadas = []

    class ColeccionFalsa:
        def query(self, **kwargs):
            llamadas.append(kwargs)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    class ClienteFalso:
        def __init__(self, path):
            pass

        def get_collection(self, nombre):
            return ColeccionFalsa()

    monkeypatch.setattr(modulo.chromadb, "PersistentClient", ClienteFalso)
    monkeypatch.setattr(
        modulo, "GeminiEmbedder", lambda cfg, **kw: type("E", (), {"embed_consulta": lambda s, c: [0.0]})()
    )

    r = modulo.Retriever(replace(cfg, tenant=AGENCIA))
    r.recuperar("¿ingresos del comprador?", "procesos", COMERCIAL)

    condiciones = llamadas[0]["where"]["$and"]
    assert {"fuente": "procesos"} in condiciones
    assert {"requiere": {"$in": [SIN_RESTRICCION]}} in condiciones


def test_la_consulta_de_auditoria_no_saca_el_texto_restringido(cfg, monkeypatch):
    """La segunda consulta averigua QUÉ retuvo el control, no qué dice.

    Es la única que mira más allá del permiso del usuario, así que es la que
    podría convertir el control estructural en uno de mentira. Pide solo
    metadatos: el texto restringido nunca llega a salir del índice.
    """
    from src import retriever as modulo

    llamadas = []

    class ColeccionFalsa:
        def query(self, **kwargs):
            llamadas.append(kwargs)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    monkeypatch.setattr(
        modulo.chromadb,
        "PersistentClient",
        lambda path: type("C", (), {"get_collection": lambda s, n: ColeccionFalsa()})(),
    )
    monkeypatch.setattr(
        modulo, "GeminiEmbedder", lambda cfg, **kw: type("E", (), {"embed_consulta": lambda s, c: [0.0]})()
    )

    r = modulo.Retriever(replace(cfg, tenant=AGENCIA))
    r.recuperar_con_control("¿ingresos del comprador?", "procesos", COMERCIAL)

    auditoria = llamadas[1]
    assert auditoria["include"] == ["metadatas"]
    assert "documents" not in auditoria["include"]
    # Sin filtro de permiso: es justo lo que la hace capaz de ver lo retenido.
    assert auditoria["where"] == {"fuente": "procesos"}


def test_el_rol_amplia_lo_que_el_where_deja_pasar(cfg, monkeypatch):
    from src import retriever as modulo

    llamadas = []

    class ColeccionFalsa:
        def query(self, **kwargs):
            llamadas.append(kwargs)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    monkeypatch.setattr(
        modulo.chromadb,
        "PersistentClient",
        lambda path: type("C", (), {"get_collection": lambda s, n: ColeccionFalsa()})(),
    )
    monkeypatch.setattr(
        modulo, "GeminiEmbedder", lambda cfg, **kw: type("E", (), {"embed_consulta": lambda s, c: [0.0]})()
    )

    r = modulo.Retriever(replace(cfg, tenant=AGENCIA))
    r.recuperar("¿ingresos del comprador?", "procesos", DIRECCION)

    assert {"requiere": {"$in": [SIN_RESTRICCION, "direccion"]}} in llamadas[0]["where"]["$and"]


# --- Coherencia entre política y banco ---

def test_toda_politica_declara_roles_que_algun_caso_ejercita():
    """Un rol que ningún caso usa es un control sin comprobar.

    Es el fallo silencioso de esta capa: se escribe la política, nadie la
    ejercita con permiso, y nunca se descubre que además de bloquear al que no
    debe pasar bloquea al que sí.
    """
    from evals.dataset import GOLDEN_CONSULTAS, cargar_consultas, ruta_golden

    for tenant in (EMPRESA, AGENCIA):
        declarados = tenant.politica.roles_declarados
        if not declarados:
            continue
        casos = cargar_consultas(ruta_golden(tenant.id, GOLDEN_CONSULTAS))
        ejercitados = {rol for c in casos for rol in c.roles_usuario}
        sin_probar = declarados - ejercitados
        assert not sin_probar, (
            f"{tenant.id}: roles declarados que ningún caso del banco usa: {sorted(sin_probar)}"
        )


def test_una_politica_vacia_no_restringe_nada():
    vacia = PoliticaAcceso()
    assert vacia.requisito_de_documento("lo_que_sea.md") == SIN_RESTRICCION
    limpio, redactados = redactar(OPERACION, vacia, COMERCIAL)
    assert limpio == OPERACION
    assert redactados == []


def test_un_campo_sensible_necesita_declarar_quien_puede_verlo():
    with pytest.raises(ValueError, match="campos_sensibles"):
        PoliticaAcceso.model_validate(
            {"campos_sensibles": [{"campo": "dni", "requiere": ""}]}
        )
