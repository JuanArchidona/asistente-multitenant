"""Ingesta del corpus en ChromaDB.

Recorre corpus/<fuente>/*.md, trocea cada documento, lo embebe con Gemini
(RETRIEVAL_DOCUMENT) y lo guarda en ChromaDB con metadato 'fuente'. El metadato
es lo que luego permite al recuperador filtrar por la fuente que dictó el enrutador.

Respecto a la 3.1 hay dos cambios, ambos para poder evaluar:

1. La estrategia de chunking es un parámetro (`chars` | `headings`), no una
   constante. El barrido de `evals/sweep.py` compara ambas con las mismas
   consultas y el mismo golden set.
2. La colección se lee de `Config`, para que cada configuración del barrido
   construya su propio índice sin pisar el de las demás.
"""
import re
from pathlib import Path

import chromadb

from .config import Config
from .embeddings import GeminiEmbedder
from .gobernanza import SIN_RESTRICCION

COLLECTION = "corpus_empresa"  # por defecto; `Config.collection` manda

# Encabezado markdown de nivel 2 o superior: el separador semántico natural de
# este corpus (cada '## Vacaciones', '## Teletrabajo'... es una unidad de sentido).
_RE_ENCABEZADO = re.compile(r"^(#{1,6})\s+.*$", re.MULTILINE)


def _chunk_chars(texto: str, max_chars: int, solape: int) -> list[str]:
    """Chunking por caracteres con solape: el de la 3.1, aquí como línea base.

    Corta a ciegas, así que puede partir una palabra o separar un encabezado de
    su contenido. Se conserva precisamente para poder medir cuánto cuesta eso.
    """
    texto = texto.strip()
    if len(texto) <= max_chars:
        return [texto]
    chunks, inicio = [], 0
    while inicio < len(texto):
        fin = inicio + max_chars
        chunks.append(texto[inicio:fin])
        inicio = fin - solape
    return chunks


def _chunk_headings(texto: str, max_chars: int, solape: int) -> list[str]:
    """Chunking por estructura: una sección por encabezado markdown.

    Cada fragmento arrastra el título del documento (primer '# ') como prefijo,
    de forma que un trozo suelto sigue diciendo de qué documento habla — importa
    porque el recuperador entrega fragmentos aislados al generador. Las secciones
    que superan `max_chars` se subdividen por caracteres.
    """
    texto = texto.strip()
    posiciones = [m.start() for m in _RE_ENCABEZADO.finditer(texto)]
    if not posiciones:
        return _chunk_chars(texto, max_chars, solape)

    # Preámbulo anterior al primer encabezado, si lo hay.
    tramos = []
    if posiciones[0] > 0:
        tramos.append(texto[: posiciones[0]].strip())
    for i, ini in enumerate(posiciones):
        fin = posiciones[i + 1] if i + 1 < len(posiciones) else len(texto)
        tramos.append(texto[ini:fin].strip())

    titulo = tramos[0].splitlines()[0].lstrip("# ").strip() if tramos else ""

    chunks: list[str] = []
    for j, tramo in enumerate(t for t in tramos if t):
        # El primer tramo ya es el título; el resto lo lleva como contexto.
        cuerpo = tramo if j == 0 else f"[{titulo}]\n{tramo}"
        if len(cuerpo) <= max_chars:
            chunks.append(cuerpo)
        else:
            chunks.extend(_chunk_chars(cuerpo, max_chars, solape))
    return chunks


def trocear(texto: str, cfg: Config) -> list[str]:
    """Aplica la estrategia de chunking configurada."""
    if cfg.chunk_strategy == "headings":
        return _chunk_headings(texto, cfg.chunk_size, cfg.chunk_overlap)
    return _chunk_chars(texto, cfg.chunk_size, cfg.chunk_overlap)


def construir_indice(cfg: Config) -> dict:
    embedder = GeminiEmbedder(cfg)
    client = chromadb.PersistentClient(path=cfg.chroma_path)

    corpus = Path(cfg.corpus_path)
    docs, metadatos, ids = [], [], []

    for fuente_dir in sorted(corpus.iterdir()):
        if not fuente_dir.is_dir():
            continue
        fuente = fuente_dir.name
        for archivo in sorted(fuente_dir.glob("*.md")):
            texto = archivo.read_text(encoding="utf-8")
            for i, chunk in enumerate(trocear(texto, cfg)):
                docs.append(chunk)
                metadatos.append({
                    "fuente": fuente,
                    "archivo": archivo.name,
                    # Clasificación del documento, del manifiesto del inquilino.
                    # Va en el índice y no se consulta en tiempo de respuesta
                    # porque el filtro tiene que aplicarse DENTRO de la búsqueda:
                    # recuperar y descartar después deja el documento en memoria
                    # del proceso y arruina el argumento.
                    "requiere": cfg.tenant.politica.requisito_de_documento(archivo.name),
                })
                ids.append(f"{fuente}__{archivo.stem}__{i}")

    if not docs:
        raise ValueError(f"No se encontraron documentos .md en {cfg.corpus_path}/")

    # Embeddings en lote (la API admite hasta 100 por llamada; troceamos por si acaso).
    # Se calculan ANTES de tocar la colección: si la API falla a mitad —cuota
    # agotada, por ejemplo— el índice anterior sigue intacto en vez de quedarse
    # creado y vacío, que es un estado que ninguna comprobación de "¿existe el
    # índice?" distingue de uno bueno.
    vectores = []
    for j in range(0, len(docs), 100):
        vectores.extend(embedder.embed_documentos(docs[j:j + 100]))

    # Reconstrucción limpia en cada ingesta (sprint; en prod sería incremental).
    # list_collections devuelve objetos (<=0.5) o nombres (>=0.6); cubrimos ambos.
    if cfg.collection in [getattr(c, "name", c) for c in client.list_collections()]:
        client.delete_collection(cfg.collection)
    col = client.create_collection(cfg.collection, metadata={"hnsw:space": "cosine"})
    col.add(ids=ids, documents=docs, embeddings=vectores, metadatas=metadatos)
    return {
        "documentos": len(docs),
        "fuentes": sorted({m["fuente"] for m in metadatos}),
        "coleccion": cfg.collection,
        "restringidos": sorted(
            {m["archivo"] for m in metadatos if m["requiere"] != SIN_RESTRICCION}
        ),
        "estrategia": cfg.chunk_strategy,
    }
