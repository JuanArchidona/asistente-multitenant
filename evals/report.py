"""Generación de informes en markdown.

El JSON con los resultados es la fuente de verdad; este módulo produce la
lectura humana. La estructura del informe sigue el orden en que conviene
diagnosticar un fallo: primero si el caso pasó entero, luego por métrica (¿qué
capa se rompió?), luego por dimensión (¿qué tipo de consulta se rompió?) y solo
al final el detalle caso a caso.
"""
ORDEN_METRICAS = [
    "routing", "hit_rate", "recall_at_k", "precision_at_k", "mrr",
    "contiene", "fuga_literal",
    "faithfulness", "answer_relevancy", "correctness",
    "abstencion", "confidencialidad", "pii_leakage",
]

ETIQUETAS = {
    "routing": "Acierto del enrutador",
    "hit_rate": "Hit rate (recuperación)",
    "recall_at_k": "Recall@k",
    "precision_at_k": "Precision@k",
    "mrr": "MRR",
    "contiene": "Dato exigido presente",
    "fuga_literal": "Sin fuga literal",
    "faithfulness": "Fidelidad al contexto",
    "answer_relevancy": "Relevancia de la respuesta",
    "correctness": "Corrección (G-Eval)",
    "abstencion": "Abstención correcta",
    "confidencialidad": "Confidencialidad",
    "pii_leakage": "PII Leakage (DeepEval)",
}


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{x:.0%}"


def _num(x: float | None) -> str:
    return "-" if x is None else f"{x:.3f}"


def _tabla(cabeceras: list[str], filas: list[list[str]]) -> str:
    lineas = ["| " + " | ".join(cabeceras) + " |",
              "|" + "|".join("---" for _ in cabeceras) + "|"]
    lineas += ["| " + " | ".join(f) + " |" for f in filas]
    return "\n".join(lineas)


def _orden(nombre: str) -> int:
    return ORDEN_METRICAS.index(nombre) if nombre in ORDEN_METRICAS else 99


def informe_consultas(resumen: dict, registros: list[dict]) -> str:
    meta = resumen.get("meta", {})
    cfg = meta.get("configuracion", {})
    uso = meta.get("uso_sistema") or {}

    out = [f"# Informe de evaluación — {meta.get('etiqueta', 'sin etiqueta')}", ""]
    out += [
        f"- Fecha: {meta.get('fecha', '-')}",
        f"- Dataset: `{meta.get('dataset', '-')}`",
        f"- Duración: {meta.get('duracion_s', '-')} s",
        f"- Métricas de juez: {'sí' if meta.get('con_juez') else 'no (solo deterministas)'}",
        "",
        "## Configuración evaluada",
        "",
        _tabla(["Parámetro", "Valor"], [[k, f"`{v}`"] for k, v in cfg.items()]),
        "",
        "## Resultado global",
        "",
    ]

    globales = [
        ["Casos ejecutados", str(resumen["casos"])],
        ["Casos que pasan todas sus métricas", f"{resumen['casos_ok']} ({_pct(resumen['tasa_casos_ok'])})"],
        ["Fallback silencioso del enrutador", f"{resumen['fallback_enrutador']} ({_pct(resumen['tasa_fallback'])})"],
        ["Latencia media por consulta", f"{resumen['latencia_media_s']} s"],
        ["Latencia p95", f"{resumen['latencia_p95_s']} s"],
    ]
    if uso:
        globales += [
            ["Llamadas al LLM del sistema", str(uso.get("llamadas", "-"))],
            ["Coste estimado de la ejecución", f"{uso.get('coste_usd_estimado', 0):.4f} USD"],
            [
                "Coste estimado por consulta",
                f"{uso.get('coste_usd_estimado', 0) / max(1, resumen['casos']):.5f} USD",
            ],
        ]
    out += [_tabla(["Indicador", "Valor"], globales), "", "## Por métrica", ""]

    filas = []
    for nombre, datos in sorted(resumen["por_metrica"].items(), key=lambda kv: _orden(kv[0])):
        filas.append([
            ETIQUETAS.get(nombre, nombre),
            f"`{nombre}`",
            str(datos["n"]),
            _num(datos["media"]),
            _pct(datos["tasa_exito"]),
        ])
    out += [_tabla(["Métrica", "Clave", "Casos", "Media", "% supera umbral"], filas), ""]

    out += ["## Por dimensión del banco", ""]
    filas = []
    for dim, datos in resumen["por_dimension"].items():
        clave = _resumen_dimension(dim, datos)
        filas.append([
            dim,
            str(datos["casos"]),
            f"{datos['ok']} ({_pct(datos['tasa_ok'])})",
            clave,
        ])
    out += [_tabla(["Dimensión", "Casos", "Casos OK", "Métrica crítica"], filas), ""]

    confusion = resumen.get("confusion_enrutador") or {}
    if confusion:
        categorias = sorted({c for fila in confusion.values() for c in fila} | set(confusion))
        filas = []
        for esperada in categorias:
            fila = [f"**{esperada}**"]
            for obtenida in categorias:
                n = confusion.get(esperada, {}).get(obtenida, 0)
                fila.append(str(n) if n else ".")
            filas.append(fila)
        out += [
            "## Matriz de confusión del enrutador",
            "",
            "Filas: categoría esperada. Columnas: categoría elegida.",
            "",
            _tabla(["esperada \\ obtenida"] + categorias, filas),
            "",
        ]

    errores = resumen.get("errores_metrica", [])
    if errores:
        out += [
            f"## Métricas que no llegaron a puntuar ({len(errores)})",
            "",
            ("Una métrica caída no es un fallo del sistema evaluado, pero sí invalida"
             " el caso: se reporta aparte para no confundir una cosa con la otra."),
            "",
            _tabla(
                ["Caso", "Métrica", "Motivo"],
                [[e["id"], f"`{e['metrica']}`", e["razon"].replace("\n", " ")[:160]]
                 for e in errores],
            ),
            "",
        ]

    fallos = resumen.get("fallos", [])
    out += [f"## Fallos ({len(fallos)})", ""]
    if not fallos:
        out += ["Ninguna métrica por debajo de su umbral.", ""]
    else:
        filas = [
            [f["id"], f["dimension"], f"`{f['metrica']}`", _num(f["valor"]),
             f["razon"].replace("\n", " ")[:180]]
            for f in fallos
        ]
        out += [_tabla(["Caso", "Dimensión", "Métrica", "Valor", "Motivo"], filas), ""]

    out += ["## Detalle por caso", ""]
    for reg in registros:
        estado = "OK" if reg["ok"] else "FALLA"
        out += [
            f"### [{estado}] `{reg['id']}` — {reg['dimension']}",
            "",
            f"**Consulta:** {reg['consulta']}",
            "",
            f"**Esperado ({reg['comportamiento_esperado']}):** {reg['respuesta_esperada']}",
            "",
            f"**Respuesta del sistema:** {reg['traza'].get('respuesta', '')[:900]}",
            "",
        ]
        filas = [
            [f"`{m['metrica']}`", _num(m["valor"]), "sí" if m["exito"] else "**NO**",
             (m["razon"] or "").replace("\n", " ")[:200]]
            for m in sorted(reg["metricas"], key=lambda m: _orden(m["metrica"]))
        ]
        out += [_tabla(["Métrica", "Valor", "Pasa", "Motivo"], filas), ""]

    return "\n".join(out) + "\n"


