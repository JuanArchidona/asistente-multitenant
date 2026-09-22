"""Fixtures compartidas.

Ninguna prueba de este directorio llama a una API: se ejecutan en CI sin claves,
en segundos, y sirven de puerta de calidad en cada push. La evaluación con
llamadas reales vive en `evals/` y se lanza a mano antes de un pase a producción
— la distinción es deliberada, porque un gate que cuesta dinero y tarda minutos
acaba desactivándose.
"""
from dataclasses import replace
from pathlib import Path

import pytest

from src.config import Config
from src.provider import ChatProvider
from src.tenant import cargar_tenant

RAIZ = Path(__file__).resolve().parents[1]

# El inquilino real, no uno de juguete: si el manifiesto de `empresa_servicios`
# se rompe, estas pruebas tienen que enterarse. Es el que sostiene el banco.
TENANT_BASE = cargar_tenant("empresa_servicios", raiz=RAIZ / "tenants")

CONFIG_BASE = Config(
    tenant=TENANT_BASE,
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
    corpus_path="corpus/empresa_servicios",
    chunk_strategy="chars",
    chunk_size=800,
    chunk_overlap=100,
    top_k=4,
    distance_threshold=None,
    gen_policy="base",
    # None = no se envia el parametro, que es como ha corrido todo el banco.
    router_temperature=None,
    judge_provider="anthropic",
    judge_model="modelo-juez",
    # Distinta de anthropic_api_key a proposito: la separacion de claves es lo
    # que permite que la factura distinga evaluar de funcionar.
    judge_api_key="clave-de-prueba-juez",
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
        # Se guarda aparte de `llamadas` para no cambiar la forma de una tupla
        # de la que dependen las pruebas heredadas.
        self.temperaturas: list[float | None] = []

    def completar(
        self, system: str, user: str, model: str, temperature: float | None = None
    ) -> str:
        self.llamadas.append((system, user, model))
        self.temperaturas.append(temperature)
        self.uso.registrar(model, 10, 20)
        return self.respuestas.pop(0) if self.respuestas else ""


@pytest.fixture
def chat_falso():
    return ChatFalso
