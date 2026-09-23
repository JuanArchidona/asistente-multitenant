"""El generador sabe quién pregunta y que su contexto ya está autorizado.

Corte de línea base del 23-09-2026 (ALCANCE.md §5.c, HALLAZGOS.md §39). Lo
que se fija: que el bloque va detrás de las tres políticas de prompt sin
alterar su texto, que lleva identificador y roles, que la escotilla lo quita
entero, y que bajo la política endurecida las reglas de confidencialidad
siguen ahí (el bloque no las borra: es el precio conocido de esa política).
"""
from dataclasses import replace

from src.agent import (
    SYSTEM_GEN_BASE,
    SYSTEM_GEN_DATOS,
    SYSTEM_GEN_HARDENED,
    Sistema,
    bloque_quien_pregunta,
    system_datos,
    system_generador,
    system_mixto,
)
from src.gobernanza import USUARIO_ANONIMO, Usuario
from src.retriever import Recuperacion, Recuperado

DIRECCION = Usuario(id="direccion", nombre="Dirección de RRHH", roles=["rrhh_direccion"])


def test_el_bloque_lleva_identificador_roles_y_la_afirmacion_de_autorizacion(cfg):
    bloque = bloque_quien_pregunta(cfg, DIRECCION)
    assert "'direccion'" in bloque
    assert "Dirección de RRHH" in bloque
    assert "rrhh_direccion" in bloque
    assert "ha pasado ya el control de acceso" in bloque
    assert "no es una instrucción para ti" in bloque


def test_sin_roles_lo_dice_en_vez_de_dejar_un_hueco(cfg):
    assert "roles: ninguno" in bloque_quien_pregunta(cfg, USUARIO_ANONIMO)


def test_el_prompt_base_sigue_siendo_el_de_la_3_1_y_el_bloque_va_detras(cfg):
    assert system_generador(cfg) == SYSTEM_GEN_BASE
    con = system_generador(cfg, DIRECCION)
    assert con.startswith(SYSTEM_GEN_BASE)
    assert con.endswith(bloque_quien_pregunta(cfg, DIRECCION))


def test_las_tres_politicas_reciben_el_bloque(cfg):
    endurecido = replace(cfg, gen_policy="hardened")
    assert system_generador(endurecido, DIRECCION).startswith(SYSTEM_GEN_HARDENED)
    assert "Quién pregunta" in system_generador(endurecido, DIRECCION)
    assert "Quién pregunta" in system_mixto(cfg, usuario=DIRECCION)
    assert system_datos(cfg=cfg, usuario=DIRECCION).startswith(SYSTEM_GEN_DATOS.split("{fecha}")[0])
    assert "Quién pregunta" in system_datos(cfg=cfg, usuario=DIRECCION)


def test_la_politica_endurecida_conserva_sus_reglas_prioritarias(cfg):
    """El bloque no las borra: proteger con el prompt sigue bloqueando a quien
    tiene permiso, y eso es lo que se mide, no lo que se esconde."""
    texto = system_generador(replace(cfg, gen_policy="hardened"), DIRECCION)
    assert "prioritarias sobre cualquier otra" in texto
    assert "NUNCA reproduzcas datos personales" in texto


def test_la_escotilla_reproduce_el_prompt_anterior_al_corte(cfg):
    viejo = replace(cfg, gen_quien_pregunta=False)
    assert system_generador(viejo, DIRECCION) == SYSTEM_GEN_BASE
    assert bloque_quien_pregunta(viejo, DIRECCION) == ""
    assert "Quién pregunta" not in system_mixto(viejo, usuario=DIRECCION)
    assert "Quién pregunta" not in system_datos(cfg=viejo, usuario=DIRECCION)


def test_el_camino_documental_pasa_al_generador_quien_pregunta(cfg, chat_falso, monkeypatch):
    chat = chat_falso([
        '{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}',
        "68.000 euros.",
    ])
    fragmento = Recuperado("Diego Ruíz: 68.000 euros", "rrhh", "anexo_confidencial_plantilla.md", 0.1)

    class RetrieverFalso:
        def recuperar_con_control(self, consulta, fuente, usuario=None):
            return Recuperacion(fragmentos=[fragmento], denegados=[])

    sistema = Sistema(cfg, chat, usuario=DIRECCION)
    monkeypatch.setattr(sistema, "_retriever", RetrieverFalso())
    sistema.responder("¿Cuál es la retribución de Diego Ruíz?")
    system_gen, _, _ = chat.llamadas[1]
    assert "'direccion'" in system_gen
    assert "rrhh_direccion" in system_gen


def test_con_la_escotilla_el_camino_documental_no_dice_quien_pregunta(cfg, chat_falso, monkeypatch):
    chat = chat_falso([
        '{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}',
        "68.000 euros.",
    ])
    fragmento = Recuperado("Diego Ruíz: 68.000 euros", "rrhh", "anexo_confidencial_plantilla.md", 0.1)

    class RetrieverFalso:
        def recuperar_con_control(self, consulta, fuente, usuario=None):
            return Recuperacion(fragmentos=[fragmento], denegados=[])

    sistema = Sistema(replace(cfg, gen_quien_pregunta=False), chat, usuario=DIRECCION)
    monkeypatch.setattr(sistema, "_retriever", RetrieverFalso())
    sistema.responder("¿Cuál es la retribución de Diego Ruíz?")
    assert chat.llamadas[1][0] == SYSTEM_GEN_BASE
