"""El registro de riesgos no puede quedarse viejo sin que nadie lo note.

`docs/RIESGOS.md` es un documento, y los documentos derivan. Estas pruebas
son lo que impide que una fila cite un hallazgo que no existe o que una
casilla del OWASP Top 10 se quede sin fila. No juzgan el contenido: juzgan
que cada afirmación tenga su evidencia enganchada.
"""
import re
from pathlib import Path

import pytest

RIESGOS = Path("docs/RIESGOS.md").read_text(encoding="utf-8")
HALLAZGOS = Path("docs/HALLAZGOS.md").read_text(encoding="utf-8")

# Las filas del registro: empiezan por `| R-NN |`.
FILAS = [
    linea for linea in RIESGOS.splitlines() if re.match(r"^\| R-\d{2} \|", linea)
]

SECCIONES_HALLAZGOS = {
    int(m.group(1)) for m in re.finditer(r"^## (\d+)\. ", HALLAZGOS, flags=re.MULTILINE)
}


def _celdas(fila: str) -> list[str]:
    return [c.strip() for c in fila.strip().strip("|").split("|")]


def test_el_registro_tiene_filas():
    assert len(FILAS) >= 20


def test_los_identificadores_son_consecutivos_y_unicos():
    ids = [int(_celdas(f)[0][2:]) for f in FILAS]
    assert ids == list(range(1, len(ids) + 1)), ids


@pytest.mark.parametrize("fila", FILAS, ids=lambda f: _celdas(f)[0])
def test_cada_hallazgo_citado_existe(fila):
    """Una fila que cite `§40` cuando HALLAZGOS.md llega al §34 es una
    afirmación sin evidencia disfrazada de cita."""
    citados = {int(n) for n in re.findall(r"§(\d+)", fila)}
    inexistentes = sorted(citados - SECCIONES_HALLAZGOS)
    assert not inexistentes, f"{_celdas(fila)[0]} cita hallazgos inexistentes: {inexistentes}"


@pytest.mark.parametrize("fila", FILAS, ids=lambda f: _celdas(f)[0])
def test_cada_fila_tiene_cuadrante_evidencia_y_estado(fila):
    celdas = _celdas(fila)
    assert len(celdas) == 9, f"{celdas[0]}: {len(celdas)} columnas, se esperan 9"
    cuadrante, evidencia, estado = celdas[2], celdas[6], celdas[8]
    assert cuadrante in {"CC", "CD", "DC", "DD", "—"}, celdas[0]
    assert evidencia.strip("—").strip() or cuadrante == "—", f"{celdas[0]} sin evidencia"
    assert re.search(r"\*\*(Medido|Por construcción|Parcial|Hueco|Tensión abierta|No aplica)", estado), (
        f"{celdas[0]}: el estado no empieza por una etiqueta conocida"
    )


def test_las_diez_casillas_del_owasp_tienen_fila():
    cubiertas = set()
    for fila in FILAS:
        casilla = _celdas(fila)[3]
        cubiertas |= {int(n) for n in re.findall(r"\b(10|[1-9])\b", casilla)}
    assert cubiertas == set(range(1, 11)), sorted(set(range(1, 11)) - cubiertas)


def test_los_cuatro_cuadrantes_tienen_fila():
    cuadrantes = {_celdas(f)[2] for f in FILAS}
    assert {"CC", "CD", "DC", "DD"} <= cuadrantes


def test_la_vista_por_cuadrante_cita_todas_las_filas_con_cuadrante():
    """La tabla del §3 es un resumen del §2 y tiene que seguirlo."""
    vista = RIESGOS.split("## 3. Vista por cuadrante")[1].split("## 4.")[0]
    en_vista = set(re.findall(r"R-\d{2}", vista))
    con_cuadrante = {_celdas(f)[0] for f in FILAS if _celdas(f)[2] != "—"}
    assert con_cuadrante <= en_vista, sorted(con_cuadrante - en_vista)
