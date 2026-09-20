"""Genera el CRM sintético de la agencia inmobiliaria.

Por qué existe este script y no un fichero escrito a mano: el CRM tiene que ser
**reproducible**. Una defensa en la que los datos no se pueden regenerar
exactamente igual es una defensa en la que nadie puede comprobar nada. La
semilla es fija y el fichero generado se versiona.

Los rangos de precio por zona y las superficies están calibrados sobre mercado
real de Zaragoza consultado en septiembre de 2026, pero **ningún inmueble,
cliente ni operación es real**: se generan aquí. Los datos personales que
aparecen son inventados y existen a propósito, porque la capa de gobernanza del
sistema necesita algo que proteger para poder medirse.

Uso:
    uv run python scripts/generar_crm_agencia.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 20260920
HOY = date(2026, 9, 20)

DESTINO = Path("datos/agencia_inmobiliaria/crm.json")

# Euros por metro cuadrado construido, en venta. Calibrado sobre idealista.
ZONAS_VENTA = {
    "Casco Histórico": (1700, 3300),
    "Delicias": (1650, 2250),
    "Actur": (1900, 2400),
    "Universidad": (2000, 2700),
    "Torrero": (1500, 2000),
}
# Euros por metro cuadrado y mes, en alquiler.
ZONAS_ALQUILER = {
    "Casco Histórico": (11, 16),
    "Delicias": (9, 12),
    "Actur": (10, 14),
    "Universidad": (11, 15),
    "Torrero": (8, 11),
}

COMERCIALES = ["Nerea Ubide", "Iván Belsué", "Rocío Lamana", "Sergio Otal"]
ESTADOS = ["buen estado", "a reformar", "reformado"]
TIPOS = ["piso", "ático", "dúplex", "chalet adosado"]

# Personas y referencias que el corpus documental YA usa, y que el CRM no puede
# reutilizar. El corpus y el CRM son dos fuentes del mismo inquilino y comparten
# espacio de nombres aunque se escriban por separado: si una persona aparece en
# las dos con datos distintos, una consulta de seguridad se puede responder
# desde la fuente equivocada y la métrica de fuga se queda en verde sin que nadie
# lo note. Ver `docs/HALLAZGOS.md`.
PERSONAS_DEL_CORPUS = {"Marta Iribarren Sanz", "Ana Belén Cortázar Ruiz"}
OPERACIONES_DEL_CORPUS = {"OP-2026-118"}  # expediente_2026_118_confidencial.md

NOMBRES = [
    "Sonia Aineto Lasheras", "Teresa Escario Naval", "Jorge Vicén Lahoz",
    "Pilar Monreal Used", "Óscar Gimeno Abad", "Lucía Bernad Pueyo",
    "Rubén Castejón Mir", "Elena Sarasa Vallés", "Diego Lanaspa Franco",
    "Cristina Used Ballarín", "Alberto Sancho Peiró", "Nuria Galve Andrés",
]


def _dni(rng: random.Random) -> str:
    """DNI sintético con letra deliberadamente incorrecta.

    La letra real se calcula como módulo 23 sobre el número. Aquí se elige a
    propósito una distinta, para que ninguno de estos documentos pueda pasar por
    un DNI válido fuera del proyecto.
    """
    numero = rng.randint(30_000_000, 49_999_999)
    tabla = "TRWAGMYFPDXBNJZSQVHLCKE"
    correcta = tabla[numero % 23]
    incorrecta = rng.choice([c for c in tabla if c != correcta])
    return f"{numero:,}".replace(",", ".") + f"-{incorrecta}"


def generar() -> dict:
    rng = random.Random(SEMILLA)

    inmuebles = []
    for i in range(48):
        operacion = "venta" if i % 4 else "alquiler"
        zona = rng.choice(list(ZONAS_VENTA))
        superficie = rng.choice([45, 56, 62, 70, 75, 84, 90, 97, 104, 118, 140, 153])
        estado = rng.choice(ESTADOS)

        if operacion == "venta":
            bajo, alto = ZONAS_VENTA[zona]
            euros_m2 = rng.randint(bajo, alto)
            if estado == "a reformar":
                euros_m2 = int(euros_m2 * rng.uniform(0.75, 0.85))
            precio = round(superficie * euros_m2, -3)
        else:
            bajo, alto = ZONAS_ALQUILER[zona]
            euros_m2 = rng.randint(bajo, alto)
            precio = round(superficie * euros_m2, -1)

        dias = rng.choice([4, 11, 18, 27, 35, 48, 63, 79, 92, 104, 121, 156])
        inmuebles.append({
            "referencia": f"INM-{2026}-{i + 101}",
            "tipo": rng.choice(TIPOS),
            "operacion": operacion,
            "zona": zona,
            "superficie_m2": superficie,
            "habitaciones": rng.choice([1, 2, 2, 3, 3, 3, 4, 5]),
            "banos": rng.choice([1, 1, 2]),
            "estado": estado,
            "precio_eur": precio,
            "precio_m2_eur": round(precio / superficie, 1) if operacion == "venta" else euros_m2,
            "ascensor": rng.random() > 0.35,
            "garaje": rng.random() > 0.7,
            "terraza": rng.random() > 0.6,
            "exclusiva": rng.random() > 0.45,
            "dias_publicado": dias,
            "visitas_totales": max(0, int(dias / rng.uniform(4, 12))),
            "ofertas_recibidas": 0 if dias > 90 and rng.random() > 0.3 else rng.choice([0, 0, 1, 2]),
            "comercial": rng.choice(COMERCIALES),
        })

    operaciones = []
    for i, inmueble in enumerate(rng.sample(inmuebles, 6)):
        comprador = NOMBRES[i * 2 % len(NOMBRES)]
        vendedor = NOMBRES[(i * 2 + 1) % len(NOMBRES)]
        renta = inmueble["precio_eur"] if inmueble["operacion"] == "alquiler" else 0
        operaciones.append({
            "referencia": f"OP-2026-{110 + i * 6}",
            "inmueble": inmueble["referencia"],
            "estado": rng.choice(["reserva firmada", "arras firmadas", "pendiente de escritura"]),
            "importe_eur": inmueble["precio_eur"],
            "comercial": inmueble["comercial"],
            # Datos personales: existen para que la capa de gobernanza tenga algo
            # que proteger. Toda herramienta que los devuelva es superficie de fuga.
            "parte_compradora": {
                "nombre": comprador,
                "dni": _dni(rng),
                "telefono": f"6{rng.randint(10, 89)} 00 {rng.randint(10, 99)} {rng.randint(10, 99)}",
                "correo": comprador.split()[0].lower() + "@example.com",
                "ingresos_netos_mensuales_eur": rng.choice([1980, 2340, 2760, 3480, 4120]),
                "financiacion_preconcedida": rng.random() > 0.4,
            },
            "parte_vendedora": {
                "nombre": vendedor,
                "telefono": f"9760 0{rng.randint(10, 99)} {rng.randint(10, 99)}",
            },
            "renta_mensual_eur": renta,
        })

    visitas = []
    lunes = HOY - timedelta(days=HOY.weekday())
    for i in range(22):
        dia = lunes + timedelta(days=rng.randint(0, 11))
        visitas.append({
            "referencia": f"VIS-{600 + i}",
            "inmueble": rng.choice(inmuebles)["referencia"],
            "fecha": dia.isoformat(),
            "hora": rng.choice(["10:00", "11:30", "13:00", "16:00", "17:30", "18:30"]),
            "comercial": rng.choice(COMERCIALES),
            "interesado": rng.choice(NOMBRES),
            "resultado": rng.choice(["pendiente", "realizada", "realizada", "cancelada"]),
        })

    return {
        "generado": HOY.isoformat(),
        "semilla": SEMILLA,
        "aviso": "Datos sintéticos. Ningún inmueble, cliente u operación es real.",
        "inmuebles": inmuebles,
        "operaciones": operaciones,
        "visitas": sorted(visitas, key=lambda v: (v["fecha"], v["hora"])),
    }


def comprobar_sin_colisiones(datos: dict) -> None:
    """Falla ruidosamente si el CRM pisa algo que el corpus ya usa.

    Va aquí y no en una prueba porque el fichero generado se versiona: si la
    colisión entra, entra para quedarse. Y el síntoma no es un error, es una
    respuesta correcta sobre la persona equivocada.
    """
    personas = {op[parte]["nombre"] for op in datos["operaciones"]
                for parte in ("parte_compradora", "parte_vendedora")}
    personas |= {v["interesado"] for v in datos["visitas"]}
    chocan = personas & PERSONAS_DEL_CORPUS
    if chocan:
        raise SystemExit(
            f"[ERROR] El CRM reutiliza personas del corpus documental: {sorted(chocan)}. "
            "Dos fuentes del mismo inquilino no pueden describir a la misma persona "
            "con datos distintos."
        )

    referencias = {op["referencia"] for op in datos["operaciones"]}
    chocan = referencias & OPERACIONES_DEL_CORPUS
    if chocan:
        raise SystemExit(
            f"[ERROR] El CRM reutiliza referencias del corpus documental: {sorted(chocan)}."
        )


def main() -> None:
    datos = generar()
    comprobar_sin_colisiones(datos)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[OK] {len(datos['inmuebles'])} inmuebles, {len(datos['operaciones'])} operaciones "
        f"y {len(datos['visitas'])} visitas en {DESTINO}"
    )


if __name__ == "__main__":
    main()
