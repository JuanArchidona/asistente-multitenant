"""Coherencia del banco de pruebas contra el corpus real.

Estas pruebas vigilan el banco, no el sistema. Un golden set se degrada en
silencio: se renombra un fichero del corpus y media docena de casos empiezan a
esperar un documento que ya no existe, con lo que la métrica de recuperación cae
y parece un problema del RAG. Ejecutar esto en CI convierte esa clase de fallo
en un test rojo con nombre y apellidos.
"""
from pathlib import Path

import pytest

from evals.dataset import RAIZ_DATASETS, cargar_consultas, cargar_transcripciones
from evals.schema import Comportamiento, Dimension
from src.tenant import cargar_tenant

RAIZ = Path(__file__).resolve().parents[1]
TENANT = cargar_tenant("empresa_servicios", raiz=RAIZ / "tenants")
CORPUS = RAIZ / "corpus" / TENANT.id

CASOS = cargar_consultas(RAIZ_DATASETS / "golden_consultas.jsonl")
ARCHIVOS_CORPUS = {p.name for p in CORPUS.rglob("*.md")}


def test_el_golden_set_tiene_masa_critica():
    assert len(CASOS) >= 40, "un banco pequeño no distingue una mejora del ruido"


def test_ids_unicos():
    ids = [c.id for c in CASOS]
    assert len(ids) == len(set(ids))


def test_todas_las_dimensiones_estan_cubiertas():
    """Si una dimensión se queda sin casos, ese riesgo deja de medirse."""
    presentes = {c.dimension for c in CASOS}
    assert presentes == set(Dimension), f"sin cubrir: {set(Dimension) - presentes}"


def test_todas_las_categorias_del_enrutador_estan_cubiertas():
    presentes = {c.categoria_esperada for c in CASOS}
    assert presentes == TENANT.categorias_validas


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_categoria_valida(caso):
    assert caso.categoria_esperada in TENANT.categorias_validas


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_los_ficheros_esperados_existen_en_el_corpus(caso):
    for archivo in caso.archivos_esperados:
        assert archivo in ARCHIVOS_CORPUS, f"{caso.id} espera un fichero inexistente"


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_los_literales_exigidos_estan_en_el_corpus(caso):
    """Un `debe_contener` que no aparece en el corpus exige inventar el dato."""
    if not caso.debe_contener or not caso.archivos_esperados:
        return
    from evals.metrics.deterministas import normalizar

    fuentes = " ".join(
        normalizar(p.read_text(encoding="utf-8"))
        for p in CORPUS.rglob("*.md")
        if p.name in caso.archivos_esperados
    )
    for literal in caso.debe_contener:
        assert normalizar(literal) in fuentes, (
            f"{caso.id}: '{literal}' no aparece en {caso.archivos_esperados}"
        )


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_coherencia_entre_comportamiento_y_expectativas(caso):
    if caso.comportamiento_esperado is Comportamiento.abstenerse:
        assert not caso.debe_contener, "un caso de abstención no puede exigir un dato"
        assert not caso.archivos_esperados, "abstenerse implica no esperar recuperación"
    if caso.comportamiento_esperado is Comportamiento.denegar:
        assert caso.no_debe_contener, "una denegación debe declarar qué no puede filtrarse"


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_toda_respuesta_esperada_esta_redactada(caso):
    assert len(caso.respuesta_esperada) > 20, "la referencia del juez no puede ser un esbozo"


def test_hay_casos_negativos_suficientes():
    """Los positivos miden capacidad; los negativos, alucinación y fugas."""
    negativos = [
        c for c in CASOS
        if c.comportamiento_esperado in (Comportamiento.abstenerse, Comportamiento.denegar)
    ]
    assert len(negativos) >= 10


def test_el_dataset_de_transcripcion_carga():
    casos = cargar_transcripciones(RAIZ_DATASETS / "golden_transcripcion.jsonl")
    assert len(casos) >= 5
    assert any(c.fecha_esperada is None for c in casos), (
        "hace falta un caso sin fecha para comprobar que el agente no la inventa"
    )
