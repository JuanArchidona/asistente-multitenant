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
from dataclasses import dataclass, field

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


@dataclass
class Recuperacion:
    """Lo que la búsqueda devolvió y lo que el permiso dejó fuera.

    Las dos cosas juntas porque por separado engañan. Una recuperación vacía
    puede significar "no hay nada que responda a esto" o "hay material y no es
    para ti", y son situaciones opuestas: la primera es un corpus incompleto, la
    segunda es el control funcionando. Sin `denegados` no se distinguen, y el
    banco daba la segunda por la primera.
    """

    fragmentos: list[Recuperado] = field(default_factory=list)
    denegados: list[str] = field(default_factory=list)


class Retriever:
    def __init__(self, cfg: Config, uso=None):
        self.cfg = cfg
        # `uso` es el acumulador del sistema: con el, cada consulta embebida
        # se contabiliza (estimada por caracteres, ver GeminiEmbedder).
        self.embedder = GeminiEmbedder(cfg, uso=uso)
        client = chromadb.PersistentClient(path=cfg.chroma_path)
        self.col = client.get_collection(cfg.collection)

    def recuperar(
        self, consulta: str, fuente: str, usuario: Usuario | None = None
    ) -> list[Recuperado]:
        """Solo los fragmentos. Atajo para quien no necesita saber qué se denegó."""
        return self.recuperar_con_control(consulta, fuente, usuario).fragmentos

    def recuperar_con_control(
        self, consulta: str, fuente: str, usuario: Usuario | None = None
    ) -> Recuperacion:
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
        return Recuperacion(salidas, self._denegados(vector, fuente, usuario))

    def _denegados(self, vector: list[float], fuente: str, usuario: Usuario) -> list[str]:
        """Qué documentos habría traído esta misma búsqueda con más permisos.

        Segunda consulta sobre el vector ya calculado, **pidiendo solo
        metadatos**: el texto restringido sigue sin salir del índice. Lo que sale
        es el nombre del fichero y el rol que exige, que es justo lo que un
        registro de auditoría tiene que poder anotar — y lo mismo que la rama
        estructurada ya publica en `campos_redactados`.

        No se le pasa al generador. Solo va a la traza, para que una recuperación
        vacía se pueda leer: sin esto, "el control lo retuvo todo" y "no hay nada
        en el corpus" son el mismo silencio.
        """
        res = self.col.query(
            query_embeddings=[vector],
            n_results=self.cfg.top_k,
            where={"fuente": fuente},
            include=["metadatas"],
        )
        visibles = set(usuario.niveles_visibles)
        vistos, orden = set(), []
        for meta in res["metadatas"][0]:
            archivo = meta["archivo"]
            if meta["requiere"] not in visibles and archivo not in vistos:
                vistos.add(archivo)
                orden.append(archivo)
        return orden
