"""Abstracción de chat sobre Anthropic | Gemini (reusada del Módulo 2.1).

Aquí solo necesitamos generación de texto (enrutador y generador), sin
tool-calling. Se mantiene la conmutabilidad de proveedor por si se quiere
Gemini como generador.

Añadido en la 3.3: **contabilidad de uso**. La 3.1 descartaba el bloque `usage`
de cada respuesta, así que no había forma de saber lo que costaba una consulta.
Como `get_chat()` es el único punto por el que pasan todas las llamadas al LLM,
instrumentar aquí cubre el 100 % del gasto sin tocar la lógica de negocio. El
banco de pruebas lo usa para reportar coste por caso y coste total de una
ejecución, que es la mitad de la respuesta a "¿compensa cambiar de modelo?".
"""
import re
import threading
import time
from dataclasses import dataclass, field

from .config import Config

# Reintentos ante límite de tasa. La app hace una llamada por consulta y nunca lo
# toca; el banco de pruebas encadena cientos y lo toca constantemente. Sin esto,
# una ejecución de dos horas muere a la mitad y hay que repetirla entera.
REINTENTOS = 5
ESPERA_POR_DEFECTO_S = 15.0
_RE_RETRY_DELAY = re.compile(r"retryDelay['\"]?[:\s]+['\"]?(\d+(?:\.\d+)?)")
_SENALES_LIMITE = ("429", "RESOURCE_EXHAUSTED", "rate_limit", "overloaded", "529")


def con_reintentos(fn, descripcion: str = "llamada"):
    """Ejecuta `fn`, reintentando solo si el error es de límite de tasa."""
    ultimo = None
    for intento in range(REINTENTOS):
        try:
            return fn()
        except Exception as e:
            mensaje = str(e)
            if not any(s in mensaje for s in _SENALES_LIMITE):
                raise
            ultimo = e
            m = _RE_RETRY_DELAY.search(mensaje)
            espera = float(m.group(1)) + 1 if m else ESPERA_POR_DEFECTO_S * (intento + 1)
            print(f"[provider] límite de tasa en {descripcion}; reintento en {espera:.0f}s...")
            time.sleep(espera)
    raise RuntimeError(f"{descripcion}: límite de tasa tras {REINTENTOS} intentos: {ultimo}")

# Precio de lista por millón de tokens (entrada, salida) en USD, a 2026-08.
# Solo para orientar el coste de una ejecución del banco; no es facturación.
# claude-sonnet-5 tiene precio de lanzamiento (2,00 / 10,00) hasta el 31/08/2026;
# se usa el de lista para no subestimar.
PRECIOS = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "gemini-2.5-flash": (0.30, 2.50),
}


@dataclass
class Uso:
    """Acumulador de consumo por modelo."""

    llamadas: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    por_modelo: dict[str, dict[str, int]] = field(default_factory=dict)
    # El banco puede ejecutar casos en paralelo; el acumulador se comparte.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def registrar(self, modelo: str, entrada: int, salida: int) -> None:
        with self._lock:
            self.llamadas += 1
            self.tokens_entrada += entrada
            self.tokens_salida += salida
            m = self.por_modelo.setdefault(
                modelo, {"llamadas": 0, "tokens_entrada": 0, "tokens_salida": 0}
            )
            m["llamadas"] += 1
            m["tokens_entrada"] += entrada
            m["tokens_salida"] += salida

    def coste_usd(self) -> float:
        total = 0.0
        for modelo, m in self.por_modelo.items():
            precio_in, precio_out = PRECIOS.get(modelo, (0.0, 0.0))
            total += m["tokens_entrada"] / 1e6 * precio_in
            total += m["tokens_salida"] / 1e6 * precio_out
        return total

    def resumen(self) -> dict:
        return {
            "llamadas": self.llamadas,
            "tokens_entrada": self.tokens_entrada,
            "tokens_salida": self.tokens_salida,
            "coste_usd_estimado": round(self.coste_usd(), 6),
            "por_modelo": self.por_modelo,
        }


# Límite de salida del sistema bajo prueba. Es el de la 3.1 y no se toca: subirlo
# cambiaría el sistema evaluado. Las herramientas del banco (generador y crítico
# de casos sintéticos) piden explícitamente un límite mayor porque producen
# lotes en JSON, y un array truncado se pierde entero al parsearlo.
MAX_TOKENS_SUT = 1024


class ChatProvider:
    def __init__(self) -> None:
        self.uso = Uso()

    def completar(
        self, system: str, user: str, model: str, max_tokens: int = MAX_TOKENS_SUT
    ) -> str:
        raise NotImplementedError


class AnthropicChat(ChatProvider):
    def __init__(self, cfg: Config):
        super().__init__()
        from anthropic import Anthropic

        self.client = Anthropic(api_key=cfg.anthropic_api_key)

    def completar(
        self, system: str, user: str, model: str, max_tokens: int = MAX_TOKENS_SUT
    ) -> str:
        resp = con_reintentos(
            lambda: self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ),
            f"anthropic:{model}",
        )
        self.uso.registrar(model, resp.usage.input_tokens, resp.usage.output_tokens)
        return "".join(b.text for b in resp.content if b.type == "text")


class GeminiChat(ChatProvider):
    def __init__(self, cfg: Config):
        super().__init__()
        from google import genai

        self.client = genai.Client(api_key=cfg.gemini_api_key)

    def completar(
        self, system: str, user: str, model: str, max_tokens: int = MAX_TOKENS_SUT
    ) -> str:
        from google.genai import types

        resp = con_reintentos(
            lambda: self.client.models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(system_instruction=system),
            ),
            f"gemini:{model}",
        )
        meta = getattr(resp, "usage_metadata", None)
        if meta is not None:
            self.uso.registrar(
                model,
                getattr(meta, "prompt_token_count", 0) or 0,
                getattr(meta, "candidates_token_count", 0) or 0,
            )
        return resp.text


def get_chat(cfg: Config) -> ChatProvider:
    return AnthropicChat(cfg) if cfg.provider == "anthropic" else GeminiChat(cfg)
