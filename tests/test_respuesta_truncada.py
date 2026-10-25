"""Una respuesta cortada por el límite de salida se marca y se avisa.

La corrección simulada del 25-10 (E-0022) vio en el servicio desplegado una
lista de cartera que terminaba a media línea ("INM-2026-129 Piso Universidad
90 3") sin ninguna señal: el proveedor paraba en `max_tokens` y el sistema la
entregaba como si estuviera entera. Es el fallback silencioso que la regla del
proyecto prohíbe. El límite no se toca (es la línea base); lo que cambia es que
el corte deja de ser invisible, en la traza, en el registro y en la respuesta.
"""
import threading
from types import SimpleNamespace

from src.acceso import gasto_registrado_usd
from src.agent import AVISO_RESPUESTA_TRUNCADA, Sistema
from src.observabilidad import Registro
from src.provider import AnthropicChat, ChatProvider, GeminiChat
from src.retriever import Recuperacion, Recuperado

RUTA_RRHH = '{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}'


def _chat_que_corta(base, respuestas, cortar):
    """El chat falso de siempre, marcando como cortadas las llamadas indicadas."""

    class ChatQueCorta(base):
        def completar(self, system, user, model, temperature=None):
            n = len(self.llamadas)
            texto = super().completar(system, user, model, temperature)
            self._hilo.cortada = n in cortar
            return texto

    return ChatQueCorta(respuestas)


class _Retriever:
    def __init__(self, fragmentos):
        self.fragmentos = fragmentos

    def recuperar_con_control(self, consulta, fuente, usuario=None):
        return Recuperacion(self.fragmentos, [])


def _sistema(cfg, chat, fragmentos):
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = _Retriever(fragmentos)
    return sistema


FRAGMENTO = Recuperado("23 días laborables", "rrhh", "convenio_colectivo.md", 0.15)


# --- El agente ---

def test_una_generacion_cortada_se_marca_y_se_avisa(cfg, chat_falso):
    chat = _chat_que_corta(chat_falso, [RUTA_RRHH, "Son 23 días y además"], cortar={1})
    traza = _sistema(cfg, chat, [FRAGMENTO]).responder("¿vacaciones?")
    assert traza["respuesta_truncada"] is True
    assert traza["respuesta"] == "Son 23 días y además" + AVISO_RESPUESTA_TRUNCADA


def test_una_generacion_entera_no_lleva_aviso(cfg, chat_falso):
    chat = _chat_que_corta(chat_falso, [RUTA_RRHH, "Son 23 días."], cortar=set())
    traza = _sistema(cfg, chat, [FRAGMENTO]).responder("¿vacaciones?")
    assert traza["respuesta_truncada"] is False
    assert traza["respuesta"] == "Son 23 días."


def test_sin_generador_no_hereda_la_marca_del_enrutador(cfg, chat_falso):
    """La marca del proveedor es la de la última llamada del hilo. Si la
    recuperación sale vacía no se llama al generador, y la última sería la del
    enrutador: el camino documental la pone a False explícitamente."""
    chat = _chat_que_corta(chat_falso, [RUTA_RRHH], cortar={0})
    traza = _sistema(cfg, chat, []).responder("¿vacaciones?")
    assert traza["respuesta_truncada"] is False


def test_la_rama_de_herramientas_lee_la_marca_de_su_traza(cfg):
    class ChatConHerramientas(ChatProvider):
        def completar(self, system, user, model, temperature=None):
            return '{"categoria": "cartera", "justificacion": "x", "confianza": 0.9}'

        def completar_con_herramientas(self, system, user, model, herramientas, ejecutar, **_):
            return "INM-2026-129 Piso Universidad 90 3", [
                {"vuelta": 1, "herramienta": "crm__buscar", "argumentos": {}, "error": False},
                {"respuesta_truncada": True, "max_tokens": 1024},
            ]

    sistema = Sistema(cfg, chat=ChatConHerramientas())
    sistema._mcp = SimpleNamespace(esquemas_anthropic=lambda: [{"name": "crm__buscar"}])
    traza = sistema._responder_con_datos("¿cartera?", 0.0, sistema.usuario)
    assert traza["respuesta_truncada"] is True
    assert traza["fuentes_usadas"] == [{"archivo": "crm__buscar", "distancia": 0.0}]


