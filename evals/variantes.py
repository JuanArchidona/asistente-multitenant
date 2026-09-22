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
from pathlib import Path

import chromadb

from src.config import Config
from src.ingest import construir_indice

# Parámetros que condicionan el contenido del índice.
CAMPOS_INDICE = ("chunk_strategy", "chunk_size", "chunk_overlap", "embed_model", "embed_dims")

# Versión del esquema de metadatos que la ingesta escribe en cada fragmento.
# Se sube al añadir o cambiar un metadato.
#
# Está aquí por un fallo real: al añadir el metadato de clasificación, el barrido
# reutilizó un índice construido antes de que ese campo existiera. El filtro de
# permisos no casaba con nada, la recuperación devolvía cero y el informe lo
# presentaba como un desplome de calidad del RAG. Un índice obsoleto no falla,
# responde mal, que es peor.
VERSION_METADATOS = 2


def firma_corpus(corpus_path: str) -> str:
    """Huella del corpus: qué documentos hay, en qué fuente y con qué contenido.

    Falta esto y el índice se queda obsoleto sin que nada lo señale. Es el mismo
    fallo del hallazgo 10 en el eje que aquel arreglo no cubrió: entonces se
    añadieron a la firma el esquema de metadatos y la política, pero no el
    corpus, que es lo más obvio que puede cambiar. Mover un documento de fuente
    no toca ningún parámetro de la configuración, así que la firma no se movía,
    el barrido reutilizaba la colección vieja y la fuente nueva salía vacía.

    Se hashea el contenido y no la fecha de modificación: `git checkout` de una
    rama a otra reescribe las fechas sin cambiar el texto, y eso reindexaría
    gratis cada vez. Leer once ficheros de markdown no se nota al lado de lo que
    cuesta equivocarse.
    """
    raiz = Path(corpus_path)
    if not raiz.is_dir():
        return "sin-corpus"
    partes = []
    for archivo in sorted(raiz.rglob("*.md")):
        relativa = archivo.relative_to(raiz).as_posix()
        contenido = hashlib.sha1(archivo.read_bytes()).hexdigest()[:10]
        partes.append(f"{relativa}:{contenido}")
    return hashlib.sha1("|".join(partes).encode()).hexdigest()[:10]


def firma_indice(cfg: Config) -> str:
    """Firma de todo lo que, al cambiar, obliga a reindexar.

    Además de los parámetros de troceado y embedding, incluye la política de
    acceso del inquilino (si un documento pasa a estar restringido, su metadato
    cambia) y el corpus entero (si el documento se mueve, se edita o desaparece,
    el índice viejo describe otro corpus).
    """
    partes = [f"{c}={getattr(cfg, c)}" for c in CAMPOS_INDICE]
    partes.append(f"metadatos=v{VERSION_METADATOS}")
    partes.append(
        "politica="
        + ";".join(
            sorted(
                f"{d.archivo}:{d.requiere}"
                for d in cfg.tenant.politica.documentos_restringidos
            )
        )
    )
    partes.append(f"corpus={firma_corpus(cfg.corpus_path)}")
    return hashlib.sha1("|".join(partes).encode()).hexdigest()[:10]


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


# Familia de cada modelo, para saber si el juez es de la misma que el generador.
# No basta con que sean modelos distintos: un juez de la misma familia comparte
# datos de entrenamiento y sesgos con lo que juzga, y la práctica recomendada es
# que no coincidan. `Config` ya impide que sean **el mismo** modelo; lo que no
# puede hacer es abortar cuando coinciden de familia, porque esa es la
# configuración con la que está medido todo el banco. Lo que sí se puede es que
# la limitación **viaje en cada informe** en vez de vivir solo en un docstring:
# un caveat que no acompaña al número se pierde en cuanto alguien cita el número.
def familia_de(modelo: str) -> str:
    m = (modelo or "").lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "google"
    if m.startswith(("gpt", "o1")):
        return "openai"
    return "desconocida"


def independencia_del_juez(cfg: Config) -> dict:
    """Qué tipo de independencia hay entre el juez y lo que juzga.

    Tres estados, no dos. Si no se reconoce la familia de alguno de los dos
    modelos, ni se afirma que la comparten ni que no: no consta. La primera
    versión de esto tenía dos estados y con familias desconocidas concluía
    "independencia de capacidad y de familia", que es afirmar la lectura
    favorable a partir de no saber. No afirmar la peor lectura no autoriza a
    afirmar la mejor.
    """
    familia_juez = familia_de(cfg.judge_model)
    familia_gen = familia_de(cfg.model_generator)
    determinada = "desconocida" not in (familia_juez, familia_gen)
    misma_familia = determinada and familia_juez == familia_gen
    if not determinada:
        tipo = (
            "sin determinar: no se reconoce la familia de "
            f"{cfg.judge_model!r} o de {cfg.model_generator!r}"
        )
    elif misma_familia:
        tipo = (
            "solo de capacidad: juez y generador son de la misma familia, así que "
            "comparten datos de entrenamiento y sesgos con lo que se juzga"
        )
    else:
        tipo = "de capacidad y de familia"
    return {
        "juez": cfg.judge_model,
        "generador": cfg.model_generator,
        "familia_juez": familia_juez,
        "familia_generador": familia_gen,
        "determinada": determinada,
        "misma_familia": misma_familia,
        "tipo": tipo,
    }


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
        "router_temperature": cfg.router_temperature,
        "judge_model": cfg.judge_model,
        "judge_provider": cfg.judge_provider,
        "independencia_del_juez": independencia_del_juez(cfg),
        "collection": cfg.collection,
    }
