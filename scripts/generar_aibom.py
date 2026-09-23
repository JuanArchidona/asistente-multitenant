"""Genera el AIBOM del proyecto: `docs/AIBOM.md` y `docs/aibom.json`.

    uv run python scripts/generar_aibom.py            # escribe los dos ficheros
    uv run python scripts/generar_aibom.py --comprobar  # sale con 1 si estan viejos

Un AIBOM (AI Bill of Materials) es el inventario de lo que compone el sistema
y de lo que depende: paquetes, modelos, servicios externos, servidores MCP y
datos. El Modulo 4.4 lo pide para la cadena de suministro (OWASP LLM 5, riesgo
R-09 de docs/RIESGOS.md), y el material lo ilustra con el incidente de LiteLLM
de marzo de 2026: no se puede saber si un incidente te afecta si no se sabe que
se tiene.

Se GENERA, no se escribe, y por dos motivos. Uno: una lista escrita a mano se
queda vieja el dia que cambia `uv.lock`, y nadie se entera. Dos: lo que no
esta en un fichero del repositorio no entra, asi que el inventario solo puede
decir lo que el repositorio declara, y eso es exactamente la garantia que se
busca. `tests/test_aibom.py` regenera y compara: si `docs/AIBOM.md` difiere
de lo que sale de los ficheros, la suite falla.

Lo que NO fija el repositorio, y el AIBOM dice que no lo fija: la version de
Node del puente MCP (`puente/`), que la pone el equipo que ejecuta la app.

El JSON sigue la forma de CycloneDX 1.6 en lo que importa (bomFormat,
components con type library/machine-learning-model/service/data). No es un
CycloneDX validado contra su esquema: es la forma, para que una herramienta
que lo lea encuentre los campos donde los espera.
"""
import json
import re
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA_MD = RAIZ / "docs" / "AIBOM.md"
SALIDA_JSON = RAIZ / "docs" / "aibom.json"

PROVEEDOR_POR_PREFIJO = {
    "claude": ("Anthropic", "https://api.anthropic.com"),
    "gemini": ("Google", "https://generativelanguage.googleapis.com"),
}


def paquetes() -> tuple[list[dict], list[dict]]:
    """Paquetes de `uv.lock`, separados en directos (los de `pyproject.toml`) y
    transitivos. Directo o no, todos tienen version y origen fijados: eso es lo
    que hace que `uv sync` reproduzca el mismo entorno."""
    lock = tomllib.loads((RAIZ / "uv.lock").read_text(encoding="utf-8"))
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))

    declarados: dict[str, str] = {}
    for dep in proyecto["project"]["dependencies"]:
        declarados[_nombre(dep)] = "runtime"
    for grupo, deps in proyecto.get("dependency-groups", {}).items():
        for dep in deps:
            declarados[_nombre(dep)] = grupo

    directos, transitivos = [], []
    for p in lock["package"]:
        if p["name"] == proyecto["project"]["name"]:
            continue  # el propio proyecto
        origen = p.get("source", {})
        entrada = {
            "name": p["name"],
            "version": p["version"],
            "source": origen.get("registry") or origen.get("editable") or str(origen),
        }
        if p["name"] in declarados:
            entrada["group"] = declarados[p["name"]]
            directos.append(entrada)
        else:
            transitivos.append(entrada)
    directos.sort(key=lambda e: e["name"])
    transitivos.sort(key=lambda e: e["name"])
    return directos, transitivos


def _nombre(especificacion: str) -> str:
    return re.split(r"[<>=!~\[ ;]", especificacion, maxsplit=1)[0].strip().lower()


