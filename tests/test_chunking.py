"""Pruebas de las dos estrategias de chunking.

El chunking es el parámetro que el barrido compara, así que un fallo aquí
invalida el experimento entero: si el chunker por encabezados estuviera roto,
el barrido concluiría que "por caracteres es mejor" cuando lo que ocurre es que
la alternativa no funciona.
"""
from src.ingest import trocear

DOCUMENTO = """# Convenio Colectivo

## Vacaciones
El personal dispone de 23 días laborables de vacaciones por año completo.

## Teletrabajo
Se permite teletrabajo hasta 3 días por semana, previa aprobación.
"""


def test_chars_respeta_el_tamano_maximo(cfg_factory):
    cfg = cfg_factory(chunk_strategy="chars", chunk_size=50, chunk_overlap=10)
    chunks = trocear(DOCUMENTO, cfg)
    assert all(len(c) <= 50 for c in chunks)
    assert len(chunks) > 1


def test_chars_aplica_solape(cfg_factory):
    cfg = cfg_factory(chunk_strategy="chars", chunk_size=50, chunk_overlap=10)
    chunks = trocear(DOCUMENTO, cfg)
    # El final de un fragmento debe reaparecer al principio del siguiente.
    assert chunks[0][-10:] == chunks[1][:10]


def test_documento_corto_no_se_trocea(cfg_factory):
    cfg = cfg_factory(chunk_strategy="chars", chunk_size=10_000)
    assert trocear(DOCUMENTO, cfg) == [DOCUMENTO.strip()]


def test_headings_separa_por_seccion(cfg_factory):
    cfg = cfg_factory(chunk_strategy="headings", chunk_size=800, chunk_overlap=100)
    chunks = trocear(DOCUMENTO, cfg)
    vacaciones = [c for c in chunks if "23 días" in c]
    teletrabajo = [c for c in chunks if "3 días por semana" in c]
    assert len(vacaciones) == 1
    assert len(teletrabajo) == 1
    # La clave del chunking estructural: cada dato viaja con su encabezado y no
    # con el de la sección vecina.
    assert "Vacaciones" in vacaciones[0]
    assert "Teletrabajo" not in vacaciones[0]


def test_headings_arrastra_el_titulo_del_documento(cfg_factory):
    """Un fragmento suelto debe seguir diciendo de qué documento sale."""
    cfg = cfg_factory(chunk_strategy="headings", chunk_size=800, chunk_overlap=100)
    chunks = trocear(DOCUMENTO, cfg)
    secciones = [c for c in chunks if c.startswith("[")]
    assert secciones, "las secciones posteriores al título deben llevar prefijo"
    assert all(c.startswith("[Convenio Colectivo]") for c in secciones)


def test_headings_subdivide_secciones_largas(cfg_factory):
    largo = "# Doc\n\n## Seccion\n" + ("palabra " * 500)
    cfg = cfg_factory(chunk_strategy="headings", chunk_size=200, chunk_overlap=20)
    chunks = trocear(largo, cfg)
    assert all(len(c) <= 200 for c in chunks)


def test_headings_sin_encabezados_cae_a_caracteres(cfg_factory):
    texto = "Texto plano sin ningun encabezado markdown. " * 40
    cfg = cfg_factory(chunk_strategy="headings", chunk_size=100, chunk_overlap=10)
    chunks = trocear(texto, cfg)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
