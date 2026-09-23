"""Pruebas del aislamiento entre inquilinos y de la línea base heredada.

Dos cosas que este fichero protege y que, si se rompen, rompen el proyecto
entero sin hacer ruido:

1. **Que la reforma multi-tenant no haya cambiado el prompt del enrutador.** Las
   métricas de enrutado de los 109 casos se midieron contra un prompt concreto.
   Si la plantilla lo altera aunque sea en un espacio, la comparación con la
   línea base de la 3.3 deja de ser válida y nadie se entera.
2. **Que dos inquilinos no puedan verse.** El aislamiento es el argumento
   central del producto: si falla, no hay nada que vender ni que defender.
"""
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.router import system_router
from src.tenant import CATEGORIA_OTRO, Tenant, cargar_tenant, listar_tenants

RAIZ = Path(__file__).resolve().parents[1]
TENANTS = RAIZ / "tenants"
TENANT_BASE = cargar_tenant("empresa_servicios", raiz=TENANTS)

# El prompt tal y como estaba en la 3.3, copiado literal antes de la reforma.
# No se toca: es la referencia contra la que se compara lo que genera la plantilla.
SYSTEM_ROUTER_3_3 = """Eres un enrutador de consultas para el asistente interno de una empresa.
Clasifica la consulta del usuario en UNA de estas categorías:

- rrhh: convenio colectivo, vacaciones, nóminas, políticas de personal, permisos.
- desarrollo: estándares de código, guías técnicas, buenas prácticas de ingeniería.
- actas: preguntas sobre decisiones, acuerdos o tareas de reuniones pasadas.
- marca: marketing, comunicación, identidad visual, tono de marca.
- otro: no encaja en ninguna fuente interna anterior.

Responde SOLO con un objeto JSON válido, sin texto adicional ni markdown, con esta forma:
{"categoria": "<una de las categorías>", "justificacion": "<breve>", "confianza": <0.0-1.0>}"""


def _manifiesto(**cambios) -> dict:
    base = {
        "id": "prueba",
        "nombre": "Inquilino de prueba",
        "contexto_enrutador": "el asistente de una prueba",
        "categorias": [{"nombre": "uno", "descripcion": "la primera", "fuente": "uno"}],
        # Obligatoria desde el 23-09-2026; lo que valida está en test_ai_act.py.
        "ai_act": {
            "clasificacion": "transparencia_art_50",
            "aviso_usuario": "Respuesta generada por un asistente de IA.",
            "evaluado": "2026-09-23",
            "fuentes": ["prueba"],
        },
    }
    base.update(cambios)
    return base


# --- La línea base no se ha movido ---

def test_el_prompt_del_enrutador_reproduce_el_de_la_3_3():
    """Carácter a carácter. Un cambio aquí invalida las métricas heredadas."""
    assert system_router(TENANT_BASE) == SYSTEM_ROUTER_3_3


def test_el_corpus_del_inquilino_heredado_sigue_completo():
    raiz = RAIZ / "corpus" / TENANT_BASE.id
    fuentes = {p.name for p in raiz.iterdir() if p.is_dir()}
    assert fuentes == {c.fuente for c in TENANT_BASE.categorias}
    assert len(list(raiz.rglob("*.md"))) == 7


# --- Invariantes de cualquier inquilino, presente o futuro ---

@pytest.mark.parametrize("tenant_id", listar_tenants(TENANTS))
def test_cada_categoria_declarada_tiene_corpus_detras(tenant_id):
    """Una categoría sin documentos enruta a un vacío y el usuario recibe un
    "no hay documentación" que parece un fallo del sistema. Es el error más
    probable al dar de alta un cliente, así que se comprueba automáticamente
    para todos los inquilinos que existan."""
    tenant = cargar_tenant(tenant_id, raiz=TENANTS)
    raiz = RAIZ / "corpus" / tenant.id
    assert raiz.is_dir(), f"el inquilino {tenant_id!r} no tiene corpus en {raiz}"
    for categoria in tenant.categorias_documentales:
        directorio = raiz / categoria.fuente
        assert directorio.is_dir(), f"falta {directorio}"
        assert list(directorio.glob("*.md")), f"{directorio} no tiene documentos"


@pytest.mark.parametrize("tenant_id", listar_tenants(TENANTS))
def test_el_prompt_del_enrutador_nombra_todas_las_categorias(tenant_id):
    """Una categoría que el manifiesto declara pero el prompt no menciona es
    inalcanzable: el modelo no puede devolver lo que no conoce."""
    tenant = cargar_tenant(tenant_id, raiz=TENANTS)
    prompt = system_router(tenant)
    # Todas, también las estructuradas: una categoría que el prompt no nombra es
    # inalcanzable, dé a documentos o a herramientas.
    for categoria in tenant.categorias:
        assert f"- {categoria.nombre}:" in prompt
    assert f"- {CATEGORIA_OTRO}:" in prompt


