"""Catálogo de prompts y versión sellada en cada traza (docs/PLAN_ENTREGA.md B3).

El catálogo se genera como el AIBOM: si alguien toca un prompt y no regenera
`docs/PROMPTS.md`, la suite falla. Y cada línea del registro de producción
lleva el commit y la huella de los prompts activos, para que una cifra de
producción se pueda partir por versión.
"""
import importlib.util
from pathlib import Path

from src import agent
from src.observabilidad import Registro, desde_config, resumir
from src.prompts import catalogo, commit_desplegado, huella, huella_activa, version
from src.tenant import cargar_tenant, listar_tenants

RAIZ = Path(__file__).resolve().parents[1]


def _generador():
    spec = importlib.util.spec_from_file_location(
        "generar_prompts", RAIZ / "scripts" / "generar_prompts.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_el_catalogo_de_docs_es_el_que_sale_del_codigo():
    assert (RAIZ / "docs" / "PROMPTS.md").read_text(encoding="utf-8") == _generador().generar()


def test_cada_inquilino_tiene_su_enrutador_y_no_hay_ids_repetidos():
    tenants = [cargar_tenant(t) for t in listar_tenants()]
    ids = [p.id for p in catalogo(tenants)]
    assert len(ids) == len(set(ids))
    for t in tenants:
        assert f"enrutador.{t.id}" in ids
    assert {"generador.base", "generador.endurecido", "generador.datos"} <= set(ids)


def test_el_catalogo_incluye_los_pasos_del_juez_sin_importar_deepeval():
    pasos = _generador().pasos_del_juez()
    assert set(pasos) == {"PASOS_CORRECCION", "PASOS_ABSTENCION", "PASOS_CONFIDENCIALIDAD"}
    assert all(pasos.values())


def test_la_huella_cambia_con_la_politica_y_con_quien_pregunta(cfg, cfg_factory):
    base = huella_activa(cfg)
    endurecida = huella_activa(cfg_factory(gen_policy="hardened"))
    sin_quien = huella_activa(cfg_factory(gen_quien_pregunta=False))
    assert base["generador"] == huella(agent.SYSTEM_GEN_BASE)
    assert endurecida["generador"] == huella(agent.SYSTEM_GEN_HARDENED)
    assert len({base["version"], endurecida["version"], sin_quien["version"]}) == 3
    assert sin_quien["quien_pregunta"] is None


def test_la_huella_cambia_al_activar_la_memoria(cfg, cfg_factory):
    """Las primeras consultas con memoria en producción llevaban la misma huella
    que sin ella: el prompt de reescritura no entraba en la versión (§66)."""
    sin = huella_activa(cfg)
    con = huella_activa(cfg_factory(memoria_turnos="reescritura"))
    assert sin["memoria"] is None and con["memoria"]
    assert sin["version"] != con["version"]


def test_el_commit_sale_de_render_cuando_corre_alli(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "0123456789abcdef")
    assert commit_desplegado() == "0123456"


def test_cada_linea_del_registro_lleva_la_version(cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef0123")
    registro = desde_config(cfg, raiz=tmp_path)
    assert registro.version == {"commit": "abcdef0", "prompts": huella_activa(cfg)["version"]}
    linea = registro.componer({"consulta": "x", "respuesta": "y", "fuentes_usadas": []}, None)
    assert linea["version"] == registro.version
    fallo = registro.anotar_fallo("x", "ana", RuntimeError("caido"))
    assert fallo["version"] == registro.version


def test_el_resumen_parte_las_consultas_por_version(tmp_path):
    v1 = {"commit": "aaaaaaa", "prompts": "111111111111"}
    v2 = {"commit": "bbbbbbb", "prompts": "222222222222"}
    filas = [
        Registro("t", raiz=tmp_path, version=v).componer({"consulta": "q", "respuesta": "r"}, None)
        for v in (v1, v1, v2)
    ] + [Registro("t", raiz=tmp_path).componer({"consulta": "q", "respuesta": "r"}, None)]
    assert resumir(filas)["por_version"] == {
        "aaaaaaa/111111111111": 2, "bbbbbbb/222222222222": 1, "sin_version": 1,
    }


def test_version_de_una_configuracion_es_commit_y_prompts(cfg):
    v = version(cfg)
    assert set(v) == {"commit", "prompts"}
    assert len(v["prompts"]) == 12
