"""Enrutador sin modelo de lenguaje: clasifica por proximidad de embeddings.

Es el "clasificador con modelo pequeño" del bloque 3 de `docs/ALCANCE.md`,
construido para **compararlo con medidas** contra el enrutador de Haiku, no
para sustituirlo por decreto. El enrutador LLM es la línea base heredada y su
prompt está protegido por un test; este módulo no lo toca: es una alternativa
conmutable con `ROUTER_KIND`, y por defecto está apagada.

Dos variantes, las dos sin entrenamiento y sin un solo dato etiquetado:

- **`descripciones`** (zero-shot). Se embeben las descripciones de las
  categorías que el inquilino declara en su manifiesto y se elige la más
  cercana a la consulta. Es exactamente la misma información que recibe el
  enrutador LLM en su prompt, leída con otro instrumento.
- **`indice`**. Se buscan los fragmentos más cercanos a la consulta en el
  índice del inquilino y se vota por la fuente a la que pertenecen. El corpus
  hace de conjunto de entrenamiento sin haberlo etiquetado nadie. Las
  categorías sin corpus (destino estructurado) solo pueden reconocerse por su
  descripción, así que esta variante cae en la anterior para ellas.

`otro` sale por umbral: si nada se parece lo bastante, la consulta no encaja.
El umbral no se elige a ojo ni sobre el mismo banco que después lo puntúa: se
calibra sobre el inquilino heredado y se aplica sin tocar a los otros dos
(`evals/comparar_enrutadores.py`, §48).

Lo que se gana si funciona: ninguna llamada al modelo de chat para enrutar
—una consulta ya necesita su embedding para recuperar, así que el enrutado
sale gratis—, latencia de milisegundos en vez de un segundo, determinismo
completo, y ninguna superficie de inyección: una consulta no puede convencer
a un producto escalar de nada. Lo que se puede perder es lo que hay que medir.
"""
import math

from .schema import Enrutamiento
from .tenant import CATEGORIA_OTRO, DESTINO_ESTRUCTURADO, Tenant

VARIANTES = ("descripciones", "indice")

# Umbral de similitud (coseno) por debajo del cual la consulta va a `otro`.
# Calibrado sobre el inquilino heredado el 23-09-2026 (§48) y aplicado tal
# cual a los demás; `ROUTER_UMBRAL_OTRO` lo cambia.
UMBRAL_OTRO_POR_DEFECTO = 0.55

# Fragmentos consultados al índice para la votación. Más que `top_k` de la
# recuperación a propósito: aquí no importa leerlos, importa contar de dónde
# vienen, y con cuatro un empate es demasiado fácil.
K_VOTACION = 8


def similitud_coseno(a: list[float], b: list[float]) -> float:
    punto = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return punto / (na * nb) if na and nb else 0.0


def _acotar(valor: float) -> float:
    return max(0.0, min(1.0, valor))


