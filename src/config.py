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

    # Temperatura del enrutador. `None` significa **no enviar el parametro**, que
    # es como corrio todo el banco hasta el 22-09-2026; desde entonces el valor
    # por defecto es 0.0, medido en HALLAZGOS.md §27. La escotilla existe para
    # poder reproducir las ejecuciones historicas: `ROUTER_TEMPERATURE=defecto`.
    router_temperature: float | None

    # --- Juez de evaluación (siempre distinto del generador) ---
    judge_provider: str
    judge_model: str
    # Clave propia del juez, distinta de la del sistema. No es una duplicación
    # por gusto: es lo que permite que la factura del proveedor responda por
    # separado cuánto cuesta funcionar y cuánto cuesta evaluar, que es lo que
    # pedía el feedback de la entrega 3.3. Si el juez usa la clave del sistema,
    # los dos gastos se suman en la misma línea y la pregunta deja de tener
    # respuesta. Ver docs/HALLAZGOS.md §18.
    judge_api_key: str
    # --- Modelo que construye y critica el banco sintético (distinto del evaluado) ---
    builder_model: str

    # La misma exigencia para el camino de Gemini. Hacía falta y no estaba: con
    # `JUDGE_PROVIDER=gemini` el juez tiraba de `GEMINI_API_KEY`, que es la
    # clave de los **embeddings**, o sea parte del sistema. El gasto del juez se
    # habría sumado al del sistema en la misma línea de factura, deshaciendo en
    # silencio lo que el §18 arregló para Anthropic — y encima solo en el camino
    # que hace falta para tener un juez de otra familia. Ver §24.
    judge_gemini_api_key: str = ""


