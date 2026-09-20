"""Recuperación filtrada por fuente.

Embebe la consulta (RETRIEVAL_QUERY) y busca en ChromaDB restringiendo por el
metadato 'fuente' que dictó el enrutador. Ese filtrado es lo que materializa el
valor del enrutamiento: cada consulta solo ve la fuente pertinente.

Novedad de la 3.3: `Config.distance_threshold`. La 3.1 devolvía siempre `top_k`
fragmentos aunque fueran irrelevantes, así que el único freno a la alucinación
era el prompt. Con umbral activo, los fragmentos por encima de esa distancia se
descartan y el generador puede quedarse sin contexto — que es la forma explícita
y medible de decir "no hay documentación relevante". Por defecto viene apagado
(`None`) para que la línea base evaluada sea exactamente el MVP de la 3.1.
"""
import chromadb

from .config import Config
from .embeddings import GeminiEmbedder
from .gobernanza import USUARIO_ANONIMO, Usuario


class Recuperado:
    def __init__(self, texto: str, fuente: str, archivo: str, distancia: float):
        self.texto = texto
        self.fuente = fuente
        self.archivo = archivo
        self.distancia = distancia


class Retriever:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.embedder = GeminiEmbedder(cfg)
        client = chromadb.PersistentClient(path=cfg.chroma_path)
        self.col = client.get_collection(cfg.collection)

    def recuperar(
        self, consulta: str, fuente: str, usuario: Usuario | None = None
    ) -> list[Recuperado]:
        """Recupera de una fuente, limitado a lo que este usuario puede ver.

        El permiso entra en el `where` de la búsqueda, no en un filtro
        posterior: un documento restringido no llega a salir del índice. Si se
        recuperase y se descartase después, el texto habría estado en memoria
        del proceso y el control dependería de que nadie lo registre por el
        camino, que es exactamente la clase de garantía que no se sostiene.
        """
        usuario = usuario or USUARIO_ANONIMO
        vector = self.embedder.embed_consulta(consulta)
        res = self.col.query(
            query_embeddings=[vector],
            n_results=self.cfg.top_k,
            where={
                "$and": [
                    {"fuente": fuente},
                    {"requiere": {"$in": usuario.niveles_visibles}},
                ]
            },
        )
        salidas = []
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        for texto, meta, dist in zip(docs, metas, dists):
            if self.cfg.distance_threshold is not None and dist > self.cfg.distance_threshold:
                continue
            salidas.append(Recuperado(texto, meta["fuente"], meta["archivo"], dist))
        return salidas
