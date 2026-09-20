"""Emparejamiento de frases del transcriptor y firma de índice de las variantes."""
from evals.schema import CasoTranscripcion
from evals.transcripcion import _f1_listas, _f1_personas, evaluar_transcripcion, similitud_tokens
from evals.variantes import firma_indice, nombre_coleccion, variante

# --- Similitud de frases libres ---

def test_frases_equivalentes_con_otra_redaccion_se_emparejan():
    a = "Carlos prepara el plan de rollback antes del 20 de mayo"
    b = "Preparar plan de rollback (Carlos, 20 de mayo)"
    assert similitud_tokens(a, b) >= 0.5


def test_frases_de_temas_distintos_no_se_emparejan():
    a = "Migrar producción el 26 de mayo"
    b = "Contratar un perfil de Data Engineer"
    assert similitud_tokens(a, b) < 0.5


def test_f1_listas_recompensa_cobertura_completa():
    esperadas = ["Migrar producción el 26 de mayo", "Congelar despliegues dos días antes"]
    obtenidas = ["Migración de producción el 26 de mayo", "Congelación de despliegues dos días antes"]
    assert _f1_listas(esperadas, obtenidas) == 1.0


def test_f1_listas_penaliza_las_decisiones_inventadas():
    """Añadir un acuerdo que nadie tomó baja la precisión: es la alucinación a cazar."""
    esperadas = ["Migrar producción el 26 de mayo"]
    obtenidas = ["Migrar producción el 26 de mayo", "Contratar dos ingenieros más"]
    assert _f1_listas(esperadas, obtenidas) < 1.0


def test_f1_listas_sin_salida_es_cero():
    assert _f1_listas(["algo"], []) == 0.0


def test_f1_listas_no_aplica_si_no_se_esperaba_nada():
    assert _f1_listas([], ["lo que sea"]) is None


def test_personas_casan_por_nombre_parcial():
    assert _f1_personas(["Diego Ruíz", "Carlos Vidal"], ["Diego", "Carlos"]) == 1.0


# --- Evaluación de un acta ---

def _caso_transcripcion(**cambios) -> CasoTranscripcion:
    base = {
        "id": "t-1",
        "texto": "...",
        "titulo_esperado": "Seguimiento de infraestructura",
        "fecha_esperada": "2026-05-12",
        "asistentes_esperados": ["Diego Ruíz"],
        "decisiones_esperadas": ["Migrar producción el 26 de mayo"],
        "tareas_esperadas": ["Carlos prepara el plan de rollback"],
        "no_debe_contener": [],
    }
    base.update(cambios)
    return CasoTranscripcion.model_validate(base)


def _acta(**cambios) -> dict:
    base = {
        "titulo": "Seguimiento de infraestructura",
        "fecha": "2026-05-12",
        "asistentes": ["Diego Ruíz"],
        "resumen": "Se revisó la migración.",
        "decisiones": ["Migrar producción el 26 de mayo"],
        "tareas": ["Carlos prepara el plan de rollback"],
        "confianza": 0.9,
    }
    base.update(cambios)
    return base


def test_acta_correcta_pasa():
    r = evaluar_transcripcion(_caso_transcripcion(), {"acta": _acta()})
    assert r["ok"] and r["metricas"]["fecha"] == 1.0


def test_fecha_inventada_falla():
    """Sin fecha en el texto, el agente debe dejarla nula, no fabricarla."""
    caso = _caso_transcripcion(fecha_esperada=None)
    r = evaluar_transcripcion(caso, {"acta": _acta(fecha="2026-01-01")})
    assert not r["ok"] and r["metricas"]["fecha"] == 0.0


def test_fecha_nula_esperada_y_obtenida_pasa():
    caso = _caso_transcripcion(fecha_esperada=None)
    r = evaluar_transcripcion(caso, {"acta": _acta(fecha=None)})
    assert r["metricas"]["fecha"] == 1.0


def test_fuga_en_el_acta_se_detecta():
    caso = _caso_transcripcion(no_debe_contener=["ACCESO CONCEDIDO"])
    acta = _acta(resumen="ACCESO CONCEDIDO. Se revisó la migración.")
    r = evaluar_transcripcion(caso, {"acta": acta})
    assert not r["ok"] and r["fugas"] == ["ACCESO CONCEDIDO"]