def modelos() -> list[dict]:
    """Los modelos por defecto, leidos de `src/config.py` (rol y valor por
    defecto de cada variable de entorno con MODEL en el nombre) y de la tabla
    de precios de `src/provider.py`."""
    fuente = (RAIZ / "src" / "config.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(RAIZ))
    from src.provider import PRECIOS

    roles: dict[str, list[str]] = {}
    # `\s*` alrededor de cada pieza: `ANTHROPIC_MODEL_GENERATOR` esta partido
    # en dos lineas en config.py, y la primera version de esta expresion no lo
    # veia. Un inventario que se salta un modelo por un salto de linea es peor
    # que ninguno, porque parece completo.
    patron = r'os\.getenv\(\s*"([A-Z_]*MODEL[A-Z_]*)"\s*,\s*"([^"]+)"\s*\)'
    for variable, valor in re.findall(patron, fuente):
        roles.setdefault(valor, []).append(variable)

    salida = []
    for modelo, variables in sorted(roles.items()):
        proveedor, endpoint = _proveedor(modelo)
        precio = PRECIOS.get(modelo)
        salida.append(
            {
                "name": modelo,
                "supplier": proveedor,
                "endpoint": endpoint,
                "roles": sorted(variables),
                "price_usd_per_mtok": list(precio) if precio else None,
            }
        )
    return salida


def _proveedor(modelo: str) -> tuple[str, str]:
    for prefijo, datos in PROVEEDOR_POR_PREFIJO.items():
        if modelo.startswith(prefijo):
            return datos
    return ("desconocido", "")


def servicios(modelos_: list[dict]) -> list[dict]:
    vistos = {}
    for m in modelos_:
        vistos.setdefault(m["supplier"], m["endpoint"])
    return [{"name": nombre, "endpoint": endpoint} for nombre, endpoint in sorted(vistos.items())]


def servidores_mcp() -> list[dict]:
    """Los del manifiesto de cada inquilino, y el puente con la app."""
    salida = []
    for ruta in sorted((RAIZ / "tenants").glob("*.json")):
        manifiesto = json.loads(ruta.read_text(encoding="utf-8"))
        for s in manifiesto.get("servidores_mcp", []):
            salida.append(
                {
                    "name": f"{manifiesto['id']}/{s['nombre']}",
                    "command": " ".join([s["comando"], *s.get("args", [])]),
                    "runtime": "python (fijado por .python-version y uv.lock)",
                    "tenant": manifiesto["id"],
                }
            )
    salida.append(
        {
            "name": "puente/servidor.mjs",
            "command": "node puente/servidor.mjs",
            "runtime": "node, SIN FIJAR en el repositorio (sin package.json ni .nvmrc); sin dependencias",
            "tenant": None,
        }
    )
    return salida


def datos() -> list[dict]:
    salida = []
    for tenant in sorted((RAIZ / "corpus").iterdir()):
        if not tenant.is_dir():
            continue
        # Solo lo que indexa `src/ingest.py`: los `.md` de cada carpeta de
        # fuente. El README de la raiz del inquilino no entra en el indice y
        # por eso no cuenta como documento del corpus.
        documentos = sorted(p.relative_to(RAIZ).as_posix() for p in tenant.glob("*/*.md"))
        salida.append(
            {
                "name": f"corpus/{tenant.name}",
                "documents": len(documentos),
                "origin": "sintetico, escrito para el proyecto; ningun dato real",
            }
        )
    for ruta in sorted((RAIZ / "datos").rglob("*.json")):
        salida.append(
            {
                "name": ruta.relative_to(RAIZ).as_posix(),
                "documents": 1,
                "origin": "sintetico, generado con semilla fija por scripts/generar_crm_agencia.py",
            }
        )
    return salida


def runtime() -> dict:
    lock = tomllib.loads((RAIZ / "uv.lock").read_text(encoding="utf-8"))
    return {
        "python": (RAIZ / ".python-version").read_text(encoding="utf-8").strip(),
        "requires_python": lock.get("requires-python", ""),
        "lock_revision": lock.get("revision"),
    }


def construir() -> dict:
    directos, transitivos = paquetes()
    modelos_ = modelos()
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "metadata": {
            "component": {"type": "application", "name": "asistente-multitenant"},
            "runtime": runtime(),
            "generated_by": "scripts/generar_aibom.py",
        },
        "components": (
            [{"type": "library", **p} for p in directos]
            + [{"type": "library", "transitive": True, **p} for p in transitivos]
            + [{"type": "machine-learning-model", **m} for m in modelos_]
            + [{"type": "service", **s} for s in servicios(modelos_)]
            + [{"type": "service", "protocol": "mcp", **s} for s in servidores_mcp()]
            + [{"type": "data", **d} for d in datos()]
        ),
    }


