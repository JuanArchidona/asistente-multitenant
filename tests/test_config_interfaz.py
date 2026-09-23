"""La interfaz desplegada no exige las claves del juez; el banco sí.

Salió del primer despliegue en Render (HALLAZGOS.md §38): el servicio
arrancó y la interfaz se paró tras el login exigiendo GEMINI_API_KEY_JUEZ a
un proceso que nunca iba a evaluar. La comprobación que impide mezclar la
factura del juez con la del sistema sigue donde importa, en el banco.
"""
import pytest

from src.config import load_config

ENTORNO_MINIMO = {
    "LLM_PROVIDER": "anthropic",
    "ANTHROPIC_API_KEY": "clave-sistema",
    "GEMINI_API_KEY": "clave-embeddings",
    "TENANT_ID": "empresa_servicios",
}


@pytest.fixture
def entorno_sin_juez(monkeypatch):
    for clave, valor in ENTORNO_MINIMO.items():
        monkeypatch.setenv(clave, valor)
    for clave in ("ANTHROPIC_API_KEY_JUEZ", "GEMINI_API_KEY_JUEZ", "JUDGE_PROVIDER", "JUDGE_MODEL"):
        monkeypatch.delenv(clave, raising=False)


def test_sin_clave_del_juez_el_banco_no_arranca(entorno_sin_juez):
    with pytest.raises(SystemExit, match="GEMINI_API_KEY_JUEZ"):
        load_config()


def test_sin_clave_del_juez_la_interfaz_si_arranca(entorno_sin_juez):
    cfg = load_config("agencia_inmobiliaria", con_juez=False)
    assert cfg.tenant.id == "agencia_inmobiliaria"
    assert cfg.judge_gemini_api_key == ""


def test_el_juez_igual_al_generador_se_rechaza_tambien_sin_juez(entorno_sin_juez, monkeypatch):
    """No depende de ninguna clave: se comprueba siempre."""
    monkeypatch.setenv("JUDGE_MODEL", "claude-haiku-4-5-20251001")
    with pytest.raises(SystemExit, match="mismo modelo"):
        load_config(con_juez=False)


def test_el_tenant_id_del_argumento_manda_sobre_el_entorno(entorno_sin_juez):
    cfg = load_config("agencia_inmobiliaria", con_juez=False)
    assert cfg.tenant.id == "agencia_inmobiliaria"
    assert cfg.collection.endswith("__agencia_inmobiliaria")
