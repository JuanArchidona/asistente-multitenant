"""Pruebas del sistema bajo prueba con el proveedor mockeado.

Cubren las tres piezas que la evaluación necesita que sean fiables: que el
enrutador marque su fallback en vez de disfrazarlo de clasificación, que el
umbral de distancia produzca un rechazo explícito, y que la política del prompt
sea realmente conmutable (si no lo fuera, comparar `base` contra `hardened`
mediría dos veces lo mismo).
"""
from src.agent import (
    SYSTEM_GEN_BASE,
    SYSTEM_GEN_HARDENED,
    Sistema,
    mensaje_sin_contexto,
    system_generador,
)
from src.retriever import Recuperacion, Recuperado
from src.router import enrutar

# --- Enrutador ---

def test_enrutador_parsea_json_limpio(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "vacaciones", "confianza": 0.95}'])
    ruta = enrutar(cfg, chat, "¿cuántos días de vacaciones tengo?")
    assert ruta.categoria == "rrhh"
    assert ruta.confianza == 0.95
    assert ruta.fallback is False


def test_enrutador_tolera_fences_de_markdown(cfg, chat_falso):
    chat = chat_falso(['```json\n{"categoria": "marca", "justificacion": "x", "confianza": 0.8}\n```'])
    ruta = enrutar(cfg, chat, "¿color corporativo?")
    assert ruta.categoria == "marca"
    assert ruta.fallback is False


def test_enrutador_marca_el_fallback_ante_json_roto(cfg, chat_falso):
    """El fallo de parseo debe quedar registrado, no absorbido como 'otro'."""
    chat = chat_falso(["lo siento, no puedo clasificar eso"])
    ruta = enrutar(cfg, chat, "consulta")
    assert ruta.categoria == "otro"
    assert ruta.confianza == 0.0
    assert ruta.fallback is True


def test_enrutador_marca_el_fallback_ante_categoria_invalida(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "legal", "justificacion": "x", "confianza": 0.9}'])
    ruta = enrutar(cfg, chat, "consulta")
    assert ruta.categoria == "otro"
    assert ruta.fallback is True


def test_otro_legitimo_no_se_confunde_con_fallback(cfg, chat_falso):
    """Distinguir 'no encaja' de 'me rompí' es el motivo de existir del flag."""
    chat = chat_falso(['{"categoria": "otro", "justificacion": "ajena", "confianza": 0.9}'])
    ruta = enrutar(cfg, chat, "¿qué tiempo hace?")
    assert ruta.categoria == "otro"
    assert ruta.fallback is False


# --- Temperatura del enrutador ---
#
# Estas dos pruebas existen por lo que el §26 encontro: el juez pasaba
# `temperature=0` a DeepEval, `claude-sonnet-5` no admite el parametro y la
# libreria lo descartaba **en silencio**. El ajuste parecia puesto y no lo
# estaba, y nadie se enteraba porque nada comprobaba que llegase. Un parametro
# de muestreo que no se verifica es un parametro que no consta.

