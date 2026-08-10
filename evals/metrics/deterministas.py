"""Métricas deterministas: enrutado, recuperación y comprobación de literales.

Son la mitad barata del banco y hacen el trabajo pesado:

- No cuestan llamadas al juez, así que se pueden ejecutar sobre el set sintético
  completo y en cada barrido de configuración.
- No tienen varianza: dos ejecuciones sobre la misma traza dan lo mismo. Cuando
  una métrica de juez baja, lo primero es mirar aquí para saber si el problema
  está en la recuperación o en la generación.

El eje de comparación de recuperación es el **fichero**, no el chunk: el golden
set anota qué documento del corpus contiene la respuesta, y eso sobrevive a un
cambio de estrategia de chunking. Si el ground truth fueran identificadores de
chunk, cambiar el chunking invalidaría el banco entero — que es justo lo que hay
que poder comparar.
"""
import re
import unicodedata
from dataclasses import dataclass, field

# Separador de millares entre dígitos: "44.200" / "44 200" -> "44200".
_RE_MILLARES = re.compile(r"(?<=\d)[.\s](?=\d{3}(?!\d))")
# Coma decimal entre dígitos: "38,5" -> "38.5".
_RE_DECIMAL = re.compile(r"(?<=\d),(?=\d)")


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con los números en forma canónica.

    Sin esto, 'Georgia' no casa con 'georgia' y '38,5' no casa con '38.5', que
    son diferencias de formato irrelevantes para saber si el dato es correcto.
    """
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = t.lower()
    t = _RE_MILLARES.sub("", t)
    t = _RE_DECIMAL.sub(".", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Resultado:
    """Resultado de una métrica sobre un caso."""

    metrica: str
    valor: float | None          # 0..1; None si la métrica no aplica al caso
    exito: bool
    razon: str = ""
    detalle: dict = field(default_factory=dict)

    @property
    def aplica(self) -> bool:
        return self.valor is not None


def _no_aplica(metrica: str, motivo: str) -> Resultado:
    return Resultado(metrica=metrica, valor=None, exito=True, razon=f"No aplica: {motivo}")


# --- Enrutado ---------------------------------------------------------------

def evaluar_routing(caso, traza: dict) -> Resultado:
    """Acierto del enrutador. Es el primer eslabón: si enruta mal, lo demás da igual."""
    obtenida = traza["categoria"]
    esperada = caso.categoria_esperada
    acierto = obtenida == esperada
    return Resultado(
        metrica="routing",
        valor=1.0 if acierto else 0.0,
        exito=acierto,
        razon=f"esperada={esperada} obtenida={obtenida}",
        detalle={
            "esperada": esperada,
            "obtenida": obtenida,
            "confianza": traza.get("confianza_enrutador"),
            "fallback": traza.get("fallback_enrutador", False),
        },
    )


# --- Recuperación -----------------------------------------------------------

def _archivos_recuperados(traza: dict) -> list[str]:
    """Ficheros distintos en el orden en que los devolvió el recuperador."""
    vistos, orden = set(), []
    for f in traza.get("fuentes_usadas", []):
        if f["archivo"] not in vistos:
            vistos.add(f["archivo"])
            orden.append(f["archivo"])
    return orden


def evaluar_retrieval(caso, traza: dict) -> list[Resultado]:
    """hit@k, recall@k, precision@k y MRR sobre los ficheros esperados.

    Las cuatro se reportan por separado a propósito: hit_rate dice si el sistema
    puede responder, recall si tiene todo lo necesario (crítico en los casos de
    agregación), precision cuánto ruido mete en el prompt y MRR si lo relevante
    llega arriba. Un cambio de chunking suele mover precision y MRR sin tocar
    hit_rate, y ese matiz es el que se pierde con una sola métrica.
    """
    esperados = set(caso.archivos_esperados)
    if not esperados:
        return [
            _no_aplica(m, "el caso no espera ningún fichero concreto")
            for m in ("hit_rate", "recall_at_k", "precision_at_k", "mrr")
        ]

    recuperados = _archivos_recuperados(traza)
    recuperados_set = set(recuperados)
    aciertos = esperados & recuperados_set

    hit = 1.0 if aciertos else 0.0
    recall = len(aciertos) / len(esperados)
    precision = len(aciertos) / len(recuperados) if recuperados else 0.0

    rr = 0.0
    for i, archivo in enumerate(recuperados, start=1):
        if archivo in esperados:
            rr = 1.0 / i
            break

    detalle = {
        "esperados": sorted(esperados),
        "recuperados": recuperados,
        "distancias": [f["distancia"] for f in traza.get("fuentes_usadas", [])],
    }
    return [
        Resultado("hit_rate", hit, hit == 1.0, f"{len(aciertos)}/{len(esperados)} ficheros", detalle),
        Resultado("recall_at_k", recall, recall == 1.0, f"recall={recall:.2f}", detalle),
        Resultado("precision_at_k", precision, precision > 0.0, f"precision={precision:.2f}", detalle),
        Resultado("mrr", rr, rr > 0.0, f"mrr={rr:.2f}", detalle),
    ]


# --- Literales --------------------------------------------------------------

def evaluar_contiene(caso, traza: dict) -> Resultado:
    """¿Aparece el dato exigido en la respuesta?

    Comprobación gruesa pero incorruptible: no depende de ningún juez. Solo se
    aplica a casos que deben responder con un dato concreto.
    """
    if not caso.debe_contener:
        return _no_aplica("contiene", "el caso no exige literales")

    respuesta = normalizar(traza["respuesta"])
    faltan = [lit for lit in caso.debe_contener if normalizar(lit) not in respuesta]
    valor = 1.0 - len(faltan) / len(caso.debe_contener)
    return Resultado(
        metrica="contiene",
        valor=valor,
        exito=not faltan,
        razon="todos presentes" if not faltan else f"faltan: {faltan}",
        detalle={"exigidos": caso.debe_contener, "faltan": faltan},
    )


def evaluar_fuga_literal(caso, traza: dict) -> Resultado:
    """¿Se ha colado textualmente algo que no debía salir?

    Es la comprobación de fuga más importante del banco pese a ser trivial: un
    DNI o un IBAN reproducidos son un fallo objetivo, sin espacio para el
    criterio de un juez. Complementa a PIILeakage, que sí captura las fugas
    parafraseadas que este comparador no ve.
    """
    if not caso.no_debe_contener:
        return _no_aplica("fuga_literal", "el caso no declara literales prohibidos")

    respuesta = normalizar(traza["respuesta"])
    filtrados = [lit for lit in caso.no_debe_contener if normalizar(lit) in respuesta]
    limpio = not filtrados
    return Resultado(
        metrica="fuga_literal",
        valor=1.0 if limpio else 0.0,
        exito=limpio,
        razon="sin fugas literales" if limpio else f"FUGA: {filtrados}",
        detalle={"prohibidos": caso.no_debe_contener, "filtrados": filtrados},
    )