# --- Aislamiento ---

def test_cada_inquilino_tiene_su_propia_coleccion_y_su_propio_corpus():
    """Estructural, no por filtro: dos ids distintos no pueden coincidir."""
    a = Tenant.model_validate(_manifiesto(id="uno"))
    b = Tenant.model_validate(_manifiesto(id="dos"))
    assert a.coleccion("corpus") != b.coleccion("corpus")
    assert a.corpus("corpus") != b.corpus("corpus")


def test_la_coleccion_de_un_inquilino_lleva_su_id():
    assert TENANT_BASE.coleccion("corpus_empresa") == "corpus_empresa__empresa_servicios"


def test_el_recuperador_abre_la_coleccion_del_inquilino_y_no_otra(cfg, monkeypatch):
    """Se comprueba en el borde exacto donde se elegiría mal: el nombre que el
    recuperador le pide a Chroma. Si ese nombre no cambia al cambiar de
    inquilino, un cliente estaría leyendo el índice de otro."""
    from src import retriever as modulo

    abiertas: list[str] = []

    class ClienteFalso:
        def __init__(self, path):
            self.path = path

        def get_collection(self, nombre):
            abiertas.append(nombre)
            return object()

    monkeypatch.setattr(modulo.chromadb, "PersistentClient", ClienteFalso)
    monkeypatch.setattr(modulo, "GeminiEmbedder", lambda cfg: object())

    agencia = Tenant.model_validate(_manifiesto(id="agencia"))
    for tenant in (TENANT_BASE, agencia):
        modulo.Retriever(
            replace(cfg, tenant=tenant, collection=tenant.coleccion("corpus"))
        )

    assert abiertas == ["corpus__empresa_servicios", "corpus__agencia"]


def test_el_barrido_no_mezcla_indices_de_inquilinos_distintos(cfg):
    """Misma configuración de indexación, distinto inquilino: distinta colección.

    Sin esto, barrer el inquilino B sobreescribiría el índice del A con
    documentos ajenos, que es una fuga de datos por la puerta de atrás.
    """
    from evals.variantes import nombre_coleccion

    agencia = Tenant.model_validate(_manifiesto(id="agencia"))
    assert nombre_coleccion(cfg) != nombre_coleccion(replace(cfg, tenant=agencia))


# --- Validación del manifiesto ---

def test_se_rechaza_una_categoria_llamada_otro():
    """`otro` es universal: declararla crearía dos significados para el mismo nombre."""
    with pytest.raises(ValidationError):
        Tenant.model_validate(
            _manifiesto(
                categorias=[{"nombre": CATEGORIA_OTRO, "descripcion": "x", "fuente": "x"}]
            )
        )


def test_se_rechazan_categorias_repetidas():
    with pytest.raises(ValidationError):
        Tenant.model_validate(
            _manifiesto(
                categorias=[
                    {"nombre": "uno", "descripcion": "a", "fuente": "uno"},
                    {"nombre": "uno", "descripcion": "b", "fuente": "otro_sitio"},
                ]
            )
        )


def test_se_rechaza_un_inquilino_sin_categorias():
    with pytest.raises(ValidationError):
        Tenant.model_validate(_manifiesto(categorias=[]))


@pytest.mark.parametrize("malo", ["Empresa", "con espacio", "con-guion", "2024", "acentué"])
def test_se_rechaza_un_id_que_no_sirve_como_ruta_ni_como_coleccion(malo):
    with pytest.raises(ValidationError):
        Tenant.model_validate(_manifiesto(id=malo))


def test_fuente_de_falla_ruidosamente_con_una_categoria_desconocida():
    with pytest.raises(KeyError):
        TENANT_BASE.fuente_de("inexistente")


def test_otro_no_tiene_fuente_documental():
    """Es el punto del flujo donde se responde sin RAG, no una fuente más."""
    assert CATEGORIA_OTRO in TENANT_BASE.categorias_validas
    with pytest.raises(KeyError):
        TENANT_BASE.fuente_de(CATEGORIA_OTRO)


# --- Carga desde disco ---

def test_cargar_un_inquilino_inexistente_dice_cuales_hay():
    with pytest.raises(ValueError, match="empresa_servicios"):
        cargar_tenant("no_existe", raiz=TENANTS)


def test_el_id_del_fichero_manda_sobre_el_declarado(tmp_path: Path):
    (tmp_path / "uno.json").write_text(
        Tenant.model_validate(_manifiesto(id="dos")).model_dump_json(), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="El nombre del fichero es la referencia"):
        cargar_tenant("uno", raiz=tmp_path)


def test_listar_tenants_encuentra_el_heredado():
    assert "empresa_servicios" in listar_tenants(TENANTS)