class EnrutadorEmbeddings:
    """Clasifica consultas por proximidad, con los prototipos calculados una vez."""

    def __init__(
        self,
        tenant: Tenant,
        embedder,
        coleccion=None,
        variante: str = "descripciones",
        umbral_otro: float = UMBRAL_OTRO_POR_DEFECTO,
        k: int = K_VOTACION,
    ):
        if variante not in VARIANTES:
            raise ValueError(f"variante desconocida {variante!r}; usa una de {VARIANTES}")
        if variante == "indice" and coleccion is None:
            raise ValueError("la variante 'indice' necesita la colección del inquilino")
        self.tenant = tenant
        self.embedder = embedder
        self.col = coleccion
        self.variante = variante
        self.umbral_otro = umbral_otro
        self.k = k
        self.categorias = list(tenant.categorias)
        # Un prototipo por categoría: el mismo texto que ve el enrutador LLM.
        self.prototipos = embedder.embed_documentos(
            [f"{c.nombre}: {c.descripcion}" for c in self.categorias]
        )
        self._categoria_de_fuente = {
            c.fuente: c.nombre for c in self.categorias if c.destino != DESTINO_ESTRUCTURADO
        }

    # --- Variante 1: descripciones ---------------------------------------

    def similitudes(self, vector: list[float]) -> dict[str, float]:
        return {
            c.nombre: similitud_coseno(vector, p)
            for c, p in zip(self.categorias, self.prototipos, strict=True)
        }

    def _por_descripciones(self, vector: list[float]) -> Enrutamiento:
        sims = self.similitudes(vector)
        mejor = max(sims, key=sims.get)
        if sims[mejor] < self.umbral_otro:
            return Enrutamiento(
                categoria=CATEGORIA_OTRO,
                justificacion=f"embeddings/descripciones: la más cercana es {mejor} "
                f"a {sims[mejor]:.3f}, bajo el umbral {self.umbral_otro:.2f}",
                confianza=_acotar(sims[mejor]),
                fallback=False,
            )
        return Enrutamiento(
            categoria=mejor,
            justificacion=f"embeddings/descripciones: similitud {sims[mejor]:.3f}",
            confianza=_acotar(sims[mejor]),
            fallback=False,
        )

    # --- Variante 2: votación sobre el índice ------------------------------

    def votos(self, vector: list[float]) -> tuple[dict[str, float], float]:
        """Peso por categoría documental entre los k fragmentos más cercanos,
        y la similitud del más cercano de todos."""
        res = self.col.query(
            query_embeddings=[vector], n_results=self.k, include=["metadatas", "distances"]
        )
        pesos: dict[str, float] = {}
        mejor_sim = 0.0
        for meta, dist in zip(res["metadatas"][0], res["distances"][0], strict=True):
            sim = 1.0 - dist
            mejor_sim = max(mejor_sim, sim)
            categoria = self._categoria_de_fuente.get(meta.get("fuente"))
            if categoria is None:
                continue
            pesos[categoria] = pesos.get(categoria, 0.0) + max(sim, 0.0)
        return pesos, mejor_sim

    def _por_indice(self, vector: list[float]) -> Enrutamiento:
        # Las categorías sin corpus solo se reconocen por su descripción: si la
        # descripción más cercana es una de ellas y supera el umbral, gana.
        sims = self.similitudes(vector)
        mejor_desc = max(sims, key=sims.get)
        if (
            self.tenant.destino_de(mejor_desc) == DESTINO_ESTRUCTURADO
            and sims[mejor_desc] >= self.umbral_otro
        ):
            return Enrutamiento(
                categoria=mejor_desc,
                justificacion=f"embeddings/indice: categoría sin corpus, por descripción "
                f"a {sims[mejor_desc]:.3f}",
                confianza=_acotar(sims[mejor_desc]),
                fallback=False,
            )
        pesos, mejor_sim = self.votos(vector)
        if not pesos or mejor_sim < self.umbral_otro:
            return Enrutamiento(
                categoria=CATEGORIA_OTRO,
                justificacion=f"embeddings/indice: el fragmento más cercano está a "
                f"{mejor_sim:.3f}, bajo el umbral {self.umbral_otro:.2f}",
                confianza=_acotar(mejor_sim),
                fallback=False,
            )
        total = sum(pesos.values())
        ganadora = max(pesos, key=pesos.get)
        return Enrutamiento(
            categoria=ganadora,
            justificacion=f"embeddings/indice: {pesos[ganadora] / total:.0%} del peso de "
            f"{self.k} fragmentos",
            confianza=_acotar(pesos[ganadora] / total),
            fallback=False,
        )

    # --- Entrada ------------------------------------------------------------

    def enrutar(self, consulta: str, vector: list[float] | None = None) -> Enrutamiento:
        """Clasifica. Acepta el vector ya calculado para no embeber dos veces."""
        if vector is None:
            vector = self.embedder.embed_consulta(consulta)
        if self.variante == "indice":
            return self._por_indice(vector)
        return self._por_descripciones(vector)
