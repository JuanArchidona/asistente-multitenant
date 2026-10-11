"""El anexo B de la memoria se genera desde las citas del texto.

Regla de las dos lecturas hostiles de la memoria: los recuentos se rehacen
con el comando, no se editan a mano. Si alguien cita un hallazgo nuevo y no
regenera el anexo, esto falla.
"""
import importlib.util
from pathlib import Path

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


def test_las_secciones_de_alcance_no_cuentan_como_hallazgos():
    mod = _modulo()
    validos = {5, 22}
    assert mod._citas("ver `ALCANCE.md` §5.c y §22", validos) == {22}
    assert mod._citas("el corte (§5.d) y el §5.", validos) == {5}
