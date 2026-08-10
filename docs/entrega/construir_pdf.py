"""Construye el PDF de entrega desde el markdown.

    uv run python docs/entrega/construir_pdf.py

Cadena: markdown -> (pandoc) -> HTML autocontenido con estilos de impresión ->
(Chrome headless) -> PDF. Se eligió esta vía en lugar de pandoc con LaTeX porque
no exige instalar una distribución TeX de un giga, y porque el motor de
impresión de Chrome respeta el CSS de `@page`, con lo que el mismo fichero de
estilos sirve para revisar el HTML en pantalla y para el PDF final.

Requisitos: pandoc y Chrome o Edge. El script los localiza solo en las rutas
habituales de Windows; con `--pandoc` y `--navegador` se pueden forzar.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]

CANDIDATOS_PANDOC = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages",
    Path("C:/Program Files/Pandoc"),
]

CANDIDATOS_NAVEGADOR = [
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
]


def localizar_pandoc(forzado: str | None) -> str:
    if forzado:
        return forzado
    if ruta := shutil.which("pandoc"):
        return ruta
    for base in CANDIDATOS_PANDOC:
        if base.is_dir():
            for hallado in base.rglob("pandoc.exe"):
                return str(hallado)
    sys.exit(
        "No se encontró pandoc. Instálalo con:\n"
        "  winget install --id JohnMacFarlane.Pandoc\n"
        "o indícalo con --pandoc RUTA"
    )


def localizar_navegador(forzado: str | None) -> str:
    if forzado:
        return forzado
    for ruta in CANDIDATOS_NAVEGADOR:
        if ruta.is_file():
            return str(ruta)
    sys.exit("No se encontró Chrome ni Edge. Indica uno con --navegador RUTA.")


def md_a_html(pandoc: str, entrada: Path, salida: Path, css: Path) -> None:
    subprocess.run(
        [
            pandoc,
            str(entrada),
            "--from", "markdown+pipe_tables+yaml_metadata_block",
            "--to", "html5",
            "--standalone",
            # Empotra el CSS en el HTML: el fichero resultante se puede abrir
            # o mover sin arrastrar dependencias.
            "--embed-resources",
            "--css", str(css),
            "--metadata", "lang=es",
            "--output", str(salida),
        ],
        check=True,
    )


def html_a_pdf(navegador: str, entrada: Path, salida: Path) -> None:
    # Chrome escribe el PDF en la ruta indicada y sale. El perfil temporal evita
    # que se enganche a una ventana ya abierta en vez de imprimir.
    with tempfile.TemporaryDirectory() as perfil:
        subprocess.run(
            [
                navegador,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={perfil}",
                # Da tiempo a que el motor aplique fuentes y estilos antes de imprimir.
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=10000",
                f"--print-to-pdf={salida}",
                entrada.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Genera el PDF de entrega")
    p.add_argument("--entrada", default=str(AQUI / "Entrega_Modulo_3.3_Juan_Archidona.md"))
    p.add_argument("--salida", default=str(RAIZ / "Entrega_Modulo_3.3_Juan_Archidona.pdf"))
    p.add_argument("--css", default=str(AQUI / "estilo.css"))
    p.add_argument("--pandoc")
    p.add_argument("--navegador")
    p.add_argument("--conservar-html", action="store_true", help="Deja el HTML intermedio")
    args = p.parse_args()

    entrada, salida, css = Path(args.entrada), Path(args.salida), Path(args.css)
    if not entrada.is_file():
        sys.exit(f"No existe el markdown de entrada: {entrada}")

    pandoc = localizar_pandoc(args.pandoc)
    navegador = localizar_navegador(args.navegador)
    html = entrada.with_suffix(".html")

    print(f"[1/2] {entrada.name} -> HTML (pandoc)")
    md_a_html(pandoc, entrada, html, css)

    print(f"[2/2] HTML -> {salida.name} ({Path(navegador).stem} headless)")
    html_a_pdf(navegador, html, salida)

    if not args.conservar_html:
        html.unlink(missing_ok=True)

    if not salida.is_file():
        sys.exit("El navegador terminó pero no escribió el PDF.")
    print(f"[OK] {salida}  ({salida.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
