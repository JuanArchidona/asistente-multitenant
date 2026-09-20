"""Configuración del sistema bajo prueba.

Diferencia clave respecto a la 3.1: todo parámetro que afecta a la calidad
(chunking, top_k, dimensiones del embedder, umbral de distancia) vive aquí y se
lee del entorno. Si un parámetro está hardcodeado no se puede experimentar con
él, que es justo lo que impedía puntuar cambios de chunking o embedder en la
entrega anterior. `Config` es un dataclass congelado: los barridos de
`evals/sweep.py` generan variantes con `dataclasses.replace`.
"""
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

from .tenant import Tenant, cargar_tenant

load_dotenv()

TENANT_POR_DEFECTO = "empresa_servicios"

ESTRATEGIAS_CHUNK = ("chars", "headings")
POLITICAS_GEN = ("base", "hardened")
PROVEEDORES_JUEZ = ("anthropic", "gemini")


@dataclass(frozen=True)
class Config:
    # --- Inquilino al que pertenece esta ejecución ---
    # Determina corpus, categorías de enrutado y colección del índice. Va en la
    # Config y no como parámetro suelto para que sea imposible ejecutar una
    # consulta sin haber decidido de quién es.
    tenant: Tenant

    # --- Proveedor de chat (enrutador + generador) ---
    provider: str
    anthropic_api_key: str
    model_router: str
    model_generator: str
    gemini_api_key: str
    gemini_model: str

    # --- Embeddings e índice ---
    embed_model: str
    embed_dims: int
    chroma_path: str
    collection: str
    corpus_path: str

    # --- Parámetros de calidad (los que se barren en los experimentos) ---
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    distance_threshold: float | None

    # --- Política del prompt del generador: 'base' (la de la 3.1) | 'hardened' ---
    gen_policy: str

    # --- Juez de evaluación (siempre distinto del generador) ---
    judge_provider: str
    judge_model: str

    # --- Modelo que construye y critica el banco sintético (distinto del evaluado) ---
    builder_model: str


def load_config() -> Config:
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider not in ("anthropic", "gemini"):
        sys.exit(f"[config] LLM_PROVIDER inválido: {provider!r}. Usa 'anthropic' o 'gemini'.")

    estrategia = os.getenv("CHUNK_STRATEGY", "chars").lower()
    if estrategia not in ESTRATEGIAS_CHUNK:
        sys.exit(
            f"[config] CHUNK_STRATEGY inválida: {estrategia!r}. "
            f"Usa una de {ESTRATEGIAS_CHUNK}."
        )

    politica = os.getenv("GEN_POLICY", "base").lower()
    if politica not in POLITICAS_GEN:
        sys.exit(f"[config] GEN_POLICY inválida: {politica!r}. Usa una de {POLITICAS_GEN}.")

    umbral = os.getenv("DISTANCE_THRESHOLD", "").strip()

    tenant_id = os.getenv("TENANT_ID", TENANT_POR_DEFECTO).strip()
    try:
        tenant = cargar_tenant(tenant_id)
    except ValueError as error:
        sys.exit(f"[config] {error}")

    # El corpus y la colección se derivan del inquilino. CORPUS_PATH y
    # CHROMA_COLLECTION son la raíz común, no el destino final: si fueran el
    # destino, dos inquilinos con la misma configuración compartirían índice y
    # el aislamiento sería mentira.
    raiz_corpus = os.getenv("CORPUS_PATH", "corpus")
    base_coleccion = os.getenv("CHROMA_COLLECTION", "corpus_empresa")

    cfg = Config(
        tenant=tenant,
        provider=provider,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model_router=os.getenv("ANTHROPIC_MODEL_ROUTER", "claude-haiku-4-5-20251001"),
        model_generator=os.getenv("ANTHROPIC_MODEL_GENERATOR", "claude-haiku-4-5-20251001"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        embed_model=os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001"),
        embed_dims=int(os.getenv("EMBED_DIMS", "768")),
        chroma_path=os.getenv("CHROMA_PATH", "data/chroma"),
        collection=tenant.coleccion(base_coleccion),
        corpus_path=tenant.corpus(raiz_corpus),
        chunk_strategy=estrategia,
        chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
        top_k=int(os.getenv("TOP_K", "4")),
        distance_threshold=float(umbral) if umbral else None,
        gen_policy=politica,
        judge_provider=os.getenv("JUDGE_PROVIDER", "anthropic").lower(),
        judge_model=os.getenv("JUDGE_MODEL", "claude-sonnet-5"),
        builder_model=os.getenv("BUILDER_MODEL", "claude-sonnet-5"),
    )

    # El chat (router/generador) usa Anthropic por defecto; los embeddings SIEMPRE Gemini.
    if provider == "anthropic" and not cfg.anthropic_api_key:
        sys.exit("[config] Falta ANTHROPIC_API_KEY en .env")
    if not cfg.gemini_api_key:
        sys.exit("[config] Falta GEMINI_API_KEY en .env (necesaria para embeddings y juez)")
    if cfg.chunk_overlap >= cfg.chunk_size:
        sys.exit("[config] CHUNK_OVERLAP debe ser menor que CHUNK_SIZE.")
    if cfg.judge_provider not in PROVEEDORES_JUEZ:
        sys.exit(f"[config] JUDGE_PROVIDER inválido: {cfg.judge_provider!r}.")
    if cfg.judge_model == cfg.model_generator:
        sys.exit(
            "[config] El juez no puede ser el mismo modelo que el generador: un modelo "
            "evaluando su propio texto se aprueba a sí mismo. Cambia JUDGE_MODEL."
        )

    return cfg
