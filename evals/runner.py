"""Ejecutor del banco de pruebas.

    uv run python -m evals.runner --suite consultas --etiqueta baseline

El flujo tiene dos fases separadas a propósito:

1. **Ejecución del sistema** — se lanza cada caso contra el MVP y se guarda la
   traza completa (respuesta, contexto recuperado, distancias, latencias).
2. **Evaluación** — las métricas se calculan sobre esas trazas.

Están separadas porque la fase 1 es la cara y la 2 la que se cambia de opinión:
ajustar un umbral, añadir una métrica o reescribir los pasos de un juez no
debería obligar a volver a llamar al modelo. `--desde-trazas` reevalúa una
ejecución anterior sin gastar una sola llamada al sistema.
"""
import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from src.agent import Sistema
from src.config import load_config
from src.gobernanza import Usuario
from src.provider import get_chat
from src.tenant import Tenant

from .dataset import (
    GOLDEN_CONSULTAS,
    GOLDEN_TRANSCRIPCION,
    cargar_consultas,
    cargar_transcripciones,
    ruta_golden,
)
from .metrics.deterministas import (
    Resultado,
    evaluar_alcance_riesgo,
    evaluar_contiene,
    evaluar_fuga_literal,
    evaluar_retrieval,
    evaluar_routing,
)
from .metrics.juez import Juez
from .report import informe_consultas, informe_transcripcion
from .schema import METRICAS_JUEZ, CasoConsulta, Metrica
from .transcripcion import ejecutar_transcripcion, evaluar_transcripcion
from .variantes import asegurar_indice, descripcion, variante

# Coste del juez por caso, medido en `reports/juez_instrumentado` (24 llamadas
# sobre 3 casos) y recalculado al corregir el precio de claude-sonnet-5, que el
# repo sobreestimaba un 50 %. Existe para poder avisar ANTES de gastar: el juez
# cuesta 11 veces lo que el sistema, y una pasada completa de los dos bancos son
# 2,53 USD. Ver docs/HALLAZGOS.md §17 y §21.
COSTE_JUEZ_POR_CASO_USD = 0.0278

RAIZ_REPO = Path(__file__).resolve().parents[1]
RAIZ_REPORTES = RAIZ_REPO / "reports"


def _ruta_relativa(ruta: Path) -> str:
    """Ruta relativa al repo: los informes se versionan y no deben llevar
    la ruta local de quien los generó."""
    try:
        return ruta.resolve().relative_to(RAIZ_REPO).as_posix()
    except ValueError:
        return ruta.as_posix()


# --- Fase 1: ejecutar el sistema bajo prueba --------------------------------

def ejecutar_sut(sistema: Sistema, casos: list[CasoConsulta], workers: int = 1) -> list[dict]:
    total = len(casos)
    trazas: list[dict | None] = [None] * total
    hecho = 0

    def _uno(indice_caso):
        i, caso = indice_caso
        try:
            traza = sistema.responder(
                caso.consulta,
                usuario=Usuario(id=caso.id, roles=caso.roles_usuario),
            )
        except Exception as e:  # noqa: BLE001 -- un caso roto no debe tumbar el banco
            traza = {
                "consulta": caso.consulta,
                "categoria": "ERROR",
                "confianza_enrutador": 0.0,
                "fallback_enrutador": False,
                "fuentes_usadas": [],
                "contexto_recuperado": [],
                "respuesta": "",
                "error": f"{type(e).__name__}: {e}",
                "latencia_router_s": 0.0,
                "latencia_retrieve_s": 0.0,
                "latencia_generacion_s": 0.0,
            }
        return i, traza

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for i, traza in pool.map(_uno, enumerate(casos)):
            trazas[i] = traza
            hecho += 1
            print(f"\r[sut] {hecho}/{total} casos ejecutados", end="", flush=True)
    print()
    return [t for t in trazas if t is not None]


# --- Fase 2: evaluar ---------------------------------------------------------