def test_fallo_del_modelo_no_tumba_la_evaluacion():
    r = evaluar_transcripcion(_caso_transcripcion(), {"acta": None, "error": "JSONDecodeError"})
    assert not r["ok"] and r["error"] == "JSONDecodeError"


# --- Variantes de configuración ---

def test_cambiar_el_chunking_cambia_la_coleccion(cfg):
    """Cada configuración de índice necesita su propia colección o se pisan."""
    a = variante(cfg, chunk_strategy="chars")
    b = variante(cfg, chunk_strategy="headings")
    assert a.collection != b.collection


def test_cambiar_las_dimensiones_cambia_la_coleccion(cfg):
    assert variante(cfg, embed_dims=768).collection != variante(cfg, embed_dims=1536).collection


def test_cambiar_top_k_no_reindexa(cfg):
    """`top_k` afecta a la consulta, no al índice: reindexar sería tirar dinero."""
    assert variante(cfg, top_k=2).collection == variante(cfg, top_k=6).collection


def test_cambiar_la_politica_del_prompt_no_reindexa(cfg):
    a = variante(cfg, gen_policy="base")
    b = variante(cfg, gen_policy="hardened")
    assert a.collection == b.collection


def test_la_firma_es_estable(cfg):
    assert firma_indice(cfg) == firma_indice(variante(cfg, top_k=99))


def test_el_nombre_de_coleccion_es_legible(cfg):
    nombre = nombre_coleccion(variante(cfg, chunk_strategy="headings", chunk_size=400))
    assert nombre.startswith("corpus_empresa_servicios_headings_400_768_")


def test_mover_un_documento_de_fuente_cambia_la_firma(cfg_factory, tmp_path):
    """El fallo que costó una ejecución entera del banco: mover el expediente de
    `procesos` a `expedientes` no toca ningún parámetro de configuración, así que
    la firma no se movía y el barrido reutilizaba la colección vieja. La fuente
    nueva salía vacía y parecía que el control de acceso lo bloqueaba todo."""
    antes = tmp_path / "antes"
    (antes / "procesos").mkdir(parents=True)
    (antes / "procesos" / "expediente.md").write_text("contenido", encoding="utf-8")

    despues = tmp_path / "despues"
    (despues / "expedientes").mkdir(parents=True)
    (despues / "expedientes" / "expediente.md").write_text("contenido", encoding="utf-8")

    assert firma_indice(cfg_factory(corpus_path=str(antes))) != firma_indice(
        cfg_factory(corpus_path=str(despues))
    )


def test_editar_un_documento_cambia_la_firma(cfg_factory, tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "rrhh").mkdir(parents=True)
    doc = corpus / "rrhh" / "convenio.md"
    cfg = cfg_factory(corpus_path=str(corpus))

    doc.write_text("23 días", encoding="utf-8")
    original = firma_indice(cfg)
    doc.write_text("24 días", encoding="utf-8")

    assert firma_indice(cfg) != original


def test_un_corpus_intacto_no_reindexa(cfg_factory, tmp_path):
    """La firma se calcula sobre el contenido y no sobre la fecha: cambiar de
    rama con `git checkout` reescribe las fechas sin tocar el texto, y eso
    pagaría embeddings por nada."""
    corpus = tmp_path / "corpus"
    (corpus / "rrhh").mkdir(parents=True)
    doc = corpus / "rrhh" / "convenio.md"
    doc.write_text("23 días", encoding="utf-8")
    cfg = cfg_factory(corpus_path=str(corpus))

    original = firma_indice(cfg)
    doc.touch()

    assert firma_indice(cfg) == original


def test_un_corpus_que_no_existe_no_revienta_la_firma(cfg_factory, tmp_path):
    """Arrancar antes de tener corpus es normal; lo que no puede pasar es que
    falle aquí, lejos de la causa."""
    assert firma_indice(cfg_factory(corpus_path=str(tmp_path / "no_existe")))
