"""El consumo de embeddings se contabiliza, aparte y declarado (HALLAZGOS.md §35).

Sin red: se sustituye el cliente de Gemini por uno falso que devuelve vectores
y cuenta tokens. Lo que se prueba es la contabilidad, no el modelo.
"""
from types import SimpleNamespace

from src.embeddings import CARACTERES_POR_TOKEN, GeminiEmbedder
from src.provider import PRECIOS, Uso


class _ClienteFalso:
    """Imita `client.models.embed_content` y `client.models.count_tokens`."""

    def __init__(self, dims: int = 4):
        self.dims = dims
        self.contadas = 0
        self.embebidas = 0
        self.models = self

    def embed_content(self, model, contents, config):
        self.embebidas += 1
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.0] * self.dims) for _ in contents],
            metadata=None,
        )

    def count_tokens(self, model, contents):
        self.contadas += 1
        # Un token por palabra: determinista y distinto de la estimacion.
        return SimpleNamespace(total_tokens=sum(len(t.split()) for t in contents))


def _embedder(cfg, uso, contar_exacto):
    e = GeminiEmbedder.__new__(GeminiEmbedder)
    e.client = _ClienteFalso()
    e.model = cfg.embed_model
    e.dims = 4
    e.uso = uso
    e.contar_exacto = contar_exacto
    return e


def test_sin_uso_no_se_contabiliza_y_no_se_cuenta(cfg):
    e = _embedder(cfg, uso=None, contar_exacto=True)
    e.embed_consulta("hola mundo")
    assert e.client.contadas == 0


def test_la_consulta_se_estima_por_caracteres_sin_llamada_extra(cfg):
    uso = Uso()
    e = _embedder(cfg, uso=uso, contar_exacto=False)
    texto = "¿Cuántos días de vacaciones tengo este año?"
    e.embed_consulta(texto)
    assert e.client.contadas == 0, "estimar no puede costar una llamada: moveria la latencia medida"
    m = uso.por_modelo[cfg.embed_model]
    assert m["tokens_embebidos"] == round(len(texto) / CARACTERES_POR_TOKEN)
    assert m["exactos"] is False
    assert m["llamadas"] == 1


def test_la_ingesta_cuenta_exacto_con_una_llamada_por_lote(cfg):
    uso = Uso()
    e = _embedder(cfg, uso=uso, contar_exacto=True)
    e.embed_documentos(["uno dos tres", "cuatro cinco"])
    assert e.client.contadas == 1
    m = uso.por_modelo[cfg.embed_model]
    assert m["tokens_embebidos"] == 5
    assert m["exactos"] is True


def test_una_estimacion_basta_para_que_el_total_deje_de_ser_exacto(cfg):
    uso = Uso()
    _embedder(cfg, uso, contar_exacto=True).embed_documentos(["a b"])
    _embedder(cfg, uso, contar_exacto=False).embed_consulta("consulta")
    assert uso.por_modelo[cfg.embed_model]["exactos"] is False


def test_los_embeddings_no_tocan_los_totales_de_tokens_del_chat(cfg):
    """Las cifras de coste por caso de las ejecuciones guardadas no cambian."""
    uso = Uso()
    uso.registrar("claude-haiku-4-5", 100, 20)
    _embedder(cfg, uso, contar_exacto=True).embed_documentos(["x y z"])
    assert uso.tokens_entrada == 100
    assert uso.tokens_salida == 20
    assert uso.llamadas == 1


def test_el_modelo_de_embeddings_aparece_como_sin_precio(cfg):
    """Es lo que hace visible el §35: el resumen dice que la cifra es un suelo."""
    assert cfg.embed_model not in PRECIOS
    uso = Uso()
    _embedder(cfg, uso, contar_exacto=True).embed_documentos(["x"])
    assert uso.modelos_sin_precio == [cfg.embed_model]
    assert "modelos_sin_precio" in uso.resumen()
    assert uso.coste_usd() == 0.0


def test_con_precio_los_embeddings_costarian_por_token_de_entrada(cfg, monkeypatch):
    monkeypatch.setitem(PRECIOS, cfg.embed_model, (0.20, 0.0))
    uso = Uso()
    uso.registrar_embeddings(cfg.embed_model, 1_000_000, exactos=True)
    assert uso.coste_usd() == 0.20
    assert uso.modelos_sin_precio == []


def test_el_consumo_se_atribuye_a_la_consulta_en_vuelo(cfg):
    uso = Uso()
    e = _embedder(cfg, uso, contar_exacto=False)
    with uso.por_consulta() as hijo:
        e.embed_consulta("una consulta")
    assert hijo.por_modelo[cfg.embed_model]["llamadas"] == 1
    assert uso.por_modelo[cfg.embed_model]["llamadas"] == 1


def test_un_reintento_por_cuota_no_se_cuenta_dos_veces(cfg):
    uso = Uso()
    e = _embedder(cfg, uso, contar_exacto=False)
    intentos = {"n": 0}

    def embed_content(model, contents, config):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: 0s")
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.0] * 4)], metadata=None)

    e.client.embed_content = embed_content
    e.embed_consulta("hola")
    assert intentos["n"] == 2
    assert uso.por_modelo[cfg.embed_model]["llamadas"] == 1


def test_el_registro_de_produccion_anota_los_embeddings_y_la_falta_de_precio(cfg, tmp_path):
    """Sin esto el registro diria "esta consulta costo X" con la misma seguridad
    tanto si X lo incluye todo como si no."""
    from src.observabilidad import Registro

    uso = Uso()
    uso.registrar("claude-haiku-4-5", 100, 20)
    _embedder(cfg, uso, contar_exacto=False).embed_consulta("una consulta cualquiera")
    r = Registro("t", raiz=tmp_path)
    fila = r.anotar({"consulta": "x", "tenant": "t", "usuario": "u", "respuesta": "r"}, uso.resumen())
    assert fila["tokens_embebidos"] == round(len("una consulta cualquiera") / CARACTERES_POR_TOKEN)
    assert fila["modelos_sin_precio"] == [cfg.embed_model]
    assert fila["tokens_entrada"] == 100
