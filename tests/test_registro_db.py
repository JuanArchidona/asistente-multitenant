"""Copia persistente del registro en una base SQL (src/registro_db.py, B6).

Contra SQLite, que habla el mismo SQL que se usa en Postgres para esto, para
que la suite siga sin red. Lo que se prueba es que la base da lo mismo que el
fichero: lo que se lee, lo que se resume, y sobre todo que la supresión y la
purga de RETENCION.md funcionan también ahí, con su lápida. Una copia
persistente que no se pudiera borrar rompería el derecho de supresión justo
donde los datos duran más.
"""
from datetime import UTC, datetime, timedelta

import pytest

from src.observabilidad import (
    CLAVE_LAPIDA,
    Registro,
    borrar_usuario,
    inquilinos,
    leer,
    purgar,
    resumir,
)
from src.registro_db import AlmacenRegistro


def _traza(usuario="ana", consulta="¿vacaciones?") -> dict:
    return {"consulta": consulta, "usuario": usuario, "categoria": "rrhh", "respuesta": "23 días.",
            "fuentes_usadas": [{"archivo": "convenio_colectivo.md"}]}


@pytest.fixture
def almacen(tmp_path):
    return AlmacenRegistro(f"sqlite:///{tmp_path / 'registro.db'}")


def test_la_base_recibe_lo_mismo_que_el_fichero(tmp_path, almacen):
    registro = Registro("empresa_servicios", raiz=tmp_path, almacen=almacen)
    registro.anotar(_traza())
    registro.anotar_fallo("¿y esto?", "ana", RuntimeError("401"))
    registro.anotar_accion("propuesta", {"id": "a1", "herramienta": "crm__x", "argumentos": {}}, "ana")
    registro.anotar_evaluacion("id1", {"veredicto": "fiel"})

    desde_fichero = leer("empresa_servicios", tmp_path)
    desde_base = leer("empresa_servicios", tmp_path, almacen=almacen)
    assert desde_base == desde_fichero
    assert resumir(desde_base) == resumir(desde_fichero)
    assert inquilinos(tmp_path, almacen=almacen) == ["empresa_servicios"]


def test_la_respuesta_tampoco_llega_a_la_base(tmp_path, almacen):
    Registro("t", raiz=tmp_path, almacen=almacen).anotar(_traza())
    assert "23 días." not in str(leer("t", tmp_path, almacen=almacen))


def test_la_supresion_borra_en_la_base_y_deja_lapida(tmp_path, almacen):
    registro = Registro("t", raiz=tmp_path, almacen=almacen)
    registro.anotar(_traza("ana"))
    registro.anotar(_traza("ana", "otra"))
    registro.anotar(_traza("luis"))

    lapida = borrar_usuario("t", "ana", tmp_path, almacen=almacen)

    assert lapida["lineas_quitadas"] == 2
    filas = leer("t", tmp_path, almacen=almacen)
    assert [f.get("usuario") for f in filas if CLAVE_LAPIDA not in f] == ["luis"]
    assert sum(1 for f in filas if CLAVE_LAPIDA in f) == 1
    assert "ana" not in str(filas)


def test_una_segunda_supresion_no_borra_la_lapida_de_la_primera(tmp_path, almacen):
    registro = Registro("t", raiz=tmp_path, almacen=almacen)
    registro.anotar(_traza("ana"))
    borrar_usuario("t", "ana", tmp_path, almacen=almacen)
    registro.anotar(_traza("luis"))
    borrar_usuario("t", "luis", tmp_path, almacen=almacen)
    filas = leer("t", tmp_path, almacen=almacen)
    assert sum(1 for f in filas if CLAVE_LAPIDA in f) == 2


def test_la_purga_por_antiguedad_funciona_en_la_base(tmp_path, almacen):
    almacen.escribir("t", {"ts": "2026-01-01T00:00:00+00:00", "usuario": "ana", "consulta": "vieja"})
    Registro("t", raiz=tmp_path, almacen=almacen).anotar(_traza("ana", "nueva"))

    lapida = purgar("t", 90, tmp_path, ahora=datetime.now(UTC) + timedelta(seconds=1), almacen=almacen)

    assert lapida["lineas_quitadas"] == 1
    consultas = [f.get("consulta") for f in leer("t", tmp_path, almacen=almacen) if CLAVE_LAPIDA not in f]
    assert consultas == ["nueva"]


def test_sin_nada_que_quitar_no_hay_lapida(tmp_path, almacen):
    Registro("t", raiz=tmp_path, almacen=almacen).anotar(_traza("luis"))
    assert borrar_usuario("t", "ana", tmp_path, almacen=almacen)["lineas_quitadas"] == 0
    assert not any(CLAVE_LAPIDA in f for f in leer("t", tmp_path, almacen=almacen))


def test_una_base_caida_no_tumba_la_consulta_y_se_cuenta(tmp_path):
    class _Caida:
        def escribir(self, *a):
            raise ConnectionError("sin red")

    registro = Registro("t", raiz=tmp_path, almacen=_Caida())
    assert registro.anotar(_traza()) is not None
    assert registro.fallos_almacen == 1
    assert "almacen" in registro.ultimo_error
    assert len(leer("t", tmp_path)) == 1  # el fichero sí quedó


def test_una_url_que_no_es_ni_postgres_ni_sqlite_se_rechaza():
    with pytest.raises(ValueError):
        AlmacenRegistro("mysql://x")


def test_desde_config_usa_la_base_si_hay_url(cfg, tmp_path, monkeypatch):
    from src.observabilidad import desde_config

    monkeypatch.setenv("REGISTRO_DB_URL", f"sqlite:///{tmp_path / 'r.db'}")
    assert desde_config(cfg, raiz=tmp_path).almacen is not None
    monkeypatch.delenv("REGISTRO_DB_URL")
    assert desde_config(cfg, raiz=tmp_path).almacen is None