def load_config(tenant_id: str | None = None, con_juez: bool = True) -> Config:
    """Configuración del sistema para un inquilino.

    `tenant_id` manda sobre `TENANT_ID`. Existe para la interfaz desplegada,
    que sirve a varios inquilinos desde un mismo proceso y no puede cambiar
    el entorno por usuario; la línea de órdenes y el banco siguen usando la
    variable.

    `con_juez=False` omite las comprobaciones de las claves del juez. Solo
    lo pasa la interfaz desplegada, que nunca evalúa: el primer despliegue en
    Render (23-09-2026, HALLAZGOS.md §38) se paró tras el login exigiendo
    `GEMINI_API_KEY_JUEZ` a un proceso que no iba a llamar al juez jamás. El
    banco y la línea de órdenes conservan la comprobación, y la regla de que
    el juez no sea el mismo modelo que el generador se comprueba siempre:
    no depende de ninguna clave.
    """
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

    tenant_id = (tenant_id or os.getenv("TENANT_ID", TENANT_POR_DEFECTO)).strip()
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

    # Modelos del chat SEGUN EL PROVEEDOR. Hacia falta y no estaba: `gemini_model`
    # se declaraba en `Config` y no se consultaba en ningun sitio, asi que con
    # `LLM_PROVIDER=gemini` el sistema llamaba a Gemini pasandole nombres de
    # modelo de Anthropic y fallaba con un 404. La abstraccion de proveedor
    # existia en la forma —dos clases con la misma interfaz— y no en el hecho.
    # Es una afirmacion que la memoria usa como justificacion, asi que no podia
    # quedarse sin comprobar. Ver §29.
    modelo_gemini = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    if provider == "gemini":
        modelo_router = os.getenv("GEMINI_MODEL_ROUTER", modelo_gemini)
        modelo_generador = os.getenv("GEMINI_MODEL_GENERATOR", modelo_gemini)
    else:
        modelo_router = os.getenv("ANTHROPIC_MODEL_ROUTER", "claude-haiku-4-5-20251001")
        modelo_generador = os.getenv(
            "ANTHROPIC_MODEL_GENERATOR", "claude-haiku-4-5-20251001"
        )

    # Temperatura del enrutador. **0.0 por defecto desde el 22-09-2026.**
    #
    # Medido en HALLAZGOS.md §27: a la temperatura por defecto del proveedor, 3
    # casos de 38 cambiaban de categoria entre pasadas identicas; a 0 son 0, el
    # acierto de enrutado sube en los dos inquilinos y la cobertura del riesgo no
    # se mueve. Sin esto, ningun acierto de enrutado se podia reportar de una
    # sola pasada.
    #
    # `defecto` (o `none`) vuelve a no enviar el parametro, que es como corrieron
    # las 15 ejecuciones anteriores. La escotilla no es adorno: es lo unico que
    # permite reproducir una cifra historica, y las cifras de antes y despues del
    # cambio **no son comparables** (docs/ALCANCE.md §5.c).
    bruto = os.getenv("ROUTER_TEMPERATURE", "").strip().lower()
    if bruto in ("defecto", "none"):
        temperatura_enrutador = None
    elif bruto == "":
        temperatura_enrutador = 0.0
    else:
        try:
            temperatura_enrutador = float(bruto)
        except ValueError:
            sys.exit(
                f"[config] ROUTER_TEMPERATURE invalido: {bruto!r}. Usa un numero, "
                "o 'defecto' para no enviar el parametro."
            )

    cfg = Config(
        tenant=tenant,
        provider=provider,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model_router=modelo_router,
        model_generator=modelo_generador,
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=modelo_gemini,
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
        router_temperature=temperatura_enrutador,
        # Juez por defecto: **Gemini desde el 22-09-2026**. Es el unico con
        # independencia de familia respecto al generador (§24) y cuesta 5,5
        # veces menos por evaluacion (§32), lo que hace asequible repetirlo.
        # NO compra estabilidad: el §32 y el §33 midieron que ni la temperatura
        # ni la mayoria de tres la resuelven, asi que el veredicto del proyecto
        # sigue anclado en metricas deterministas.
        judge_provider=os.getenv("JUDGE_PROVIDER", "gemini").lower(),
        judge_model=os.getenv("JUDGE_MODEL", "gemini-3.6-flash"),
        judge_api_key=os.getenv("ANTHROPIC_API_KEY_JUEZ", ""),
        judge_gemini_api_key=os.getenv("GEMINI_API_KEY_JUEZ", ""),
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
    if not con_juez:
        return cfg
    # Sin clave propia se falla en el arranque en vez de tirar de la del
    # sistema: caer a la clave del sistema funcionaría igual de bien y dejaría
    # la facturación mezclada sin que nadie se enterase. Es exactamente el
    # fallback silencioso que el proyecto no se permite.
    if cfg.judge_provider == "anthropic" and not cfg.judge_api_key:
        sys.exit(
            "[config] Falta ANTHROPIC_API_KEY_JUEZ en .env. El juez tiene clave propia "
            "para que la factura separe lo que cuesta evaluar de lo que cuesta funcionar. "
            "Usa --sin-juez si no quieres ejecutar el juez."
        )
    if cfg.judge_api_key and cfg.judge_api_key == cfg.anthropic_api_key:
        sys.exit(
            "[config] ANTHROPIC_API_KEY_JUEZ es la misma clave que ANTHROPIC_API_KEY. "
            "Siendo la misma, el proveedor no puede separar los dos gastos y tener dos "
            "variables solo aparenta que sí."
        )
    if cfg.judge_provider == "gemini" and not cfg.judge_gemini_api_key:
        sys.exit(
            "[config] JUDGE_PROVIDER=gemini pero falta GEMINI_API_KEY_JUEZ en .env. "
            "GEMINI_API_KEY es la clave de los embeddings, que son parte del sistema: "
            "usarla para el juez sumaría los dos gastos en la misma línea de factura "
            "y la pregunta 'cuánto cuesta evaluar' dejaría de tener respuesta. "
            "Crea una clave de Gemini en un PROYECTO DISTINTO (ver abajo), o usa "
            "JUDGE_PROVIDER=anthropic."
        )
    # Esta comprobación es NECESARIA Y NO SUFICIENTE, y conviene saber por qué.
    # En Anthropic la consola desglosa el coste **por clave**, así que dos claves
    # distintas bastan para separar los gastos (§18, §21). En Google no: la
    # documentación dice que los límites y la facturación se aplican **por
    # proyecto, no por clave**. Dos claves del mismo proyecto pasarían esta
    # validación y seguirían compartiendo línea de factura y cuota.
    #
    # El código no puede comprobarlo —una clave de Gemini no lleva el proyecto
    # dentro y no hay forma local de deducirlo—, así que lo que queda es decirlo
    # donde se lee. La cuota compartida importa además por sí sola: un juez que
    # agote el límite del proyecto deja sin embeddings al sistema a mitad de una
    # ejecución. Ver docs/HALLAZGOS.md §24.
    if (
        cfg.judge_gemini_api_key
        and cfg.judge_gemini_api_key == cfg.gemini_api_key
    ):
        sys.exit(
            "[config] GEMINI_API_KEY_JUEZ es la misma clave que GEMINI_API_KEY. "
            "Siendo la misma, el proveedor no puede separar los dos gastos y tener dos "
            "variables solo aparenta que sí. Y con claves distintas no basta: en "
            "Google la cuota y la facturación van por PROYECTO, así que la clave del "
            "juez tiene que salir de un proyecto distinto al de los embeddings."
        )

    return cfg
