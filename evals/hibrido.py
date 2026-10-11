"""Recuperación híbrida, fuera de línea: densa frente a BM25 frente a su fusión RRF.

    uv run python -m evals.hibrido --etiqueta hibrido_2026-10-11

El Módulo 2 trató la búsqueda densa, la dispersa (BM25) y la híbrida, y el
programa nombra "recuperación y ranking". El sistema solo hace la densa
(`src/retriever.py`). Este experimento mide si añadir BM25 mejoraría algo,
sin tocar la línea base: no cambia el recuperador, compara tres métodos sobre
los mismos casos y con el mismo filtro de permisos.

- **Enrutado oráculo**: cada caso busca en la fuente de su categoría esperada,
  para medir solo la recuperación. Las cifras del banco (capítulo 4.2) llevan
  además los errores del enrutador y no son comparables con estas.
- **El mismo permiso**: los fragmentos candidatos de BM25 se filtran con el
  mismo `where` que la densa (fuente y nivel visible del usuario del caso), y
  se excluyen los casos cuyo documento esperado no puede ver ese usuario (los
  de confidencialidad: ahí lo correcto es no recuperarlo).
- **BM25 propio**, sin dependencias: minúsculas, sin tildes, tokens de tres
  letras o más; k1=1,5 y b=0,75.
- **RRF** (fusión por rango recíproco, k=60) sobre los 20 primeros de cada
  método, y se quedan los `top_k` del sistema.

Métricas: las mismas del banco (`evaluar_retrieval`: hit, recall, precision
y MRR por fichero), sobre los casos con `archivos_esperados` de categoría
documental. Coste: los embeddings de las consultas, nada de chat.
"""
import argparse
import json
import math
import re
import time
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from src.config import load_config
from src.gobernanza import Usuario
from src.retriever import Retriever
from src.tenant import DESTINO_DOCUMENTAL

from .dataset import cargar_consultas, ruta_golden
from .metrics.deterministas import evaluar_retrieval

RAIZ = Path(__file__).resolve().parents[1]
INQUILINOS = ("empresa_servicios", "agencia_inmobiliaria", "gestoria_laboral")
METODOS = ("densa", "bm25", "rrf")
METRICAS = ("hit_rate", "recall_at_k", "precision_at_k", "mrr")
CANDIDATOS = 20
K_RRF = 60


def tokens(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [p for p in re.split(r"\W+", t) if len(p) >= 3]


class BM25:
    def __init__(self, documentos: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokens(d) for d in documentos]
        self.k1, self.b = k1, b
        self.n = len(self.docs)
        self.media = sum(len(d) for d in self.docs) / max(1, self.n)
        df = Counter(t for d in self.docs for t in set(d))
        self.idf = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def puntuar(self, consulta: str) -> list[float]:
        q = tokens(consulta)
        salida = []
        for i, tf in enumerate(self.tf):
            largo = len(self.docs[i])
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * largo / self.media))
            salida.append(s)
        return salida


def rrf(*rankings: list[str]) -> list[str]:
    puntos: dict[str, float] = {}
    for ranking in rankings:
        for pos, ident in enumerate(ranking, start=1):
            puntos[ident] = puntos.get(ident, 0.0) + 1.0 / (K_RRF + pos)
    return sorted(puntos, key=lambda i: -puntos[i])


def _traza(archivos: list[str]) -> dict:
    return {"fuentes_usadas": [{"archivo": a, "distancia": 0.0} for a in archivos]}


def medir_inquilino(tenant_id: str) -> dict:
    cfg = load_config(tenant_id, con_juez=False)
    retriever = Retriever(cfg)
    fuentes = {
        c.nombre: (c.fuente or c.nombre)
        for c in cfg.tenant.categorias if c.destino == DESTINO_DOCUMENTAL
    }
    candidatos = [
        c for c in cargar_consultas(ruta_golden(tenant_id, "golden_consultas.jsonl"))
        if c.archivos_esperados and c.categoria_esperada in fuentes
    ]
    # Fuera los casos cuyo documento esperado no puede ver el usuario del caso:
    # ahí ningún método debe recuperarlo, y medirlo sería medir el control de
    # acceso, no la recuperación. Se cuentan aparte.
    politica = cfg.tenant.politica

    def visible(caso) -> bool:
        usuario = Usuario(id="banco", roles=list(caso.roles_usuario or []))
        return all(usuario.puede(politica.requisito_de_documento(a)) for a in caso.archivos_esperados)

    casos = [c for c in candidatos if visible(c)]
    retenidos_por_permiso = len(candidatos) - len(casos)
    acumulado = {m: {k: [] for k in METRICAS} for m in METODOS}
    por_caso = []
    for caso in casos:
        usuario = Usuario(id="banco", roles=list(caso.roles_usuario or []))
        fuente = fuentes[caso.categoria_esperada]
        where = {"$and": [{"fuente": fuente}, {"requiere": {"$in": usuario.niveles_visibles}}]}

        vector = retriever.embedder.embed_consulta(caso.consulta)
        densa = retriever.col.query(query_embeddings=[vector], n_results=CANDIDATOS, where=where)
        ids_densa = densa["ids"][0]

        todos = retriever.col.get(where=where, include=["documents", "metadatas"])
        archivo_de = {i: m["archivo"] for i, m in zip(todos["ids"], todos["metadatas"])}
        archivo_de.update({i: m["archivo"] for i, m in zip(ids_densa, densa["metadatas"][0])})
        puntos = BM25(todos["documents"]).puntuar(caso.consulta)
        orden = sorted(range(len(puntos)), key=lambda i: -puntos[i])
        ids_bm25 = [todos["ids"][i] for i in orden[:CANDIDATOS] if puntos[i] > 0]

        rankings = {
            "densa": ids_densa[: cfg.top_k],
            "bm25": ids_bm25[: cfg.top_k],
            "rrf": rrf(ids_densa, ids_bm25)[: cfg.top_k],
        }
        fila = {"id": caso.id, "esperados": caso.archivos_esperados}
        for metodo, ids in rankings.items():
            archivos = [archivo_de[i] for i in ids]
            resultados = {r.metrica: r.valor for r in evaluar_retrieval(caso, _traza(archivos))}
            for k in METRICAS:
                acumulado[metodo][k].append(resultados[k])
            fila[metodo] = {"archivos": archivos, **resultados}
        por_caso.append(fila)

    medias = {
        m: {k: round(sum(v) / len(v), 4) if v else None for k, v in metricas.items()}
        for m, metricas in acumulado.items()
    }
    return {
        "casos": len(casos),
        "excluidos_por_permiso": retenidos_por_permiso,
        "top_k": cfg.top_k,
        "medias": medias,
        "por_caso": por_caso,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--etiqueta", required=True)
    p.add_argument("--tenant", nargs="*", default=list(INQUILINOS))
    args = p.parse_args()

    t0 = time.perf_counter()
    resultados = {t: medir_inquilino(t) for t in args.tenant}
    resumen = {
        "etiqueta": args.etiqueta,
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "enrutado": "oráculo (categoría esperada)",
        "bm25": {"k1": 1.5, "b": 0.75, "tokens": ">=3 letras, sin tildes"},
        "rrf": {"k": K_RRF, "candidatos": CANDIDATOS},
        "duracion_s": round(time.perf_counter() - t0, 1),
        "por_inquilino": {t: {k: v for k, v in r.items() if k != "por_caso"} for t, r in resultados.items()},
    }
    salida = RAIZ / "reports" / args.etiqueta
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "casos.json").write_text(
        json.dumps({t: r["por_caso"] for t, r in resultados.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(resumen["por_inquilino"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
