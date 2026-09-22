"""Mide la estabilidad del enrutador: cuantas veces repite sobre la misma consulta.

Motivo. El §15 midio un 11 % de casos que cambian de categoria entre pasadas
identicas en el inquilino A y el §22 un 13,2 % en el C. Las dos cifras salieron
de pasadas completas del banco, que ademas llaman al generador y cuestan. Aqui
se aisla el enrutador: **solo se le llama a el**, varias veces por consulta, con
la misma configuracion. Es la unica forma de separar "el enrutador no repite" de
"algo mas abajo cambio".

Y sirve para responder una pregunta que decide una linea de trabajo entera: si
la varianza se va fijando la temperatura, la votacion por autoconsistencia —tres
llamadas y mayoria— no hace falta. Una cuesta un parametro; la otra, el triple
de llamadas al enrutador para siempre.

No usa el banco ni las metricas: solo el golden set, para tener las consultas y
la categoria esperada. No escribe en `reports/` porque no es una evaluacion del
sistema, es una caracterizacion de un componente.

    uv run python -m evals.estabilidad_router --muestras 5
    TENANT_ID=agencia_inmobiliaria uv run python -m evals.estabilidad_router
"""
import argparse
import collections
import json
import sys
from pathlib import Path

from src.config import load_config
from src.provider import get_chat
from src.router import enrutar

from .dataset import cargar_consultas

RAIZ = Path(__file__).resolve().parents[1]


def _muestrear(cfg, chat, consultas, muestras: int) -> dict[str, list[str]]:
    """Enruta cada consulta `muestras` veces. Devuelve las categorias por caso."""
    salida: dict[str, list[str]] = {}
    total = len(consultas) * muestras
    hecho = 0
    for caso in consultas:
        categorias = []
        for _ in range(muestras):
            categorias.append(enrutar(cfg, chat, caso.consulta).categoria)
            hecho += 1
            print(f"\r[router] {hecho}/{total} llamadas", end="", file=sys.stderr)
        salida[caso.id] = categorias
    print(file=sys.stderr)
    return salida


def _resumir(por_caso: dict[str, list[str]], esperadas: dict[str, str]) -> dict:
    """Estabilidad y acierto, y el acierto de la mayoria frente al de una muestra.

    `acierto_muestra_unica` es el valor esperado de una pasada cualquiera: la
    proporcion de muestras correctas sobre el total. Es la cifra con la que hay
    que comparar la mayoria, y no el acierto de una pasada concreta, que a su
    vez varia.
    """
    inestables = []
    aciertos_muestra = 0
    total_muestras = 0
    aciertos_mayoria = 0
    empates = []
    for caso, categorias in por_caso.items():
        cuenta = collections.Counter(categorias)
        if len(cuenta) > 1:
            inestables.append({"id": caso, "reparto": dict(cuenta)})
        total_muestras += len(categorias)
        aciertos_muestra += sum(1 for c in categorias if c == esperadas[caso])
        # Mayoria simple. Un empate no se resuelve a favor de nadie: se anota,
        # porque es justo el caso en el que la votacion tendria que abstenerse y
        # consultar las categorias empatadas en vez de elegir.
        mas = cuenta.most_common()
        if len(mas) > 1 and mas[0][1] == mas[1][1]:
            empates.append({"id": caso, "reparto": dict(cuenta)})
        elif mas[0][0] == esperadas[caso]:
            aciertos_mayoria += 1
    n = len(por_caso)
    return {
        "casos": n,
        "muestras_por_caso": total_muestras // n if n else 0,
        "casos_inestables": len(inestables),
        "tasa_inestabilidad": round(len(inestables) / n, 4) if n else None,
        "acierto_muestra_unica": round(aciertos_muestra / total_muestras, 4)
        if total_muestras
        else None,
        "acierto_mayoria": round(aciertos_mayoria / n, 4) if n else None,
        "empates": empates,
        "inestables": inestables,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--muestras", type=int, default=5)
    p.add_argument(
        "--temperaturas",
        default="defecto,0",
        help="Lista separada por comas. 'defecto' = no enviar el parametro.",
    )
    p.add_argument("--salida", default=None, help="Fichero JSON con el detalle.")
    args = p.parse_args()

    base = load_config()
    consultas = cargar_consultas(
        RAIZ / "evals" / "datasets" / base.tenant.id / "golden_consultas.jsonl"
    )
    esperadas = {c.id: c.categoria_esperada for c in consultas}

    brazos = [t.strip() for t in args.temperaturas.split(",") if t.strip()]
    print(
        f"[router] inquilino {base.tenant.id}, {len(consultas)} consultas, "
        f"{args.muestras} muestras, brazos {brazos}"
    )
    print(
        f"[!] AVISO DE COSTE: {len(consultas) * args.muestras * len(brazos)} "
        f"llamadas al enrutador ({base.model_router})."
    )

    chat = get_chat(base)
    resultados = {}
    for brazo in brazos:
        temp = None if brazo == "defecto" else float(brazo)
        from dataclasses import replace

        cfg = replace(base, router_temperature=temp)
        por_caso = _muestrear(cfg, chat, consultas, args.muestras)
        resultados[brazo] = {"resumen": _resumir(por_caso, esperadas), "por_caso": por_caso}

    print()
    print(f"{'brazo':>10} {'inestables':>12} {'tasa':>8} {'acierto 1 muestra':>19} {'mayoria':>9}")
    for brazo, d in resultados.items():
        r = d["resumen"]
        print(
            f"{brazo:>10} {r['casos_inestables']:>5}/{r['casos']:<6} "
            f"{r['tasa_inestabilidad']:>8} {r['acierto_muestra_unica']:>19} "
            f"{r['acierto_mayoria']:>9}"
        )

    print()
    print("Coste de esta medicion:", json.dumps(chat.uso.resumen(), ensure_ascii=False))

    if args.salida:
        Path(args.salida).write_text(
            json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("Detalle en", args.salida)


if __name__ == "__main__":
    main()