def markdown(bom: dict) -> str:
    comps = bom["components"]
    directos = [c for c in comps if c["type"] == "library" and not c.get("transitive")]
    transitivos = [c for c in comps if c["type"] == "library" and c.get("transitive")]
    modelos_ = [c for c in comps if c["type"] == "machine-learning-model"]
    servicios_ = [c for c in comps if c["type"] == "service" and "protocol" not in c]
    mcp = [c for c in comps if c.get("protocol") == "mcp"]
    datos_ = [c for c in comps if c["type"] == "data"]
    rt = bom["metadata"]["runtime"]

    lineas = [
        "# AIBOM: inventario de lo que compone el sistema",
        "",
        "> **Generado** por `scripts/generar_aibom.py` a partir de `uv.lock`,",
        "> `pyproject.toml`, `.python-version`, `src/config.py`, `src/provider.py`,",
        "> `tenants/*.json`, `corpus/` y `datos/`. No se edita a mano:",
        "> `tests/test_aibom.py` lo regenera y falla si difiere. La version",
        "> legible por maquina, con la forma de CycloneDX 1.6, es `docs/aibom.json`.",
        ">",
        "> Cierra el riesgo R-09 de `RIESGOS.md` (cadena de suministro, OWASP LLM 5):",
        "> sin inventario no se puede saber si un incidente de una dependencia o de",
        "> un modelo afecta al proyecto.",
        "",
        "## Entorno de ejecucion",
        "",
        f"- Python `{rt['python']}` (`.python-version`); el lock exige `{rt['requires_python']}`.",
        (
            f"- `uv.lock` revision {rt['lock_revision']}: {len(directos)} paquetes directos y "
            f"{len(transitivos)} transitivos, todos con version y origen fijados."
        ),
        "- Node para el puente MCP: **sin fijar en el repositorio**. Lo pone el equipo",
        "  que ejecuta la app. Es el unico componente ejecutable cuya version no",
        "  esta escrita, y por eso se dice aqui.",
        "",
        "## Paquetes declarados",
        "",
        "| Paquete | Version | Grupo | Origen |",
        "|---|---|---|---|",
    ]
    lineas += [f"| `{c['name']}` | {c['version']} | {c['group']} | {c['source']} |" for c in directos]
    lineas += [
        "",
        f"Los {len(transitivos)} transitivos estan en `docs/aibom.json`, con version y origen.",
        "",
        "## Modelos",
        "",
        "Los valores por defecto de `src/config.py`; una variable de entorno los",
        "cambia, y entonces el inventario vigente es el de ese despliegue, no este.",
        "",
        "| Modelo | Proveedor | Roles (variable de entorno) | Precio USD por millon de tokens (entrada, salida) |",
        "|---|---|---|---|",
    ]
    for m in modelos_:
        precio = (
            f"{m['price_usd_per_mtok'][0]:.2f} / {m['price_usd_per_mtok'][1]:.2f}"
            if m["price_usd_per_mtok"]
            else "**sin precio en la tabla**"
        )
        lineas.append(f"| `{m['name']}` | {m['supplier']} | {', '.join(m['roles'])} | {precio} |")
    lineas += [
        "",
        "## Servicios externos",
        "",
        "Cada llamada a un modelo es una transferencia de datos a este servicio",
        "(RIESGOS.md R-18).",
        "",
        "| Servicio | Endpoint |",
        "|---|---|",
    ]
    lineas += [f"| {s['name']} | `{s['endpoint']}` |" for s in servicios_]
    lineas += [
        "",
        "## Servidores MCP",
        "",
        "| Servidor | Orden de arranque | Runtime |",
        "|---|---|---|",
    ]
    lineas += [f"| `{s['name']}` | `{s['command']}` | {s['runtime']} |" for s in mcp]
    lineas += [
        "",
        "## Datos",
        "",
        "| Conjunto | Documentos | Origen |",
        "|---|---|---|",
    ]
    lineas += [f"| `{d['name']}` | {d['documents']} | {d['origin']} |" for d in datos_]
    lineas += [
        "",
        "## Como se mantiene",
        "",
        "```bash",
        "uv run python scripts/generar_aibom.py             # regenera",
        "uv run python scripts/generar_aibom.py --comprobar # sale con 1 si esta viejo",
        "```",
        "",
        "Cuando cambia `uv.lock`, un modelo por defecto o un manifiesto, la suite",
        "falla hasta que se regenera. Es la unica forma de que un inventario diga la",
        "verdad seis meses despues de escribirse.",
        "",
    ]
    return "\n".join(lineas)


def main(argv: list[str]) -> int:
    bom = construir()
    md = markdown(bom)
    js = json.dumps(bom, ensure_ascii=False, indent=2) + "\n"
    if "--comprobar" in argv:
        viejo_md = SALIDA_MD.read_text(encoding="utf-8") if SALIDA_MD.exists() else ""
        viejo_js = SALIDA_JSON.read_text(encoding="utf-8") if SALIDA_JSON.exists() else ""
        if viejo_md == md and viejo_js == js:
            print("AIBOM al dia.")
            return 0
        print("AIBOM VIEJO: regenera con `uv run python scripts/generar_aibom.py`.")
        return 1
    SALIDA_MD.write_text(md, encoding="utf-8")
    SALIDA_JSON.write_text(js, encoding="utf-8")
    print(f"Escritos {SALIDA_MD.relative_to(RAIZ)} y {SALIDA_JSON.relative_to(RAIZ)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
