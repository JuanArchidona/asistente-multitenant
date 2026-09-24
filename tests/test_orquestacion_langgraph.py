"""El prototipo de LangGraph produce la misma traza que la línea base.

Es la condición de la comparativa del capítulo 3.1 de la memoria: si los dos
orquestadores no dieran trazas iguales con las mismas respuestas del
proveedor, el banco compararía dos sistemas y no dos orquestaciones. Aquí se
comprueba con el proveedor y el recuperador falsos, sin llamar a nada, para
las dos ramas que no necesitan servidores MCP (documental y sin fuente) y
para la elección de rama en las cuatro.
"""
from dataclasses import replace

import pytest

from src.agent import Sistema, crear_sistema
from src.gobernanza import Usuario
from src.retriever import Recuperacion, Recuperado
from src.schema import Enrutamiento
from src.tenant import cargar_tenant

langgraph = pytest.importorskip("langgraph")

from src.orquestacion_langgraph import (
    NODO_DOCUMENTAL,
    NODO_ESTRUCTURADA,
    NODO_MIXTA,
    NODO_SIN_FUENTE,
    SistemaLangGraph,
    _decidir_rama,
)

RUTA_RRHH = '{"categoria": "rrhh", "justificacion": "vacaciones", "confianza": 0.9}'
RUTA_OTRO = '{"categoria": "otro", "justificacion": "ajena", "confianza": 0.9}'
RESPUESTA = "Son 23 días laborables (convenio_colectivo.md)."


class RetrieverFalso:
    def __init__(self, fragmentos, denegados=()):
        self.fragmentos = fragmentos
        self.denegados = list(denegados)

    def recuperar_con_control(self, consulta, fuente, usuario=None):
        return Recuperacion(self.fragmentos, list(self.denegados))


def _quitar_latencias(traza: dict) -> dict:
    return {k: v for k, v in traza.items() if not k.startswith("latencia_")}


def _par(cfg, chat_falso, respuestas, fragmentos):
    """El mismo caso por los dos orquestadores, cada uno con su chat falso."""
    vanilla = Sistema(cfg, chat=chat_falso(respuestas))
    grafo = SistemaLangGraph(cfg, chat=chat_falso(respuestas))
    vanilla._retriever = RetrieverFalso(fragmentos)
    grafo._retriever = RetrieverFalso(fragmentos)
    return vanilla, grafo


def test_rama_documental_da_la_misma_traza(cfg, chat_falso):
    fragmento = Recuperado("23 días laborables", "rrhh", "convenio_colectivo.md", 0.15)
    vanilla, grafo = _par(cfg, chat_falso, [RUTA_RRHH, RESPUESTA], [fragmento])
    a = vanilla.responder("¿vacaciones?")
    b = grafo.responder("¿vacaciones?")
    assert _quitar_latencias(a) == _quitar_latencias(b)
    assert set(a) == set(b)  # también las claves de latencia, aunque su valor difiera


def test_rama_sin_fuente_da_la_misma_traza(cfg, chat_falso):
    vanilla, grafo = _par(cfg, chat_falso, [RUTA_OTRO, "No hay documentación."], [])
    a = vanilla.responder("¿capital de Australia?")
    b = grafo.responder("¿capital de Australia?")
    assert _quitar_latencias(a) == _quitar_latencias(b)
    assert b["contexto_vacio"] is True and b["fuentes_usadas"] == []


