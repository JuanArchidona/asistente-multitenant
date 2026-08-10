"""Fixtures compartidas.

Ninguna prueba de este directorio llama a una API: se ejecutan en CI sin claves,
en segundos, y sirven de puerta de calidad en cada push. La evaluación con
llamadas reales vive en `evals/` y se lanza a mano antes de un pase a producción
— la distinción es deliberada, porque un gate que cuesta dinero y tarda minutos
acaba desactivándose.
"""
from dataclasses import replace

import pytest

from src.config import Config
from src.provider import ChatProvider

CONFIG_BASE = Config(
    provider="anthropic",
    anthropic_api_key="clave-de-prueba",
    model_router="modelo-router",
    model_generator="modelo-generador",
    gemini_api_key="clave-de-prueba",
    gemini_model="modelo-gemini",
    embed_model="modelo-embed",
    embed_dims=768,
    chroma_path="data/chroma-test",
    collection="coleccion_test",
    corpus_path="corpus",
    chunk_strategy="chars",
    chunk_size=800,
    chunk_overlap=100,
    top_k=4,
    distance_threshold=None,
    gen_policy="base",
    judge_provider="anthropic",
    judge_model="modelo-juez",
    builder_model="modelo-constructor",
)


@pytest.fixture
def cfg() -> Config:
    return CONFIG_BASE


@pytest.fixture
def cfg_factory():
    def _crear(**cambios) -> Config:
        return replace(CONFIG_BASE, **cambios)

    return _crear


class ChatFalso(ChatProvider):
    """Proveedor de chat con respuestas prefijadas que registra cada llamada."""

    def __init__(self, respuestas: list[str]):
        super().__init__()
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[str, str, str]] = []

    def completar(self, system: str, user: str, model: str) -> str:
        self.llamadas.append((system, user, model))
        self.uso.registrar(model, 10, 20)
        return self.respuestas.pop(0) if self.respuestas else ""


@pytest.fixture
def chat_falso():
    return ChatFalso