def _metricas_deterministas(
    caso: CasoConsulta, traza: dict, tenant: Tenant
) -> list[Resultado]:
    salidas: list[Resultado] = []
    pedidas = set(caso.metricas)
    if Metrica.routing in pedidas:
        salidas.append(evaluar_routing(caso, traza))
    if Metrica.retrieval in pedidas:
        salidas.extend(evaluar_retrieval(caso, traza))
    if Metrica.contiene in pedidas:
        salidas.append(evaluar_contiene(caso, traza))
    # Las dos últimas no las pide el caso: se aplican siempre que tengan
    # sentido, son gratis y ninguna otra métrica las sustituye. La de fuga
    # literal dice si se filtró algo; la de alcance, si la pregunta llegó
    # siquiera al sitio donde podía filtrarse.
    salidas.append(evaluar_fuga_literal(caso, traza))
    salidas.append(evaluar_alcance_riesgo(caso, traza, tenant))
    return salidas


def evaluar_casos(
    casos: list[CasoConsulta],
    trazas: list[dict],
    juez: Juez | None,
    tenant: Tenant,
    workers: int = 1,
) -> list[dict]:
    registros: list[dict | None] = [None] * len(casos)
    total = len(casos)
    hecho = 0

    def _uno(args):
        i, caso, traza = args
        resultados = _metricas_deterministas(caso, traza, tenant)
        if juez is not None:
            pedidas = [m for m in caso.metricas if m in METRICAS_JUEZ]
            if pedidas and traza.get("respuesta"):
                resultados.extend(juez.evaluar(caso, traza, pedidas))
        return i, {
            "id": caso.id,
            "dimension": caso.dimension.value,
            "origen": caso.origen,
            "consulta": caso.consulta,
            "comportamiento_esperado": caso.comportamiento_esperado.value,
            "respuesta_esperada": caso.respuesta_esperada,
            "traza": traza,
            "metricas": [
                {
                    "metrica": r.metrica,
                    "valor": r.valor,
                    "exito": r.exito,
                    "razon": r.razon,
                    "detalle": r.detalle,
                }
                for r in resultados
            ],
            # Las métricas que no aplican vienen con exito=True, así que no
            # penalizan; los fallos del juez vienen con exito=False y sí.
            "ok": all(r.exito for r in resultados),
        }

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for i, registro in pool.map(_uno, ((i, c, t) for i, (c, t) in enumerate(zip(casos, trazas)))):
            registros[i] = registro
            hecho += 1
            print(f"\r[eval] {hecho}/{total} casos evaluados", end="", flush=True)
    print()
    return [r for r in registros if r is not None]


# --- Agregación --------------------------------------------------------------

def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = min(len(orden) - 1, round((len(orden) - 1) * p))
    return orden[k]


# Métricas cuyo verde solo significa algo si la consulta llegó al control.
METRICAS_DE_FUGA = ("fuga_literal", "confidencialidad", "pii_leakage")

# La cobertura no puntúa al sistema, describe al banco: se agrega aparte para
# que no contamine la media de las métricas que sí lo puntúan.
METRICAS_INFORMATIVAS = ("alcance_riesgo",)


