"""Métricas del banco: deterministas (gratis, sin varianza) y de juez LLM."""
from .deterministas import (
    Resultado,
    evaluar_alcance_riesgo,
    evaluar_contiene,
    evaluar_fuga_literal,
    evaluar_retrieval,
    evaluar_routing,
    normalizar,
    superficie_de_riesgo,
)

__all__ = [
    "Resultado",
    "evaluar_alcance_riesgo",
    "evaluar_contiene",
    "evaluar_fuga_literal",
    "evaluar_retrieval",
    "evaluar_routing",
    "normalizar",
    "superficie_de_riesgo",
]
