"""Servidor MCP sobre el CRM de la agencia inmobiliaria.

Es la **rama estructurada** del sistema: la mitad del concepto original que
nunca se había construido. Las consultas documentales van al RAG; las que
preguntan por el estado de la cartera, la agenda o una operación concreta se
responden contra datos de negocio, no contra documentos.

## Por qué MCP y no tool-calling suelto

Un `tools=[...]` cableado en el agente ata el sistema a las herramientas de un
cliente. Un servidor MCP convierte esas herramientas en un **contrato**: dar de
alta un cliente nuevo con otro sistema de negocio es escribir otro servidor y
declararlo en su manifiesto, sin tocar el agente. Es lo que hace que la
agnosticidad sea una propiedad del diseño y no una afirmación de la memoria.

## Superficie de fuga, a propósito

`estado_operacion` devuelve DNI, teléfono, correo e ingresos de la parte
compradora. No es un descuido: es el hallazgo que ya se midió con el conector de
idealista, donde los datos personales llegaban en el resultado de la herramienta
y no en el corpus. La capa de gobernanza tiene que envolver **las dos ramas de
recuperación**, y para demostrarlo hace falta que esta rama tenga algo que
filtrar.

Uso como proceso independiente:
    uv run python -m mcp_servers.agencia_crm
"""
import json
import os
import statistics
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

RAIZ = Path(__file__).resolve().parents[1]
CRM_POR_DEFECTO = RAIZ / "datos" / "agencia_inmobiliaria" / "crm.json"

servidor = MCPServer(
    name="agencia-crm",
    instructions=(
        "Datos de negocio de una agencia inmobiliaria: cartera de inmuebles, "
        "agenda de visitas y operaciones en curso. Usa estas herramientas para "
        "cualquier pregunta sobre el estado real de la cartera o de una "
        "operación concreta; la documentación interna vive en otra fuente."
    ),
)


def _cargar() -> dict[str, Any]:
    """Lee el CRM en cada llamada.

    Es un fichero pequeño y releerlo evita servir datos obsoletos si se
    regenera. En un cliente real este sería el punto de conexión al CRM.
    """
    ruta = Path(os.getenv("CRM_PATH", CRM_POR_DEFECTO))
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No se encuentra el CRM en {ruta}. "
            "Genéralo con: uv run python scripts/generar_crm_agencia.py"
        )
    return json.loads(ruta.read_text(encoding="utf-8"))


@servidor.tool()
def buscar_inmuebles(
    zona: str | None = None,
    operacion: str | None = None,
    precio_max_eur: int | None = None,
    habitaciones_min: int | None = None,
    dias_publicado_min: int | None = None,
    solo_sin_ofertas: bool = False,
    limite: int = 10,
) -> dict[str, Any]:
    """Busca inmuebles en la cartera de la agencia.

    Filtra por zona, tipo de operación ('venta' o 'alquiler'), precio máximo,
    habitaciones mínimas, días publicado y ausencia de ofertas. Devuelve el
    total de coincidencias y los primeros resultados.
    """
    datos = _cargar()
    resultado = datos["inmuebles"]

    if zona:
        resultado = [i for i in resultado if zona.lower() in i["zona"].lower()]
    if operacion:
        resultado = [i for i in resultado if i["operacion"] == operacion.lower()]
    if precio_max_eur is not None:
        resultado = [i for i in resultado if i["precio_eur"] <= precio_max_eur]
    if habitaciones_min is not None:
        resultado = [i for i in resultado if i["habitaciones"] >= habitaciones_min]
    if dias_publicado_min is not None:
        resultado = [i for i in resultado if i["dias_publicado"] >= dias_publicado_min]
    if solo_sin_ofertas:
        resultado = [i for i in resultado if i["ofertas_recibidas"] == 0]

    resultado.sort(key=lambda i: i["dias_publicado"], reverse=True)
    return {
        "total": len(resultado),
        "mostrados": min(limite, len(resultado)),
        "inmuebles": resultado[:limite],
    }


@servidor.tool()
def detalle_inmueble(referencia: str) -> dict[str, Any]:
    """Devuelve la ficha completa de un inmueble por su referencia (INM-2026-XXX)."""
    datos = _cargar()
    for inmueble in datos["inmuebles"]:
        if inmueble["referencia"].lower() == referencia.lower().strip():
            return inmueble
    return {"error": f"No existe el inmueble {referencia!r} en la cartera."}


@servidor.tool()
def estadisticas_cartera(
    zona: str | None = None, operacion: str = "venta"
) -> dict[str, Any]:
    """Resume la cartera: número de inmuebles, precio por metro cuadrado y antigüedad.

    Útil para preguntas de mercado propio del tipo "a cuánto tenemos el metro en
    una zona" o "cuántos inmuebles llevan mucho tiempo publicados".
    """
    datos = _cargar()
    seleccion = [i for i in datos["inmuebles"] if i["operacion"] == operacion.lower()]
    if zona:
        seleccion = [i for i in seleccion if zona.lower() in i["zona"].lower()]
    if not seleccion:
        return {"error": "Ningún inmueble de la cartera cumple ese filtro.", "inmuebles": 0}

    precios_m2 = [i["precio_m2_eur"] for i in seleccion]
    dias = [i["dias_publicado"] for i in seleccion]
    return {
        "zona": zona or "todas",
        "operacion": operacion.lower(),
        "inmuebles": len(seleccion),
        "precio_m2_medio_eur": round(statistics.mean(precios_m2), 1),
        "precio_m2_mediana_eur": round(statistics.median(precios_m2), 1),
        "precio_m2_min_eur": min(precios_m2),
        "precio_m2_max_eur": max(precios_m2),
        "dias_publicado_medio": round(statistics.mean(dias), 1),
        "con_mas_de_90_dias_sin_ofertas": sum(
            1 for i in seleccion if i["dias_publicado"] > 90 and i["ofertas_recibidas"] == 0
        ),
        "en_exclusiva": sum(1 for i in seleccion if i["exclusiva"]),
    }


@servidor.tool()
def agenda_comercial(
    comercial: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict[str, Any]:
    """Consulta la agenda de visitas.

    Filtra por comercial y por rango de fechas en formato AAAA-MM-DD. Sin
    filtros devuelve la agenda completa registrada.
    """
    datos = _cargar()
    visitas = datos["visitas"]
    if comercial:
        visitas = [v for v in visitas if comercial.lower() in v["comercial"].lower()]
    if desde:
        visitas = [v for v in visitas if v["fecha"] >= desde]
    if hasta:
        visitas = [v for v in visitas if v["fecha"] <= hasta]
    return {"total": len(visitas), "visitas": visitas}


@servidor.tool()
def estado_operacion(referencia: str) -> dict[str, Any]:
    """Estado de una operación en curso por su referencia (OP-2026-XXX).

    AVISO: la respuesta incluye datos personales de las partes. Quien la consuma
    es responsable de no reproducirlos en una respuesta al usuario.
    """
    datos = _cargar()
    for operacion in datos["operaciones"]:
        if operacion["referencia"].lower() == referencia.lower().strip():
            return operacion
    return {"error": f"No existe la operación {referencia!r}."}


def main() -> None:
    servidor.run()


if __name__ == "__main__":
    main()
