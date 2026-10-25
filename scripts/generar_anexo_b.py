"""Regenera el anexo B de la memoria: cada hallazgo, qué midió y dónde se usa.

    uv run python scripts/generar_anexo_b.py              # reescribe el anexo en docs/MEMORIA.md
    uv run python scripts/generar_anexo_b.py --comprobar  # sale con 1 si está viejo

Desde el 25-10-2026 la memoria no cita hallazgos dentro de la prosa: dos
lecturas externas (Gemini y ChatGPT, encargo E-0025) coincidieron en que las
cientos de referencias `§N` impedían seguir el texto. Cada apartado termina
con una línea `*Evidencia: hallazgos 22 y 47.*`, y este anexo dice, para cada
hallazgo, su título y los apartados que lo usan, de modo que el lector sabe
qué es el 22 sin abrir otro fichero.

Se genera y no se edita porque el anexo hecho a mano se quedaba viejo (la
bitácora del 27-09 lo dejó anotado). `tests/test_anexo_b.py` falla si el
anexo difiere de lo que sale del texto, si una línea de evidencia cita un
hallazgo que no existe o si vuelve a aparecer una `§` en la memoria.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MEMORIA = RAIZ / "docs" / "MEMORIA.md"
HALLAZGOS = RAIZ / "docs" / "HALLAZGOS.md"

INICIO = "## Anexo B. Los hallazgos y dónde se usan"
RE_CABECERA = re.compile(r"^(#{2,3}) (.+)$")
RE_EVIDENCIA = re.compile(r"^\*Evidencia: (.+)\*$")
RE_TITULO = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)
MAX_TITULO = 120


def titulos() -> dict[int, str]:
    """Número y título de cada hallazgo de HALLAZGOS.md."""
    return {int(n): t.strip() for n, t in RE_TITULO.findall(HALLAZGOS.read_text(encoding="utf-8"))}


def titulo_breve(titulo: str) -> str:
    """La primera afirmación del título: hasta el primer ':' o ';' si lo que
    queda antes ya se entiende solo, y nunca más de `MAX_TITULO` caracteres."""
    for corte in (": ", "; "):
        cabeza = titulo.split(corte)[0]
        if len(cabeza) >= 25:
            titulo = cabeza
            break
    if len(titulo) > MAX_TITULO:
        titulo = titulo[:MAX_TITULO].rsplit(" ", 1)[0] + "..."
    return titulo.replace("|", "/")


def numeros_de_evidencia(linea: str) -> set[int]:
    m = RE_EVIDENCIA.match(linea.strip())
    return {int(n) for n in re.findall(r"\d+", m.group(1))} if m else set()


def etiqueta(titulo_seccion: str) -> str:
    """'2.4 El control de acceso...' -> '2.4'; los apartados sin número, por su nombre."""
    m = re.match(r"^(\d+(?:\.\d+)?)\.? ", titulo_seccion)
    return m.group(1) if m else titulo_seccion


def usos(texto: str) -> dict[int, list[str]]:
    """Para cada hallazgo, los apartados cuya línea de evidencia lo cita."""
    cuerpo = texto.split(INICIO)[0]
    salida: dict[int, list[str]] = {}
    seccion = None
    for linea in cuerpo.splitlines():
        if m := RE_CABECERA.match(linea):
            seccion = etiqueta(m.group(2).strip())
            continue
        for n in sorted(numeros_de_evidencia(linea)):
            salida.setdefault(n, [])
            if seccion not in salida[n]:
                salida[n].append(seccion)
    return salida


def tabla(texto: str) -> tuple[str, int]:
    existentes = titulos()
    citados = usos(texto)
    inexistentes = sorted(set(citados) - set(existentes))
    if inexistentes:
        raise ValueError(f"La memoria cita hallazgos que no existen: {inexistentes}")
    filas = [
        f"| {n} | {titulo_breve(t)} | {', '.join(citados.get(n, [])) or '—'} |"
        for n, t in sorted(existentes.items())
    ]
    # Las rayas del separador fijan el ancho relativo de las columnas en pandoc.
    return "\n".join(["| Nº | Qué se midió | Dónde se usa |", "|-|------------|---|", *filas]), len(existentes)


def regenerar(texto: str) -> str:
    i = texto.index(INICIO)
    resto = texto[i:]
    # El anexo termina en la siguiente cabecera de nivel 2, o al final.
    m = re.search(r"\n## ", resto[len(INICIO):])
    fin = i + len(INICIO) + m.start() if m else len(texto)
    tabla_md, total = tabla(texto)
    anexo = (
        f"{INICIO}\n\n"
        f"Los {total} hallazgos de `docs/HALLAZGOS.md`, con lo que midió cada uno y\n"
        "los apartados de esta memoria que se apoyan en él. Cada hallazgo, en ese\n"
        "fichero, explica la medida completa y nombra la ejecución guardada en\n"
        "`reports/` que la respalda, o dice que no la tiene. Los que no se usan en\n"
        "la memoria aparecen con una raya: son medidas intermedias o superadas.\n"
        "Esta tabla se genera desde el texto y una prueba falla si difiere.\n\n"
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
