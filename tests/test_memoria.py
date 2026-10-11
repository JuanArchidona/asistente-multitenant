"""Memoria entre turnos por reescritura (src/memoria.py, PLAN_ENTREGA C3).

Lo que importa: apagada no cambia nada (la línea base), encendida reescribe
solo cuando hay historial, y la traza dice qué se buscó de verdad.
"""
from src.agent import Sistema
from src.memoria import SYSTEM_REESCRITURA, contexto_de_historial, reescribir
from src.retriever import Recuperacion, Recuperado

ENRUTADO = '{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}'


class _RetrieverFalso:
    def recuperar_con_control(self, consulta, fuente, usuario=None):
        return Recuperacion([Recuperado("texto", "rrhh", "convenio_colectivo.md", 0.2)], [])


def test_sin_historial_la_consulta_no_se_toca(chat_falso):
    chat = chat_falso(["no debería llamarse"])
    assert reescribir(chat, "m", [], "¿Y la baja?") == "¿Y la baja?"
    assert chat.llamadas == []


def test_la_reescritura_usa_el_historial_y_limpia_comillas(chat_falso):
    chat = chat_falso(['"¿Qué plazo hay para comunicar la baja de un trabajador?"'])
    salida = reescribir(chat, "m", [("¿Plazo del alta?", "60 días naturales.")], "¿Y la baja?")
    assert salida == "¿Qué plazo hay para comunicar la baja de un trabajador?"
    system, usuario, _ = chat.llamadas[0]
    assert system == SYSTEM_REESCRITURA
    assert "¿Plazo del alta?" in usuario and "¿Y la baja?" in usuario
    assert chat.temperaturas == [0.0]


def test_el_historial_se_recorta_a_los_ultimos_turnos():
    historial = [(f"p{i}", "r" * 2000) for i in range(5)]
    texto = contexto_de_historial(historial)
    assert "p0" not in texto and "p4" in texto
    assert len(texto) < 1500


def test_apagada_el_sistema_ignora_el_historial(cfg, chat_falso):
    chat = chat_falso([ENRUTADO, "23 días."])
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = _RetrieverFalso()
    traza = sistema.responder("¿Y si no los gasto?", historial=[("¿Vacaciones?", "23 días.")])
    assert len(chat.llamadas) == 2  # enrutador y generador, sin reescritura
    assert "consulta_reescrita" not in traza


def test_encendida_enruta_la_consulta_reescrita(cfg_factory, chat_falso):
    chat = chat_falso(["¿Qué pasa con las vacaciones no disfrutadas?", ENRUTADO, "Hasta 5 días."])
    sistema = Sistema(cfg_factory(memoria_turnos="reescritura"), chat=chat)
    sistema._retriever = _RetrieverFalso()
    traza = sistema.responder("¿Y si no los gasto?", historial=[("¿Vacaciones?", "23 días.")])
    assert chat.llamadas[1][1] == "¿Qué pasa con las vacaciones no disfrutadas?"  # lo que recibe el enrutador
    assert traza["consulta_original"] == "¿Y si no los gasto?"
    assert traza["consulta_reescrita"] == "¿Qué pasa con las vacaciones no disfrutadas?"
    assert traza["latencia_reescritura_s"] >= 0


def test_encendida_sin_historial_no_reescribe(cfg_factory, chat_falso):
    chat = chat_falso([ENRUTADO, "23 días."])
    sistema = Sistema(cfg_factory(memoria_turnos="reescritura"), chat=chat)
    sistema._retriever = _RetrieverFalso()
    traza = sistema.responder("¿Cuántos días de vacaciones tengo?")
    assert len(chat.llamadas) == 2
    assert "consulta_reescrita" not in traza
