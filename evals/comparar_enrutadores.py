"""Compara el enrutador LLM con el enrutador por embeddings, con medidas.

Bloque 3 de `docs/ALCANCE.md`: "clasificador con modelo pequeño, comparado con
medidas contra Haiku". Tres brazos sobre los tres bancos (121 casos):

- **`llm`**: la línea base heredada, Haiku a temperatura 0. No se vuelve a
  ejecutar: sus decisiones están en las trazas guardadas de la última pasada
  de cada inquilino, y a temperatura 0 son las que serían (§27). Reutilizarlas
  cuesta cero y evita comparar contra una pasada distinta de la que el banco
  ya midió.
- **`embeddings_descripciones`** y **`embeddings_indice`**: las dos variantes
  de `src/router_embeddings.py`, ejecutadas aquí. Cuestan embeddings, no chat.
- **`cascada`**: embeddings por descripciones cuando la decisión es clara
  —la categoría más cercana supera el umbral y saca a la segunda un margen
  mínimo— y el LLM cuando no. Se simula con las decisiones guardadas del LLM,
  así que no cuesta nada medirla, y responde a la pregunta útil: cuántas
  llamadas al modelo se ahorrarían sin perder acierto. El margen se calibra
  donde el umbral.

Lo que se mide por brazo e inquilino: acierto de enrutado contra
`categoria_esperada` (la misma métrica `routing` del banco), acierto en los
casos de riesgo (confidencialidad e inyección: si el enrutador no los manda a
la fuente, el control de acceso no llega a actuar), matriz de confusión,
latencia por consulta y coste estimado por consulta.

El umbral de `otro` **se calibra sobre el inquilino heredado y se congela**
antes de mirar a los otros dos. Es la regla del §34 y del §44: un parámetro
elegido sobre el banco que después lo puntúa produce una cifra que no
significa nada; sobre otro banco, sí. El acierto del heredado se marca como
"en muestra" en el informe.

    uv run python -m evals.comparar_enrutadores
    uv run python -m evals.comparar_enrutadores --salida reports/enrutadores
"""
import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import chromadb

from evals.dataset import cargar_consultas
from src.config import load_config
from src.embeddings import GeminiEmbedder
from src.provider import PRECIOS, Uso
from src.router import system_router
from src.router_embeddings import VARIANTES, EnrutadorEmbeddings

RAIZ = Path(__file__).resolve().parents[1]

# Última pasada de cada inquilino con el enrutador LLM a temperatura 0.
TRAZAS_LLM = {
    "empresa_servicios": "empresa_quien",
    "agencia_inmobiliaria": "agencia_hitl_v3",
    "gestoria_laboral": "gestoria_denegacion",
}
TENANT_CALIBRACION = "empresa_servicios"
DIMENSIONES_RIESGO = ("confidencialidad", "inyeccion")
REJILLA_UMBRAL = [round(0.30 + 0.01 * i, 2) for i in range(51)]  # 0,30 .. 0,80
REJILLA_MARGEN = [round(0.01 * i, 2) for i in range(31)]  # 0,00 .. 0,30
TOKENS_SALIDA_ROUTER = 45  # un JSON de tres campos; medido a ojo sobre las trazas


def acierto(casos, predicciones: dict[str, str]) -> dict:
    """Acierto global y en los casos de riesgo, más la confusión."""
    total = riesgo_total = ok = riesgo_ok = 0
    confusion: dict[str, dict[str, int]] = {}
    fallos = []
    for c in casos:
        pred = predicciones[c.id]
        total += 1
        bien = pred == c.categoria_esperada
        ok += bien
        if c.dimension in DIMENSIONES_RIESGO:
            riesgo_total += 1
            riesgo_ok += bien
        confusion.setdefault(c.categoria_esperada, {})
        confusion[c.categoria_esperada][pred] = confusion[c.categoria_esperada].get(pred, 0) + 1
        if not bien:
            fallos.append({"id": c.id, "esperada": c.categoria_esperada, "obtenida": pred})
    return {
        "casos": total,
        "aciertos": ok,
        "tasa": round(ok / total, 4) if total else None,
        "riesgo_casos": riesgo_total,
        "riesgo_aciertos": riesgo_ok,
        "riesgo_tasa": round(riesgo_ok / riesgo_total, 4) if riesgo_total else None,
        "confusion": confusion,
        "fallos": fallos,
    }


