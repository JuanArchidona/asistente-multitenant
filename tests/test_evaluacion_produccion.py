"""Evaluación de la calidad en producción (src/evaluacion_produccion.py, B4).

Lo que importa no es que el juez acierte, que eso no se puede probar sin
llamarlo, sino tres propiedades del diseño: que el verificador determinista
corre sobre todas las respuestas, que el juez solo deja veredicto y coste y
nunca texto, y que un juez sin clave se ve en cada línea en vez de pasar por
"no le tocó".
"""
import random

from src.agent import Sistema
from src.evaluacion_produccion import (
    JuezProduccion,
    calidad_determinista,
    juez_desde_config,
    lanzar,
)
from src.observabilidad import CLAVE_EVALUACION, Registro, leer, resumir
from src.provider import ChatProvider
from src.retriever import Recuperacion, Recuperado

RESPUESTA_CON_SECRETO = "El salario es 41.000 EUR (convenio_colectivo.md)."


class _ChatJuez(ChatProvider):
    def __init__(self, salida: str):
        super().__init__()
        self.salida = salida
        self.recibido: list[str] = []

    def completar(self, system, user, model, max_tokens=1024, temperature=None):
        self.recibido.append(user)
        self.uso.registrar(model, 100, 5)
        return self.salida


class _RetrieverFalso:
    def recuperar_con_control(self, consulta, fuente, usuario=None):
        return Recuperacion([Recuperado("texto del convenio", "rrhh", "convenio_colectivo.md", 0.2)], [])


def _traza(respuesta: str, archivos=("convenio_colectivo.md",)) -> dict:
    return {
        "consulta": "¿salario?",
        "respuesta": respuesta,
        "fuentes_usadas": [{"archivo": a} for a in archivos],
        "contexto_recuperado": ["texto del convenio"] if archivos else [],
    }


def _juez(salida: str, fraccion: float = 1.0) -> JuezProduccion:
    return JuezProduccion(chat=_ChatJuez(salida), modelo="juez-falso", fraccion=fraccion,
                          azar=random.Random(0))


# --- Determinista, sobre todas ---------------------------------------------


def test_una_cita_a_un_documento_no_recuperado_cuenta_como_inventada():
    c = calidad_determinista(_traza("Según convenio_colectivo.md y anexo_secreto.md, sí."))
    assert c == {"citas_fichero": 2, "citas_inventadas": 1, "cita_alguna_fuente": True}


def test_sin_nada_recuperado_no_hay_citas_que_juzgar():
    assert calidad_determinista(_traza("No tengo esa información.", archivos=())) is None


# --- El juez -----------------------------------------------------------------


def test_el_juez_da_un_veredicto_de_tres_valores_y_lo_demas_es_ilegible():
    assert _juez('{"veredicto": "no_fiel"}').juzgar(_traza("x"))["veredicto"] == "no_fiel"
    assert _juez('```json\n{"veredicto": "fiel"}\n```').juzgar(_traza("x"))["veredicto"] == "fiel"
    assert _juez("0.8").juzgar(_traza("x"))["veredicto"] == "ilegible"
    assert _juez('{"veredicto": "excelente"}').juzgar(_traza("x"))["veredicto"] == "ilegible"


def test_sin_contexto_el_juez_no_se_llama():
    juez = _juez('{"veredicto": "fiel"}')
    assert juez.juzgar(_traza("x", archivos=()))["veredicto"] == "no_aplica"
    assert juez.chat.recibido == []


def test_el_juez_lleva_su_coste_aparte_del_sistema():
    resultado = _juez('{"veredicto": "fiel"}').juzgar(_traza("x"))
    assert resultado["tokens_entrada"] == 100
    assert "coste_usd" in resultado


def test_estado_del_juez(cfg, monkeypatch):
    monkeypatch.delenv("EVAL_PRODUCCION_FRACCION", raising=False)
    assert juez_desde_config(cfg).estado() == "apagado"
    monkeypatch.setenv("EVAL_PRODUCCION_FRACCION", "0.5")
    from dataclasses import replace

    assert juez_desde_config(replace(cfg, judge_gemini_api_key="")).estado() == "sin_clave"
    con_clave = juez_desde_config(replace(cfg, judge_gemini_api_key="k"), chat_factory=lambda c: _ChatJuez(""))
    assert con_clave.estado() == "activo"


