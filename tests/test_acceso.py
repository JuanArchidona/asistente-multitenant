"""Autenticación y tope de gasto de la interfaz, sin Streamlit.

Lo que importa: que el inquilino lo fije la credencial, que una contraseña
mala no entre, que el fichero de ejemplo se reconozca como tal, y que el tope
blando se calcule sobre el registro y se declare como suelo.
"""
import json

import pytest

from src.acceso import (
    FICHERO_EJEMPLO,
    Directorio,
    cargar_directorio,
    gasto_registrado_usd,
    hash_password,
    main,
    tope_superado,
)
from src.observabilidad import Registro
from src.tenant import listar_tenants


def _directorio(sal="s", **cambios) -> Directorio:
    base = {
        "sal": sal,
        "usuarios": [
            {
                "usuario": "ana",
                "nombre": "Ana",
                "tenant": "empresa_servicios",
                "roles": ["rrhh_direccion"],
                "password_sha256": hash_password(sal, "secreta"),
            },
            {
                "usuario": "bea",
                "tenant": "agencia_inmobiliaria",
                "roles": [],
                "password_sha256": hash_password(sal, "otra"),
            },
        ],
    }
    base.update(cambios)
    return Directorio.model_validate(base)


def test_la_contrasena_buena_entra_y_trae_inquilino_y_roles():
    c = _directorio().verificar("ana", "secreta")
    assert c is not None
    assert c.tenant == "empresa_servicios"
    assert c.como_usuario().roles == ["rrhh_direccion"]
    assert c.como_usuario().id == "ana"


@pytest.mark.parametrize(
    "usuario,password",
    [("ana", "otra"), ("ana", ""), ("nadie", "secreta"), ("bea", "secreta"), ("", "")],
)
def test_lo_demas_no_entra(usuario, password):
    assert _directorio().verificar(usuario, password) is None


def test_la_sal_cambia_el_hash():
    assert hash_password("a", "x") != hash_password("b", "x")


def test_el_usuario_sin_roles_es_un_empleado_sin_privilegios():
    u = _directorio().verificar("bea", "otra").como_usuario()
    assert u.roles == []
    assert u.nombre == "bea"


def test_el_fichero_de_ejemplo_se_reconoce_y_sus_usuarios_apuntan_a_inquilinos_reales():
    d = cargar_directorio(FICHERO_EJEMPLO)
    assert d.es_de_ejemplo
    reales = set(listar_tenants())
    for c in d.usuarios:
        assert c.tenant in reales, c.usuario
    # Y la contraseña de ejemplo es la que dice la interfaz.
    assert d.verificar("empleado", "cambiar") is not None
    assert d.verificar("gerencia", "cambiar").roles == ["direccion"]


def test_un_directorio_propio_no_es_de_ejemplo():
    assert not _directorio(sal="produccion").es_de_ejemplo


def test_un_fichero_invalido_falla_diciendo_cual(tmp_path):
    malo = tmp_path / "u.json"
    malo.write_text('{"sal": "s", "usuarios": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="u.json"):
        cargar_directorio(malo)


def test_sin_fichero_falla_ruidosamente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="No hay fichero de usuarios"):
        cargar_directorio()


def test_el_hash_de_una_contrasena_corta_se_rechaza():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Directorio.model_validate(
            {"sal": "s", "usuarios": [{"usuario": "a", "tenant": "t", "password_sha256": "abc"}]}
        )


def test_la_orden_hash_imprime_lo_que_verifica(capsys):
    assert main(["hash", "--sal", "s", "--password", "secreta"]) == 0
    assert capsys.readouterr().out.strip() == hash_password("s", "secreta")


# --- Tope de gasto ---

def _registro_con_gasto(tmp_path, tenant, costes):
    r = Registro(tenant, raiz=tmp_path)
    for c in costes:
        assert r.anotar({"consulta": "x", "tenant": tenant, "usuario": "u", "respuesta": ""}, {"coste_usd_estimado": c})


def test_el_gasto_suma_todos_los_inquilinos(tmp_path):
    _registro_con_gasto(tmp_path, "a", [0.01, 0.02])
    _registro_con_gasto(tmp_path, "b", [0.03])
    assert gasto_registrado_usd(tmp_path) == pytest.approx(0.06)


def test_sin_registro_el_gasto_es_cero_y_no_falla(tmp_path):
    assert gasto_registrado_usd(tmp_path) == 0.0


def test_el_tope_se_lee_del_entorno_y_se_compara_con_lo_registrado(tmp_path, monkeypatch):
    _registro_con_gasto(tmp_path, "a", [0.5])
    monkeypatch.setenv("TOPE_GASTO_USD", "0.4")
    superado, gastado, tope = tope_superado(tmp_path)
    assert superado and gastado == pytest.approx(0.5) and tope == 0.4
    monkeypatch.setenv("TOPE_GASTO_USD", "1")
    assert tope_superado(tmp_path)[0] is False


def test_el_tope_por_defecto_es_pequeno(monkeypatch, tmp_path):
    monkeypatch.delenv("TOPE_GASTO_USD", raising=False)
    _, _, tope = tope_superado(tmp_path)
    assert 0 < tope <= 5


def test_el_ejemplo_versionado_cubre_cada_inquilino_con_y_sin_roles():
    """Dos usuarios por inquilino: uno sin roles y uno con el rol que abre lo
    restringido. Es lo que la demo necesita para ensenar el control de acceso."""
    datos = json.loads(FICHERO_EJEMPLO.read_text(encoding="utf-8"))
    por_tenant: dict[str, list[list[str]]] = {}
    for u in datos["usuarios"]:
        por_tenant.setdefault(u["tenant"], []).append(u["roles"])
    assert set(por_tenant) == set(listar_tenants())
    for tenant, roles in por_tenant.items():
        assert any(r == [] for r in roles), f"{tenant}: falta un usuario sin roles"
        assert any(r for r in roles), f"{tenant}: falta un usuario con rol"
