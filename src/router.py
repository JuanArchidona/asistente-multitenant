"""Enrutador: clasifica la consulta del usuario en una categoría del inquilino.

Es el "primer modelo enrutador" del enunciado 2.3. Usa un modelo ligero (Haiku)
y devuelve una salida estructurada validada con Pydantic. La categoría determina
a qué fuente del corpus se dirigirá la recuperación.

Cambio de la 3.3: el fallback por fallo de parseo queda **marcado**. En la 3.1
un JSON malformado se convertía en `otro` con confianza 0.0, indistinguible de
una clasificación legítima de `otro`; un fallo de formato se contabilizaba como
acierto o error de clasificación según el caso, y nadie se enteraba. Ahora
`Enrutamiento.fallback` lo delata y la métrica de enrutado lo reporta aparte:
es la diferencia entre "el modelo cree que no encaja" y "el modelo se rompió".

Cambio de este proyecto: el prompt deja de ser una constante y se construye a
partir de las categorías que declara el inquilino. Para que la línea base siga
siendo comparable, la plantilla reproduce **carácter a carácter** el prompt de la
3.1 cuando el inquilino es la empresa de servicios; hay un test que lo comprueba,
porque un cambio accidental de prompt invalidaría en silencio las métricas de
enrutado de los 109 casos.
"""
import json

from pydantic import ValidationError

from .config import Config
from .provider import ChatProvider
from .schema import Enrutamiento
from .tenant import CATEGORIA_OTRO, Tenant

_PLANTILLA_ROUTER = """Eres un enrutador de consultas para {contexto}.
Clasifica la consulta del usuario en UNA de estas categorías:

{categorias}
- {otro}: no encaja en ninguna fuente interna anterior.

Responde SOLO con un objeto JSON válido, sin texto adicional ni markdown, con esta forma:
{{"categoria": "<una de las categorías>", "justificacion": "<breve>", "confianza": <0.0-1.0>}}"""


def system_router(tenant: Tenant) -> str:
    """Prompt del enrutador para este inquilino."""
    lineas = "\n".join(f"- {c.nombre}: {c.descripcion}" for c in tenant.categorias)
    return _PLANTILLA_ROUTER.format(
        contexto=tenant.contexto_enrutador, categorias=lineas, otro=CATEGORIA_OTRO
    )


def _fallback(motivo: str) -> Enrutamiento:
    """Clasificación de emergencia, siempre marcada.

    Se usa tanto si el JSON no parsea como si la categoría no existe en el
    inquilino: en los dos casos el modelo ha fallado, y meterlos en el mismo
    cajón que un `otro` legítimo es lo que la 3.3 vino a arreglar.
    """
    return Enrutamiento(
        categoria=CATEGORIA_OTRO, justificacion=motivo, confianza=0.0, fallback=True
    )


def enrutar(cfg: Config, chat: ChatProvider, consulta: str) -> Enrutamiento:
    raw = chat.completar(system_router(cfg.tenant), consulta, cfg.model_router).strip()

    # Robustez: quitar fences de markdown si el modelo los añade.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    raw = raw[: raw.rfind("}") + 1]

    try:
        ruta = Enrutamiento.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        return _fallback("No se pudo parsear la respuesta del enrutador.")

    if ruta.categoria not in cfg.tenant.categorias_validas:
        return _fallback(
            f"El enrutador devolvió una categoría inexistente para el inquilino "
            f"{cfg.tenant.id!r}: {ruta.categoria!r}."
        )
    return ruta