def test_la_fraccion_se_respeta_con_semilla():
    juez = _juez("", fraccion=0.3)
    tiradas = [juez.toca() for _ in range(2000)]
    assert 0.25 < sum(tiradas) / len(tiradas) < 0.35


# --- Lo que queda en el registro ------------------------------------------


def test_la_linea_del_juez_no_lleva_texto_de_la_respuesta(tmp_path):
    registro = Registro("t", raiz=tmp_path)
    juez = _juez('{"veredicto": "parcial", "razon": "dice 41.000 EUR"}')
    lanzar(juez, _traza(RESPUESTA_CON_SECRETO), registro, "abc123").join(timeout=5)
    linea = leer("t", tmp_path)[0]
    assert linea[CLAVE_EVALUACION] == "juez"
    assert linea["id_consulta"] == "abc123"
    assert linea["veredicto"] == "parcial"
    assert "41.000" not in str(linea)


def test_un_juez_que_revienta_no_tumba_nada_y_queda_escrito(tmp_path):
    class _Roto(_ChatJuez):
        def completar(self, *a, **k):
            raise TimeoutError("sin respuesta")

    registro = Registro("t", raiz=tmp_path)
    juez = JuezProduccion(chat=_Roto(""), modelo="m", fraccion=1.0, azar=random.Random(0))
    lanzar(juez, _traza("x"), registro, "id1").join(timeout=5)
    assert leer("t", tmp_path)[0]["veredicto"] == "error"


def test_produccion_marca_cada_consulta_y_juzga_la_muestra(cfg, chat_falso, tmp_path):
    chat = chat_falso(['{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}',
                       RESPUESTA_CON_SECRETO])
    registro = Registro(cfg.tenant.id, raiz=tmp_path)
    juez = _juez('{"veredicto": "fiel"}', fraccion=1.0)
    sistema = Sistema(cfg, chat=chat, registro=registro, juez_produccion=juez)
    sistema._retriever = _RetrieverFalso()

    traza = sistema.responder("¿salario?")
    for hilo in __import__("threading").enumerate():
        if hilo.name.startswith("juez-"):
            hilo.join(timeout=5)

    lineas = leer(cfg.tenant.id, tmp_path)
    consulta = next(r for r in lineas if CLAVE_EVALUACION not in r)
    evaluacion = next(r for r in lineas if CLAVE_EVALUACION in r)
    assert consulta["calidad"]["juez"] == "muestreada"
    assert consulta["calidad"]["citas_inventadas"] == 0
    assert evaluacion["id_consulta"] == consulta["id_consulta"] == traza["id_consulta"]
    assert "respuesta" not in consulta and "41.000" not in str(evaluacion)

    resumen = resumir(lineas)
    assert resumen["consultas"] == 1
    assert resumen["calidad"]["juzgadas"] == 1
    assert resumen["calidad"]["veredictos"] == {"fiel": 1}
    assert resumen["calidad"]["tasa_no_fiel"] == 0.0


def test_sin_clave_cada_linea_lo_dice(cfg, chat_falso, tmp_path):
    chat = chat_falso(['{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "23 días."])
    juez = JuezProduccion(chat=None, modelo="m", fraccion=0.5, azar=random.Random(0))
    sistema = Sistema(cfg, chat=chat, registro=Registro(cfg.tenant.id, raiz=tmp_path),
                      juez_produccion=juez)
    sistema._retriever = _RetrieverFalso()
    sistema.responder("¿vacaciones?")
    assert leer(cfg.tenant.id, tmp_path)[0]["calidad"]["juez"] == "sin_clave"


def test_el_banco_sigue_sin_juez_ni_marcas(cfg, chat_falso):
    """Sin registro, como lo crea el banco: ni id, ni calidad, ni juez."""
    chat = chat_falso(['{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "23 días."])
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = _RetrieverFalso()
    traza = sistema.responder("¿vacaciones?")
    assert sistema.juez_produccion is None
    assert "calidad" not in traza and "id_consulta" not in traza
