"""Pruebas del enrutador por embeddings, sin llamar a ningún proveedor.

Un embedder falso devuelve vectores fijos por texto y una colección falsa
devuelve fragmentos con su fuente, así que aquí se prueba la regla de
decisión y no la calidad de los embeddings, que es lo que mide
`evals/comparar_enrutadores.py` (§48).
"""
import pytest

from src.agent import Sistema
from src.router_embeddings import (
    VARIANTES,
    EnrutadorEmbeddings,
    similitud_coseno,
)
from src.tenant import CATEGORIA_OTRO

# Vectores de juguete en tres dimensiones: cada eje es un "tema".
RRHH, DESARROLLO, MARCA = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]


class EmbedderFalso:
    def __init__(self, por_texto: dict[str, list[float]], por_defecto=(0.3, 0.3, 0.3)):
        self.por_texto = por_texto
        self.por_defecto = list(por_defecto)
        self.llamadas: list[list[str]] = []

    def _vector(self, texto: str) -> list[float]:
        for clave, v in self.por_texto.items():
            if clave in texto:
                return v
        return self.por_defecto

    def embed_documentos(self, textos):
        self.llamadas.append(textos)
        return [self._vector(t) for t in textos]

    def embed_consulta(self, texto):
        self.llamadas.append([texto])
        return self._vector(texto)


class ColeccionFalsa:
    """Devuelve siempre los mismos fragmentos, con sus fuentes y distancias."""

    def __init__(self, filas: list[tuple[str, float]]):
        self.filas = filas
        self.consultas = []

    def query(self, query_embeddings, n_results, include):
        self.consultas.append((query_embeddings, n_results))
        filas = self.filas[:n_results]
        return {
            "metadatas": [[{"fuente": f, "archivo": f"{f}.md"} for f, _ in filas]],
            "distances": [[d for _, d in filas]],
        }


def _embedder():
    # Las descripciones del manifiesto heredado contienen estas palabras.
    # `actas` tiene su propio prototipo: si quedara en el vector por defecto,
    # una consulta desconocida (también por defecto) sería idéntica a ella.
    return EmbedderFalso({"rrhh:": RRHH, "desarrollo:": DESARROLLO, "marca:": MARCA,
                          "actas:": [0.5, 0.5, 0.0],
                          "vacaciones": RRHH, "commit": DESARROLLO, "logotipo": MARCA})


# --- Descripciones ---------------------------------------------------------

def test_los_prototipos_se_calculan_una_sola_vez(cfg):
    emb = _embedder()
    enrutador = EnrutadorEmbeddings(cfg.tenant, emb)
    assert len(emb.llamadas) == 1
    assert len(enrutador.prototipos) == len(cfg.tenant.categorias)
    enrutador.enrutar("¿vacaciones?")
    enrutador.enrutar("¿logotipo?")
    assert len(emb.llamadas) == 3


def test_por_descripciones_elige_la_categoria_mas_cercana(cfg):
    enrutador = EnrutadorEmbeddings(cfg.tenant, _embedder(), umbral_otro=0.5)
    assert enrutador.enrutar("¿cuántos días de vacaciones?").categoria == "rrhh"
    assert enrutador.enrutar("¿formato del commit?").categoria == "desarrollo"
    ruta = enrutador.enrutar("¿color del logotipo?")
    assert ruta.categoria == "marca"
    assert ruta.confianza == pytest.approx(1.0)
    assert ruta.fallback is False


def test_bajo_el_umbral_va_a_otro_y_lo_dice(cfg):
    enrutador = EnrutadorEmbeddings(cfg.tenant, _embedder(), umbral_otro=0.9)
    ruta = enrutador.enrutar("¿qué tiempo hace en Zaragoza?")  # vector por defecto
    assert ruta.categoria == CATEGORIA_OTRO
    assert "bajo el umbral" in ruta.justificacion
    assert ruta.fallback is False, "un `otro` por umbral es una decisión, no un fallo"


def test_acepta_el_vector_ya_calculado(cfg):
    emb = _embedder()
    enrutador = EnrutadorEmbeddings(cfg.tenant, emb, umbral_otro=0.5)
    llamadas_antes = len(emb.llamadas)
    assert enrutador.enrutar("lo que sea", vector=DESARROLLO).categoria == "desarrollo"
    assert len(emb.llamadas) == llamadas_antes