def cobertura_riesgo(registros: list[dict]) -> dict:
    """Qué proporción de los casos de seguridad llegó al punto donde el control actúa.

    Devuelve además el contraste que motiva la métrica: la tasa de "sin fuga"
    calculada sobre todos los casos de riesgo frente a la calculada solo sobre
    los que llegaron a ponerla a prueba. La primera es la que engaña; la segunda
    es la que se puede defender.
    """
    en_riesgo: list[dict] = []
    for reg in registros:
        alcance = next(
            (m for m in reg["metricas"] if m["metrica"] == "alcance_riesgo"), None
        )
        if alcance is None or alcance["valor"] is None:
            continue
        fuga = [m for m in reg["metricas"] if m["metrica"] in METRICAS_DE_FUGA
                and m["valor"] is not None]
        en_riesgo.append({
            "id": reg["id"],
            "dimension": reg["dimension"],
            "alcanza": alcance["valor"] == 1.0,
            "superficie": alcance["detalle"].get("superficie", "?"),
            "razon": alcance["razon"],
            # Sin métricas de fuga (los casos de acceso autorizado) no hay nada
            # que declarar limpio: el veredicto se deja en None en vez de
            # contarlo como verde, que es justo el error que esta métrica ataca.
            "sin_fuga": all(m["exito"] for m in fuga) if fuga else None,
        })

    n = len(en_riesgo)
    cubiertos = [c for c in en_riesgo if c["alcanza"]]

    def _tasa_sin_fuga(grupo: list[dict]) -> dict:
        juzgados = [c for c in grupo if c["sin_fuga"] is not None]
        limpios = sum(1 for c in juzgados if c["sin_fuga"])
        return {
            "casos": len(juzgados),
            "limpios": limpios,
            "tasa": round(limpios / len(juzgados), 4) if juzgados else None,
        }

    return {
        "casos_en_riesgo": n,
        "alcanzan_el_control": len(cubiertos),
        "cobertura": round(len(cubiertos) / n, 4) if n else None,
        "sin_fuga_aparente": _tasa_sin_fuga(en_riesgo),
        "sin_fuga_medido": _tasa_sin_fuga(cubiertos),
        "por_superficie": {
            s: {
                "casos": sum(1 for c in en_riesgo if c["superficie"] == s),
                "alcanzan": sum(1 for c in cubiertos if c["superficie"] == s),
            }
            for s in sorted({c["superficie"] for c in en_riesgo})
        },
        "no_alcanzados": [
            {"id": c["id"], "dimension": c["dimension"], "razon": c["razon"]}
            for c in en_riesgo
            if not c["alcanza"]
        ],
        "detalle": en_riesgo,
    }


def alcance_de_fuente(registros: list[dict]) -> dict:
    """Con qué frecuencia se consultó de verdad la categoría esperada.

    `routing` mide la **elección** del enrutador y no se toca: es la línea base
    de los 109 casos heredados. Pero con grupos de solapamiento declarados,
    acertar la elección y consultar la fuente correcta dejan de ser lo mismo, y
    al usuario le importa la segunda: una consulta que el enrutador manda a
    `expedientes` pero que acaba mirando también el CRM sí recibe su respuesta.

    Se reporta **al lado** de `routing`, nunca en su lugar. Si sustituyera a
    `routing`, un inquilino que declarase un grupo con todas sus categorías
    sacaría un acierto perfecto sin haber enrutado nada: la cifra mediría la
    amplitud del grupo y no la calidad del enrutado. Separadas, la distancia
    entre las dos es justo el precio que se paga por no elegir.
    """
    casos = 0
    alcanzadas = 0
    por_solapamiento = 0
    for reg in registros:
        routing = next(
            (m for m in reg["metricas"] if m["metrica"] == "routing"), None
        )
        if routing is None or routing["valor"] is None:
            continue
        esperada = routing["detalle"].get("esperada")
        if not esperada:
            continue
        traza = reg["traza"]
        consultadas = traza.get("categorias_consultadas") or [traza.get("categoria")]
        casos += 1
        if esperada in consultadas:
            alcanzadas += 1
            if esperada != traza.get("categoria"):
                por_solapamiento += 1
    return {
        "casos": casos,
        "consultada": alcanzadas,
        "tasa": round(alcanzadas / casos, 4) if casos else None,
        "solo_por_solapamiento": por_solapamiento,
    }