METRICA_CRITICA = {
    "confidencialidad": "confidencialidad",
    "inyeccion": "confidencialidad",
    "fuera_de_alcance": "abstencion",
    "fuera_de_dominio": "abstencion",
    "agregacion": "recall_at_k",
    "frontera": "routing",
    "robustez": "routing",
    "conocimiento": "contiene",
}


def _resumen_dimension(dim: str, datos: dict) -> str:
    """La métrica que define si esa dimensión funciona.

    Cada tipo de caso se juega la vida en una métrica distinta: los de
    confidencialidad en no filtrar, los de fuera de alcance en abstenerse, los
    de frontera en enrutar. Mirar la media global de todas las métricas mezcla
    cosas que no se comparan.
    """
    clave = METRICA_CRITICA.get(dim)
    if clave and clave in datos["metricas"]:
        m = datos["metricas"][clave]
        return f"`{clave}` = {_num(m['media'])} ({_pct(m['tasa_exito'])} pasan)"
    return "-"


def informe_transcripcion(resumen: dict, registros: list[dict]) -> str:
    meta = resumen.get("meta", {})
    out = [
        "# Informe de evaluación — agente transcriptor (flujo 2.1)",
        "",
        f"- Fecha: {meta.get('fecha', '-')}",
        f"- Dataset: `{meta.get('dataset', '-')}`",
        f"- Modelo: `{meta.get('modelo', '-')}`",
        "",
        "## Resultado global",
        "",
        _tabla(
            ["Indicador", "Valor"],
            [["Casos", str(resumen["casos"])],
             ["Casos OK", f"{resumen['casos_ok']} ({resumen['casos_ok'] / max(1, resumen['casos']):.0%})"]]
            + [[k, _num(v)] for k, v in resumen.get("medias", {}).items()],
        ),
        "",
        "## Detalle por caso",
        "",
    ]
    for reg in registros:
        estado = "OK" if reg["ok"] else "FALLA"
        out += [f"### [{estado}] `{reg['id']}`", ""]
        if reg.get("nota"):
            out += [f"_{reg['nota']}_", ""]
        filas = [[k, _num(v)] for k, v in reg["metricas"].items()]
        out += [_tabla(["Métrica", "Valor"], filas), ""]
        if reg.get("fugas"):
            out += [f"**Fuga detectada:** {reg['fugas']}", ""]
        acta = reg.get("acta") or {}
        out += [
            f"- Título: {acta.get('titulo', '-')} (esperado: {reg['esperado']['titulo']})",
            f"- Fecha: {acta.get('fecha')} (esperada: {reg['esperado']['fecha']})",
            f"- Asistentes: {acta.get('asistentes', [])}",
            f"- Decisiones: {acta.get('decisiones', [])}",
            f"- Tareas: {acta.get('tareas', [])}",
            "",
        ]
    return "\n".join(out) + "\n"
