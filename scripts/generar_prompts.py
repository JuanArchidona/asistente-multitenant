"""Genera `docs/PROMPTS.md`: el catálogo de prompts del sistema con su huella.

    uv run python scripts/generar_prompts.py              # escribe el fichero
    uv run python scripts/generar_prompts.py --comprobar  # sale con 1 si está viejo

Como el AIBOM, se genera y no se escribe: una lista de prompts escrita a mano
se queda vieja el día que alguien toca uno. `tests/test_prompts.py` regenera y
compara. Los criterios del juez se leen de `evals/metrics/juez.py` con `ast`,
sin importar DeepEval, para que el catálogo se pueda comprobar en la CI, que
no instala el grupo del juez.
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.prompts import catalogo, huella
from src.provider import MAX_TOKENS_SUT
from src.tenant import cargar_tenant, listar_tenants

SALIDA = RAIZ / "docs" / "PROMPTS.md"
JUEZ = RAIZ / "evals" / "metrics" / "juez.py"
PASOS_JUEZ = ("PASOS_CORRECCION", "PASOS_ABSTENCION", "PASOS_CONFIDENCIALIDAD")


def pasos_del_juez() -> dict[str, list[str]]:
    arbol = ast.parse(JUEZ.read_text(encoding="utf-8"))
    pasos = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            nombre = getattr(nodo.targets[0], "id", None)
            if nombre in PASOS_JUEZ:
                pasos[nombre] = ast.literal_eval(nodo.value)
    return pasos


def generar() -> str:
    tenants = [cargar_tenant(t) for t in listar_tenants()]
    prompts = catalogo(tenants)
    juez = pasos_del_juez()

    lineas = [
        "# Catálogo de prompts",
        "",
        "> **Generado** por `scripts/generar_prompts.py` desde el código; no se edita a",
        "> mano. `tests/test_prompts.py` falla si este fichero difiere de lo que sale",
        "> del código. Cada línea del registro de producción y cada `resumen.json`",
        "> del banco llevan la huella combinada de los prompts activos y el commit",
        "> (`src/prompts.py`), así que cualquier cifra se puede partir por versión.",
        "",
        f"Todas las llamadas del sistema usan `max_tokens={MAX_TOKENS_SUT}` (`MAX_TOKENS_SUT`,",
        "`src/provider.py`). La huella es el sha256 del texto recortado a 12",
        "caracteres; de una plantilla, la huella es de la plantilla.",
        "",
        "## Resumen",
        "",
        "| Prompt | Uso | Modelo | Temperatura | Huella | Evidencia |",
        "|---|---|---|---|---|---|",
    ]
    for p in prompts:
        lineas.append(
            f"| `{p.id}` | {p.uso} | {p.modelo} | {p.temperatura} | `{p.huella}` | {p.evidencia} |"
        )
    for nombre, pasos in juez.items():
        lineas.append(
            f"| `juez.{nombre.lower()}` | Pasos de G-Eval del juez (solo en evaluación) | "
            f"`JUDGE_MODEL` (por defecto `gemini-3.6-flash`) | 0,0 | `{huella(chr(10).join(pasos))}` | "
            "§30, §32 |"
        )
    lineas += ["", "## Textos", ""]
    for p in prompts:
        lineas += [f"### `{p.id}`", "", "```text", p.texto.strip("\n"), "```", ""]
    for nombre, pasos in juez.items():
        lineas += [f"### `juez.{nombre.lower()}`", "", "```text", *pasos, "```", ""]
    return "\n".join(lineas)


def main() -> int:
    contenido = generar()
    if "--comprobar" in sys.argv:
        actual = SALIDA.read_text(encoding="utf-8") if SALIDA.exists() else ""
        if actual != contenido:
            print("docs/PROMPTS.md está viejo: uv run python scripts/generar_prompts.py")
            return 1
        print("docs/PROMPTS.md al día.")
        return 0
    SALIDA.write_text(contenido, encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
