"""El blueprint de Render no despliega nada que la CI no haya dado en verde.

Es el criterio del tramo 9-10 del enunciado ("automatización de los pases a
producción", docs/MODULO_5.md): cada servicio de render.yaml lleva
`autoDeployTrigger: checksPass` y ninguno conserva el `autoDeploy` obsoleto,
que desplegaba cada push aunque los tests fallaran. Se lee como texto para no
añadir un parser de YAML a las dependencias.
"""
import re
from pathlib import Path

BLUEPRINT = Path(__file__).resolve().parents[1] / "render.yaml"


def _servicios(texto: str) -> dict[str, str]:
    """Bloque de texto de cada servicio, por nombre."""
    bloques = re.split(r"\n  - type: ", texto.split("services:", 1)[1])
    servicios = {}
    for bloque in bloques[1:]:
        nombre = re.search(r"^    name: (\S+)", bloque, re.MULTILINE)
        assert nombre, f"servicio sin nombre en render.yaml: {bloque[:60]!r}"
        servicios[nombre.group(1)] = bloque
    return servicios


def test_los_tres_servicios_estan_en_el_blueprint():
    servicios = _servicios(BLUEPRINT.read_text(encoding="utf-8"))
    assert set(servicios) == {"asistente-multitenant", "asistente-whatsapp", "asistente-correo"}


def test_cada_servicio_despliega_solo_con_la_ci_en_verde():
    for nombre, bloque in _servicios(BLUEPRINT.read_text(encoding="utf-8")).items():
        assert re.search(r"^    autoDeployTrigger: checksPass$", bloque, re.MULTILINE), nombre
        assert not re.search(r"^    autoDeploy:", bloque, re.MULTILINE), nombre
