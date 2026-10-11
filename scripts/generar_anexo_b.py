"""Regenera el anexo B de la memoria: qué hallazgos cita cada capítulo.

    uv run python scripts/generar_anexo_b.py              # reescribe el anexo en docs/MEMORIA.md
    uv run python scripts/generar_anexo_b.py --comprobar  # sale con 1 si está viejo

Se hacía a mano y se quedaba viejo: la bitácora del 27-09 lo dejó anotado, y
la regla que salió de las dos lecturas hostiles de la memoria es que los
recuentos se rehacen con el comando, no se editan. Las citas `§N` se leen del
texto de cada capítulo (los de nivel `## N.` también, por su texto antes del
primer apartado), y no cuentan las que son secciones de `ALCANCE.md` (§5.c,
§5.d), que no son hallazgos. `tests/test_anexo_b.py` falla si el anexo
difiere de lo que sale del texto.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MEMORIA = RAIZ / "docs" / "MEMORIA.md"
HALLAZGOS = RAIZ / "docs" / "HALLAZGOS.md"

INICIO = "## Anexo B. Índice de hallazgos por capítulo"
RE_CITA = re.compile(r"§(\d+)")
RE_CABECERA = re.compile(r"^(#{2,3}) (.+)$")


def hallazgos_existentes() -> set[int]:
    return {int(n) for n in re.findall(r"^## (\d+)\.", HALLAZGOS.read_text(encoding="utf-8"), re.MULTILINE)}


def _citas(texto: str, validos: set[int]) -> set[int]:
    salida = set()
    for m in RE_CITA.finditer(texto):
        antes = texto[max(0, m.start() - 16): m.start()]
        despues = texto[m.end(): m.end() + 2]
        if re.search(r"ALCANCE(\.md)?`?\s*$", antes) or re.match(r"\.[a-z0-9]", despues):
            continue
        n = int(m.group(1))
        if n in validos:
            salida.add(n)
    return salida


def secciones(texto: str) -> list[tuple[str, str]]:
    """(título, texto) de cada capítulo y apartado hasta el anexo B."""
    cuerpo = texto.split(INICIO)[0]
    salida, titulo, buffer = [], None, []
    for linea in cuerpo.splitlines():
        m = RE_CABECERA.match(linea)
        if m:
            if titulo is not None:
                salida.append((titulo, "\n".join(buffer)))
            titulo, buffer = m.group(2).strip(), []
        elif titulo is not None:
            buffer.append(linea)
    if titulo is not None:
        salida.append((titulo, "\n".join(buffer)))
    return salida


def tabla(texto: str) -> tuple[str, int]:
    validos = hallazgos_existentes()
    filas = []
    for titulo, cuerpo in secciones(texto):
        citas = _citas(cuerpo, validos)
        if citas:
            filas.append(f"| {titulo} | {', '.join(f'§{n}' for n in sorted(citas))} |")
    return "\n".join(["| Capítulo | Hallazgos citados |", "|---|---|", *filas]), len(validos)


def regenerar(texto: str) -> str:
    i = texto.index(INICIO)
    resto = texto[i:]
    # El anexo termina en la siguiente cabecera de nivel 2, o al final.
    m = re.search(r"\n## ", resto[len(INICIO):])
    fin = i + len(INICIO) + m.start() if m else len(texto)
    tabla_md, total = tabla(texto)
    anexo = (
        f"{INICIO}\n\n"
        f"Los {total} hallazgos de `docs/HALLAZGOS.md`, con los apartados de esta\n"
        "memoria que los citan (todos los que lo hacen, no solo el principal).\n"
        "Generado por `scripts/generar_anexo_b.py` desde las citas `§N` del texto;\n"
        "un test falla si difiere. Cada hallazgo nombra la ejecución de `reports/`\n"
        "que lo respalda o dice que no la tiene.\n\n"
        f"{tabla_md}\n"
    )
    return texto[:i] + anexo + texto[fin:]


def main() -> int:
    actual = MEMORIA.read_text(encoding="utf-8")
    nuevo = regenerar(actual)
    if "--comprobar" in sys.argv:
        if nuevo != actual:
            print("El anexo B está viejo: uv run python scripts/generar_anexo_b.py")
            return 1
        print("Anexo B al día.")
        return 0
    MEMORIA.write_text(nuevo, encoding="utf-8")
    print("Anexo B regenerado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