def agregar(registros: list[dict]) -> dict:
    por_metrica: dict[str, dict] = {}
    por_dimension: dict[str, dict] = {}
    confusion: dict[str, dict[str, int]] = {}
    fallos: list[dict] = []
    # Una métrica que no llegó a puntuar no puede desaparecer del informe: sin
    # esto, un juez caído deja los casos en rojo con todas sus métricas en verde
    # y el informe parece contradecirse. Es la misma regla que se le exige al
    # enrutador: ningún fallo silencioso.
    errores: list[dict] = []
    fallback = 0
    latencias: list[float] = []

    for reg in registros:
        dim = reg["dimension"]
        d = por_dimension.setdefault(dim, {"casos": 0, "ok": 0, "metricas": {}})
        d["casos"] += 1
        d["ok"] += 1 if reg["ok"] else 0

        traza = reg["traza"]
        if traza.get("fallback_enrutador"):
            fallback += 1
        latencias.append(
            traza.get("latencia_router_s", 0.0)
            + traza.get("latencia_retrieve_s", 0.0)
            + traza.get("latencia_generacion_s", 0.0)
        )

        for m in reg["metricas"]:
            if m["metrica"] in METRICAS_INFORMATIVAS:
                continue
            if m["valor"] is None:
                if not m["exito"]:
                    errores.append(
                        {"id": reg["id"], "metrica": m["metrica"], "razon": m["razon"][:300]}
                    )
                continue
            g = por_metrica.setdefault(m["metrica"], {"n": 0, "suma": 0.0, "exitos": 0})
            g["n"] += 1
            g["suma"] += m["valor"]
            g["exitos"] += 1 if m["exito"] else 0

            gd = d["metricas"].setdefault(m["metrica"], {"n": 0, "suma": 0.0, "exitos": 0})
            gd["n"] += 1
            gd["suma"] += m["valor"]
            gd["exitos"] += 1 if m["exito"] else 0

            if not m["exito"]:
                fallos.append(
                    {
                        "id": reg["id"],
                        "dimension": dim,
                        "metrica": m["metrica"],
                        "valor": m["valor"],
                        "razon": m["razon"][:400],
                        "consulta": reg["consulta"],
                    }
                )

            if m["metrica"] == "routing":
                esperada = m["detalle"].get("esperada", "?")
                obtenida = m["detalle"].get("obtenida", "?")
                confusion.setdefault(esperada, {})
                confusion[esperada][obtenida] = confusion[esperada].get(obtenida, 0) + 1

    def _cerrar(g: dict) -> dict:
        return {
            "n": g["n"],
            "media": round(g["suma"] / g["n"], 4) if g["n"] else None,
            "tasa_exito": round(g["exitos"] / g["n"], 4) if g["n"] else None,
        }

    for dim in por_dimension.values():
        dim["tasa_ok"] = round(dim["ok"] / dim["casos"], 4)
        dim["metricas"] = {k: _cerrar(v) for k, v in dim["metricas"].items()}

    n = len(registros)
    return {
        "casos": n,
        "casos_ok": sum(1 for r in registros if r["ok"]),
        "tasa_casos_ok": round(sum(1 for r in registros if r["ok"]) / n, 4) if n else 0.0,
        "fallback_enrutador": fallback,
        "tasa_fallback": round(fallback / n, 4) if n else 0.0,
        "latencia_media_s": round(statistics.fmean(latencias), 3) if latencias else 0.0,
        "latencia_p95_s": round(_percentil(latencias, 0.95), 3),
        "por_metrica": {k: _cerrar(v) for k, v in sorted(por_metrica.items())},
        "por_dimension": dict(sorted(por_dimension.items())),
        "confusion_enrutador": confusion,
        "alcance_de_fuente": alcance_de_fuente(registros),
        "cobertura_riesgo": cobertura_riesgo(registros),
        "fallos": fallos,
        "errores_metrica": errores,
    }


# --- Orquestación ------------------------------------------------------------

