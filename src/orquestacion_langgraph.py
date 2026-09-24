"""Orquestación con LangGraph: el mismo sistema, encadenado por un grafo.

Prototipo para la comparativa del capítulo 3.1 de la memoria (Python sin
framework frente a LangGraph). Existe para medir, no para sustituir: la línea
base sigue siendo `Sistema._responder`, y se activa con `ORQUESTADOR=langgraph`
tras `uv sync --group langgraph`.

Lo que se porta y lo que no, para que la comparación mida lo que dice medir:

- **Se porta solo la orquestación**: qué se hace después de enrutar y en qué
  orden. Aquí eso es un grafo de estado con un nodo por rama y una arista
  condicional que elige rama.
- **No se porta ninguna rama.** El enrutador, la recuperación con el permiso
  dentro del `where`, el cliente MCP con la redacción a la salida de la
  herramienta, la generación y el formato de la traza son los mismos métodos
  de `Sistema` que usa la línea base. Si el grafo produjera trazas distintas,
  el banco lo vería, y eso es la primera prueba de este módulo.

La única lógica que vive aquí y también en `Sistema._responder` es la elección
de rama (`_decidir_rama`), porque eso ES la orquestación. Está escrita dos
veces a propósito: es lo que se compara.

Por qué `SistemaLangGraph` hereda de `Sistema` en vez de envolverlo: el banco,
la interfaz y el canal de WhatsApp crean un `Sistema` y llaman a `responder`,
`aprobar` y `rechazar`; heredar deja todo eso igual y cambia solo `_responder`,
que es exactamente el trozo que se quiere comparar.
"""
from __future__ import annotations

import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agent import Sistema
from .gobernanza import Usuario
from .schema import Enrutamiento
from .tenant import DESTINO_ESTRUCTURADO

NODO_SIN_FUENTE = "sin_fuente"
NODO_DOCUMENTAL = "documental"
NODO_ESTRUCTURADA = "estructurada"
NODO_MIXTA = "mixta"
RAMAS = (NODO_SIN_FUENTE, NODO_DOCUMENTAL, NODO_ESTRUCTURADA, NODO_MIXTA)


class Estado(TypedDict, total=False):
    """Lo que viaja entre nodos. `total=False` porque cada nodo rellena su parte."""

    consulta: str
    usuario: Usuario
    ruta: Enrutamiento
    t_router: float
    categorias: list[str]
    cabecera: dict
    rama: dict
    traza: dict


def _decidir_rama(sistema: Sistema, estado: Estado) -> str:
    """La arista condicional. Es el `if` de `Sistema._responder`, y por eso
    está aquí otra vez: es lo único que cambia entre los dos orquestadores."""
    ruta = estado["ruta"]
    categorias = estado["categorias"]
    if ruta.sin_fuente:
        return NODO_SIN_FUENTE
    if len(categorias) > 1:
        return NODO_MIXTA
    if sistema.cfg.tenant.destino_de(ruta.categoria) == DESTINO_ESTRUCTURADO:
        return NODO_ESTRUCTURADA
    return NODO_DOCUMENTAL


def construir_grafo(sistema: Sistema):
    """Compila el grafo sobre un `Sistema` concreto. Los nodos son clausuras
    sobre `sistema` para que cada uno llame a la rama de siempre."""

    def enrutar(estado: Estado) -> Estado:
        t0 = time.perf_counter()
        ruta = sistema._enrutar(estado["consulta"])
        t_router = time.perf_counter() - t0
        categorias = (
            [] if ruta.sin_fuente else sistema.cfg.tenant.categorias_a_consultar(ruta.categoria)
        )
        return {
            "ruta": ruta,
            "t_router": t_router,
            "categorias": categorias,
            "cabecera": sistema._cabecera_traza(
                estado["consulta"], estado["usuario"], ruta, categorias
            ),
        }

    def sin_fuente(estado: Estado) -> Estado:
        return {"rama": sistema._responder_sin_fuente(estado["consulta"], estado["t_router"])}

    def documental(estado: Estado) -> Estado:
        fuente = sistema.cfg.tenant.fuente_de(estado["ruta"].categoria)
        return {
            "rama": sistema._responder_documental(
                estado["consulta"], fuente, estado["t_router"], estado["usuario"]
            )
        }

    def estructurada(estado: Estado) -> Estado:
        return {
            "rama": sistema._responder_con_datos(
                estado["consulta"], estado["t_router"], estado["usuario"]
            )
        }

    def mixta(estado: Estado) -> Estado:
        return {
            "rama": sistema._responder_mixto(
                estado["consulta"], estado["categorias"], estado["t_router"], estado["usuario"]
            )
        }

    def fundir(estado: Estado) -> Estado:
        # La traza final tiene la misma forma que en `Sistema._responder`:
        # cabecera común más la parte de la rama, y la rama pisa lo que
        # sobreescriba (por ejemplo `acciones_pendientes`).
        return {"traza": {**estado["cabecera"], **estado["rama"]}}

    grafo = StateGraph(Estado)
    grafo.add_node("enrutar", enrutar)
    grafo.add_node(NODO_SIN_FUENTE, sin_fuente)
    grafo.add_node(NODO_DOCUMENTAL, documental)
    grafo.add_node(NODO_ESTRUCTURADA, estructurada)
    grafo.add_node(NODO_MIXTA, mixta)
    grafo.add_node("fundir", fundir)

    grafo.add_edge(START, "enrutar")
    grafo.add_conditional_edges(
        "enrutar",
        lambda estado: _decidir_rama(sistema, estado),
        {nombre: nombre for nombre in RAMAS},
    )
    for nombre in RAMAS:
        grafo.add_edge(nombre, "fundir")
    grafo.add_edge("fundir", END)
    return grafo.compile()


class SistemaLangGraph(Sistema):
    """`Sistema` con `_responder` sustituido por la ejecución del grafo."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grafo = construir_grafo(self)

    def _responder(self, consulta: str, usuario: Usuario) -> dict:
        final = self.grafo.invoke({"consulta": consulta, "usuario": usuario})
        return final["traza"]
