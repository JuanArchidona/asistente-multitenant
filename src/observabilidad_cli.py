"""Lee el registro de producción y responde las preguntas de explotación.

    uv run python -m src.observabilidad_cli
    uv run python -m src.observabilidad_cli --tenant agencia_inmobiliaria --ultimas 10
    uv run python -m src.observabilidad_cli --json

Las preguntas que tiene que poder responder, que son las del feedback de la 3.1
y las del bloque 2 de `docs/ALCANCE.md`: cuánto llevo gastado por cliente, qué
se está preguntando, cuánto se tarda, cuántas veces ha actuado el control de
acceso y cuántas consultas salieron degradadas.
"""
import argparse
import json

from .observabilidad import RAIZ_POR_DEFECTO, inquilinos, leer, resumir


def _fila(etiqueta: str, valor) -> str:
    return f"  {etiqueta:38} {valor}"


def _informe(tenant: str, resumen: dict, ultimas: list[dict]) -> str:
    out = [f"\n=== {tenant} ==="]
    if not resumen["consultas"]:
        out.append("  Sin consultas registradas.")
        if resumen.get("_lineas_ilegibles"):
            out.append(_fila("Lineas ilegibles", resumen["_lineas_ilegibles"]))
        return "\n".join(out)

    out += [
        _fila("Consultas", resumen["consultas"]),
        _fila("Periodo", f"{resumen['desde']}  ->  {resumen['hasta']}"),
        _fila("Usuarios distintos", resumen["usuarios_distintos"]),
        "",
        _fila("Coste acumulado", f"{resumen['coste_usd_acumulado']:.6f} USD"),
        _fila("Coste por consulta", f"{resumen['coste_usd_por_consulta']:.6f} USD"),
        _fila("Tokens", f"{resumen['tokens_entrada']:,} entrada / {resumen['tokens_salida']:,} salida"),
        "",
        _fila("Latencia media", f"{resumen['latencia_media_s']} s"),
        _fila("Latencia p95", f"{resumen['latencia_p95_s']} s"),
        "",
        # Etiquetas literales a proposito: "el control actuo" se leia como
        # "alguien intento colarse", y casi nunca es eso. Ver HALLAZGOS §20.
        _fila("Consultas SIN ACCESO a lo que pedian", resumen["sin_acceso_a_lo_pedido"]),
        _fila("Consultas con campos redactados", resumen["redaccion_aplicada"]),
        _fila(
            "Consultas donde el filtro retuvo algun doc",
            f"{resumen['filtro_retuvo_documentos']}  (ruidoso: casi constante por fuente)",
        ),
        _fila(
            "Consultas degradadas",
            f"{resumen['consultas_degradadas']} ({resumen['tasa_degradadas']:.1%})",
        ),
        _fila("Fallback del enrutador", resumen["fallback_enrutador"]),
        "",
        _fila("Por rama", json.dumps(resumen["por_rama"], ensure_ascii=False)),
        _fila("Por categoria", json.dumps(resumen["por_categoria"], ensure_ascii=False)),
    ]
    if resumen.get("_lineas_ilegibles"):
        out.append(
            _fila("[!] Lineas ilegibles (log incompleto)", resumen["_lineas_ilegibles"])
        )

    if ultimas:
        out += ["", f"  Ultimas {len(ultimas)} consultas:"]
        for r in ultimas:
            marcas = []
            if r.get("error"):
                marcas.append("ERROR")
            if r.get("contexto_vacio"):
                marcas.append("sin contexto")
            if r.get("sin_acceso_a_lo_pedido"):
                marcas.append("SIN ACCESO")
            if r.get("redaccion_aplicada"):
                marcas.append("redactado")
            sufijo = f"  [{', '.join(marcas)}]" if marcas else ""
            consulta = (r.get("consulta") or "")[:70]
            out.append(
                f"    {r.get('ts', '?')[:19]}  {str(r.get('categoria'))[:12]:12} "
                f"{r.get('latencia_total_s', 0):5.1f}s  {consulta}{sufijo}"
            )
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="Observabilidad del asistente en produccion")
    p.add_argument("--tenant", help="Un inquilino concreto. Por defecto, todos.")
    p.add_argument("--raiz", default=str(RAIZ_POR_DEFECTO))
    p.add_argument("--ultimas", type=int, default=5, help="Cuantas consultas recientes listar")
    p.add_argument("--json", action="store_true", help="Volcar el resumen en JSON")
    args = p.parse_args()

    tenants = [args.tenant] if args.tenant else inquilinos(args.raiz)
    if not tenants:
        print(
            f"No hay registros en {args.raiz}/.\n"
            "El registro es opt-in: lo activa el punto de entrada de produccion "
            "(`src.main`), no el banco de pruebas."
        )
        return

    salida = {}
    for t in tenants:
        registros = leer(t, args.raiz)
        resumen = resumir(registros)
        salida[t] = resumen
        if not args.json:
            filas = [r for r in registros if "_ilegible" not in r]
            print(_informe(t, resumen, filas[-args.ultimas:] if args.ultimas else []))

    if args.json:
        print(json.dumps(salida, ensure_ascii=False, indent=2))
    elif len(tenants) > 1:
        total = sum(s["coste_usd_acumulado"] for s in salida.values() if s["consultas"])
        n = sum(s["consultas"] for s in salida.values())
        print(f"\n=== TOTAL ===\n{_fila('Consultas', n)}\n{_fila('Coste acumulado', f'{total:.6f} USD')}")


if __name__ == "__main__":
    main()
