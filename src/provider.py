"""Abstracción de chat sobre Anthropic | Gemini (reusada del Módulo 2.1).

Aquí solo necesitamos generación de texto (enrutador y generador), sin
tool-calling. Se mantiene la conmutabilidad de proveedor por si se quiere
Gemini como generador.

Añadido en la 3.3: **contabilidad de uso**. La 3.1 descartaba el bloque `usage`
de cada respuesta, así que no había forma de saber lo que costaba una consulta.
Como `get_chat()` es el único punto por el que pasan todas las llamadas al LLM,
instrumentar aquí cubre todo lo que pasa por el proveedor sin tocar la lógica de
negocio. **No cubre el gasto de la cuenta**, y la diferencia importa: la consola
del proveedor atribuyó a esta clave un 22 % más de lo que el repositorio
contabilizó en septiembre (`docs/HALLAZGOS.md` §16). Lo que se escapa son las
llamadas sueltas de desarrollo, que no producen informe, y los reintentos del
SDK, que el proveedor factura y este contador registra una sola vez. El
banco de pruebas lo usa para reportar coste por caso y coste total de una
ejecución, que es la mitad de la respuesta a "¿compensa cambiar de modelo?".
"""
import re
import threading
import time
from contextlib import contextmanager
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

# Precio por millón de tokens (entrada, salida) en USD.
# Solo para orientar el coste de una ejecución del banco; no es facturación.
# claude-sonnet-5 estuvo fijado en 3,00/15,00 por suponer que 2,00/10,00 era un
# precio de lanzamiento que vencía el 31/08/2026. No lo era: 2,00/10,00 es el
# precio vigente, y 3,00/15,00 es el de claude-sonnet-4-6. Contrastado el
# 22-09-2026 contra el coste que la consola del proveedor atribuye a la clave
# del juez, que solo había pagado una ejecución conocida. Ver HALLAZGOS.md §21.
PRECIOS = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
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
    # Acumulador hijo, por hilo, para atribuir coste a UNA consulta. Ver
    # `por_consulta`. Es local al hilo y no al objeto porque el banco ejecuta
    # varios casos a la vez sobre el mismo `Sistema`: con un atributo normal,
    # el coste de una consulta se mezclaria con el de la de al lado.
    _local: threading.local = field(default_factory=threading.local, repr=False, compare=False)

    @contextmanager
    def por_consulta(self):
        """Acumula aparte lo que se gaste dentro del bloque, sin dejar de sumarlo al total.

        Hace falta porque el acumulador global responde "cuanto ha costado esta
        ejecucion" y la observabilidad en produccion necesita "cuanto ha costado
        esta consulta". Restar dos instantaneas del total seria mas corto y
        estaria mal: con varias consultas en vuelo, la resta atribuye a una lo
        que gasto otra.
        """
        hijo = Uso()
        anterior = getattr(self._local, "hijo", None)
        self._local.hijo = hijo
        try:
            yield hijo
        finally:
            self._local.hijo = anterior

    def registrar(self, modelo: str, entrada: int, salida: int) -> None:
        hijo = getattr(self._local, "hijo", None)
        if hijo is not None:
            # El hijo tiene su propio `_local`, vacio, asi que aqui se para.
            hijo.registrar(modelo, entrada, salida)
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


# Vueltas máximas del bucle de herramientas. Cuatro dan margen para encadenar
# (buscar, luego detallar) sin permitir que una consulta se vaya de coste si el
# modelo entra en bucle. Al agotarse se marca en la traza: nunca se corta en
# silencio, porque una respuesta incompleta que parece completa es peor que un
# error.
MAX_VUELTAS_HERRAMIENTAS = 4


class ChatProvider:
    def __init__(self) -> None:
        self.uso = Uso()

    def completar(
        self, system: str, user: str, model: str, max_tokens: int = MAX_TOKENS_SUT
    ) -> str:
        raise NotImplementedError

    def completar_con_herramientas(
        self,
        system: str,
        user: str,
        model: str,
        herramientas: list[dict],
        ejecutar,
        max_vueltas: int = MAX_VUELTAS_HERRAMIENTAS,
        max_tokens: int = MAX_TOKENS_SUT,
    ) -> tuple[str, list[dict]]:
        """Conversación con tool-calling. Devuelve el texto final y la traza de llamadas."""
        raise NotImplementedError(
            f"{type(self).__name__} no implementa tool-calling. La rama estructurada "
            "requiere un proveedor que lo soporte."
        )


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

    def completar_con_herramientas(
        self,
        system: str,
        user: str,
        model: str,
        herramientas: list[dict],
        ejecutar,
        max_vueltas: int = MAX_VUELTAS_HERRAMIENTAS,
        max_tokens: int = MAX_TOKENS_SUT,
    ) -> tuple[str, list[dict]]:
        """Bucle de tool-calling nativo del SDK.

        El modelo decide qué herramienta invocar; el programa la ejecuta y le
        devuelve el resultado. Esa inversión de control es lo que separa un
        agente de una cadena de llamadas, y es el mismo patrón de la entrega 2.1,
        ahora con las herramientas viniendo de un servidor MCP en vez de estar
        cableadas.
        """
        mensajes: list[dict] = [{"role": "user", "content": user}]
        traza: list[dict] = []

        for vuelta in range(max_vueltas):
            resp = con_reintentos(
                lambda: self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=mensajes,
                    tools=herramientas,
                ),
                f"anthropic:{model}:tools",
            )
            self.uso.registrar(model, resp.usage.input_tokens, resp.usage.output_tokens)

            if resp.stop_reason != "tool_use":
                texto = "".join(b.text for b in resp.content if b.type == "text")
                return texto, traza

            mensajes.append({"role": "assistant", "content": resp.content})
            resultados = []
            for bloque in resp.content:
                if bloque.type != "tool_use":
                    continue
                try:
                    salida = ejecutar(bloque.name, bloque.input or {})
                    error = False
                except Exception as fallo:  # noqa: BLE001 - se devuelve al modelo, no se traga
                    salida = f"La herramienta falló: {type(fallo).__name__}: {fallo}"
                    error = True
                traza.append({
                    "vuelta": vuelta + 1,
                    "herramienta": bloque.name,
                    "argumentos": bloque.input or {},
                    "error": error,
                    "caracteres_resultado": len(salida),
                })
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": salida,
                    "is_error": error,
                })
            mensajes.append({"role": "user", "content": resultados})

        # Se agotaron las vueltas con el modelo todavía pidiendo herramientas.
        traza.append({"limite_vueltas_alcanzado": True, "vueltas": max_vueltas})
        return "", traza


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
