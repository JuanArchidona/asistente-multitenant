"""Transcripcion local de un video o audio del master (tutorias, clases).

    uv sync --group material
    uv run python scripts/transcribir_material.py --entrada "https://..." \
        --salida "../../Módulo 5/Grabaciones/tutoria_2026-10-06" [--cookies-chrome]
    uv run python scripts/transcribir_material.py --entrada video.mp4 --salida ...

Existe porque la app de Claude puede navegar el campus pero no escuchar un
video: localiza la fuente y Claude Code la descarga y la transcribe aqui, en
CPU y sin mandar el audio a ningun servicio externo.

La entrada es una URL (la descarga yt-dlp, solo el audio; `--cookies-chrome`
reutiliza la sesion del navegador si el video exige estar dentro del campus)
o un fichero local. La salida es una ruta sin extension: se escriben
`<salida>.txt` con marcas de tiempo cada segmento, `<salida>.srt` y
`<salida>.json` con la duracion, el modelo, el idioma detectado y el tiempo
de transcripcion, para poder decir cuanto costo.

**La salida va fuera del repositorio.** Una tutoria es material docente y el
repositorio es publico (CLAUDE.md seccion 8); este script solo es la
herramienta. Si la ruta de salida cae dentro del repositorio, se niega.
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _dentro_del_repo(ruta: Path) -> bool:
    try:
        ruta.resolve().relative_to(RAIZ)
        return True
    except ValueError:
        return False


def descargar_audio(url: str, destino: Path, cookies_chrome: bool) -> Path:
    import imageio_ffmpeg
    import yt_dlp

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": str(destino.with_suffix(".%(ext)s")),
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "noplaylist": True,
        "quiet": False,
    }
    if cookies_chrome:
        opciones["cookiesfrombrowser"] = ("chrome",)
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info))


def _marca(segundos: float, separador: str = ".") -> str:
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{separador}{ms:03d}"


def transcribir(audio: Path, salida: Path, modelo: str, idioma: str | None) -> dict:
    from faster_whisper import WhisperModel

    inicio = time.perf_counter()
    whisper = WhisperModel(modelo, device="cpu", compute_type="int8")
    segmentos, info = whisper.transcribe(
        str(audio), language=idioma, vad_filter=True, beam_size=5
    )
    lineas_txt, bloques_srt = [], []
    for i, seg in enumerate(segmentos, start=1):
        texto = seg.text.strip()
        lineas_txt.append(f"[{_marca(seg.start)[:8]}] {texto}")
        bloques_srt.append(
            f"{i}\n{_marca(seg.start, ',')} --> {_marca(seg.end, ',')}\n{texto}\n"
        )
        if i % 50 == 0:
            print(f"  {_marca(seg.end)[:8]} de {_marca(info.duration)[:8]}", flush=True)
    segundos = time.perf_counter() - inicio

    salida.with_suffix(".txt").write_text("\n".join(lineas_txt) + "\n", encoding="utf-8")
    salida.with_suffix(".srt").write_text("\n".join(bloques_srt), encoding="utf-8")
    resumen = {
        "fuente": str(audio),
        "modelo": modelo,
        "idioma": info.language,
        "probabilidad_idioma": round(info.language_probability, 3),
        "duracion_s": round(info.duration, 1),
        "transcripcion_s": round(segundos, 1),
        "factor_tiempo_real": round(segundos / info.duration, 3) if info.duration else None,
        "segmentos": len(lineas_txt),
    }
    salida.with_suffix(".json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return resumen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entrada", required=True, help="URL o fichero de audio/video")
    p.add_argument("--salida", required=True, help="Ruta sin extension, fuera del repo")
    p.add_argument("--modelo", default="large-v3-turbo")
    p.add_argument("--idioma", default="es", help="'auto' para detectarlo")
    p.add_argument("--cookies-chrome", action="store_true")
    args = p.parse_args()

    salida = Path(args.salida)
    if _dentro_del_repo(salida):
        print("La salida cae dentro del repositorio, que es publico. Elige otra ruta.")
        return 2
    salida.parent.mkdir(parents=True, exist_ok=True)

    if args.entrada.startswith(("http://", "https://")):
        audio = descargar_audio(args.entrada, salida, args.cookies_chrome)
    else:
        audio = Path(args.entrada)
        if not audio.exists():
            print(f"No existe: {audio}")
            return 2

    idioma = None if args.idioma == "auto" else args.idioma
    resumen = transcribir(audio, salida, args.modelo, idioma)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
