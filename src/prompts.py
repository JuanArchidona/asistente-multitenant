"""Catálogo de prompts del sistema y su huella (PromptOps, docs/PLAN_ENTREGA.md B3).

El Módulo 3 pide versionar los prompts como el código y el enunciado del TFM
pide declarar "configuración, forma de consumo, parametrización y prompts
empleados". Los prompts ya estaban versionados por git, pero ninguna traza
decía con qué versión se había respondido: si mañana cambia un prompt, una
línea del registro de producción no permite saber si es de antes o de
después. Este módulo da tres cosas:

- `catalogo()`: todos los prompts del sistema, con quién los usa, con qué
  modelo y temperatura, y su huella (sha256 recortado del texto). Lo vuelca
  `scripts/generar_prompts.py` en `docs/PROMPTS.md`, y un test falla si el
  fichero difiere de lo que sale del código, como el AIBOM.
- `huella_activa(cfg)`: la huella de los prompts que de verdad usa una
  configuración (el enrutador de su inquilino y el generador de su política),
  y una huella combinada, `version`, que cambia si cambia cualquiera.
- `commit_desplegado()`: el commit que corre, de `RENDER_GIT_COMMIT` en Render
  o de git en local.

El registro de producción y el `resumen.json` de cada ejecución del banco
llevan las dos, así que cualquier cifra se puede partir por versión.
"""
import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import agent, evaluacion_produccion, router, transcriber
from .config import Config
from .tenant import Tenant

RAIZ = Path(__file__).resolve().parents[1]


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Prompt:
    id: str
    uso: str
    modelo: str
    temperatura: str
    texto: str
    evidencia: str

    @property
    def huella(self) -> str:
        return huella(self.texto)


_GENERADOR = "`ANTHROPIC_MODEL_GENERATOR` (por defecto `claude-haiku-4-5`)"
_TEMP_GEN = "por defecto del proveedor (1,0 en Anthropic)"


def catalogo(tenants: list[Tenant]) -> list[Prompt]:
    """Todos los prompts de sistema del producto, los del enrutador por inquilino.

    Los textos con huecos (`{fecha}`, `{nombre}`...) van como plantilla: la
    huella es de la plantilla, que es lo que se versiona; lo que se rellena en
    cada consulta es dato, no prompt.
    """
    prompts = [
        Prompt(
            f"enrutador.{t.id}",
            f"Clasifica la consulta en una categoría de `{t.id}`; se construye desde su manifiesto",
            "`ANTHROPIC_MODEL_ROUTER` (por defecto `claude-haiku-4-5`)",
            "0,0 (`ROUTER_TEMPERATURE`), desde el primer corte de línea base",
            router.system_router(t),
            "§27, `ALCANCE.md` §5.c; el del heredado está congelado por test contra la 3.3",
        )
        for t in tenants
    ]
    prompts += [
        Prompt(
            "generador.base",
            "Rama documental, política `base` (la de producción)",
            _GENERADOR, _TEMP_GEN, agent.SYSTEM_GEN_BASE,
            "Línea base literal de la 3.1; elegida frente a la endurecida en §40",
        ),
        Prompt(
            "generador.endurecido",
            "Rama documental, política `hardened` (`GEN_POLICY=hardened`), candidato medido y no elegido",
            _GENERADOR, _TEMP_GEN, agent.SYSTEM_GEN_HARDENED,
            "§31, §33: 10/10 en `fuga_literal`, pero bloquea a quien tiene permiso (§39)",
        ),
        Prompt(
            "generador.quien_pregunta",
            "Bloque que se añade al generador con la identidad y los roles de quien pregunta",
            _GENERADOR, _TEMP_GEN, agent.BLOQUE_QUIEN_PREGUNTA,
            "§39, §40, `ALCANCE.md` §5.d (segundo corte); `GEN_QUIEN_PREGUNTA=0` lo quita",
        ),
        Prompt(
            "generador.datos",
            "Rama estructurada: responde con las herramientas MCP del inquilino",
            _GENERADOR, _TEMP_GEN, agent.SYSTEM_GEN_DATOS,
            "§23 (citar la herramienta), §40",
        ),
        Prompt(
            "generador.mixto",
            "Bloque que se añade al documental cuando la categoría consulta las dos ramas",
            _GENERADOR, _TEMP_GEN, agent.SYSTEM_GEN_MIXTO_EXTRA,
            "§22",
        ),
        Prompt(
            "generador.sin_fuente",
            "Consulta que el enrutador manda a `otro`: responde sin contexto interno",
            _GENERADOR, _TEMP_GEN, agent.SYSTEM_SIN_FUENTE,
            "Heredado de la 2.3",
        ),
        Prompt(
            "herramienta.accion_pendiente",
            "Lo que recibe el modelo en lugar de ejecutar una herramienta que escribe",
            "El de la rama estructurada", "—", agent.TEXTO_ACCION_PENDIENTE,
            "§42 (`accion_sin_aprobar` 40/40)",
        ),
        Prompt(
            "ingesta.transcriptor",
            "Ingesta: convierte un PDF en el documento estructurado que se indexa",
            _GENERADOR, _TEMP_GEN, transcriber.SYSTEM_TRANSCRIPTOR,
            "Heredado de la entrega 2.1; no interviene al responder",
        ),
        Prompt(
            "juez.produccion",
            "Juez de producción: fidelidad de la respuesta a su contexto, sobre la fracción muestreada",
            "`JUDGE_MODEL` (por defecto `gemini-3.6-flash`), clave `GEMINI_API_KEY_JUEZ`",
            "0,0",
            evaluacion_produccion.SYSTEM_JUEZ_PRODUCCION,
            "Capítulo 6.1 de la memoria; veredicto de tres valores por el §30",
        ),
    ]
    return prompts


def huella_activa(cfg: Config) -> dict:
    """Huellas de los prompts que usa esta configuración, y una combinada."""
    generador = agent.SYSTEM_GEN_HARDENED if cfg.gen_policy == "hardened" else agent.SYSTEM_GEN_BASE
    partes = {
        "enrutador": huella(router.system_router(cfg.tenant)),
        "generador": huella(generador),
        "quien_pregunta": huella(agent.BLOQUE_QUIEN_PREGUNTA) if cfg.gen_quien_pregunta else None,
        "datos": huella(agent.SYSTEM_GEN_DATOS),
        "mixto": huella(agent.SYSTEM_GEN_MIXTO_EXTRA),
    }
    combinada = huella("|".join(f"{k}={v}" for k, v in sorted(partes.items())))
    return {"version": combinada, **partes}


def commit_desplegado() -> str:
    """Commit corto que corre: el de Render si lo hay, el de git si no."""
    render = os.getenv("RENDER_GIT_COMMIT", "").strip()
    if render:
        return render[:7]
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=RAIZ, capture_output=True, text=True, timeout=5, check=True,
        )
        return salida.stdout.strip() or "desconocido"
    except (OSError, subprocess.SubprocessError):
        return "desconocido"


def version(cfg: Config) -> dict:
    """Lo que se sella en cada traza: commit y huella de los prompts activos."""
    activa = huella_activa(cfg)
    return {"commit": commit_desplegado(), "prompts": activa["version"]}

