"""El anexo B de la memoria se genera desde las líneas de evidencia del texto.

Regla de las lecturas hostiles de la memoria: los recuentos se rehacen con el
comando, no se editan a mano. Y regla de la reescritura del 25-10-2026: la
prosa no lleva referencias `§N`, que dos lecturas externas señalaron como lo
que más impedía seguir el texto; la trazabilidad va en una línea de evidencia
por apartado y en este anexo.
"""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _modulo():
    spec = importlib.util.spec_from_file_location("generar_anexo_b", RAIZ / "scripts" / "generar_anexo_b.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_el_anexo_b_es_el_que_sale_del_texto():
    mod = _modulo()
    texto = mod.MEMORIA.read_text(encoding="utf-8")
    assert mod.regenerar(texto) == texto


def test_la_memoria_no_cita_hallazgos_con_el_simbolo_de_parrafo():
    mod = _modulo()
    assert "§" not in mod.MEMORIA.read_text(encoding="utf-8")


def test_cada_hallazgo_aparece_en_el_anexo_con_su_titulo():
    mod = _modulo()
    texto = mod.MEMORIA.read_text(encoding="utf-8")
    anexo = texto.split(mod.INICIO)[1].split("\n## ")[0]
    for n in mod.titulos():
        assert f"\n| {n} | " in anexo


def test_la_linea_de_evidencia_se_lee_y_lo_demas_no():
    mod = _modulo()
    assert mod.numeros_de_evidencia("*Evidencia: hallazgos 22, 47 y 53.*") == {22, 47, 53}
    assert mod.numeros_de_evidencia("*Evidencia: hallazgo 42.*") == {42}
    assert mod.numeros_de_evidencia("Hubo 22 casos y 47 fallos.") == set()


def test_una_evidencia_inexistente_rompe_la_generacion(monkeypatch):
    mod = _modulo()
    texto = f"## 1. Algo\n\n*Evidencia: hallazgo 9999.*\n\n{mod.INICIO}\n"
    with pytest.raises(ValueError, match="9999"):
        mod.regenerar(texto)


def test_el_titulo_breve_corta_en_la_primera_afirmacion():
    mod = _modulo()
    largo = "Ocho consultas a la vez tardan lo que una: el pipeline escala en hilos"
    assert mod.titulo_breve(largo) == "Ocho consultas a la vez tardan lo que una"
    assert mod.titulo_breve("Corto: nada") == "Corto: nada"
