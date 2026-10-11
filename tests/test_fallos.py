"""Mensaje al usuario cuando una consulta no se puede atender (src/fallos.py, B5).

Tres propiedades: la clase del fallo sale del código HTTP o del tipo sin
importar los SDK; el mensaje dice qué ha pasado y a quién acudir, con el
contacto que declara el manifiesto; y la clase queda en el registro.
"""
import pytest

from src.fallos import (
    CREDENCIAL,
    LIMITE_DE_TASA,
    OTRO,
    PROVEEDOR_NO_DISPONIBLE,
    clasificar,
    mensaje_para_el_usuario,
)
from src.observabilidad import Registro, leer
from src.tenant import cargar_tenant, listar_tenants


class _ErrorHTTP(Exception):
    def __init__(self, status_code):
        super().__init__(f"error {status_code}")
        self.status_code = status_code


class APIConnectionError(Exception):
    """Mismo nombre que la del SDK de Anthropic."""


@pytest.mark.parametrize(
    ("error", "clase"),
    [
        (_ErrorHTTP(529), PROVEEDOR_NO_DISPONIBLE),
        (_ErrorHTTP(503), PROVEEDOR_NO_DISPONIBLE),
        (APIConnectionError("sin red"), PROVEEDOR_NO_DISPONIBLE),
        (TimeoutError(), PROVEEDOR_NO_DISPONIBLE),
        (_ErrorHTTP(429), LIMITE_DE_TASA),
        (RuntimeError("gemini:x: límite de tasa tras 3 intentos"), LIMITE_DE_TASA),
        (_ErrorHTTP(401), CREDENCIAL),
        (_ErrorHTTP(403), CREDENCIAL),
        (KeyError("x"), OTRO),
    ],
)
def test_la_clase_sale_del_codigo_o_del_tipo(error, clase):
    assert clasificar(error) == clase


def test_el_mensaje_dice_que_paso_y_a_quien_acudir():
    texto = mensaje_para_el_usuario(_ErrorHTTP(529), "Llama a la extensión 2100.")
    assert texto.startswith("La consulta no se pudo atender (_ErrorHTTP).")
    assert "no responde" in texto
    assert texto.endswith("Llama a la extensión 2100.")


def test_sin_contacto_el_mensaje_no_inventa_uno():
    assert mensaje_para_el_usuario(KeyError("x")).endswith("para el equipo técnico.")


def test_los_tres_inquilinos_declaran_un_contacto_sintetico():
    for t in listar_tenants():
        contacto = cargar_tenant(t).contacto_alternativo
        assert contacto, t
        assert ".example" in contacto, f"{t}: ningún dato real en el repositorio"


def test_el_registro_guarda_la_clase_del_fallo(tmp_path):
    Registro("t", raiz=tmp_path).anotar_fallo("¿vacaciones?", "ana", _ErrorHTTP(401))
    assert leer("t", tmp_path)[0]["clase"] == CREDENCIAL