def brazo_llm(tenant_id: str, casos, cfg) -> dict:
    trazas = [
        json.loads(ln)
        for ln in (RAIZ / "reports" / TRAZAS_LLM[tenant_id] / "trazas.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    por_consulta = {t["consulta"]: t for t in trazas}
    predicciones = {c.id: por_consulta[c.consulta]["categoria"] for c in casos}
    latencias = [por_consulta[c.consulta]["latencia_router_s"] for c in casos]
    # Coste por consulta: prompt del enrutador + consulta a ~4 caracteres por
    # token, más un JSON corto de salida, al precio del modelo enrutador.
    precio_in, precio_out = PRECIOS.get(cfg.model_router, (None, None))
    system = system_router(cfg.tenant)
    tokens_in = statistics.fmean((len(system) + len(c.consulta)) / 4 for c in casos)
    coste = (
        (tokens_in * precio_in + TOKENS_SALIDA_ROUTER * precio_out) / 1e6
        if precio_in is not None else None
    )
    return {
        "origen": f"reports/{TRAZAS_LLM[tenant_id]}",
        "modelo": cfg.model_router,
        "temperatura": cfg.router_temperature,
        **acierto(casos, predicciones),
        "latencia_media_s": round(statistics.fmean(latencias), 3),
        "latencia_p95_s": round(sorted(latencias)[int(0.95 * (len(latencias) - 1))], 3),
        "coste_usd_por_consulta": round(coste, 6) if coste is not None else None,
        "tokens_entrada_estimados": round(tokens_in),
    }


def _predicciones_llm(tenant_id: str, casos) -> dict[str, str]:
    trazas = [
        json.loads(ln)
        for ln in (RAIZ / "reports" / TRAZAS_LLM[tenant_id] / "trazas.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    por_consulta = {t["consulta"]: t["categoria"] for t in trazas}
    return {c.id: por_consulta[c.consulta] for c in casos}


def predecir(enrutador: EnrutadorEmbeddings, casos, vectores, umbral: float) -> dict[str, str]:
    enrutador.umbral_otro = umbral
    return {c.id: enrutador.enrutar(c.consulta, vector=v).categoria for c, v in zip(casos, vectores, strict=True)}


def calibrar(enrutador, casos, vectores) -> dict:
    """Umbral que maximiza el acierto en el inquilino de calibración.

    Ante empate, el más alto: un umbral alto manda más cosas a `otro`, y
    equivocarse hacia `otro` es abstenerse, no responder con la fuente
    equivocada.
    """
    curva = []
    for u in REJILLA_UMBRAL:
        tasa = acierto(casos, predecir(enrutador, casos, vectores, u))["tasa"]
        curva.append({"umbral": u, "tasa": tasa})
    mejor = max(curva, key=lambda p: (p["tasa"], p["umbral"]))
    return {"umbral": mejor["umbral"], "tasa_en_muestra": mejor["tasa"], "curva": curva}


def predecir_cascada(enrutador, casos, vectores, umbral, margen, llm: dict[str, str]) -> tuple[dict, int]:
    """Decisión por embeddings si es clara; si no, la del LLM. Devuelve también
    cuántas consultas necesitaron al LLM."""
    enrutador.umbral_otro = umbral
    predicciones, al_llm = {}, 0
    for c, v in zip(casos, vectores, strict=True):
        sims = sorted(enrutador.similitudes(v).values(), reverse=True)
        clara = sims[0] >= umbral and (len(sims) < 2 or sims[0] - sims[1] >= margen)
        if clara:
            predicciones[c.id] = enrutador.enrutar(c.consulta, vector=v).categoria
        else:
            predicciones[c.id] = llm[c.id]
            al_llm += 1
    return predicciones, al_llm


def calibrar_margen(enrutador, casos, vectores, umbral, llm) -> dict:
    """Margen que maximiza el acierto; a igual acierto, el que menos llama al LLM."""
    curva = []
    for m in REJILLA_MARGEN:
        pred, al_llm = predecir_cascada(enrutador, casos, vectores, umbral, m, llm)
        curva.append({"margen": m, "tasa": acierto(casos, pred)["tasa"], "al_llm": al_llm})
    mejor = max(curva, key=lambda p: (p["tasa"], -p["al_llm"]))
    return {"margen": mejor["margen"], "tasa_en_muestra": mejor["tasa"], "curva": curva}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", default="reports/enrutadores")
    p.add_argument("--muestra-latencia", type=int, default=8,
                   help="Consultas embebidas una a una para medir la latencia real.")
    args = p.parse_args()

    t_total = time.perf_counter()
    cliente = chromadb.PersistentClient(path="data/chroma")
    resultado: dict = {"fecha": datetime.now(UTC).isoformat(timespec="seconds"), "tenants": {}}
    umbrales: dict[str, float] = {}
    uso = Uso()

    # El heredado primero: es donde se calibra.
    orden = [TENANT_CALIBRACION] + [t for t in TRAZAS_LLM if t != TENANT_CALIBRACION]
    for tenant_id in orden:
        cfg = load_config(tenant_id, con_juez=False)
        casos = cargar_consultas(RAIZ / "evals" / "datasets" / tenant_id / "golden_consultas.jsonl")
        embedder = GeminiEmbedder(cfg, uso=uso)
        col = cliente.get_collection(cfg.collection)
        print(f"[{tenant_id}] {len(casos)} casos")

        # Latencia real: una consulta por llamada, como en producción.
        muestra = casos[: args.muestra_latencia]
        lat = []
        for c in muestra:
            t0 = time.perf_counter()
            embedder.embed_consulta(c.consulta)
            lat.append(time.perf_counter() - t0)
        # Y el resto en lote, para la exactitud, que no depende de cómo se pida.
        vectores = embedder.embed_consultas([c.consulta for c in casos])

        brazos = {"llm": brazo_llm(tenant_id, casos, cfg)}
        for variante in VARIANTES:
            t1 = time.perf_counter()
            enrutador = EnrutadorEmbeddings(cfg.tenant, embedder, col, variante=variante)
            t_prototipos = time.perf_counter() - t1
            clave = f"embeddings_{variante}"
            calibracion = None
            if tenant_id == TENANT_CALIBRACION:
                calibracion = calibrar(enrutador, casos, vectores)
                umbrales[variante] = calibracion["umbral"]
            umbral = umbrales[variante]
            t2 = time.perf_counter()
            predicciones = predecir(enrutador, casos, vectores, umbral)
            t_clasificar = (time.perf_counter() - t2) / len(casos)
            brazos[clave] = {
                "umbral_otro": umbral,
                "calibrado_aqui": tenant_id == TENANT_CALIBRACION,
                **acierto(casos, predicciones),
                # Latencia = embeber la consulta (medida una a una) + clasificar.
                "latencia_media_s": round(statistics.fmean(lat) + t_clasificar, 3),
                "latencia_embedding_s": round(statistics.fmean(lat), 3),
                "latencia_clasificar_s": round(t_clasificar, 4),
                "prototipos_s": round(t_prototipos, 3),
                # Sin precio publicado para el modelo de embeddings (§35): se
                # da el consumo, no el dólar.
                "coste_usd_por_consulta": None,
                "tokens_embebidos_por_consulta": round(
                    statistics.fmean(len(c.consulta) for c in casos) / 4.2
                ),
            }
            if calibracion:
                brazos[clave]["calibracion"] = calibracion
            if variante == "descripciones":
                llm_pred = _predicciones_llm(tenant_id, casos)
                if tenant_id == TENANT_CALIBRACION:
                    cal_m = calibrar_margen(enrutador, casos, vectores, umbral, llm_pred)
                    umbrales["margen_cascada"] = cal_m["margen"]
                margen = umbrales["margen_cascada"]
                pred, al_llm = predecir_cascada(enrutador, casos, vectores, umbral, margen, llm_pred)
                lat_llm = brazos["llm"]["latencia_media_s"]
                lat_emb = brazos[clave]["latencia_media_s"]
                brazos["cascada"] = {
                    "umbral_otro": umbral,
                    "margen": margen,
                    "calibrado_aqui": tenant_id == TENANT_CALIBRACION,
                    **acierto(casos, pred),
                    "consultas_al_llm": al_llm,
                    "fraccion_al_llm": round(al_llm / len(casos), 4),
                    # La latencia media es la de embeddings siempre, más la del
                    # LLM en la fracción que lo necesita.
                    "latencia_media_s": round(lat_emb + lat_llm * al_llm / len(casos), 3),
                    "coste_usd_por_consulta": round(
                        brazos["llm"]["coste_usd_por_consulta"] * al_llm / len(casos), 6
                    ),
                }
                if tenant_id == TENANT_CALIBRACION:
                    brazos["cascada"]["calibracion"] = cal_m
        resultado["tenants"][tenant_id] = {"casos": len(casos), "brazos": brazos}

    resultado["umbrales"] = umbrales
    resultado["uso_embeddings"] = uso.resumen()
    resultado["duracion_s"] = round(time.perf_counter() - t_total, 1)

    # Agregado sobre los 121 casos, con y sin el inquilino de calibración.
    agregados = {}
    for brazo in ("llm", *[f"embeddings_{v}" for v in VARIANTES], "cascada"):
        for etiqueta, filtro in (("todos", lambda t: True), ("transferencia", lambda t: t != TENANT_CALIBRACION)):
            ts = [d["brazos"][brazo] for t, d in resultado["tenants"].items() if filtro(t)]
            casos = sum(b["casos"] for b in ts)
            agregados.setdefault(brazo, {})[etiqueta] = {
                "casos": casos,
                "tasa": round(sum(b["aciertos"] for b in ts) / casos, 4),
                "riesgo_tasa": round(
                    sum(b["riesgo_aciertos"] for b in ts) / sum(b["riesgo_casos"] for b in ts), 4
                ),
            }
    resultado["agregados"] = agregados

    print()
    print("=== ENRUTADOR LLM FRENTE A EMBEDDINGS ===")
    print(f"umbrales calibrados en {TENANT_CALIBRACION}: {umbrales}")
    print(f"{'inquilino':<22} {'brazo':<26} {'acierto':>9} {'riesgo':>8} {'lat. media':>11} {'USD/consulta':>13}")
    for tenant_id, d in resultado["tenants"].items():
        for brazo, b in d["brazos"].items():
            marca = " (en muestra)" if b.get("calibrado_aqui") else ""
            coste = "sin precio" if b["coste_usd_por_consulta"] is None else f"{b['coste_usd_por_consulta']:.6f}"
            extra = f"  (al LLM {b['fraccion_al_llm']:.0%})" if "fraccion_al_llm" in b else ""
            print(f"{tenant_id:<22} {brazo:<26} {b['aciertos']:>3}/{b['casos']:<5} "
                  f"{b['riesgo_aciertos']:>3}/{b['riesgo_casos']:<4} {b['latencia_media_s']:>9.3f} s {coste:>13}{marca}{extra}")
    print()
    for brazo, a in agregados.items():
        print(f"  {brazo:<26} todos {a['todos']['tasa']:.3f} (riesgo {a['todos']['riesgo_tasa']:.3f}) | "
              f"transferencia {a['transferencia']['tasa']:.3f} (riesgo {a['transferencia']['riesgo_tasa']:.3f})")
    print()
    print("Consumo de embeddings:", json.dumps(uso.resumen(), ensure_ascii=False))

    salida = RAIZ / args.salida
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resumen.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Detalle en", salida / "resumen.json")


if __name__ == "__main__":
    main()
