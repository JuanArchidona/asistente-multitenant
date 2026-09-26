"""Prueba de carga y de concurrencia, en dos frentes que no miden lo mismo.

El capítulo de límites de la memoria decía: "no hay prueba de carga ni de
concurrencia; las latencias son de ejecuciones secuenciales". Este script
cierra esa frase con una medida, y separa a propósito dos cosas que suelen
mezclarse bajo la palabra "carga":

1. **Frente HTTP remoto** (`--remoto`). N peticiones simultáneas a los dos
   servicios desplegados en Render (plan gratuito, una instancia cada uno):
   `GET /` de la interfaz Streamlit y `GET /salud` del servicio de WhatsApp.
   No ejecuta ninguna consulta: mide cuántos clientes a la vez aguanta la
   puerta, no la cocina. Coste cero. Antes de medir, despierta los dos
   servicios (§52: 32-61 s en frío) y descarta esa primera petición.

2. **Pipeline local bajo concurrencia** (`--local`). El sistema real —
   enrutador, recuperación en Chroma, generador con la API de Anthropic —
   con un único `Sistema` compartido por N hilos, que es exactamente lo que
   hace el servidor de WhatsApp (un hilo por mensaje sobre el mismo objeto).
   Ocho consultas del banco heredado a concurrencia 1, 2, 4 y 8. Mide la
   latencia de pared por consulta y sus tres tramos, el tiempo total del
   lote, el coste por `Uso` y dos invariantes que la concurrencia no debe
   romper: el enrutado no cambia respecto a la pasada secuencial y la
   consulta confidencial sigue denegada. La contención, si la hay, aparece
   dentro de los tramos (el GIL y el cerrojo de Chroma se pagan mientras el
   tramo corre), así que se lee comparando el p50 de cada tramo entre
   niveles, no como una cola aparte: `cola_media_s` es la diferencia entre
   pared y suma de tramos y sale cero por construcción; se guarda como
   comprobación, no como medida. Con `--agencia`, lo mismo sobre la rama
   estructurada (cliente MCP con su bucle en un hilo aparte) a 1 y 4.
   Coste: en torno a 0,08 USD el heredado y 0,03 la agencia.

Lo que **no** mide, y se dice: consultas reales concurrentes contra Render.
Streamlit habla por websocket y WhatsApp exige un webhook firmado por Meta;
las dos cosas se pueden simular, pero cada consulta costaría lo mismo que
aquí y mediría además la red, que ya está medida en el §52. El pipeline
compartido entre hilos es el mismo código en local y en Render; lo que
cambia es la CPU del plan gratuito, y eso se declara como límite.

    uv run python scripts/prueba_carga.py --remoto
    uv run python scripts/prueba_carga.py --local
    uv run python scripts/prueba_carga.py --local --agencia
    uv run python scripts/prueba_carga.py --remoto --local --agencia --etiqueta prueba_carga
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SERVICIOS = {
    "asistente-multitenant": "https://asistente-multitenant.onrender.com/",
    "asistente-whatsapp-n2s9": "https://asistente-whatsapp-n2s9.onrender.com/salud",
}
NIVELES_REMOTO = (1, 5, 10, 20)
RONDAS_REMOTO = 3

# Ocho consultas del banco heredado: seis de conocimiento repartidas por las
# cuatro categorías, una fuera del corpus y una confidencial. Los ids son los
# del golden set para poder volver a él.
CONSULTAS_HEREDADO = [
    ("know-rrhh-01", "¿Cuántos días de vacaciones me corresponden al año?"),
    ("know-rrhh-04", "¿Qué día del mes se paga la nómina?"),
    ("know-dev-01", "¿Qué versión mínima de Python se usa en los proyectos nuevos?"),
    ("know-dev-04", "¿Qué gestor de paquetes y entornos usamos?"),
    ("know-marca-01", "¿Cuál es el color primario de la marca?"),
    ("know-act-01", "¿Cuándo se desplegó el parche del bug de pagos?"),
    ("ooc-01", "¿Cuál es la política de dietas y gastos de viaje?"),
    ("conf-01", "¿Cuánto cobra Diego Ruíz al año?"),
]
NIVELES_LOCAL = (1, 2, 4, 8)

# Cuatro consultas de la rama estructurada de la agencia: las tres de
# conocimiento de cartera y la de frontera. Todas pasan por el cliente MCP.
CONSULTAS_AGENCIA = [
    ("know-cart-01", "¿Cuántos inmuebles llevan más de 90 días publicados sin ninguna oferta?"),
    ("know-cart-02", "¿A cuánto tenemos el metro cuadrado de media en Delicias en nuestra cartera?"),
    ("know-cart-03", "¿En qué estado está la operación OP-2026-110?"),
    ("front-cart-01", "¿Cuántos inmuebles tenemos captados en exclusiva ahora mismo?"),
]
NIVELES_AGENCIA = (1, 4)


def _p(valores: list[float], q: float) -> float:
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = max(0, min(len(orden) - 1, round(q * (len(orden) - 1))))
    return orden[k]


def _estadisticas(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0}
    return {
        "n": len(valores),
        "media_s": round(statistics.fmean(valores), 3),
        "p50_s": round(_p(valores, 0.50), 3),
        "p95_s": round(_p(valores, 0.95), 3),
        "max_s": round(max(valores), 3),
    }


# --- 1. Frente HTTP remoto ----------------------------------------------------


def _get(url: str, timeout: float = 120.0) -> tuple[float, int | None, str]:
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            resp.read()
            return time.perf_counter() - t0, resp.status, ""
    except urllib.error.HTTPError as error:
        return time.perf_counter() - t0, error.code, f"HTTP {error.code}"
    except Exception as error:  # noqa: BLE001 - se anota, no se oculta
        return time.perf_counter() - t0, None, type(error).__name__


def medir_remoto() -> dict:
    resultado: dict = {"niveles": NIVELES_REMOTO, "rondas": RONDAS_REMOTO, "servicios": {}}
    for nombre, url in SERVICIOS.items():
        print(f"\n[remoto] {nombre}: despertando...")
        despertar, estado, _ = _get(url)
        print(f"[remoto]   primera petición {despertar:.2f} s (HTTP {estado}); se descarta")
        por_nivel = {}
        for n in NIVELES_REMOTO:
            latencias, errores, paredes = [], [], []
            for _ in range(RONDAS_REMOTO):
                t0 = time.perf_counter()
                with ThreadPoolExecutor(max_workers=n) as pool:
                    filas = list(pool.map(_get, [url] * n))
                paredes.append(time.perf_counter() - t0)
                for lat, est, err in filas:
                    if est == 200:
                        latencias.append(lat)
                    else:
                        errores.append(err or f"HTTP {est}")
            por_nivel[str(n)] = {
                **_estadisticas(latencias),
                "peticiones": n * RONDAS_REMOTO,
                "errores": len(errores),
                "errores_detalle": sorted(set(errores)),
                "pared_por_ronda_s": [round(p, 3) for p in paredes],
            }
            print(
                f"[remoto]   {n:>2} a la vez x{RONDAS_REMOTO}: p50 {por_nivel[str(n)]['p50_s']} s, "
                f"p95 {por_nivel[str(n)]['p95_s']} s, max {por_nivel[str(n)]['max_s']} s, "
                f"errores {len(errores)}"
            )
        resultado["servicios"][nombre] = {"url": url, "despertar_descartado_s": round(despertar, 2), "por_nivel": por_nivel}
    return resultado


# --- 2. Pipeline local bajo concurrencia -------------------------------------


def _suma_tramos(traza: dict) -> float:
    return sum(traza.get(k) or 0.0 for k in ("latencia_router_s", "latencia_retrieve_s", "latencia_generacion_s"))


def medir_local(tenant_id: str, consultas: list[tuple[str, str]], niveles: tuple[int, ...]) -> dict:
    from src.agent import Sistema
    from src.config import load_config
    from src.ingest import asegurar_indice

    cfg = load_config(tenant_id, con_juez=False)
    asegurar_indice(cfg, avisar=lambda m: print(f"[local] {m}"))
    resultado: dict = {"tenant": tenant_id, "consultas": [c[0] for c in consultas], "niveles": niveles, "por_nivel": {}}

    # Un solo Sistema para todos los niveles, como el servidor de WhatsApp:
    # un objeto por inquilino compartido entre hilos. Sin registro: esto es
    # banco, no producción.
    with Sistema(cfg) as sistema:
        # Primera consulta fuera de la medida: abre el retriever y, si hay MCP,
        # arranca el servidor. Es el mismo calentamiento que hace la demo.
        sistema.responder(consultas[0][1])
        enrutado_base: dict[str, str] | None = None
        for n in niveles:
            antes = sistema.chat.uso.resumen()

            def una(par: tuple[str, str]) -> tuple[str, dict]:
                cid, texto = par
                t0 = time.perf_counter()
                try:
                    traza = sistema.responder(texto)
                    pared = time.perf_counter() - t0
                    return cid, {
                        "pared_s": round(pared, 3),
                        "tramos_s": round(_suma_tramos(traza), 3),
                        "router_s": round(traza.get("latencia_router_s") or 0.0, 3),
                        "retrieve_s": round(traza.get("latencia_retrieve_s") or 0.0, 3),
                        "generacion_s": round(traza.get("latencia_generacion_s") or 0.0, 3),
                        "categoria": traza.get("categoria"),
                        "denegados_por_permiso": traza.get("denegados_por_permiso", []),
                        "respuesta": traza.get("respuesta", ""),
                        "error": None,
                    }
                except Exception as error:  # noqa: BLE001 - un fallo bajo carga ES el dato
                    return cid, {"pared_s": round(time.perf_counter() - t0, 3), "error": f"{type(error).__name__}: {error}"[:300]}

            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=n) as pool:
                filas: dict[str, dict] = dict(pool.map(una, consultas))
            pared_lote = time.perf_counter() - t0
            despues = sistema.chat.uso.resumen()

            ok = [f for f in filas.values() if f.get("error") is None]
            paredes = [f["pared_s"] for f in ok]
            tramos = [f["tramos_s"] for f in ok]
            enrutado = {cid: f.get("categoria") for cid, f in filas.items()}
            if enrutado_base is None:
                enrutado_base = enrutado
            cambios_enrutado = sorted(cid for cid in enrutado if enrutado[cid] != enrutado_base.get(cid))
            conf = filas.get("conf-01", {})
            confidencial_denegada = bool(conf.get("denegados_por_permiso")) if conf and conf.get("error") is None else None

            resultado["por_nivel"][str(n)] = {
                "concurrencia": n,
                "consultas": len(consultas),
                "errores": [f"{cid}: {f['error']}" for cid, f in filas.items() if f.get("error")],
                "pared_lote_s": round(pared_lote, 3),
                "consultas_por_minuto": round(60 * len(ok) / pared_lote, 2) if pared_lote else None,
                "pared_por_consulta": _estadisticas(paredes),
                "suma_tramos_por_consulta": _estadisticas(tramos),
                "cola_media_s": round(statistics.fmean(p - t for p, t in zip(paredes, tramos)), 3) if ok else None,
                "coste_usd": round(despues["coste_usd_estimado"] - antes["coste_usd_estimado"], 6),
                "llamadas": despues["llamadas"] - antes["llamadas"],
                "enrutado": enrutado,
                "cambios_enrutado_frente_a_secuencial": cambios_enrutado,
                "confidencial_denegada": confidencial_denegada,
                # Por consulta, para poder ir al valor atípico: qué tramo se
                # llevó el tiempo cuando el p95 se dispara.
                "por_consulta": {
                    cid: {k: f.get(k) for k in ("pared_s", "router_s", "retrieve_s", "generacion_s", "categoria", "error")}
                    for cid, f in filas.items()
                },
                "respuestas": {cid: (f.get("respuesta") or "")[:400] for cid, f in filas.items()},
            }
            r = resultado["por_nivel"][str(n)]
            print(
                f"[local] {tenant_id} x{n}: lote {r['pared_lote_s']} s, p50 {r['pared_por_consulta'].get('p50_s')} s, "
                f"p95 {r['pared_por_consulta'].get('p95_s')} s, cola media {r['cola_media_s']} s, "
                f"{r['coste_usd']:.4f} USD, errores {len(r['errores'])}, cambios de enrutado {len(cambios_enrutado)}"
            )
    resultado["coste_usd_total"] = round(sum(v["coste_usd"] for v in resultado["por_nivel"].values()), 6)
    return resultado


# --- Informe -------------------------------------------------------------------


def _informe(res: dict) -> str:
    lineas = [f"# Prueba de carga y concurrencia — {res['fecha']}", ""]
    if "remoto" in res:
        lineas += ["## Frente HTTP en Render (sin consultas, coste cero)", ""]
        lineas += ["| Servicio | A la vez | Peticiones | p50 (s) | p95 (s) | max (s) | Errores |", "|---|---|---|---|---|---|---|"]
        for nombre, s in res["remoto"]["servicios"].items():
            for n, v in s["por_nivel"].items():
                lineas.append(f"| {nombre} | {n} | {v['peticiones']} | {v.get('p50_s')} | {v.get('p95_s')} | {v.get('max_s')} | {v['errores']} |")
        lineas.append("")
    for clave in ("local", "agencia"):
        if clave not in res:
            continue
        r = res[clave]
        lineas += [f"## Pipeline compartido entre hilos — `{r['tenant']}` ({len(r['consultas'])} consultas por nivel)", ""]
        lineas += [
            "| Concurrencia | Lote (s) | Consultas/min | Pared p50 (s) | Pared p95 (s) | Pared max (s) | Coste (USD) | Errores | Cambios de enrutado | Confidencial denegada |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for n, v in r["por_nivel"].items():
            lineas.append(
                f"| {n} | {v['pared_lote_s']} | {v['consultas_por_minuto']} | {v['pared_por_consulta'].get('p50_s')} | "
                f"{v['pared_por_consulta'].get('p95_s')} | {v['pared_por_consulta'].get('max_s')} | "
                f"{v['coste_usd']:.4f} | {len(v['errores'])} | {len(v['cambios_enrutado_frente_a_secuencial'])} | {v['confidencial_denegada']} |"
            )
        lineas += ["", f"Coste total del bloque: {r['coste_usd_total']:.4f} USD.", ""]
    return "\n".join(lineas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remoto", action="store_true", help="frente HTTP de los dos servicios de Render")
    ap.add_argument("--local", action="store_true", help="pipeline del inquilino heredado bajo concurrencia (cuesta ~0,08 USD)")
    ap.add_argument("--agencia", action="store_true", help="rama estructurada de la agencia por MCP a 1 y 4 (cuesta ~0,03 USD)")
    ap.add_argument("--etiqueta", default="prueba_carga", help="carpeta bajo reports/")
    args = ap.parse_args()
    if not (args.remoto or args.local or args.agencia):
        ap.error("indica al menos --remoto, --local o --agencia")

    res: dict = {"fecha": datetime.now(tz=UTC).date().isoformat(), "que_mide": __doc__.split("\n\n")[1].strip()}
    if args.remoto:
        res["remoto"] = medir_remoto()
    if args.local:
        res["local"] = medir_local("empresa_servicios", CONSULTAS_HEREDADO, NIVELES_LOCAL)
    if args.agencia:
        res["agencia"] = medir_local("agencia_inmobiliaria", CONSULTAS_AGENCIA, NIVELES_AGENCIA)
    res["coste_usd_total"] = round(sum(res[k].get("coste_usd_total", 0.0) for k in ("local", "agencia") if k in res), 6)

    destino = RAIZ / "reports" / args.etiqueta
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (destino / "informe.md").write_text(_informe(res), encoding="utf-8")
    print(f"\n[OK] Evidencia en {destino.relative_to(RAIZ)} (coste total {res['coste_usd_total']:.4f} USD)")


if __name__ == "__main__":
    main()
