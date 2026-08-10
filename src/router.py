"""Enrutador: clasifica la consulta del usuario en una categoría fija.

Es el "primer modelo enrutador" del enunciado 2.3. Usa un modelo ligero (Haiku)
y devuelve una salida estructurada validada con Pydantic. La categoría determina
a qué fuente del corpus se dirigirá la recuperación.

Cambio de la 3.3: el fallback por fallo de parseo queda **marcado**. En la 3.1
un JSON malformado se convertía en `otro` con confianza 0.0, indistinguible de
una clasificación legítima de `otro`; un fallo de formato se contabilizaba como
acierto o error de clasificación según el caso, y nadie se enteraba. Ahora
`Enrutamiento.fallback` lo delata y la métrica de enrutado lo reporta aparte:
es la diferencia entre "el modelo cree que no encaja" y "el modelo se rompió".
"""
import json

from pydantic import ValidationError

from .config import Config
from .provider import ChatProvider
from .schema import Categoria, Enrutamiento

SYSTEM_ROUTER = """Eres un enrutador de consultas para el asistente interno de una empresa.
Clasifica la consulta del usuario en UNA de estas categorías:

- rrhh: convenio colectivo, vacaciones, nóminas, políticas de personal, permisos.
- desarrollo: estándares de código, guías técnicas, buenas prácticas de ingeniería.
- actas: preguntas sobre decisiones, acuerdos o tareas de reuniones pasadas.
- marca: marketing, comunicación, identidad visual, tono de marca.
- otro: no encaja en ninguna fuente interna anterior.

Responde SOLO con un objeto JSON válido, sin texto adicional ni markdown, con esta forma:
{"categoria": "<una de las categorías>", "justificacion": "<breve>", "confianza": <0.0-1.0>}"""


def enrutar(cfg: Config, chat: ChatProvider, consulta: str) -> Enrutamiento:
    raw = chat.completar(SYSTEM_ROUTER, consulta, cfg.model_router).strip()

    # Robustez: quitar fences de markdown si el modelo los añade.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    raw = raw[: raw.rfind("}") + 1]

    try:
        data = json.loads(raw)
        return Enrutamiento.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        # Fallback seguro: si no parsea, tratamos como 'otro' con baja confianza,
        # pero dejando constancia (fallback=True) para poder medirlo.
        return Enrutamiento(
            categoria=Categoria.otro,
            justificacion="No se pudo parsear la respuesta del enrutador.",
            confianza=0.0,
            fallback=True,
        )
