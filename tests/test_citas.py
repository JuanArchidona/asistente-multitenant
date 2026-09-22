"""Pruebas del verificador determinista de citas.

El prompt del generador exige "cita la fuente y el archivo de donde sale la
información" y hasta ahora ninguna métrica lo comprobaba: las deterministas
miden lo que se **recuperó**, no lo que la respuesta **citó**. La diferencia es
donde vive la cita inventada.

Las dos rúbricas usan reglas distintas a propósito, y la mitad de estas pruebas
existe para fijar esa asimetría:

- Acusar de inventar una fuente es la acusación más grave del banco, así que la
  regla es conservadora y **no puede dar falsos positivos**. Los dos primeros
  tests de esa sección son los que fallaron en el primer censo real.
- Decidir si citó *algo* tiene que ser generoso, porque un falso negativo acusa
  al sistema de no citar cuando citó en prosa.
"""
import pytest

from evals.metrics import evaluar_citas
from evals.schema import Comportamiento


class CasoFalso:
    """Lo único que la métrica mira del caso."""

    def __init__(self, comportamiento="responder"):
        self.comportamiento_esperado = Comportamiento(comportamiento)


def _metricas(respuesta, archivos=(), herramientas=(), comportamiento="responder"):
    traza = {
        "respuesta": respuesta,
        "fuentes_usadas": [{"archivo": a, "distancia": 0.1} for a in archivos],
        "herramientas_invocadas": [{"herramienta": h} for h in herramientas],
    }
    return {r.metrica: r for r in evaluar_citas(CasoFalso(comportamiento), traza)}


# --- Resolubilidad: ¿lo citado se recuperó? ---------------------------------

def test_una_cita_a_un_documento_recuperado_es_resoluble():
    r = _metricas("Son 23 días (convenio_colectivo.md).", ["convenio_colectivo.md"])
    assert r["citas_resolubles"].valor == 1.0


def test_una_cita_a_un_documento_no_recuperado_se_detecta():
    """El fallo dominante de 2026 en producción: una respuesta bien anclada al
    contexto que atribuye lo que dice a un documento que nunca se recuperó."""
    r = _metricas("Según politica_dietas.md son 40 euros.", ["convenio_colectivo.md"])
    assert r["citas_resolubles"].valor == 0.0
    assert r["citas_resolubles"].detalle["no_recuperados"] == ["politica_dietas.md"]


def test_los_acentos_no_convierten_una_cita_buena_en_inventada():
    """Los seis únicos fallos del primer censo retroactivo, y los seis eran
    culpa de la métrica: el corpus tiene `politica_valoracion.md` y el modelo
    la escribe como la escribiría cualquiera en español. El documento estaba
    recuperado y la cita era correcta; lo que fallaba era comparar bytes."""
    r = _metricas(
        "Según política_valoración.md, el criterio es el comparativo.",
        ["politica_valoracion.md"],
    )
    assert r["citas_resolubles"].valor == 1.0, "acentuar no es inventar"


def test_las_mayusculas_tampoco():
    r = _metricas("Ver Convenio_Colectivo.MD.", ["convenio_colectivo.md"])
    assert r["citas_resolubles"].valor == 1.0


def test_una_ruta_completa_cuenta_como_el_fichero():
    r = _metricas(
        "Ver corpus/rrhh/convenio_colectivo.md.", ["convenio_colectivo.md"]
    )
    assert r["citas_resolubles"].valor == 1.0


def test_la_proporcion_distingue_una_cita_mala_de_todas_malas():
    r = _metricas(
        "Ver convenio_colectivo.md y tambien inventado.md.",
        ["convenio_colectivo.md"],
    )
    assert r["citas_resolubles"].valor == pytest.approx(0.5)
    assert r["citas_resolubles"].exito is False, "una sola cita falsa ya es un fallo"


def test_sin_citas_de_fichero_la_resolubilidad_no_aplica():
    """Que falte la cita ya lo dice la rúbrica estructural. Contarlo aquí
    también sería castigar dos veces el mismo hecho."""
    r = _metricas("Son 23 días laborables.", ["convenio_colectivo.md"])
    assert r["citas_resolubles"].valor is None


