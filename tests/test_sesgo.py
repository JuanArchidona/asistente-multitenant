"""Pruebas del experimento de sesgo, y son pruebas de metodología.

Cada una de estas fija una lección que costó una medición equivocada. El
experimento se ejecutó cuatro veces el 22-09-2026 y las tres primeras versiones
produjeron **una afirmación falsa, específica y alarmante** cada una
(HALLAZGOS.md §34):

1. Sin controles: "el mayor sesgo es contra la discapacidad". Era una frase
   extra en una variante y no en la otra.
2. Con control de frase: "sesgo por origen, 3 veces el suelo". Era la longitud
   del nombre.
3. Con un solo par de control de longitud: "origen a 1,09 veces el suelo". Era
   el tamaño del grupo: un eje de cuatro variantes contra un control de dos.

Ninguna de las tres la habría detectado un test de que el código funciona. Lo
que estas pruebas comprueban es que **los pares sigan emparejados**, que es la
única condición de la que depende que la cifra signifique algo.
"""
import pytest

from evals.sesgo import CONSULTAS, CONTROL_DE, PARES, distancia_coseno

EJES_MEDIDOS = [e for e in PARES if not e.startswith("control")]
CONTROLES = [e for e in PARES if e.startswith("control")]


# --- Que los pares esten emparejados ---------------------------------------

def test_cada_eje_tiene_al_menos_dos_variantes():
    """Un eje de una variante no compara nada."""
    for eje, variantes in PARES.items():
        assert len(variantes) >= 2, eje


def test_las_etiquetas_de_un_eje_no_se_repiten():
    """Dos variantes con la misma etiqueta se pisan en el diccionario de
    distancias y una desaparece del resultado sin avisar."""
    for eje, variantes in PARES.items():
        etiquetas = [v.etiqueta for v in variantes]
        assert len(set(etiquetas)) == len(etiquetas), eje


def test_las_variantes_de_un_eje_comparten_plantilla():
    """Entre variantes solo puede cambiar el atributo protegido.

    Se comprueba por la longitud: dos textos que solo difieren en un nombre o en
    una frase equivalente no pueden diferenciarse en mas de un 15 %. Es el
    defecto de la version 1, donde una variante llevaba una frase entera que la
    otra no tenia, y el experimento medía esa frase.
    """
    for eje, variantes in PARES.items():
        largos = [len(v.texto) for v in variantes]
        assert min(largos) / max(largos) > 0.85, (
            f"{eje}: las variantes difieren demasiado en longitud {largos}; "
            "el rango medira eso y no el atributo"
        )


def test_los_ejes_de_frase_no_tienen_una_variante_pelada():
    """El defecto exacto de la version 1: `discapacidad` comparaba "con frase"
    contra "sin frase". Todas las variantes de un eje cuyo atributo va en una
    frase tienen que llevar frase."""
    for eje in ("edad", "discapacidad"):
        for v in PARES[eje]:
            assert "Tiene " in v.texto, f"{eje}/{v.etiqueta} sin frase de atributo"


# --- Que los controles sean comparables ------------------------------------

def test_hay_control_para_cada_eje_medido():
    for eje in EJES_MEDIDOS:
        assert eje in CONTROL_DE, f"{eje} sin control asignado"
        assert CONTROL_DE[eje] in PARES, f"el control de {eje} no existe"


def test_cada_control_tiene_al_menos_tantas_variantes_como_su_eje():
    """El defecto de la version 3.

    El rango de un grupo crece con el numero de variantes, porque hay mas
    oportunidades de separarse. Un eje de cuatro contra un control de dos infla
    el eje, y asi `origen` salio a 1,09 veces el suelo cuando esta a 0,99.
    """
    for eje in EJES_MEDIDOS:
        control = CONTROL_DE[eje]
        assert len(PARES[control]) >= len(PARES[eje]), (
            f"{eje} tiene {len(PARES[eje])} variantes y su control "
            f"{control} solo {len(PARES[control])}: el rango no es comparable"
        )


def test_los_controles_son_eticamente_irrelevantes():
    """Un control que mencionara un atributo protegido dejaria de ser suelo: su
    rango incluiria sesgo y el cociente saldria artificialmente bajo."""
    prohibidas = ("discapacidad", "años", "edad", "sexo", "género", "origen")
    for control in CONTROLES:
        for v in PARES[control]:
            texto = v.texto.lower()
            for palabra in prohibidas:
                assert palabra not in texto, f"{control}/{v.etiqueta} menciona {palabra!r}"


# --- Que las consultas sean neutras ----------------------------------------

def test_hay_consulta_para_cada_eje():
    for eje in PARES:
        assert eje in CONSULTAS, f"{eje} sin consulta"


def test_ninguna_consulta_menciona_el_atributo_protegido():
    """Es la condicion del experimento. Si la consulta lo mencionara, una
    diferencia de distancia seria lo correcto y no un sesgo, y la medida dejaria
    de significar lo que dice significar."""
    prohibidas = ("discapacidad", "años", "edad", "hombre", "mujer", "origen")
    for eje, consulta in CONSULTAS.items():
        texto = consulta.lower()
        for palabra in prohibidas:
            assert palabra not in texto, f"la consulta de {eje} menciona {palabra!r}"


def test_ninguna_consulta_menciona_un_nombre_de_las_variantes():
    """Nombrar a una de las personas en la consulta haria que su variante
    estuviese legitimamente mas cerca, y el rango mediria eso.

    Con limites de palabra, y no por subcadena: la primera version de esta
    prueba fallaba porque "Ana" esta dentro de "analista". Es el mismo error de
    forma que el §23 cometio comparando nombres de fichero byte a byte — una
    comparacion demasiado literal que acusa de lo que no hay.
    """
    import re

    nombres = ("Carlos", "Carmen", "Javier", "Mohamed", "Wei", "Amadou", "Álex", "Ana",
               "María", "Luis")
    for eje, variantes in PARES.items():
        consulta = CONSULTAS[eje]
        presentes = {n for n in nombres for v in variantes if n in v.texto}
        for nombre in presentes:
            assert not re.search(
                rf"\b{re.escape(nombre)}\b", consulta, re.IGNORECASE
            ), (
                f"la consulta de {eje} nombra a {nombre}"
            )


# --- La medida en si -------------------------------------------------------

def test_la_distancia_de_un_vector_consigo_mismo_es_cero():
    v = [0.3, -0.5, 0.8, 0.1]
    assert distancia_coseno(v, v) == pytest.approx(0.0, abs=1e-9)


def test_la_distancia_no_depende_de_la_escala():
    """Es distancia de coseno: multiplicar un vector por una constante no puede
    cambiarla. Si cambiara, el rango dependeria de la norma del embedding."""
    a = [0.3, -0.5, 0.8]
    b = [0.1, 0.2, -0.4]
    assert distancia_coseno(a, b) == pytest.approx(
        distancia_coseno(a, [x * 7 for x in b]), abs=1e-9
    )


def test_vectores_opuestos_estan_a_distancia_dos():
    a = [1.0, 0.0]
    assert distancia_coseno(a, [-1.0, 0.0]) == pytest.approx(2.0)
