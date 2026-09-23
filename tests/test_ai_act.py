"""La clasificación por el artículo 6 del AI Act vive en el manifiesto y la
valida el código.

Lo que se comprueba no es que el sistema "cumpla el AI Act" —eso no lo decide
un test— sino que **la regla del artículo 6.3 está codificada y no se puede
saltar**: tocar el anexo III sin salida documentada no valida, y perfilar
personas no admite excepción. Y que los dos inquilinos reales la declaran.
"""
import pytest
from pydantic import ValidationError

from src.tenant import (
    CLASIFICACION_ALTO_RIESGO,
    CLASIFICACION_TRANSPARENCIA,
    CONDICIONES_ART_6_3,
    ClasificacionAIAct,
    cargar_tenant,
    listar_tenants,
)

BASE = {
    "aviso_usuario": "Respuesta generada por un asistente de IA.",
    "evaluado": "2026-09-23",
    "fuentes": ["Reglamento (UE) 2024/1689"],
}

EXCEPCION = {
    "condicion": "a",
    "justificacion": "Recupera y cita documentos; no decide nada sobre nadie.",
    "usos_excluidos": ["evaluar a una persona"],
    "perfila_personas": False,
}


# --- Los inquilinos reales ---

@pytest.mark.parametrize("tenant_id", listar_tenants())
def test_cada_inquilino_declara_su_clasificacion(tenant_id):
    tenant = cargar_tenant(tenant_id)
    assert tenant.ai_act.clasificacion in (
        CLASIFICACION_TRANSPARENCIA,
        CLASIFICACION_ALTO_RIESGO,
    )
    assert tenant.ai_act.aviso_usuario.strip()
    assert tenant.ai_act.fuentes


@pytest.mark.parametrize("tenant_id", listar_tenants())
def test_los_dos_inquilinos_tocan_el_anexo_iii_y_documentan_la_salida(tenant_id):
    """Los dos corpus contienen datos que el anexo III nombra (salarios y
    evaluaciones en uno, solvencia de personas en el otro). Ninguno se declara
    de alto riesgo, así que los dos tienen que alegar el 6.3 por escrito."""
    ai_act = cargar_tenant(tenant_id).ai_act
    assert ai_act.puntos_anexo_iii, "el corpus toca el anexo III y no lo declara"
    assert ai_act.excepcion_art_6_3 is not None
    assert ai_act.excepcion_art_6_3.usos_excluidos
    assert ai_act.excepcion_art_6_3.perfila_personas is False


def test_el_heredado_toca_empleo_y_la_agencia_toca_solvencia():
    assert "4" in cargar_tenant("empresa_servicios").ai_act.puntos_anexo_iii
    assert "5b" in cargar_tenant("agencia_inmobiliaria").ai_act.puntos_anexo_iii


# --- La regla del artículo 6.3, codificada ---

def test_tocar_el_anexo_iii_sin_excepcion_ni_alto_riesgo_no_valida():
    with pytest.raises(ValidationError, match="sin alegar la excepción"):
        ClasificacionAIAct.model_validate(
            {**BASE, "clasificacion": CLASIFICACION_TRANSPARENCIA, "puntos_anexo_iii": ["4"]}
        )


def test_tocar_el_anexo_iii_con_excepcion_documentada_valida():
    c = ClasificacionAIAct.model_validate(
        {
            **BASE,
            "clasificacion": CLASIFICACION_TRANSPARENCIA,
            "puntos_anexo_iii": ["4"],
            "excepcion_art_6_3": EXCEPCION,
        }
    )
    assert c.excepcion_art_6_3.condicion == "a"


def test_el_perfilado_de_personas_no_admite_excepcion():
    """Último párrafo del 6.3: siempre alto riesgo."""
    with pytest.raises(ValidationError, match="perfila personas"):
        ClasificacionAIAct.model_validate(
            {
                **BASE,
                "clasificacion": CLASIFICACION_TRANSPARENCIA,
                "puntos_anexo_iii": ["4"],
                "excepcion_art_6_3": {**EXCEPCION, "perfila_personas": True},
            }
        )


def test_alto_riesgo_sin_puntos_del_anexo_no_valida():
    with pytest.raises(ValidationError, match="exige declarar qué puntos"):
        ClasificacionAIAct.model_validate(
            {**BASE, "clasificacion": CLASIFICACION_ALTO_RIESGO}
        )


def test_alto_riesgo_con_puntos_valida_sin_excepcion():
    c = ClasificacionAIAct.model_validate(
        {**BASE, "clasificacion": CLASIFICACION_ALTO_RIESGO, "puntos_anexo_iii": ["4", "5b"]}
    )
    assert c.excepcion_art_6_3 is None


def test_una_excepcion_sin_anexo_no_tiene_de_que_exceptuar():
    with pytest.raises(ValidationError, match="sin tocar el anexo III"):
        ClasificacionAIAct.model_validate(
            {
                **BASE,
                "clasificacion": CLASIFICACION_TRANSPARENCIA,
                "excepcion_art_6_3": EXCEPCION,
            }
        )


@pytest.mark.parametrize("malo", ["e", "A", "", "tarea limitada"])
def test_la_condicion_tiene_que_ser_una_letra_del_6_3(malo):
    with pytest.raises(ValidationError, match="condición del artículo 6.3"):
        ClasificacionAIAct.model_validate(
            {
                **BASE,
                "clasificacion": CLASIFICACION_TRANSPARENCIA,
                "puntos_anexo_iii": ["4"],
                "excepcion_art_6_3": {**EXCEPCION, "condicion": malo},
            }
        )


def test_las_cuatro_condiciones_del_6_3_estan():
    assert sorted(CONDICIONES_ART_6_3) == ["a", "b", "c", "d"]


@pytest.mark.parametrize("malo", ["9", "4.a", "punto 4", "5B"])
def test_los_puntos_del_anexo_iii_tienen_forma_de_punto(malo):
    with pytest.raises(ValidationError, match="puntos del anexo III inválidos"):
        ClasificacionAIAct.model_validate(
            {**BASE, "clasificacion": CLASIFICACION_ALTO_RIESGO, "puntos_anexo_iii": [malo]}
        )


def test_una_excepcion_sin_usos_excluidos_no_valida():
    """Sin usos excluidos, la excepción no dice qué no hace el sistema, y eso es
    justo lo que la sostiene."""
    with pytest.raises(ValidationError):
        ClasificacionAIAct.model_validate(
            {
                **BASE,
                "clasificacion": CLASIFICACION_TRANSPARENCIA,
                "puntos_anexo_iii": ["4"],
                "excepcion_art_6_3": {**EXCEPCION, "usos_excluidos": []},
            }
        )


def test_una_clasificacion_desconocida_no_valida():
    with pytest.raises(ValidationError, match="clasificación inválida"):
        ClasificacionAIAct.model_validate({**BASE, "clasificacion": "riesgo_minimo"})


def test_un_manifiesto_sin_ai_act_no_carga(tmp_path):
    """Un inquilino sin clasificación no arranca: es lo que hace que el alta de
    un cliente nuevo incluya la evaluación del artículo 6."""
    import json

    datos = {
        "id": "nuevo",
        "nombre": "Nuevo",
        "contexto_enrutador": "una prueba",
        "categorias": [{"nombre": "docs", "descripcion": "x", "fuente": "docs"}],
    }
    (tmp_path / "nuevo.json").write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ValidationError, match="ai_act"):
        cargar_tenant("nuevo", raiz=tmp_path)