def _escribir(directorio: Path, nombre: str, contenido) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / nombre
    if isinstance(contenido, str):
        ruta.write_text(contenido, encoding="utf-8")
    else:
        ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def suite_consultas(args) -> None:
    base = load_config()
    cfg = variante(
        base,
        chunk_strategy=args.chunk_strategy or base.chunk_strategy,
        chunk_size=args.chunk_size or base.chunk_size,
        top_k=args.top_k or base.top_k,
        embed_dims=args.embed_dims or base.embed_dims,
        gen_policy=args.gen_policy or base.gen_policy,
        distance_threshold=(
            args.distance_threshold
            if args.distance_threshold is not None
            else base.distance_threshold
        ),
    )

    ruta_dataset = (
        Path(args.dataset)
        if args.dataset
        else ruta_golden(cfg.tenant.id, GOLDEN_CONSULTAS)
    )
    casos = cargar_consultas(ruta_dataset)
    if args.dimensiones:
        pedidas = set(args.dimensiones.split(","))
        casos = [c for c in casos if c.dimension.value in pedidas]
    if args.limite:
        casos = casos[: args.limite]
    if not casos:
        sys.exit("[runner] El filtro no dejó ningún caso que ejecutar.")

    directorio = RAIZ_REPORTES / args.etiqueta
    t0 = time.perf_counter()
    uso = None

    if args.desde_trazas:
        trazas = [json.loads(linea) for linea in Path(args.desde_trazas).read_text("utf-8").splitlines() if linea.strip()]
        por_id = {t["consulta"]: t for t in trazas}
        trazas = [por_id[c.consulta] for c in casos if c.consulta in por_id]
        casos = [c for c in casos if c.consulta in por_id]
        print(f"[runner] Reevaluando {len(casos)} trazas de {args.desde_trazas} (sin llamar al sistema).")
    else:
        asegurar_indice(cfg)
        chat = get_chat(cfg)
        sistema = Sistema(cfg, chat=chat)
        print(f"[runner] Ejecutando {len(casos)} casos contra el MVP...")
        trazas = ejecutar_sut(sistema, casos, workers=args.workers)
        uso = chat.uso.resumen()
        _escribir(
            directorio,
            "trazas.jsonl",
            "\n".join(json.dumps(t, ensure_ascii=False) for t in trazas) + "\n",
        )

    juez = None
    if not args.sin_juez:
        # El aviso va antes de crear el juez y no en la ayuda: `--desde-trazas`
        # no llama al sistema, y es facil leer eso como "esta ejecucion no
        # cuesta". El juez se lanza igual, y es la parte cara.
        print(f"[runner] Juez: {cfg.judge_model} (distinto del generador {cfg.model_generator}).")
        print(f"[!] AVISO DE COSTE: el juez se ejecutara sobre {len(casos)} casos. "
              f"Estimado {COSTE_JUEZ_POR_CASO_USD * len(casos):.2f} USD "
              f"({COSTE_JUEZ_POR_CASO_USD:.4f} USD/caso, medido). "
              f"Anade --sin-juez para no pagarlo.")
        # La clave del juez, no la del sistema: es la que hace que la factura
        # del proveedor pueda responder cuánto cuesta evaluar.
        clave = cfg.gemini_api_key if cfg.judge_provider == "gemini" else cfg.judge_api_key
        juez = Juez(api_key=clave, modelo=cfg.judge_model, proveedor=cfg.judge_provider)

    registros = evaluar_casos(
        casos, trazas, juez, cfg.tenant, workers=args.workers_juez
    )
    resumen = agregar(registros)
    resumen["meta"] = {
        "etiqueta": args.etiqueta,
        "dataset": _ruta_relativa(ruta_dataset),
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "duracion_s": round(time.perf_counter() - t0, 1),
        "con_juez": not args.sin_juez,
        "configuracion": descripcion(cfg),
        "uso_sistema": uso,
        # El gasto del juez, aparte del del sistema y nunca sumado por el
        # camino: las dos claves estan separadas desde el feedback de la 3.3
        # para poder decir cuanto cuesta evaluar frente a cuanto cuesta
        # funcionar, y un total unico borra justo esa distincion.
        "uso_juez": juez.uso.resumen() if juez else None,
        "juez_llamadas_sin_tokens": juez.model.sin_tokens if juez else 0,
    }

    _escribir(directorio, "resultados.json", registros)
    _escribir(directorio, "resumen.json", resumen)
    ruta_md = _escribir(directorio, "informe.md", informe_consultas(resumen, registros))

    print(f"\n[OK] Casos OK: {resumen['casos_ok']}/{resumen['casos']} "
          f"({resumen['tasa_casos_ok']:.0%})")
    if uso:
        print(f"[OK] Coste estimado de la ejecución del sistema: "
              f"{uso['coste_usd_estimado']:.4f} USD ({uso['llamadas']} llamadas)")
    if juez is not None:
        uj = resumen["meta"]["uso_juez"]
        print(f"[OK] Coste estimado del juez: {uj['coste_usd_estimado']:.4f} USD "
              f"({uj['llamadas']} llamadas)")
        if resumen["meta"]["juez_llamadas_sin_tokens"]:
            print(f"[!]  {resumen['meta']['juez_llamadas_sin_tokens']} llamadas del juez "
                  f"no informaron tokens: el coste del juez es una cota INFERIOR.")
    print(f"[OK] Informe: {ruta_md}")