def test_la_denegacion_por_permiso_pasa_igual_por_el_grafo(cfg, chat_falso):
    """El permiso va dentro de la recuperación, no en el grafo: si el
    recuperador retiene un documento y no queda nada, el mensaje determinista
    de denegación tiene que salir por los dos caminos sin llamar al generador."""
    vanilla = Sistema(cfg, chat=chat_falso([RUTA_RRHH]))
    grafo = SistemaLangGraph(cfg, chat=chat_falso([RUTA_RRHH]))
    vanilla._retriever = RetrieverFalso([], denegados=["anexo_confidencial_plantilla.md"])
    grafo._retriever = RetrieverFalso([], denegados=["anexo_confidencial_plantilla.md"])
    a = vanilla.responder("¿salario de Diego?")
    b = grafo.responder("¿salario de Diego?")
    assert _quitar_latencias(a) == _quitar_latencias(b)
    assert b["denegados_por_permiso"] == ["anexo_confidencial_plantilla.md"]
    assert len(grafo.chat.llamadas) == 1  # solo el enrutador


def test_el_mismo_chat_recibe_las_mismas_llamadas(cfg, chat_falso):
    """Misma orquestación implica mismas llamadas al proveedor, en el mismo
    orden y con los mismos prompts: es lo que hace comparable el coste."""
    fragmento = Recuperado("23 días laborables", "rrhh", "convenio_colectivo.md", 0.15)
    vanilla, grafo = _par(cfg, chat_falso, [RUTA_RRHH, RESPUESTA], [fragmento])
    vanilla.responder("¿vacaciones?")
    grafo.responder("¿vacaciones?")
    assert vanilla.chat.llamadas == grafo.chat.llamadas


@pytest.mark.parametrize(
    "categoria, categorias, esperado",
    [
        ("otro", [], NODO_SIN_FUENTE),
        ("rrhh", ["rrhh"], NODO_DOCUMENTAL),
    ],
)
def test_decidir_rama_en_el_heredado(cfg, categoria, categorias, esperado):
    sistema = Sistema(cfg, chat=object())
    ruta = Enrutamiento(categoria=categoria, justificacion="x", confianza=0.9)
    assert _decidir_rama(sistema, {"ruta": ruta, "categorias": categorias}) == esperado


def test_decidir_rama_estructurada_y_mixta(cfg):
    sistema = Sistema(replace(cfg, tenant=cargar_tenant("agencia_inmobiliaria")), chat=object())
    cartera = Enrutamiento(categoria="cartera", justificacion="x", confianza=0.9)
    assert _decidir_rama(sistema, {"ruta": cartera, "categorias": ["cartera"]}) == NODO_ESTRUCTURADA
    expedientes = Enrutamiento(categoria="expedientes", justificacion="x", confianza=0.9)
    assert (
        _decidir_rama(sistema, {"ruta": expedientes, "categorias": ["expedientes", "cartera"]})
        == NODO_MIXTA
    )


def test_crear_sistema_respeta_el_conmutador(cfg, chat_falso):
    assert type(crear_sistema(cfg, chat=chat_falso([]))) is Sistema
    con_grafo = crear_sistema(replace(cfg, orquestador="langgraph"), chat=chat_falso([]))
    assert isinstance(con_grafo, SistemaLangGraph)
    assert isinstance(con_grafo, Sistema)  # aprobar, rechazar y el registro siguen ahí


def test_el_grafo_tiene_un_nodo_por_rama_y_ninguno_mas(cfg, chat_falso):
    grafo = SistemaLangGraph(cfg, chat=chat_falso([])).grafo
    nodos = set(grafo.get_graph().nodes) - {"__start__", "__end__"}
    assert nodos == {"enrutar", NODO_SIN_FUENTE, NODO_DOCUMENTAL, NODO_ESTRUCTURADA, NODO_MIXTA, "fundir"}


def test_el_usuario_llega_a_la_rama(cfg, chat_falso):
    fragmento = Recuperado("68.000", "rrhh", "anexo_confidencial_plantilla.md", 0.1)
    grafo = SistemaLangGraph(cfg, chat=chat_falso([RUTA_RRHH, "68.000 euros"]))
    grafo._retriever = RetrieverFalso([fragmento])
    traza = grafo.responder("¿salario?", usuario=Usuario(id="direccion", roles=["rrhh_direccion"]))
    assert traza["usuario"] == "direccion"
