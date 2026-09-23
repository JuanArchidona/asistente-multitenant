"""Simulacro cronometrado del plan de respuesta a incidentes (`docs/INCIDENTES.md`).

El plan tenía cuatro pasos y ningún reloj: "no hay simulacro" era la primera
carencia declarada de su propio §5, y el registro de riesgos lo tenía como
residual de R-23. Este script pulsa el botón rojo en frío, sobre el sistema
real, y mide lo que se puede medir desde aquí:

1. **Clave revocada.** Se lanza una consulta de producción (`src.main`, la
   que sí registra) con una clave de Anthropic inválida, en un subproceso y
   sin tocar `.env`. Se mide cuánto tarda en fallar, si falla de forma legible
   (un mensaje, no un traceback) y, sobre todo, **si el fallo queda en el
   registro de producción**: la primera vez que se ejecutó, no quedaba (§46).
2. **Congelar la evidencia.** Copia de `reports/` y del registro de producción
   a una carpeta fechada con manifiesto SHA-256 de cada fichero. Se mide el
   tiempo y el tamaño.
3. **Volver.** La misma consulta con la clave buena: cuánto tarda el sistema
   en volver a responder y anotar. Es la única llamada que cuesta dinero
   (una consulta, en torno a 0,002 USD).

Lo que **no** se simula, y se dice: revocar y rotar la clave en la consola
del proveedor. Exige navegador y la cuenta de Juan, y hacerlo de verdad deja
el servicio desplegado sin clave hasta que se rota. Queda como el paso manual
del plan, con el tiempo estimado en el hallazgo, no medido.

    uv run python scripts/simulacro_incidente.py
    uv run python scripts/simulacro_incidente.py --destino data/incidentes --etiqueta simulacro_2
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONSULTA = "¿Cuántos días de vacaciones tengo?"
CLAVE_REVOCADA = "sk-ant-api03-REVOCADA-simulacro"


def _contar(ruta: Path, clave: str | None = None) -> int:
    if not ruta.is_file():
        return 0
    lineas = [ln for ln in ruta.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if clave is None:
        return len(lineas)
    return sum(1 for ln in lineas if f'"{clave}"' in ln)


def _consulta(env_extra: dict[str, str]) -> tuple[float, int, str]:
    env = {**os.environ, **env_extra, "PYTHONIOENCODING": "utf-8"}
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "src.main", CONSULTA],
        cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    return time.perf_counter() - t0, proc.returncode, (proc.stdout + proc.stderr)


def paso_clave_revocada(registro: Path) -> dict:
    antes = _contar(registro)
    fallos_antes = _contar(registro, "_fallo")
    duracion, codigo, salida = _consulta({"ANTHROPIC_API_KEY": CLAVE_REVOCADA})
    lineas_salida = [ln for ln in salida.splitlines() if ln.strip()]
    return {
        "duracion_s": round(duracion, 2),
        "codigo_salida": codigo,
        "fallo": codigo != 0,
        # Legible: la salida es un mensaje corto y no un traceback.
        "legible": "Traceback" not in salida and len(lineas_salida) <= 4,
        "ultima_linea": lineas_salida[-1][:200] if lineas_salida else "",
        "lineas_registro_antes": antes,
        "lineas_registro_despues": _contar(registro),
        "fallos_registrados": _contar(registro, "_fallo") - fallos_antes,
    }


def paso_congelar(destino: Path, registro_raiz: Path) -> dict:
    t0 = time.perf_counter()
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copytree(RAIZ / "reports", destino / "reports", dirs_exist_ok=True)
    if registro_raiz.is_dir():
        shutil.copytree(registro_raiz, destino / "observabilidad", dirs_exist_ok=True)
    ficheros = sorted(p for p in destino.rglob("*") if p.is_file() and p.name != "MANIFIESTO.sha256")
    with (destino / "MANIFIESTO.sha256").open("w", encoding="utf-8") as f:
        for p in ficheros:
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(destino).as_posix()}\n")
    return {
        "duracion_s": round(time.perf_counter() - t0, 2),
        "ficheros": len(ficheros),
        "bytes": sum(p.stat().st_size for p in ficheros),
        "destino": str(destino),
    }


def paso_volver(registro: Path) -> dict:
    antes = _contar(registro)
    duracion, codigo, salida = _consulta({})
    coste = None
    for ln in salida.splitlines():
        if ln.startswith("--- uso:"):
            try:
                coste = json.loads(ln.split(":", 1)[1]).get("coste_usd_estimado")
            except ValueError:
                coste = None
    return {
        "duracion_s": round(duracion, 2),
        "codigo_salida": codigo,
        "respondio": codigo == 0,
        "anotada": _contar(registro) - antes == 1,
        "coste_usd": coste,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", default="data/incidentes", help="Dónde congelar la evidencia.")
    p.add_argument("--etiqueta", default="simulacro_incidente", help="Subcarpeta de reports/.")
    args = p.parse_args()

    sys.path.insert(0, str(RAIZ))
    from src.config import load_config
    from src.observabilidad import RAIZ_POR_DEFECTO

    cfg = load_config(con_juez=False)
    registro = RAIZ / RAIZ_POR_DEFECTO / cfg.tenant.id / "trazas.jsonl"
    ts = datetime.now(UTC)
    print(f"[simulacro] inquilino {cfg.tenant.id} | registro {registro}")

    t_total = time.perf_counter()
    print("[1/3] clave revocada (simulada)...")
    r1 = paso_clave_revocada(registro)
    print(f"      fallo={r1['fallo']} legible={r1['legible']} en {r1['duracion_s']} s; "
          f"fallos registrados: {r1['fallos_registrados']}")
    print(f"      {r1['ultima_linea']}")

    print("[2/3] congelar evidencia...")
    r2 = paso_congelar(RAIZ / args.destino / ts.strftime("%Y%m%dT%H%M%SZ"), RAIZ / RAIZ_POR_DEFECTO)
    print(f"      {r2['ficheros']} ficheros, {r2['bytes'] / 1e6:.1f} MB en {r2['duracion_s']} s")

    print("[3/3] volver con la clave buena...")
    r3 = paso_volver(registro)
    print(f"      respondio={r3['respondio']} anotada={r3['anotada']} en {r3['duracion_s']} s, "
          f"{r3['coste_usd']} USD")

    resumen = {
        "fecha": ts.isoformat(timespec="seconds"),
        "tenant": cfg.tenant.id,
        "consulta": CONSULTA,
        "duracion_total_s": round(time.perf_counter() - t_total, 2),
        "pasos": {"clave_revocada": r1, "congelar_evidencia": r2, "volver": r3},
        "no_simulado": [
            "revocar la clave en la consola del proveedor",
            "rotar la clave y actualizar .env y el servicio desplegado",
        ],
    }
    salida = RAIZ / "reports" / args.etiqueta
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[simulacro] total {resumen['duracion_total_s']} s. Detalle en {salida / 'resumen.json'}")


if __name__ == "__main__":
    main()