def suite_transcripcion(args) -> None:
    cfg = load_config()
    ruta = (
        Path(args.dataset)
        if args.dataset
        else ruta_golden(cfg.tenant.id, GOLDEN_TRANSCRIPCION)
    )
    casos = cargar_transcripciones(ruta)
    if args.limite:
        casos = casos[: args.limite]

    chat = get_chat(cfg)
    print(f"[runner] Transcribiendo {len(casos)} reuniones...")
    salidas = ejecutar_transcripcion(cfg, chat, casos)
    registros = [evaluar_transcripcion(c, s) for c, s in zip(casos, salidas)]

    n = len(registros)
    resumen = {
        "casos": n,
        "casos_ok": sum(1 for r in registros if r["ok"]),
        "medias": {
            campo: round(
                statistics.fmean([r["metricas"][campo] for r in registros if r["metricas"][campo] is not None]), 4
            )
            for campo in ("titulo", "fecha", "asistentes_f1", "decisiones_f1", "tareas_f1", "sin_fuga")
            if any(r["metricas"][campo] is not None for r in registros)
        },
        "meta": {
            "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
            "dataset": _ruta_relativa(ruta),
            "modelo": cfg.model_generator,
            "uso": chat.uso.resumen(),
        },
    }

    directorio = RAIZ_REPORTES / args.etiqueta
    _escribir(directorio, "transcripcion_resultados.json", registros)
    _escribir(directorio, "transcripcion_resumen.json", resumen)
    ruta_md = _escribir(directorio, "informe_transcripcion.md", informe_transcripcion(resumen, registros))
    print(f"[OK] Casos OK: {resumen['casos_ok']}/{n}. Informe: {ruta_md}")


def main() -> None:
    p = argparse.ArgumentParser(description="Banco de pruebas del asistente RAG (entrega 3.3)")
    p.add_argument("--suite", choices=("consultas", "transcripcion"), default="consultas")
    p.add_argument("--dataset", help="Ruta a un JSONL alternativo (p. ej. el set sintético)")
    p.add_argument("--etiqueta", default="ultima", help="Subcarpeta de reports/ donde escribir")
    p.add_argument("--limite", type=int, help="Ejecutar solo los N primeros casos")
    p.add_argument("--dimensiones", help="Filtrar por dimensiones, separadas por comas")
    p.add_argument(
        "--sin-juez",
        action="store_true",
        help=(
            "Solo métricas deterministas: sin coste de juez. NO implica coste cero: "
            "el sistema bajo prueba sigue llamando al proveedor salvo que además "
            "se use --desde-trazas"
        ),
    )
    p.add_argument(
        "--desde-trazas",
        help=(
            "Reevaluar las trazas de una ejecución anterior sin llamar al sistema. "
            "OJO: por sí solo NO evita el coste del juez, que es el caro; para una "
            "ejecución sin coste hacen falta las dos banderas"
        ),
    )
    p.add_argument("--workers", type=int, default=4, help="Casos en paralelo contra el sistema")
    p.add_argument("--workers-juez", type=int, default=2, help="Casos en paralelo contra el juez")
    # Sobreescrituras de configuración: permiten evaluar una variante sin tocar .env
    p.add_argument("--chunk-strategy", choices=("chars", "headings"))
    p.add_argument("--chunk-size", type=int)
    p.add_argument("--top-k", type=int)
    p.add_argument("--embed-dims", type=int)
    p.add_argument("--gen-policy", choices=("base", "hardened"))
    p.add_argument("--distance-threshold", type=float)
    args = p.parse_args()

    if args.suite == "consultas":
        suite_consultas(args)
    else:
        suite_transcripcion(args)


if __name__ == "__main__":
    main()
