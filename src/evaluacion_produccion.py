"""Evaluación de la calidad en producción sin guardar la respuesta (PLAN_ENTREGA B4).

El enunciado del TFM pide saber "cómo están yendo en producción", y el tutor
concretó: LLM como juez sobre muestras aleatorias de las conversaciones reales.
El registro de producción no guarda la respuesta, a propósito (RETENCION.md),
así que no se puede juzgar después. Se juzga **al servir**, en memoria, y al
registro solo van números y veredictos:

- **Sobre el 100 %, determinista**: el verificador de citas del banco
  (`src/citas.py`, §23). Cuántos ficheros cita la respuesta, cuántos de ellos
  no estaban en lo recuperado (citas inventadas) y si cita alguna fuente. No
  cuesta nada y no varía entre pasadas.
- **Sobre una fracción aleatoria, el juez**: `EVAL_PRODUCCION_FRACCION` (0 lo
  apaga). Un modelo de otra familia que el generador (Gemini por defecto, con
  su clave propia, `GEMINI_API_KEY_JUEZ`) decide si lo que afirma la respuesta
  está respaldado por el contexto que recibió el generador. Corre en un hilo
  aparte para no sumar latencia, y deja una línea `_evaluacion` enlazada a la
  consulta por su `id_consulta`, con el veredicto, la latencia y el coste,
  separado del coste del sistema.

Lo que el juez **no** deja en el registro es su razonamiento: podría repetir
datos de la respuesta, que es justo lo que no se guarda. El precio es que un
veredicto no se puede leer con su razón, y el §30 dice que una puntuación de
juez no se lee sin ella; por eso se pide un veredicto de tres valores y no un
número, y por eso ninguna decisión cuelga de él: es una señal para mirar, y lo
determinista es lo que se cuenta. Mandar la consulta, el contexto y la
respuesta a Gemini es una transferencia a otro encargado, aceptada por el
autor el 11-10-2026 y registrada en R-18.

Nada de fallbacks silenciosos: si la fracción es mayor que cero y falta la
clave, cada línea lo dice (`juez: "sin_clave"`) en vez de aparentar que el
juez no tocó esa consulta por azar.
"""
import json
import os
import random
import secrets
import threading
import time
from dataclasses import dataclass, replace

from .citas import citables, citas_de_fichero, menciona_alguna_fuente
from .config import Config

VEREDICTOS = ("fiel", "parcial", "no_fiel")

SYSTEM_JUEZ_PRODUCCION = """Eres un evaluador de un asistente interno de empresa. Recibes la
consulta de un empleado, el contexto que recibió el asistente (fragmentos de
documentos o resultados de herramientas) y la respuesta que dio.

Decide si lo que AFIRMA la respuesta está respaldado por el contexto:
- "fiel": todo lo que afirma sale del contexto, o la respuesta dice con
  claridad que el contexto no contiene la información.
- "parcial": casi todo sale del contexto, pero añade algún detalle que no está.
- "no_fiel": afirma datos importantes que el contexto no contiene o contradice.

Ignora el estilo y la extensión. Responde SOLO con un objeto JSON:
{"veredicto": "fiel" | "parcial" | "no_fiel"}"""


def nuevo_id() -> str:
    return secrets.token_hex(6)


def calidad_determinista(traza: dict) -> dict | None:
    """Citas de la respuesta contra lo recuperado. None si no había nada que citar."""
    archivos, herramientas = citables(traza)
    if not archivos and not herramientas:
        return None
    respuesta = traza.get("respuesta") or ""
    citadas = citas_de_fichero(respuesta)
    return {
        "citas_fichero": len(citadas),
        "citas_inventadas": sum(1 for c in citadas if c not in archivos),
        "cita_alguna_fuente": menciona_alguna_fuente(respuesta, archivos, herramientas),
    }


@dataclass
class JuezProduccion:
    """Juez muestreado. `chat` es un ChatProvider con la clave del juez."""

    chat: object | None
    modelo: str
    fraccion: float
    azar: random.Random

    def estado(self) -> str:
        if self.fraccion <= 0:
            return "apagado"
        return "activo" if self.chat is not None else "sin_clave"

    def toca(self) -> bool:
        return self.estado() == "activo" and self.azar.random() < self.fraccion

    def juzgar(self, traza: dict) -> dict:
        contexto = traza.get("contexto_recuperado") or []
        if not contexto:
            return {"veredicto": "no_aplica", "motivo": "sin contexto"}
        usuario = json.dumps(
            {
                "consulta": traza.get("consulta"),
                "contexto": contexto,
                "respuesta": traza.get("respuesta"),
            },
            ensure_ascii=False,
        )
        t0 = time.perf_counter()
        with self.chat.uso.por_consulta() as uso:
            bruto = self.chat.completar(
                SYSTEM_JUEZ_PRODUCCION, usuario, self.modelo, max_tokens=64, temperature=0.0
            )
        resultado = {
            "veredicto": _veredicto(bruto),
            "latencia_s": round(time.perf_counter() - t0, 3),
            "modelo": self.modelo,
        }
        resumen = uso.resumen()
        resultado["coste_usd"] = resumen.get("coste_usd_estimado")
        resultado["tokens_entrada"] = resumen.get("tokens_entrada")
        return resultado


def _veredicto(bruto: str) -> str:
    texto = (bruto or "").strip().strip("`")
    texto = texto[texto.find("{"): texto.rfind("}") + 1]
    try:
        valor = json.loads(texto).get("veredicto")
    except (json.JSONDecodeError, AttributeError):
        return "ilegible"
    return valor if valor in VEREDICTOS else "ilegible"


def juez_desde_config(cfg: Config, chat_factory=None) -> JuezProduccion:
    """El juez de producción según el entorno.

    `chat_factory(cfg)` crea el chat; por defecto, el de Gemini con la clave
    del juez (otra familia que el generador, como en el banco desde §32).
    """
    fraccion = float(os.getenv("EVAL_PRODUCCION_FRACCION", "0") or 0)
    semilla = os.getenv("EVAL_PRODUCCION_SEMILLA")
    azar = random.Random(int(semilla)) if semilla else random.Random()
    chat = None
    if fraccion > 0 and cfg.judge_gemini_api_key:
        if chat_factory is None:
            from .provider import GeminiChat

            def chat_factory(c):
                return GeminiChat(replace(c, gemini_api_key=c.judge_gemini_api_key))

        chat = chat_factory(cfg)
    return JuezProduccion(chat=chat, modelo=cfg.judge_model, fraccion=fraccion, azar=azar)


def lanzar(juez: JuezProduccion, traza: dict, registro, id_consulta: str) -> threading.Thread:
    """Juzga en un hilo aparte y anota el resultado. Nunca lanza al llamador."""

    def _trabajo():
        try:
            resultado = juez.juzgar(traza)
        except Exception as error:  # noqa: BLE001 -- un juez caído no tumba una consulta servida
            resultado = {"veredicto": "error", "error": type(error).__name__}
        registro.anotar_evaluacion(id_consulta, resultado)

    hilo = threading.Thread(target=_trabajo, name=f"juez-{id_consulta}", daemon=True)
    hilo.start()
    return hilo