def test_la_resolubilidad_no_tiene_puerta_de_comportamiento():
    """Citar un documento que no se recuperó está mal también al negarse."""
    r = _metricas(
        "No puedo darte eso, ver inventado.md.",
        ["convenio_colectivo.md"],
        comportamiento="denegar",
    )
    assert r["citas_resolubles"].valor == 0.0


# --- Estructural: ¿cita algo? -----------------------------------------------

def test_citar_el_fichero_por_su_nombre_cuenta():
    r = _metricas("Son 23 días (convenio_colectivo.md).", ["convenio_colectivo.md"])
    assert r["cita_alguna_fuente"].valor == 1.0


def test_citar_sin_extension_cuenta():
    r = _metricas("Según convenio_colectivo, 23 días.", ["convenio_colectivo.md"])
    assert r["cita_alguna_fuente"].valor == 1.0


def test_citar_en_prosa_con_espacios_cuenta():
    """El modelo cita en prosa: para `acta_captaciones_2026-08-24.md` escribe
    "el acta de captaciones del 24 de agosto", que identifica el documento igual
    de bien. Exigir el nombre de fichero literal mediría estilo de redacción."""
    r = _metricas(
        "Según el acta de captaciones del 2026-08-24, se acordó publicar.",
        ["acta_captaciones_2026-08-24.md"],
    )
    assert r["cita_alguna_fuente"].valor == 1.0


def test_nombrar_la_herramienta_sin_el_prefijo_del_servidor_cuenta():
    """El modelo escribe "Fuente: CRM - estado_operacion", no
    `crm__estado_operacion`."""
    r = _metricas(
        "Fuente: CRM - estado_operacion. La operación está en curso.",
        herramientas=["crm__estado_operacion"],
    )
    assert r["cita_alguna_fuente"].valor == 1.0


def test_no_citar_nada_habiendo_contexto_es_un_fallo():
    r = _metricas("Son 23 días laborables.", ["convenio_colectivo.md"])
    assert r["cita_alguna_fuente"].valor == 0.0
    assert "el prompt lo exige" in r["cita_alguna_fuente"].razon


def test_decir_el_crm_sin_nombrar_la_herramienta_es_un_fallo():
    """El caso real que esta métrica destapó. Con varias herramientas, "el CRM"
    no dice cuál de ellas produjo el número, y el prompt pide la herramienta."""
    r = _metricas(
        "Según la búsqueda en el CRM hay 9 inmuebles.",
        herramientas=["crm__buscar_inmuebles", "crm__estadisticas_cartera"],
    )
    assert r["cita_alguna_fuente"].valor == 0.0


# --- Las dos puertas --------------------------------------------------------

def test_sin_nada_recuperado_ninguna_rubrica_aplica():
    """Si la recuperación vino vacía o el control lo retuvo todo, no hay fuente
    a la que atribuir nada."""
    r = _metricas("No he encontrado documentación relevante.")
    assert r["cita_alguna_fuente"].valor is None
    assert r["citas_resolubles"].valor is None


@pytest.mark.parametrize("comportamiento", ["denegar", "abstenerse"])
def test_a_quien_debe_negarse_no_se_le_exige_citar(comportamiento):
    """El recorte que el primer censo obligó a hacer: el 47 % de los casos de
    `fuera_de_alcance` y el 42 % de los de confidencialidad "no citaban", y
    decían exactamente lo que debían. "Cita de dónde sale lo que dices" no
    tiene sujeto cuando la respuesta correcta no afirma nada."""
    r = _metricas(
        "El contexto recuperado no contiene esa información.",
        ["proceso_captacion.md"],
        comportamiento=comportamiento,
    )
    assert r["cita_alguna_fuente"].valor is None
    assert comportamiento in r["cita_alguna_fuente"].razon


def test_la_puerta_la_declara_el_banco_y_no_la_respuesta():
    """Si la puerta dependiera de que la respuesta parezca una negativa, el
    sistema la aprobaría negándose más. Depende de `comportamiento_esperado`,
    que está en el golden set."""
    negativa = "El contexto recuperado no contiene esa información."
    r = _metricas(negativa, ["proceso_captacion.md"], comportamiento="responder")
    assert r["cita_alguna_fuente"].valor == 0.0
