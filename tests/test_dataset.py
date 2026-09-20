"""Coherencia de los bancos de pruebas contra los corpus reales.

Estas pruebas vigilan el banco, no el sistema. Un golden set se degrada en
silencio: se renombra un fichero del corpus y media docena de casos empiezan a
esperar un documento que ya no existe, con lo que la métrica de recuperación cae
y parece un problema del RAG. Ejecutar esto en CI convierte esa clase de fallo
en un test rojo con nombre y apellidos.

Desde la reforma multi-tenant, todo lo de aquí se ejecuta **por cada inquilino
que tenga banco**. Un banco nuevo entra en CI por el hecho de existir, sin que
nadie tenga que acordarse de añadirlo.
"""
from pathlib import Path

import pytest

from evals.dataset import (
    GOLDEN_CONSULTAS,
    GOLDEN_TRANSCRIPCION,
    cargar_consultas,
    cargar_transcripciones,
    ruta_golden,
    tenants_con_banco,
)
from evals.schema import Comportamiento, Dimension
from src.tenant import cargar_tenant

RAIZ = Path(__file__).resolve().parents[1]

# El inquilino de las entregas anteriores. Su banco es la línea base contra la
# que se comparan los cambios del sistema, así que no puede encoger.
TENANT_HEREDADO = "empresa_servicios"
CASOS_HEREDADOS_MINIMOS = 52

# Suelo para cualquier banco. Por debajo de esto, la diferencia entre dos
# configuraciones se confunde con el ruido de muestreo.
MINIMO_POR_BANCO = 25

BANCOS = tenants_con_banco()
CASOS = {t: cargar_consultas(ruta_golden(t, GOLDEN_CONSULTAS)) for t in BANCOS}
TENANTS = {t: cargar_tenant(t, raiz=RAIZ / "tenants") for t in BANCOS}
ARCHIVOS_CORPUS = {t: {p.name for p in (RAIZ / "corpus" / t).rglob("*.md")} for t in BANCOS}

PARES = [(t, caso) for t in BANCOS for caso in CASOS[t]]


def _id(par) -> str:
    tenant, caso = par
    return f"{tenant}:{caso.id}"


# --- Invariantes de cada banco ---

def test_hay_al_menos_un_banco():
    assert BANCOS, "sin ningún golden set no hay nada que medir"


@pytest.mark.parametrize("tenant", BANCOS)
def test_el_banco_tiene_masa_critica(tenant):
    assert len(CASOS[tenant]) >= MINIMO_POR_BANCO


def test_el_banco_heredado_no_ha_encogido():
    """Su tamaño es parte de la línea base: perder casos invalida la comparación."""
    assert len(CASOS[TENANT_HEREDADO]) >= CASOS_HEREDADOS_MINIMOS


@pytest.mark.parametrize("tenant", BANCOS)
def test_ids_unicos(tenant):
    ids = [c.id for c in CASOS[tenant]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("tenant", BANCOS)
def test_todas_las_dimensiones_estan_cubiertas(tenant):
    """Si una dimensión se queda sin casos, ese riesgo deja de medirse."""
    presentes = {c.dimension for c in CASOS[tenant]}
    assert presentes == set(Dimension), f"sin cubrir: {set(Dimension) - presentes}"


@pytest.mark.parametrize("tenant", BANCOS)
def test_todas_las_categorias_del_enrutador_estan_cubiertas(tenant):
    presentes = {c.categoria_esperada for c in CASOS[tenant]}
    assert presentes == TENANTS[tenant].categorias_validas


@pytest.mark.parametrize("tenant", BANCOS)
def test_hay_casos_negativos_suficientes(tenant):
    """Los positivos miden capacidad; los negativos, alucinación y fugas."""
    negativos = [
        c for c in CASOS[tenant]
        if c.comportamiento_esperado in (Comportamiento.abstenerse, Comportamiento.denegar)
    ]
    assert len(negativos) >= 8


# --- Invariantes de cada caso ---

@pytest.mark.parametrize("par", PARES, ids=_id)
def test_categoria_valida(par):
    tenant, caso = par
    assert caso.categoria_esperada in TENANTS[tenant].categorias_validas


@pytest.mark.parametrize("par", PARES, ids=_id)
def test_los_ficheros_esperados_existen_en_el_corpus(par):
    tenant, caso = par
    for archivo in caso.archivos_esperados:
        assert archivo in ARCHIVOS_CORPUS[tenant], (
            f"{caso.id} espera un fichero que no existe en el corpus de {tenant}"
        )


@pytest.mark.parametrize("par", PARES, ids=_id)
def test_los_literales_exigidos_estan_en_el_corpus(par):
    """Un `debe_contener` que no aparece en el corpus exige inventar el dato."""
    tenant, caso = par
    if not caso.debe_contener or not caso.archivos_esperados:
        return
    from evals.metrics.deterministas import normalizar

    fuentes = " ".join(
        normalizar(p.read_text(encoding="utf-8"))
        for p in (RAIZ / "corpus" / tenant).rglob("*.md")
        if p.name in caso.archivos_esperados
    )
    for literal in caso.debe_contener:
        assert normalizar(literal) in fuentes, (
            f"{caso.id}: '{literal}' no aparece en {caso.archivos_esperados}"
        )


@pytest.mark.parametrize("par", PARES, ids=_id)
def test_coherencia_entre_comportamiento_y_expectativas(par):
    _, caso = par
    if caso.comportamiento_esperado is Comportamiento.abstenerse:
        assert not caso.debe_contener, "un caso de abstención no puede exigir un dato"
        assert not caso.archivos_esperados, "abstenerse implica no esperar recuperación"
    if caso.comportamiento_esperado is Comportamiento.denegar:
        assert caso.no_debe_contener, "una denegación debe declarar qué no puede filtrarse"


@pytest.mark.parametrize("par", PARES, ids=_id)
def test_toda_respuesta_esperada_esta_redactada(par):
    _, caso = par
    assert len(caso.respuesta_esperada) > 20, "la referencia del juez no puede ser un esbozo"


# --- Transcripción (flujo 2.1, propio del inquilino heredado) ---

def test_el_dataset_de_transcripcion_carga():
    casos = cargar_transcripciones(ruta_golden(TENANT_HEREDADO, GOLDEN_TRANSCRIPCION))
    assert len(casos) >= 5
    assert any(c.fecha_esperada is None for c in casos), (
        "hace falta un caso sin fecha para comprobar que el agente no la inventa"
    )
