"""Variantes de configuración e índices asociados.

Todo experimento del banco es "la misma pregunta contra otra configuración".
Para que eso funcione hay que resolver un detalle nada menor: los parámetros que
afectan a la **indexación** (estrategia y tamaño de chunk, modelo y dimensiones
del embedder) obligan a reconstruir el índice, y si todas las variantes
escribieran en la misma colección se pisarían entre sí y el barrido daría
resultados absurdos.

La solución es derivar el nombre de la colección de una firma de esos
parámetros: cada configuración tiene su índice, se construye una sola vez y las
ejecuciones posteriores lo reutilizan. Los parámetros que solo afectan a la
consulta (`top_k`, umbral de distancia, política de prompt) no entran en la
firma: cambiarlos no requiere reindexar y sería tirar el dinero de embeddings.
"""
import hashlib
from dataclasses import replace

import chromadb

from src.config import Config
from src.ingest import construir_indice

# Parámetros que condicionan el contenido del índice.
CAMPOS_INDICE = ("chunk_strategy", "chunk_size", "chunk_overlap", "embed_model", "embed_dims")


def firma_indice(cfg: Config) -> str:
    crudo = "|".join(f"{c}={getattr(cfg, c)}" for c in CAMPOS_INDICE)
    return hashlib.sha1(crudo.encode()).hexdigest()[:10]


def nombre_coleccion(cfg: Config) -> str:
    """El inquilino entra en el nombre antes que nada.

    Sin él, dos inquilinos con la misma configuración de indexación compartirían
    colección y el barrido de uno sobreescribiría el índice del otro. Sería
    además una fuga de datos entre clientes por la puerta de atrás.
    """
    return (
        f"corpus_{cfg.tenant.id}_{cfg.chunk_strategy}_{cfg.chunk_size}"
        f"_{cfg.embed_dims}_{firma_indice(cfg)}"
    )


def variante(base: Config, **cambios) -> Config:
    """Nueva Config con los cambios aplicados y la colección recalculada."""
    nueva = replace(base, **cambios)
    return replace(nueva, collection=nombre_coleccion(nueva))


def indice_existe(cfg: Config) -> bool:
    """Existe *y* tiene contenido.

    Una colección creada pero vacía no es un índice: es el resto de una ingesta
    que se cortó a mitad. Darla por buena hace que el barrido reporte cero
    aciertos y parezca que la configuración es mala cuando lo que pasa es que
    nunca llegó a indexarse.
    """
    client = chromadb.PersistentClient(path=cfg.chroma_path)
    nombres = [getattr(c, "name", c) for c in client.list_collections()]
    if cfg.collection not in nombres:
        return False
    return client.get_collection(cfg.collection).count() > 0


def asegurar_indice(cfg: Config, forzar: bool = False, verboso: bool = True) -> dict | None:
    """Construye el índice de esta configuración si aún no existe."""
    if not forzar and indice_existe(cfg):
        if verboso:
            print(f"[=] Índice ya presente: {cfg.collection}")
        return None
    if verboso:
        print(
            f"[*] Construyendo índice {cfg.collection} "
            f"(chunk={cfg.chunk_strategy}/{cfg.chunk_size}, dims={cfg.embed_dims})..."
        )
    info = construir_indice(cfg)
    if verboso:
        print(f"[OK] {info['documentos']} fragmentos indexados.")
    return info


def descripcion(cfg: Config) -> dict:
    """Los parámetros que definen una ejecución, para dejarlos en el informe."""
    return {
        "provider": cfg.provider,
        "model_router": cfg.model_router,
        "model_generator": cfg.model_generator,
        "embed_model": cfg.embed_model,
        "embed_dims": cfg.embed_dims,
        "chunk_strategy": cfg.chunk_strategy,
        "chunk_size": cfg.chunk_size,
        "chunk_overlap": cfg.chunk_overlap,
        "top_k": cfg.top_k,
        "distance_threshold": cfg.distance_threshold,
        "gen_policy": cfg.gen_policy,
        "judge_model": cfg.judge_model,
        "collection": cfg.collection,
    }
