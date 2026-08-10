"""Pruebas de las métricas deterministas.

Una métrica con un bug no da error: da un número. El informe entero se apoya en
que estas funciones midan lo que dicen medir, así que se prueban con más cuidado
que el propio sistema evaluado.
"""
from evals.metrics.deterministas import (
    evaluar_contiene,
    evaluar_fuga_literal,
    evaluar_retrieval,
    evaluar_routing,
    normalizar,
)
from evals.schema import CasoConsulta


def _caso(**cambios) -> CasoConsulta:
    base = {
        "id": "t-1",
        "dimension": "conocimiento",
        "consulta": "¿Cuántos días de vacaciones?",
        "categoria_esperada": "rrhh",
        "archivos_esperados": ["convenio_colectivo.md"],
        "respuesta_esperada": "23 días laborables.",
        "debe_contener": ["23"],
    }
    base.update(cambios)
    return CasoConsulta.model_validate(base)


def _traza(**cambios) -> dict:
    base = {
        "consulta": "x",
        "categoria": "rrhh",
        "confianza_enrutador": 0.9,
        "fallback_enrutador": False,
        "fuentes_usadas": [{"archivo": "convenio_colectivo.md", "distancia": 0.2}],
        "contexto_recuperado": ["texto"],
        "respuesta": "Son 23 días laborables (convenio_colectivo.md).",
    }
    base.update(cambios)
    return base


# --- normalización ---

def test_normalizar_quita_acentos_y_mayusculas():
    assert normalizar("Días LABORABLES") == "dias laborables"


def test_normalizar_unifica_decimales():
    assert normalizar("38,5 horas") == normalizar("38.5 horas")


def test_normalizar_quita_separadores_de_millares():
    assert normalizar("318.100 €") == normalizar("318100 €")


def test_normalizar_no_toca_decimales_de_tres_cifras():
    """'3.11' es una versión, no 3110: el separador exige exactamente 3 dígitos."""
    assert "3.11" in normalizar("Python 3.11")


# --- enrutado ---

def test_routing_acierto():
    r = evaluar_routing(_caso(), _traza())
    assert r.valor == 1.0 and r.exito


def test_routing_fallo_registra_ambas_categorias():
    r = evaluar_routing(_caso(), _traza(categoria="marca"))
    assert r.valor == 0.0 and not r.exito
    assert r.detalle["esperada"] == "rrhh" and r.detalle["obtenida"] == "marca"


def test_routing_expone_el_fallback():
    r = evaluar_routing(_caso(categoria_esperada="otro"), _traza(categoria="otro", fallback_enrutador=True))
    # Acierta la categoría, pero la traza delata que fue un fallo de parseo.
    assert r.exito and r.detalle["fallback"] is True


# --- recuperación ---

def test_retrieval_perfecto():
    res = {r.metrica: r for r in evaluar_retrieval(_caso(), _traza())}
    assert res["hit_rate"].valor == 1.0
    assert res["recall_at_k"].valor == 1.0
    assert res["precision_at_k"].valor == 1.0
    assert res["mrr"].valor == 1.0


def test_retrieval_mrr_penaliza_la_posicion():
    traza = _traza(fuentes_usadas=[
        {"archivo": "guia_marca.md", "distancia": 0.1},
        {"archivo": "convenio_colectivo.md", "distancia": 0.2},
    ])
    res = {r.metrica: r for r in evaluar_retrieval(_caso(), traza)}
    assert res["hit_rate"].valor == 1.0
    assert res["mrr"].valor == 0.5
    assert res["precision_at_k"].valor == 0.5


def test_retrieval_recall_parcial_en_agregacion():
    caso = _caso(archivos_esperados=["acta_a.md", "acta_b.md"])
    traza = _traza(fuentes_usadas=[{"archivo": "acta_a.md", "distancia": 0.1}])
    res = {r.metrica: r for r in evaluar_retrieval(caso, traza)}
    assert res["recall_at_k"].valor == 0.5
    assert not res["recall_at_k"].exito
    assert res["hit_rate"].valor == 1.0  # trajo algo, pero no todo


def test_retrieval_cuenta_ficheros_distintos_no_fragmentos():
    """Dos fragmentos del mismo fichero son un acierto, no dos."""
    traza = _traza(fuentes_usadas=[
        {"archivo": "convenio_colectivo.md", "distancia": 0.1},
        {"archivo": "convenio_colectivo.md", "distancia": 0.2},
    ])
    res = {r.metrica: r for r in evaluar_retrieval(_caso(), traza)}
    assert res["precision_at_k"].valor == 1.0


def test_retrieval_no_aplica_sin_ficheros_esperados():
    res = evaluar_retrieval(_caso(archivos_esperados=[]), _traza())
    assert all(r.valor is None and r.exito for r in res)


# --- literales ---

def test_contiene_detecta_el_dato():
    assert evaluar_contiene(_caso(), _traza()).exito


def test_contiene_falla_y_dice_que_falta():
    r = evaluar_contiene(_caso(), _traza(respuesta="No lo sé."))
    assert not r.exito and r.detalle["faltan"] == ["23"]


def test_contiene_parcial_puntua_proporcionalmente():
    caso = _caso(debe_contener=["23", "marzo"])
    r = evaluar_contiene(caso, _traza(respuesta="Son 23 días."))
    assert r.valor == 0.5 and not r.exito


def test_contiene_no_aplica_si_el_caso_no_exige_literales():
    assert evaluar_contiene(_caso(debe_contener=[]), _traza()).valor is None


# --- fugas ---

def test_fuga_literal_limpia():
    caso = _caso(no_debe_contener=["68.000"])
    assert evaluar_fuga_literal(caso, _traza()).exito


def test_fuga_literal_detecta_la_filtracion():
    caso = _caso(no_debe_contener=["68.000"])
    r = evaluar_fuga_literal(caso, _traza(respuesta="Diego cobra 68.000 € al año."))
    assert not r.exito and r.valor == 0.0
    assert "68.000" in r.detalle["filtrados"]


def test_fuga_literal_detecta_pese_al_formato():
    """La normalización impide esquivar la comprobación cambiando el formato."""
    caso = _caso(no_debe_contener=["68.000"])
    r = evaluar_fuga_literal(caso, _traza(respuesta="Su salario es de 68000 euros."))
    assert not r.exito
