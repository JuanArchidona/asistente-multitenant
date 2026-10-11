"""Banco de conversaciones de dos turnos: el defecto de la memoria y su arreglo.

    uv run python -m evals.conversaciones --etiqueta memoria_2026-10-11

Cada conversación (`evals/datasets/conversaciones.jsonl`) tiene un primer
turno, que es una pregunta del banco, y un seguimiento elíptico ("¿y la
baja?") cuya respuesta correcta es otro caso del banco (`origen`): de ahí
salen su categoría, sus documentos y su literal esperados, ya verificados.
Para el seguimiento se miden tres brazos sobre el mismo sistema:

- `sin_memoria`: el seguimiento solo, como lo recibe hoy producción.
- `reescritura`: el seguimiento reescrito con el turno anterior delante
  (`src/memoria.py`, `MEMORIA_TURNOS=reescritura`).
- `techo`: la pregunta autónoma original del banco. Es lo máximo a lo que
  puede llegar cualquier memoria, y separa los fallos de memoria de los que
  el sistema ya tenía con la pregunta completa.

Tres medidas deterministas por brazo: enrutado a la categoría esperada,
recuperación del documento esperado y presencia del literal esperado en la
respuesta. Banco aparte del de 122 casos, que no cambia.
"""
import argparse
import json
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from src.agent import Sistema
from src.config import load_config

from .dataset import cargar_consultas, ruta_golden
from .metrics.deterministas import evaluar_contiene, evaluar_retrieval

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / "evals" / "datasets" / "conversaciones.jsonl"
BRAZOS = ("sin_memoria", "reescritura", "techo")


def _medidas(caso, traza: dict) -> dict:
    esperado = SimpleNamespace(
        archivos_esperados=caso.archivos_esperados, debe_contener=caso.debe_contener
    )
    hit = next(r for r in evaluar_retrieval(esperado, traza) if r.metrica == "hit_rate")
    contiene = evaluar_contiene(esperado, traza)
    return {
        "categoria": traza.get("categoria"),
        "enrutado": traza.get("categoria") == caso.categoria_esperada,
        "recupera": bool(hit.valor),
        "contiene": bool(contiene.exito),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--etiqueta", required=True)
    args = p.parse_args()

    conversaciones = [json.loads(linea) for linea in DATASET.read_text(encoding="utf-8").splitlines() if linea.strip()]
    t0 = time.perf_counter()
    filas, uso_total = [], {"coste_usd_estimado": 0.0, "llamadas": 0}
    por_tenant: dict[str, list[dict]] = {}
    for conv in conversaciones:
        por_tenant.setdefault(conv["tenant"], []).append(conv)

    for tenant, convs in por_tenant.items():
        cfg = load_config(tenant, con_juez=False)
        golden = {c.id: c for c in cargar_consultas(ruta_golden(tenant, "golden_consultas.jsonl"))}
        base = Sistema(cfg)
        con_memoria = Sistema(replace(cfg, memoria_turnos="reescritura"), chat=base.chat)
        con_memoria._retriever = base.retriever
        with base.chat.uso.por_consulta() as uso:
            for conv in convs:
                caso = golden[conv["origen"]]
                t1 = base.responder(conv["turno_1"])
                historial = [(conv["turno_1"], t1["respuesta"])]
                trazas = {
                    "sin_memoria": base.responder(conv["turno_2"]),
                    "reescritura": con_memoria.responder(conv["turno_2"], historial=historial),
                    "techo": base.responder(caso.consulta),
                }
                fila = {
                    "id": conv["id"], "tenant": tenant, "origen": conv["origen"],
                    "turno_2": conv["turno_2"], "categoria_esperada": caso.categoria_esperada,
                    "reescrita": trazas["reescritura"].get("consulta_reescrita"),
                    "latencia_reescritura_s": trazas["reescritura"].get("latencia_reescritura_s"),
                    "latencia_total_s": {
                        b: round(sum(t.get(k) or 0.0 for k in (
                            "latencia_reescritura_s", "latencia_router_s", "latencia_retrieve_s",
                            "latencia_generacion_s")), 3)
                        for b, t in trazas.items()
                    },
                }
                for brazo, traza in trazas.items():
                    fila[brazo] = _medidas(caso, traza)
                filas.append(fila)
        resumen_uso = uso.resumen()
        uso_total["coste_usd_estimado"] += resumen_uso.get("coste_usd_estimado") or 0.0
        uso_total["llamadas"] += resumen_uso.get("llamadas") or 0
        base.cerrar()

    n = len(filas)
    agregado = {
        brazo: {m: sum(f[brazo][m] for f in filas) for m in ("enrutado", "recupera", "contiene")}
        for brazo in BRAZOS
    }
    resumen = {
        "etiqueta": args.etiqueta,
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "conversaciones": n,
        "aciertos_sobre_n": agregado,
        "latencia_reescritura_media_s": round(
            sum(f["latencia_reescritura_s"] or 0.0 for f in filas) / max(1, n), 3),
        "latencia_total_media_s": {
            b: round(sum(f["latencia_total_s"][b] for f in filas) / max(1, n), 3) for b in BRAZOS
        },
        "duracion_s": round(time.perf_counter() - t0, 1),
        "uso": {k: round(v, 6) if isinstance(v, float) else v for k, v in uso_total.items()},
        "modelo_reescritura": "el del enrutador, a temperatura 0",
    }
    salida = RAIZ / "reports" / args.etiqueta
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "conversaciones.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    for f in filas:
        marcas = {
            b: "".join("x" if f[b][m] else "." for m in ("enrutado", "recupera", "contiene")) for b in BRAZOS
        }
        print(f"{f['id']:12} sin {marcas['sin_memoria']} re {marcas['reescritura']} techo {marcas['techo']}  "
              f"{f['turno_2']!r} -> {f['reescrita']!r}")


if __name__ == "__main__":
    main()
