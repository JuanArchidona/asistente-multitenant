"""Barrido de configuraciones sobre las métricas de recuperación.

    uv run python -m evals.sweep

Esto es lo que pedía la corrección de la 3.1: poder **puntuar** un cambio de
chunking, de embedder o de `top_k` en vez de decidirlo por intuición. Tres
decisiones de método hacen que salga barato y limpio:

1. **Se evalúa solo la recuperación.** No se genera respuesta ni se llama al
   juez. Un cambio de chunking actúa sobre qué fragmentos llegan al generador;
   si esos fragmentos mejoran, la respuesta solo puede mejorar. Medir la
   generación en cada combinación multiplicaría el coste por veinte para
   observar el mismo efecto con más ruido.

2. **Se salta el enrutador**: cada consulta se busca directamente en la fuente
   que el golden set declara correcta. No es un atajo, es control experimental —
   si el enrutador se equivoca en una consulta, ese error contaminaría por igual
   a todas las configuraciones y solo añadiría varianza a la comparación. El
   acierto del enrutador se mide aparte, en el banco principal.

3. **Se cachean los embeddings de consulta** por dimensionalidad: las
   configuraciones que solo cambian el chunking o `top_k` reutilizan los mismos
   vectores de consulta y no se vuelven a pagar.

El eje que no se puede barrer gratis es la dimensionalidad del embedder: obliga
a reindexar el corpus entero. Con este corpus son segundos; conviene tenerlo
presente antes de que crezca.
"""
import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import chromadb

from src.config import Config, load_config
from src.embeddings import GeminiEmbedder

from .dataset import RAIZ_DATASETS, cargar_consultas
from .variantes import asegurar_indice, variante

RAIZ_REPORTES = Path(__file__).resolve().parents[1] / "reports"


@dataclass
class Ejecucion:
    nombre: str
    cambios: dict
    metricas: dict = field(default_factory=dict)
    fragmentos: int = 0
    segundos_indexado: float = 0.0


# Rejilla por defecto: se mueve un eje cada vez desde la línea base de la 3.1.
# Un producto cartesiano completo daría decenas de combinaciones sin decir mucho
# más: lo que interesa es aislar el efecto de cada parámetro.
REJILLA = [
    ("baseline (3.1)", {}),
    ("chars-400", {"chunk_size": 400, "chunk_overlap": 50}),
    ("chars-1200", {"chunk_size": 1200, "chunk_overlap": 150}),
    ("headings-800", {"chunk_strategy": "headings"}),
    ("headings-1200", {"chunk_strategy": "headings", "chunk_size": 1200, "chunk_overlap": 150}),
    ("headings-400", {"chunk_strategy": "headings", "chunk_size": 400, "chunk_overlap": 50}),
    ("top_k=2", {"top_k": 2}),
    ("top_k=6", {"top_k": 6}),
    ("headings + top_k=2", {"chunk_strategy": "headings", "top_k": 2}),
    ("dims=1536", {"embed_dims": 1536}),
    ("dims=3072", {"embed_dims": 3072}),
]


class CacheConsultas:
    """Embeddings de consulta reutilizados entre configuraciones de igual dims.

    Se precalculan en lote la primera vez que aparece una dimensionalidad: son
    43 consultas en una llamada en vez de 43 llamadas, lo que además de ser más
    rápido es lo que permite ejecutar el barrido completo dentro de la cuota del
    plan gratuito de Gemini.
    """

    def __init__(self):
        self._cache: dict[tuple[str, int, str], list[float]] = {}
        self.llamadas = 0

    def precalentar(self, embedder: GeminiEmbedder, textos: list[str]) -> None:
        pendientes = [
            t for t in dict.fromkeys(textos)
            if (embedder.model, embedder.dims, t) not in self._cache
        ]
        if not pendientes:
            return
        vectores = embedder.embed_consultas(pendientes)
        for texto, vector in zip(pendientes, vectores):
            self._cache[(embedder.model, embedder.dims, texto)] = vector
        self.llamadas += 1

    def obtener(self, embedder: GeminiEmbedder, texto: str) -> list[float]:
        clave = (embedder.model, embedder.dims, texto)
        if clave not in self._cache:
            self._cache[clave] = embedder.embed_consulta(texto)
            self.llamadas += 1
        return self._cache[clave]


def _metricas_recuperacion(esperados: set[str], recuperados: list[str]) -> dict:
    aciertos = esperados & set(recuperados)
    rr = 0.0
    for i, archivo in enumerate(recuperados, start=1):
        if archivo in esperados:
            rr = 1.0 / i
            break
    return {
        "hit_rate": 1.0 if aciertos else 0.0,
        "recall_at_k": len(aciertos) / len(esperados),
        "precision_at_k": len(aciertos) / len(recuperados) if recuperados else 0.0,
        "mrr": rr,
    }


