"""Pruebas del sistema bajo prueba con el proveedor mockeado.

Cubren las tres piezas que la evaluación necesita que sean fiables: que el
enrutador marque su fallback en vez de disfrazarlo de clasificación, que el
umbral de distancia produzca un rechazo explícito, y que la política del prompt
sea realmente conmutable (si no lo fuera, comparar `base` contra `hardened`
mediría dos veces lo mismo).
"""
from src.agent import SYSTEM_GEN_BASE, SYSTEM_GEN_HARDENED, Sistema, system_generador
from src.retriever import Recuperado
from src.router import enrutar
from src.schema import Categoria

# --- Enrutador ---

def test_enrutador_parsea_json_limpio(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "vacaciones", "confianza": 0.95}'])
    ruta = enrutar(cfg, chat, "¿cuántos días de vacaciones tengo?")
    assert ruta.categoria is Categoria.rrhh
    assert ruta.confianza == 0.95
    assert ruta.fallback is False


def test_enrutador_tolera_fences_de_markdown(cfg, chat_falso):
    chat = chat_falso(['```json\n{"categoria": "marca", "justificacion": "x", "confianza": 0.8}\n```'])
    ruta = enrutar(cfg, chat, "¿color corporativo?")
    assert ruta.categoria is Categoria.marca
    assert ruta.fallback is False


def test_enrutador_marca_el_fallback_ante_json_roto(cfg, chat_falso):
    """El fallo de parseo debe quedar registrado, no absorbido como 'otro'."""
    chat = chat_falso(["lo siento, no puedo clasificar eso"])
    ruta = enrutar(cfg, chat, "consulta")
    assert ruta.categoria is Categoria.otro
    assert ruta.confianza == 0.0
    assert ruta.fallback is True


def test_enrutador_marca_el_fallback_ante_categoria_invalida(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "legal", "justificacion": "x", "confianza": 0.9}'])
    ruta = enrutar(cfg, chat, "consulta")
    assert ruta.categoria is Categoria.otro
    assert ruta.fallback is True


def test_otro_legitimo_no_se_confunde_con_fallback(cfg, chat_falso):
    """Distinguir 'no encaja' de 'me rompí' es el motivo de existir del flag."""
    chat = chat_falso(['{"categoria": "otro", "justificacion": "ajena", "confianza": 0.9}'])
    ruta = enrutar(cfg, chat, "¿qué tiempo hace?")
    assert ruta.categoria is Categoria.otro
    assert ruta.fallback is False


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
    def __init__(self, fragmentos):
        self.fragmentos = fragmentos
        self.consultas = []

    def recuperar(self, consulta, fuente):
        self.consultas.append((consulta, fuente))
        return self.fragmentos


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
    assert system_gen == SYSTEM_GEN_BASE
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
