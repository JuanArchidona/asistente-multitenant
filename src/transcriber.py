"""Transcripcion de PDFs a actas del corpus (flujo del Modulo 2.1 adaptado).

En la 2.1 el agente estructuraba el PDF y lo guardaba en SQLite via tool-calling.
Aqui el destino es el corpus del RAG (continuidad 2.1 -> 2.3): el PDF con la
transcripcion de una reunion se estructura con salida JSON validada por Pydantic
y se persiste como acta markdown en corpus/actas/, lista para re-ingestar y
consultar desde el asistente.
"""
import json
import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader

from .config import Config
from .provider import ChatProvider

SYSTEM_TRANSCRIPTOR = """Eres un agente de transcripcion documental. Recibes el texto plano
extraido de un PDF con la transcripcion de una reunion y debes estructurarlo fielmente
como acta.

Reglas:
- No inventes datos. Si un campo no aparece, dejalo vacio o nulo.
- 'confianza' refleja tu certeza real sobre la extraccion global.

Responde SOLO con un objeto JSON valido, sin texto adicional ni markdown, con esta forma:
{"titulo": "<asunto de la reunion>", "fecha": "YYYY-MM-DD o null", "asistentes": ["..."],
 "resumen": "<2-4 frases>", "decisiones": ["..."], "tareas": ["..."], "confianza": 0.0}"""


class Acta(BaseModel):
    """Salida estructurada de la transcripcion (heredera del RegistroTranscripcion 2.1)."""

    titulo: str = Field(description="Asunto principal de la reunion")
    fecha: str | None = Field(default=None, description="Fecha ISO YYYY-MM-DD si existe")
    asistentes: list[str] = Field(default_factory=list, description="Personas presentes")
    resumen: str = Field(description="Resumen del contenido en 2-4 frases")
    decisiones: list[str] = Field(default_factory=list, description="Decisiones tomadas")
    tareas: list[str] = Field(default_factory=list, description="Tareas o acciones acordadas")
    confianza: float = Field(ge=0.0, le=1.0, description="Confianza en la extraccion (0-1)")


def extraer_texto_pdf(archivo) -> str:
    """Extrae el texto de un PDF (ruta o file-like, p. ej. el uploader de Streamlit)."""
    reader = PdfReader(archivo)
    partes = [page.extract_text() or "" for page in reader.pages]
    texto = "\n\n".join(partes).strip()
    if not texto:
        raise ValueError(
            "No se extrajo texto del PDF. Este flujo asume PDF con capa de texto, "
            "no escaneado."
        )
    return texto


def transcribir(cfg: Config, chat: ChatProvider, texto: str) -> Acta:
    """Estructura el texto plano en un Acta validada (mismo patron que el router 2.3)."""
    user = (
        "Transcribe y estructura el siguiente documento como acta de reunion.\n\n"
        f"=== TEXTO DEL PDF ===\n{texto}"
    )
    raw = chat.completar(SYSTEM_TRANSCRIPTOR, user, cfg.model_generator).strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    raw = raw[: raw.rfind("}") + 1]

    return Acta.model_validate(json.loads(raw))


def _slug(texto: str, max_len: int = 40) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")
    return limpio[:max_len] or "sin_titulo"


def acta_a_markdown(acta: Acta) -> str:
    lineas = [f"# Acta: {acta.titulo}", ""]
    if acta.fecha:
        lineas.append(f"**Fecha:** {acta.fecha}")
    if acta.asistentes:
        lineas.append(f"**Asistentes:** {', '.join(acta.asistentes)}")
    lineas += ["", "## Resumen", "", acta.resumen]
    if acta.decisiones:
        lineas += ["", "## Decisiones", ""] + [f"- {d}" for d in acta.decisiones]
    if acta.tareas:
        lineas += ["", "## Tareas", ""] + [f"- {t}" for t in acta.tareas]
    return "\n".join(lineas) + "\n"


def guardar_acta(cfg: Config, acta: Acta) -> Path:
    """Persiste el acta como markdown en corpus/actas/ (la fuente que consume el RAG)."""
    destino = Path(cfg.corpus_path) / "actas"
    destino.mkdir(parents=True, exist_ok=True)
    fecha = acta.fecha or "sin_fecha"
    ruta = destino / f"acta_{_slug(acta.titulo)}_{fecha}.md"
    ruta.write_text(acta_a_markdown(acta), encoding="utf-8")
    return ruta