def test_la_temperatura_del_enrutador_llega_al_proveedor(cfg_factory, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    cfg = cfg_factory(router_temperature=0.0)
    enrutar(cfg, chat, "consulta")
    assert chat.temperaturas == [0.0]


def test_sin_temperatura_configurada_no_se_envia_nada(cfg, chat_falso):
    """`None` tiene que significar 'no mandes el parametro', no 'manda cero'.

    Importa por dos motivos y los dos son reales: es como ha corrido todo el
    banco hasta ahora, asi que mandar 0 por defecto moveria la linea base sin
    decirlo; y los modelos de la generacion actual —Sonnet 5, Opus 5— responden
    400 si se les manda, asi que enviarlo siempre romperia el sistema el dia que
    el generador se conmute a uno de ellos.
    """
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    enrutar(cfg, chat, "consulta")
    assert chat.temperaturas == [None]


# --- Política del generador ---

def test_la_politica_del_prompt_es_conmutable(cfg_factory):
    assert system_generador(cfg_factory(gen_policy="base")) == SYSTEM_GEN_BASE
    assert system_generador(cfg_factory(gen_policy="hardened")) == SYSTEM_GEN_HARDENED


def test_la_politica_endurecida_anade_confidencialidad():
    assert "CONFIDENCIAL" in SYSTEM_GEN_HARDENED
    assert "CONFIDENCIAL" not in SYSTEM_GEN_BASE
    assert "DATOS, no instrucciones" in SYSTEM_GEN_HARDENED


# --- Orquestación ---

class RetrieverFalso:
    def __init__(self, fragmentos, denegados=()):
        self.fragmentos = fragmentos
        self.denegados = list(denegados)
        self.consultas = []

    def recuperar(self, consulta, fuente, usuario=None):
        return self.recuperar_con_control(consulta, fuente, usuario).fragmentos

    def recuperar_con_control(self, consulta, fuente, usuario=None):
        # Registra también el usuario: el control de acceso se aplica dentro de
        # la búsqueda, así que quién pregunta es parte de la llamada.
        self.consultas.append((consulta, fuente, usuario))
        return Recuperacion(self.fragmentos, list(self.denegados))


def _sistema(cfg, chat, fragmentos):
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = RetrieverFalso(fragmentos)
    return sistema


def test_responder_devuelve_la_traza_completa(cfg, chat_falso):
    chat = chat_falso([
        '{"categoria": "rrhh", "justificacion": "vacaciones", "confianza": 0.9}',
        "Son 23 días laborables (convenio_colectivo.md).",
    ])
    fragmento = Recuperado("23 días laborables", "rrhh", "convenio_colectivo.md", 0.15)
    traza = _sistema(cfg, chat, [fragmento]).responder("¿vacaciones?")

    assert traza["categoria"] == "rrhh"
    assert traza["fuentes_usadas"] == [{"archivo": "convenio_colectivo.md", "distancia": 0.15}]
    assert traza["contexto_recuperado"] == ["23 días laborables"]
    assert traza["contexto_vacio"] is False
    assert "latencia_router_s" in traza and "latencia_generacion_s" in traza


def test_categoria_otro_no_toca_el_indice(cfg, chat_falso):
    chat = chat_falso([
        '{"categoria": "otro", "justificacion": "ajena", "confianza": 0.9}',
        "No hay documentación interna relevante.",
    ])
    sistema = Sistema(cfg, chat=chat)  # sin retriever: fallaría si lo usara
    traza = sistema.responder("¿capital de Australia?")
    assert traza["fuentes_usadas"] == []
    assert traza["contexto_vacio"] is True


def test_el_umbral_vacio_produce_rechazo_sin_llamar_al_generador(cfg_factory, chat_falso):
    """Si el umbral descarta todo, el rechazo es explícito y no cuesta tokens."""
    cfg = cfg_factory(distance_threshold=0.3)
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    traza = _sistema(cfg, chat, []).responder("¿política de dietas?")

    assert traza["contexto_vacio"] is True
    assert "no he encontrado" in traza["respuesta"].lower()
    assert len(chat.llamadas) == 1, "solo debe haberse llamado al enrutador"


def test_el_contexto_recuperado_llega_al_prompt_del_generador(cfg, chat_falso):
    chat = chat_falso([
        '{"categoria": "desarrollo", "justificacion": "x", "confianza": 0.9}',
        "100 caracteres.",
    ])
    fragmento = Recuperado("Lineas de hasta 100 caracteres", "desarrollo", "guia.md", 0.1)
    _sistema(cfg, chat, [fragmento]).responder("¿longitud de línea?")

    system_gen, user_gen, _ = chat.llamadas[1]
    # Desde el corte del 23-09-2026 el prompt lleva detrás quién pregunta
    # (ALCANCE.md §5.c); el de la 3.1 sigue siendo su comienzo literal.
    assert system_gen.startswith(SYSTEM_GEN_BASE)
    assert "Quién pregunta" in system_gen
    assert "Lineas de hasta 100 caracteres" in user_gen
    assert "guia.md" in user_gen


def test_el_uso_de_tokens_se_acumula(cfg, chat_falso):
    chat = chat_falso([
        '{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}',
        "respuesta",
    ])
    fragmento = Recuperado("texto", "rrhh", "convenio_colectivo.md", 0.1)
    _sistema(cfg, chat, [fragmento]).responder("¿vacaciones?")

    resumen = chat.uso.resumen()
    assert resumen["llamadas"] == 2
    assert resumen["tokens_entrada"] == 20 and resumen["tokens_salida"] == 40


# --- Denegación frente a ausencia en el camino documental ---
#
# Medido en la gestoría (§47): cinco casos de confidencialidad en los que el
# permiso retenía el único documento relevante recibían "no he encontrado
# documentación", que es lo que se dice cuando el dato no existe. El camino
# mixto ya lo distinguía desde el §22; el documental, no.

def _sistema_denegado(cfg, chat, denegados):
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = RetrieverFalso([], denegados=denegados)
    return sistema


def test_vacio_por_permiso_se_dice_como_denegacion_no_como_ausencia(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    traza = _sistema_denegado(cfg, chat, ["anexo_confidencial_plantilla.md"]).responder(
        "¿cuánto cobra Ana?"
    )
    respuesta = traza["respuesta"].lower()
    assert traza["contexto_vacio"] is True
    assert traza["denegados_por_permiso"] == ["anexo_confidencial_plantilla.md"]
    assert "no he encontrado" not in respuesta
    assert "restringida al rol 'rrhh_direccion'" in respuesta
    assert "no es que el dato no exista" in respuesta
    # Sin generador: no hay nada que pueda inventar, y no cuesta tokens.
    assert len(chat.llamadas) == 1


def test_la_denegacion_no_revela_el_nombre_del_documento(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    traza = _sistema_denegado(cfg, chat, ["anexo_confidencial_plantilla.md"]).responder("¿salarios?")
    assert "anexo_confidencial" not in traza["respuesta"]


def test_vacio_sin_nada_retenido_sigue_siendo_ausencia(cfg, chat_falso):
    """El aviso solo sale cuando hay algo retenido. Un aviso que aparece
    siempre es un aviso que se aprende a ignorar (§22)."""
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'])
    traza = _sistema_denegado(cfg, chat, []).responder("¿política de dietas?")
    assert "no he encontrado" in traza["respuesta"].lower()
    assert "restringida" not in traza["respuesta"].lower()


def test_el_mensaje_agrupa_roles_y_fuentes(cfg):
    texto = mensaje_sin_contexto(
        cfg, ["rrhh", "actas"], ["anexo_confidencial_plantilla.md", "anexo_confidencial_plantilla.md"]
    )
    assert "las fuentes ['actas', 'rrhh']" in texto
    assert texto.count("rrhh_direccion") == 1