def test_el_registro_de_produccion_guarda_la_marca(tmp_path):
    registro = Registro("t", raiz=tmp_path)
    linea = registro.componer({"respuesta": "x", "respuesta_truncada": True}, {})
    assert linea["respuesta_truncada"] is True
    assert registro.componer({"respuesta": "x"}, {})["respuesta_truncada"] is False


# --- Los proveedores ---

def _respuesta_anthropic(stop_reason, texto="hola"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=1, output_tokens=2),
        content=[SimpleNamespace(type="text", text=texto)],
    )


def _anthropic(respuesta):
    chat = AnthropicChat.__new__(AnthropicChat)
    ChatProvider.__init__(chat)
    chat.client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: respuesta))
    return chat


def test_anthropic_marca_el_corte_en_completar():
    chat = _anthropic(_respuesta_anthropic("max_tokens"))
    chat.completar("s", "u", "claude-haiku-4-5")
    assert chat.ultima_cortada() is True
    chat.client.messages.create = lambda **_: _respuesta_anthropic("end_turn")
    chat.completar("s", "u", "claude-haiku-4-5")
    assert chat.ultima_cortada() is False


def test_anthropic_marca_el_corte_en_la_traza_de_herramientas():
    chat = _anthropic(_respuesta_anthropic("max_tokens"))
    _, traza = chat.completar_con_herramientas("s", "u", "claude-haiku-4-5", [], lambda *_: "")
    assert traza == [{"respuesta_truncada": True, "max_tokens": 1024}]
    chat.client.messages.create = lambda **_: _respuesta_anthropic("end_turn")
    assert chat.completar_con_herramientas("s", "u", "claude-haiku-4-5", [], lambda *_: "")[1] == []


def test_gemini_marca_el_corte_por_su_motivo_de_parada():
    chat = GeminiChat.__new__(GeminiChat)
    ChatProvider.__init__(chat)

    def respuesta(motivo):
        return SimpleNamespace(
            text="hola",
            usage_metadata=None,
            candidates=[SimpleNamespace(finish_reason=motivo)],
        )

    chat.client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **_: respuesta("FinishReason.MAX_TOKENS")
    ))
    chat.completar("s", "u", "gemini-3.6-flash")
    assert chat.ultima_cortada() is True
    chat.client.models.generate_content = lambda **_: respuesta("FinishReason.STOP")
    chat.completar("s", "u", "gemini-3.6-flash")
    assert chat.ultima_cortada() is False


def test_la_marca_es_de_cada_hilo():
    """El sistema se comparte entre consultas concurrentes (§53): un corte en
    una no puede aparecer en la de al lado."""
    chat = _anthropic(_respuesta_anthropic("max_tokens"))
    chat.completar("s", "u", "claude-haiku-4-5")
    visto = []
    hilo = threading.Thread(target=lambda: visto.append(chat.ultima_cortada()))
    hilo.start()
    hilo.join()
    assert chat.ultima_cortada() is True and visto == [False]


# --- El tope blando lee lo que sobrevive a un reinicio ---

def test_el_tope_lee_el_almacen_persistente_si_lo_hay(tmp_path, monkeypatch):
    """El tope sumaba el fichero del disco efímero y volvía a cero en cada
    despertar del servicio, aunque el registro ya persistiera en Postgres."""
    from src.observabilidad import almacen_del_entorno

    monkeypatch.setenv("REGISTRO_DB_URL", f"sqlite:///{tmp_path / 'r.db'}")
    escrito = Registro("t", raiz=tmp_path / "antes", almacen=almacen_del_entorno())
    escrito.anotar({"consulta": "x", "tenant": "t", "usuario": "u", "respuesta": ""},
                   {"coste_usd_estimado": 0.25})

    despertado = tmp_path / "despues"  # disco vacío, como tras un reinicio
    assert gasto_registrado_usd(despertado) == 0.25
    assert gasto_registrado_usd(despertado, almacen=None) == 0.0
