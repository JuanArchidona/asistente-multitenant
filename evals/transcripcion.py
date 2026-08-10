"""Evaluación del agente transcriptor (flujo heredado de la entrega 2.1).

El asistente RAG no es todo el sistema: el corpus de actas lo escribe un agente
que convierte una transcripción en un `Acta` estructurada. Si ese agente inventa
una decisión, la alucinación entra en el corpus y a partir de ahí el RAG la
"recupera correctamente". Evaluar solo el RAG dejaría ciega justo la vía por la
que se contamina la base de conocimiento.

Aquí no hace falta juez LLM: la salida es un objeto con campos, así que se puede
comparar con el esperado de forma determinista. Lo único que exige criterio es
emparejar frases libres (decisiones y tareas), que se resuelve con solape de
tokens en vez de igualdad literal — "Carlos prepara el plan de rollback antes
del 20 de mayo" y "Preparar plan de rollback (Carlos, 20/5)" son la misma tarea.
"""
import re
import unicodedata

from src.config import Config
from src.provider import ChatProvider
from src.transcriber import transcribir

from .schema import CasoTranscripcion

UMBRAL_EMPAREJAMIENTO = 0.5
PALABRAS_VACIAS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en", "para",
    "por", "con", "que", "se", "al", "lo", "su", "sus", "es", "antes", "hasta",
}


def _tokens(texto: str) -> set[str]:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return {p for p in re.findall(r"[a-z0-9]+", t) if p not in PALABRAS_VACIAS and len(p) > 1}


def similitud_tokens(a: str, b: str) -> float:
    """F1 de tokens: 1.0 si dicen lo mismo con otras palabras de relleno."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    comunes = len(ta & tb)
    if not comunes:
        return 0.0
    precision = comunes / len(tb)
    recall = comunes / len(ta)
    return 2 * precision * recall / (precision + recall)


def _f1_listas(esperadas: list[str], obtenidas: list[str]) -> float | None:
    """F1 de conjuntos con emparejamiento voraz por similitud de tokens."""
    if not esperadas:
        return None
    if not obtenidas:
        return 0.0

    libres = list(obtenidas)
    emparejadas = 0
    for esperada in esperadas:
        mejor, mejor_sim = None, 0.0
        for candidata in libres:
            sim = similitud_tokens(esperada, candidata)
            if sim > mejor_sim:
                mejor, mejor_sim = candidata, sim
        if mejor is not None and mejor_sim >= UMBRAL_EMPAREJAMIENTO:
            libres.remove(mejor)
            emparejadas += 1

    precision = emparejadas / len(obtenidas)
    recall = emparejadas / len(esperadas)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _coincide_persona(esperada: str, obtenida: str) -> bool:
    te, to = _tokens(esperada), _tokens(obtenida)
    return bool(te & to)


def _f1_personas(esperadas: list[str], obtenidas: list[str]) -> float | None:
    if not esperadas:
        return None
    if not obtenidas:
        return 0.0
    libres = list(obtenidas)
    aciertos = 0
    for e in esperadas:
        for o in libres:
            if _coincide_persona(e, o):
                libres.remove(o)
                aciertos += 1
                break
    precision = aciertos / len(obtenidas)
    recall = aciertos / len(esperadas)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def ejecutar_transcripcion(
    cfg: Config, chat: ChatProvider, casos: list[CasoTranscripcion]
) -> list[dict]:
    salidas = []
    for i, caso in enumerate(casos, start=1):
        try:
            acta = transcribir(cfg, chat, caso.texto)
            salidas.append({"ok": True, "acta": acta.model_dump(mode="json")})
        except Exception as e:  # noqa: BLE001 -- frontera con el modelo
            salidas.append({"ok": False, "error": f"{type(e).__name__}: {e}", "acta": None})
        print(f"\r[transcripcion] {i}/{len(casos)}", end="", flush=True)
    print()
    return salidas


def evaluar_transcripcion(caso: CasoTranscripcion, salida: dict) -> dict:
    acta = salida.get("acta")
    if acta is None:
        return {
            "id": caso.id,
            "ok": False,
            "error": salida.get("error"),
            "acta": None,
            "metricas": {
                "titulo": 0.0, "fecha": 0.0, "asistentes_f1": 0.0,
                "decisiones_f1": 0.0, "tareas_f1": 0.0, "sin_fuga": 0.0,
            },
        }

    titulo = similitud_tokens(caso.titulo_esperado, acta.get("titulo", "")) if caso.titulo_esperado else None
    fecha = 1.0 if (acta.get("fecha") or None) == (caso.fecha_esperada or None) else 0.0
    asistentes = _f1_personas(caso.asistentes_esperados, acta.get("asistentes", []))
    decisiones = _f1_listas(caso.decisiones_esperadas, acta.get("decisiones", []))
    tareas = _f1_listas(caso.tareas_esperadas, acta.get("tareas", []))

    plano = " ".join(
        [str(acta.get("titulo", "")), str(acta.get("resumen", "")), str(acta.get("fecha") or "")]
        + list(acta.get("asistentes", []))
        + list(acta.get("decisiones", []))
        + list(acta.get("tareas", []))
    )
    plano_norm = " ".join(sorted(_tokens(plano)))
    fugas = [lit for lit in caso.no_debe_contener if _tokens(lit) and _tokens(lit) <= set(plano_norm.split())]
    sin_fuga = 0.0 if fugas else 1.0

    metricas = {
        "titulo": titulo,
        "fecha": fecha,
        "asistentes_f1": asistentes,
        "decisiones_f1": decisiones,
        "tareas_f1": tareas,
        "sin_fuga": sin_fuga,
    }
    # Umbrales: la fecha y la ausencia de fugas son binarias y no se negocian;
    # en los campos de texto libre se exige 0,6 de F1, por debajo del cual el
    # acta ya no refleja lo que se acordó.
    ok = (
        fecha == 1.0
        and sin_fuga == 1.0
        and all(v is None or v >= 0.6 for v in (titulo, asistentes, decisiones, tareas))
    )
    return {
        "id": caso.id,
        "ok": ok,
        "nota": caso.nota,
        "acta": acta,
        "fugas": fugas,
        "metricas": metricas,
        "esperado": {
            "titulo": caso.titulo_esperado,
            "fecha": caso.fecha_esperada,
            "asistentes": caso.asistentes_esperados,
            "decisiones": caso.decisiones_esperadas,
            "tareas": caso.tareas_esperadas,
        },
    }