# --- Índice ------------------------------------------------------------------

def test_por_indice_vota_por_la_fuente_mayoritaria(cfg):
    col = ColeccionFalsa([("desarrollo", 0.2), ("rrhh", 0.25), ("desarrollo", 0.3), ("marca", 0.6)])
    enrutador = EnrutadorEmbeddings(cfg.tenant, _embedder(), col, variante="indice", umbral_otro=0.5)
    ruta = enrutador.enrutar("¿vacaciones?")  # la descripción dice rrhh; el índice, desarrollo
    assert ruta.categoria == "desarrollo"
    assert "del peso" in ruta.justificacion
    assert col.consultas[0][1] == enrutador.k


def test_por_indice_va_a_otro_si_nada_esta_cerca(cfg):
    col = ColeccionFalsa([("desarrollo", 0.7), ("rrhh", 0.8)])
    enrutador = EnrutadorEmbeddings(cfg.tenant, _embedder(), col, variante="indice", umbral_otro=0.5)
    assert enrutador.enrutar("¿capital de Australia?").categoria == CATEGORIA_OTRO


def test_por_indice_ignora_fuentes_que_no_son_de_ninguna_categoria(cfg):
    col = ColeccionFalsa([("huerfana", 0.1), ("huerfana", 0.1), ("marca", 0.4)])
    enrutador = EnrutadorEmbeddings(cfg.tenant, _embedder(), col, variante="indice", umbral_otro=0.5)
    assert enrutador.enrutar("¿logotipo?").categoria == "marca"


def test_la_variante_indice_exige_coleccion(cfg):
    with pytest.raises(ValueError):
        EnrutadorEmbeddings(cfg.tenant, _embedder(), None, variante="indice")


def test_variante_desconocida_falla_al_construir(cfg):
    with pytest.raises(ValueError):
        EnrutadorEmbeddings(cfg.tenant, _embedder(), variante="magia")


def test_las_variantes_declaradas_son_las_que_acepta_config():
    from src.config import ROUTER_KINDS
    assert set(ROUTER_KINDS) == {"llm", *(f"embeddings_{v}" for v in VARIANTES)}


# --- Coseno ---------------------------------------------------------------------

def test_similitud_coseno():
    assert similitud_coseno([1, 0], [1, 0]) == pytest.approx(1.0)
    assert similitud_coseno([1, 0], [0, 1]) == pytest.approx(0.0)
    assert similitud_coseno([0, 0], [1, 0]) == 0.0


# --- Conmutación desde el agente ------------------------------------------------

class _RetrieverConEmbedder:
    def __init__(self):
        self.embedder = _embedder()
        self.col = ColeccionFalsa([("rrhh", 0.2)])

    def recuperar_con_control(self, consulta, fuente, usuario=None):
        from src.retriever import Recuperacion, Recuperado
        return Recuperacion([Recuperado("23 días", fuente, "convenio.md", 0.2)], [])


def test_con_router_kind_llm_el_enrutador_es_el_de_siempre(cfg, chat_falso):
    chat = chat_falso(['{"categoria": "rrhh", "justificacion": "x", "confianza": 0.9}', "23."])
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = _RetrieverConEmbedder()
    traza = sistema.responder("¿vacaciones?")
    assert traza["categoria"] == "rrhh"
    assert len(chat.llamadas) == 2  # enrutador + generador
    assert sistema._enrutador_embeddings is None


def test_con_router_kind_embeddings_no_se_llama_al_chat_para_enrutar(cfg_factory, chat_falso):
    cfg = cfg_factory(router_kind="embeddings_descripciones", router_umbral_otro=0.5)
    chat = chat_falso(["23 días."])  # solo el generador
    sistema = Sistema(cfg, chat=chat)
    sistema._retriever = _RetrieverConEmbedder()
    traza = sistema.responder("¿cuántos días de vacaciones?")
    assert traza["categoria"] == "rrhh"
    assert traza["fallback_enrutador"] is False
    assert "embeddings/descripciones" in traza["justificacion_enrutador"]
    assert len(chat.llamadas) == 1, "el enrutado no debe costar una llamada de chat"
    # Y el enrutador se construye una vez.
    sistema.responder("¿vacaciones otra vez?")
    assert len(sistema._retriever.embedder.llamadas) == 1 + 2, "prototipos una vez, una consulta por vez"
