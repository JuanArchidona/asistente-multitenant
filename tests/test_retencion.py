"""Supresion y retencion del registro de produccion (RIESGOS.md R-16).

Lo que se prueba: que borrar a un usuario quita TODAS sus lineas y NINGUNA
ajena, que queda una lapida que lo dice sin decir quien, que las lineas
ilegibles se conservan porque no se sabe de quien son, que la retencion corta
por fecha, y que el resumen no esconde que hubo borrados.
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.observabilidad import (
    CLAVE_LAPIDA,
    Registro,
    borrar_usuario,
    leer,
    purgar,
    resumir,
)


def _traza(usuario: str, consulta: str = "¿Cuántos días de vacaciones?") -> dict:
    return {
        "consulta": consulta,
        "tenant": "t",
        "usuario": usuario,
        "categoria": "rrhh",
        "respuesta": "23",
        "fuentes_usadas": [],
    }


def _log(tmp_path: Path, usuarios: list[str]) -> Path:
    r = Registro("t", raiz=tmp_path)
    for u in usuarios:
        assert r.anotar(_traza(u)) is not None
    return r.ruta


def _lineas(ruta: Path) -> list[dict]:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


# --- Supresion ---

def test_borrar_usuario_quita_todas_sus_lineas_y_ninguna_ajena(tmp_path):
    ruta = _log(tmp_path, ["ana", "bea", "ana", "carlos", "ana"])
    lapida = borrar_usuario("t", "ana", raiz=tmp_path)
    assert lapida["lineas_quitadas"] == 3
    filas = [l for l in _lineas(ruta) if CLAVE_LAPIDA not in l]
    assert [f["usuario"] for f in filas] == ["bea", "carlos"]


def test_la_lapida_dice_que_se_borro_sin_decir_a_quien(tmp_path):
    ruta = _log(tmp_path, ["ana", "bea"])
    borrar_usuario("t", "ana", raiz=tmp_path)
    lapidas = [l for l in _lineas(ruta) if CLAVE_LAPIDA in l]
    assert len(lapidas) == 1
    lp = lapidas[0]
    assert lp["motivo"] == "supresion_usuario"
    assert lp["lineas_quitadas"] == 1
    assert "ana" not in json.dumps(lp)
    assert len(lp["usuario_hash"]) == 16


def test_borrar_a_quien_no_esta_no_toca_el_fichero_ni_deja_lapida(tmp_path):
    ruta = _log(tmp_path, ["ana", "bea"])
    antes = ruta.read_text(encoding="utf-8")
    lapida = borrar_usuario("t", "nadie", raiz=tmp_path)
    assert lapida["lineas_quitadas"] == 0
    assert ruta.read_text(encoding="utf-8") == antes


def test_borrar_dos_veces_es_idempotente_y_conserva_la_primera_lapida(tmp_path):
    ruta = _log(tmp_path, ["ana", "bea"])
    borrar_usuario("t", "ana", raiz=tmp_path)
    borrar_usuario("t", "ana", raiz=tmp_path)
    lapidas = [l for l in _lineas(ruta) if CLAVE_LAPIDA in l]
    assert len(lapidas) == 1


def test_las_lineas_ilegibles_se_conservan_porque_no_se_sabe_de_quien_son(tmp_path):
    ruta = _log(tmp_path, ["ana", "bea"])
    with ruta.open("a", encoding="utf-8") as f:
        f.write('{"usuario": "ana", "consulta": "a med')  # proceso muerto a mitad
    lapida = borrar_usuario("t", "ana", raiz=tmp_path)
    assert lapida["lineas_quitadas"] == 1
    assert lapida["lineas_ilegibles_conservadas"] == 1
    assert '{"usuario": "ana", "consulta": "a med' in ruta.read_text(encoding="utf-8")


def test_un_log_inexistente_no_falla_ni_se_crea(tmp_path):
    lapida = borrar_usuario("t", "ana", raiz=tmp_path)
    assert lapida["lineas_quitadas"] == 0
    assert not (tmp_path / "t" / "trazas.jsonl").exists()


# --- Retencion ---

def _log_con_fechas(tmp_path: Path, dias_atras: list[int]) -> Path:
    ruta = tmp_path / "t" / "trazas.jsonl"
    ruta.parent.mkdir(parents=True)
    ahora = datetime.now(UTC)
    with ruta.open("w", encoding="utf-8") as f:
        for d in dias_atras:
            ts = (ahora - timedelta(days=d)).isoformat(timespec="seconds")
            f.write(json.dumps({"ts": ts, "usuario": f"u{d}", "consulta": "x"}) + "\n")
    return ruta


def test_purgar_quita_lo_mas_viejo_que_n_dias_y_deja_el_resto(tmp_path):
    ruta = _log_con_fechas(tmp_path, [1, 30, 91, 200])
    lapida = purgar("t", 90, raiz=tmp_path)
    assert lapida["lineas_quitadas"] == 2
    filas = [l for l in _lineas(ruta) if CLAVE_LAPIDA not in l]
    assert sorted(f["usuario"] for f in filas) == ["u1", "u30"]
    assert lapida["motivo"] == "retencion"
    assert lapida["dias"] == 90


def test_la_retencion_no_admite_cero_dias(tmp_path):
    with pytest.raises(ValueError):
        purgar("t", 0, raiz=tmp_path)


def test_purgar_no_borra_lapidas_anteriores(tmp_path):
    ruta = _log_con_fechas(tmp_path, [1, 200])
    purgar("t", 90, raiz=tmp_path)
    purgar("t", 90, raiz=tmp_path)  # nada nuevo que quitar
    lapidas = [l for l in _lineas(ruta) if CLAVE_LAPIDA in l]
    assert len(lapidas) == 1
    # Y una lapida vieja tampoco se purga aunque su ts sea anterior al limite.
    lapidas[0]["ts"] = (datetime.now(UTC) - timedelta(days=400)).isoformat(timespec="seconds")
    ruta.write_text("\n".join(json.dumps(l) for l in _lineas(ruta)[:-1] + [lapidas[0]]) + "\n", encoding="utf-8")
    purgar("t", 90, raiz=tmp_path)
    assert any(CLAVE_LAPIDA in l for l in _lineas(ruta))


# --- El resumen no esconde los borrados ---

def test_el_resumen_cuenta_los_borrados_y_no_los_mezcla_con_consultas(tmp_path):
    _log(tmp_path, ["ana", "bea", "ana"])
    borrar_usuario("t", "ana", raiz=tmp_path)
    resumen = resumir(leer("t", raiz=tmp_path))
    assert resumen["consultas"] == 1
    assert resumen["usuarios_distintos"] == 1
    assert resumen["borrados"] == 1
    assert resumen["lineas_borradas"] == 2


def test_un_log_solo_con_lapida_dice_cero_consultas_y_un_borrado(tmp_path):
    _log(tmp_path, ["ana"])
    borrar_usuario("t", "ana", raiz=tmp_path)
    resumen = resumir(leer("t", raiz=tmp_path))
    assert resumen["consultas"] == 0
    assert resumen["borrados"] == 1
