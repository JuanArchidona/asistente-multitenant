"""Carga y validación de los datasets del banco.

JSONL y no CSV ni YAML por dos motivos prácticos: cada línea es un caso
independiente (un `git diff` sobre el fichero muestra exactamente qué caso se
añadió o cambió) y el generador sintético puede ir escribiendo casos según los
valida, sin reescribir el fichero entero.
"""
import json
from pathlib import Path

from pydantic import ValidationError

from .schema import CasoConsulta, CasoTranscripcion

RAIZ_DATASETS = Path(__file__).parent / "datasets"


def _leer_jsonl(ruta: Path) -> list[dict]:
    filas = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
        linea = linea.strip()
        if not linea or linea.startswith("//"):
            continue
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError as e:
            raise ValueError(f"{ruta.name}:{n} no es JSON válido: {e}") from e
    return filas


def cargar_consultas(ruta: str | Path) -> list[CasoConsulta]:
    ruta = Path(ruta)
    casos, ids = [], set()
    for fila in _leer_jsonl(ruta):
        try:
            caso = CasoConsulta.model_validate(fila)
        except ValidationError as e:
            raise ValueError(f"Caso inválido en {ruta.name} ({fila.get('id')}): {e}") from e
        if caso.id in ids:
            raise ValueError(f"ID duplicado en {ruta.name}: {caso.id}")
        ids.add(caso.id)
        casos.append(caso)
    return casos


def cargar_transcripciones(ruta: str | Path) -> list[CasoTranscripcion]:
    ruta = Path(ruta)
    casos, ids = [], set()
    for fila in _leer_jsonl(ruta):
        caso = CasoTranscripcion.model_validate(fila)
        if caso.id in ids:
            raise ValueError(f"ID duplicado en {ruta.name}: {caso.id}")
        ids.add(caso.id)
        casos.append(caso)
    return casos


def escribir_jsonl(ruta: str | Path, objetos: list) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for o in objetos:
            datos = o.model_dump(mode="json") if hasattr(o, "model_dump") else o
            f.write(json.dumps(datos, ensure_ascii=False) + "\n")
