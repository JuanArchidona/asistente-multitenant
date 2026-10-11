"""Verificación determinista de citas, compartida por el banco y por producción.

Vivía en `evals/metrics/deterministas.py` (HALLAZGOS.md §23) y se movió aquí el
11-10-2026 sin cambiar una regla, para que el servicio desplegado evalúe cada
respuesta con exactamente el mismo criterio que el banco
(`src/evaluacion_produccion.py`) sin que `src/` dependa de `evals/`. Las
reglas y su porqué siguen documentados junto a `evaluar_citas`, en el banco.
"""
import re
import unicodedata

RE_ARCHIVO_MD = re.compile(r"[\w.\-/]+\.md\b", re.IGNORECASE)


def canonico(nombre: str) -> str:
    """Nombre de fichero en minúsculas y sin acentos.

    Hace falta y se descubrió midiendo. El primer censo retroactivo marcó seis
    citas como inventadas y **las seis eran culpa de la métrica**: el corpus
    tiene `politica_valoracion.md` y `guia_estilo_python.md`, y el modelo las
    escribe como las escribiría cualquiera en español, con tilde. El documento
    estaba recuperado y la cita era buena; lo que fallaba era comparar bytes.

    Acusar de fabricar una fuente es la acusación más grave que hace este
    banco, así que la comparación tiene que ser insensible a lo que es
    ortografía y no atribución. Ver `docs/HALLAZGOS.md` §23.
    """
    sin_tilde = unicodedata.normalize("NFKD", nombre.lower())
    return "".join(c for c in sin_tilde if not unicodedata.combining(c))


def citables(traza: dict) -> tuple[set[str], set[str]]:
    """Lo que esta traza permite citar: (ficheros, herramientas).

    Los ficheros se devuelven como nombre completo en minúsculas; las
    herramientas, con y sin el prefijo del servidor MCP.
    """
    archivos = {
        canonico(f["archivo"])
        for f in traza.get("fuentes_usadas", [])
        if f.get("archivo")
    }
    herramientas: set[str] = set()
    for paso in traza.get("herramientas_invocadas") or []:
        nombre = paso.get("herramienta")
        if not nombre:
            continue
        herramientas.add(canonico(nombre))
        # `crm__estado_operacion` -> también `estado_operacion`: es como lo
        # escribe el modelo en la respuesta.
        if "__" in nombre:
            herramientas.add(canonico(nombre.split("__", 1)[1]))
    return archivos, herramientas


def citas_de_fichero(respuesta: str) -> list[str]:
    """Ficheros citados explícitamente, con extensión. Regla conservadora."""
    vistos, orden = set(), []
    for bruto in RE_ARCHIVO_MD.findall(respuesta or ""):
        nombre = canonico(bruto.rsplit("/", 1)[-1])
        if nombre not in vistos:
            vistos.add(nombre)
            orden.append(nombre)
    return orden


def menciona_alguna_fuente(respuesta: str, archivos: set[str], herramientas: set[str]) -> bool:
    """¿Aparece alguna fuente recuperada, en cualquier forma reconocible?"""
    texto = canonico(respuesta or "")
    for archivo in archivos:
        if archivo in texto:
            return True
        # Sin extensión: "según convenio_colectivo" también es una cita. Y con
        # los separadores en espacios, porque el modelo cita en prosa: para
        # `acta_captaciones_2026-08-24.md` escribe "el acta de captaciones del
        # 24 de agosto", que identifica el documento igual de bien.
        tallo = archivo.rsplit(".", 1)[0]
        if len(tallo) < 6:
            continue
        if tallo in texto:
            return True
        palabras = [p for p in re.split(r"[_\-]+", tallo) if len(p) > 3]
        if palabras and all(p in texto for p in palabras):
            return True
    return any(h in texto for h in herramientas)