def evaluar_configuracion(cfg: Config, casos, cache: CacheConsultas) -> dict:
    embedder = GeminiEmbedder(cfg)
    cache.precalentar(embedder, [c.consulta for c in casos])
    client = chromadb.PersistentClient(path=cfg.chroma_path)
    col = client.get_collection(cfg.collection)

    acumulado = {"hit_rate": 0.0, "recall_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0}
    distancias: list[float] = []
    n = 0

    for caso in casos:
        vector = cache.obtener(embedder, caso.consulta)
        res = col.query(
            query_embeddings=[vector],
            n_results=cfg.top_k,
            where={"fuente": caso.categoria_esperada},
        )
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        if cfg.distance_threshold is not None:
            pares = [(m, d) for m, d in zip(metas, dists) if d <= cfg.distance_threshold]
        else:
            pares = list(zip(metas, dists))

        vistos, orden = set(), []
        for m, _ in pares:
            if m["archivo"] not in vistos:
                vistos.add(m["archivo"])
                orden.append(m["archivo"])
        distancias.extend(d for _, d in pares)

        for k, v in _metricas_recuperacion(set(caso.archivos_esperados), orden).items():
            acumulado[k] += v
        n += 1

    salida = {k: round(v / n, 4) for k, v in acumulado.items()} if n else acumulado
    salida["distancia_media"] = round(sum(distancias) / len(distancias), 4) if distancias else None
    salida["casos"] = n
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description="Barrido de configuraciones de recuperación")
    p.add_argument("--dataset", help="JSONL de casos (por defecto, el golden set curado)")
    p.add_argument("--etiqueta", default="sweep")
    p.add_argument("--solo", help="Ejecutar solo las variantes cuyo nombre contenga este texto")
    args = p.parse_args()

    base = load_config()
    ruta = Path(args.dataset) if args.dataset else RAIZ_DATASETS / "golden_consultas.jsonl"
    casos = [
        c for c in cargar_consultas(ruta)
        if c.archivos_esperados and c.categoria_esperada != "otro"
    ]
    print(f"[sweep] {len(casos)} casos con fichero esperado sobre {ruta.name}")

    rejilla = REJILLA
    if args.solo:
        rejilla = [(n, c) for n, c in REJILLA if args.solo.lower() in n.lower()]

    cache = CacheConsultas()
    ejecuciones: list[Ejecucion] = []

    for nombre, cambios in rejilla:
        cfg = variante(base, **cambios)
        t0 = time.perf_counter()
        info = asegurar_indice(cfg, verboso=False)
        segundos = time.perf_counter() - t0
        if info is None:
            client = chromadb.PersistentClient(path=cfg.chroma_path)
            fragmentos = client.get_collection(cfg.collection).count()
            segundos = 0.0
        else:
            fragmentos = info["documentos"]

        metricas = evaluar_configuracion(cfg, casos, cache)
        ejecuciones.append(Ejecucion(nombre, cambios, metricas, fragmentos, round(segundos, 1)))
        print(
            f"[sweep] {nombre:<20} hit={metricas['hit_rate']:.3f} "
            f"recall={metricas['recall_at_k']:.3f} prec={metricas['precision_at_k']:.3f} "
            f"mrr={metricas['mrr']:.3f} ({fragmentos} fragmentos)"
        )

    directorio = RAIZ_REPORTES / args.etiqueta
    directorio.mkdir(parents=True, exist_ok=True)
    datos = [
        {
            "nombre": e.nombre, "cambios": e.cambios, "fragmentos": e.fragmentos,
            "segundos_indexado": e.segundos_indexado, **e.metricas,
        }
        for e in ejecuciones
    ]
    (directorio / "sweep.json").write_text(
        json.dumps(
            {"dataset": str(ruta), "casos": len(casos),
             "embeddings_de_consulta_calculados": cache.llamadas, "resultados": datos},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    (directorio / "sweep.md").write_text(_informe(datos, len(casos), cache.llamadas), encoding="utf-8")
    print(f"\n[OK] Informe: {directorio / 'sweep.md'}")


def _informe(datos: list[dict], casos: int, llamadas: int) -> str:
    base = next((d for d in datos if d["nombre"].startswith("baseline")), None)

    def delta(d: dict, clave: str) -> str:
        if base is None or d is base:
            return "-"
        diff = d[clave] - base[clave]
        if abs(diff) < 1e-9:
            return "="
        return f"{diff:+.3f}"

    cabeceras = ["Configuración", "Fragmentos", "hit_rate", "recall@k", "precision@k", "MRR",
                 "Δ recall", "Δ precision", "Dist. media"]
    filas = [
        [
            d["nombre"], str(d["fragmentos"]),
            f"{d['hit_rate']:.3f}", f"{d['recall_at_k']:.3f}",
            f"{d['precision_at_k']:.3f}", f"{d['mrr']:.3f}",
            delta(d, "recall_at_k"), delta(d, "precision_at_k"),
            "-" if d["distancia_media"] is None else f"{d['distancia_media']:.3f}",
        ]
        for d in datos
    ]
    tabla = "| " + " | ".join(cabeceras) + " |\n"
    tabla += "|" + "|".join("---" for _ in cabeceras) + "|\n"
    tabla += "\n".join("| " + " | ".join(f) + " |" for f in filas)

    return (
        "# Barrido de configuraciones — recuperación\n\n"
        f"- Casos evaluados: {casos} (los del golden set que declaran fichero esperado)\n"
        f"- Embeddings de consulta calculados: {llamadas} "
        "(el resto se reutilizaron de la caché)\n"
        "- Sin generación ni juez LLM: el coste del barrido es solo de embeddings.\n"
        "- La recuperación se hace sobre la fuente correcta conocida, sin pasar por el\n"
        "  enrutador, para que un error de enrutado no contamine la comparación.\n\n"
        f"{tabla}\n"
    )


if __name__ == "__main__":
    main()
