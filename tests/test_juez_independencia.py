"""Pruebas de la independencia del juez y de su clave.

Dos defectos del instrumento, encontrados al ir a montar un juez de otra
familia y no al buscar fallos:

1. La exigencia de clave propia para el juez existía solo en el camino de
   Anthropic. Con `JUDGE_PROVIDER=gemini` el juez tiraba de `GEMINI_API_KEY`,
   que es la clave de los **embeddings** —parte del sistema—, así que su gasto
   se habría sumado al del sistema en la misma línea de factura. Es el fallback
   silencioso del §18 otra vez, y justo en el único camino que hace falta para
   tener un juez que no sea de la familia del generador.

2. La limitación de que juez y generador comparten familia vivía en el docstring
   de `evals/metrics/juez.py`, que es donde no sirve: estos informes están
   hechos para citarse en una memoria, y un caveat que no acompaña al número se
   pierde en cuanto alguien cita el número.
"""
import pytest

from evals.report import _seccion_independencia_juez
from evals.variantes import descripcion, familia_de, independencia_del_juez

# --- Familias ---------------------------------------------------------------

@pytest.mark.parametrize(
    ("modelo", "familia"),
    [
        ("claude-sonnet-5", "anthropic"),
        ("claude-haiku-4-5-20251001", "anthropic"),
        ("gemini-2.5-flash", "google"),
        ("gpt-5", "openai"),
        ("llama-3", "desconocida"),
        ("", "desconocida"),
    ],
)
def test_la_familia_se_deduce_del_nombre(modelo, familia):
    assert familia_de(modelo) == familia


def test_con_modelos_desconocidos_la_independencia_queda_sin_determinar(cfg_factory):
    """Si no se sabe, no se afirma ninguna de las dos cosas. Declararlos de la
    misma familia inventaría un sesgo; declararlos de distinta prometería una
    independencia que nadie ha comprobado."""
    cfg = cfg_factory(judge_model="modelo-raro-a", model_generator="modelo-raro-b")
    ind = independencia_del_juez(cfg)
    assert ind["determinada"] is False
    assert ind["misma_familia"] is False
    assert "sin determinar" in ind["tipo"]


# --- La configuración real del proyecto ------------------------------------

def test_la_configuracion_por_defecto_es_de_la_misma_familia(cfg_factory):
    """No es un fallo que haya que arreglar aquí: es la configuración con la que
    está medido todo el banco, y cambiarla invalidaría la comparación. Lo que
    este test fija es que el sistema lo **sepa** y lo diga."""
    cfg = cfg_factory(
        judge_model="claude-sonnet-5", model_generator="claude-haiku-4-5-20251001"
    )
    ind = independencia_del_juez(cfg)
    assert ind["misma_familia"] is True
    assert "solo de capacidad" in ind["tipo"]


def test_un_juez_de_gemini_sobre_un_generador_de_claude_si_es_independiente(cfg_factory):
    cfg = cfg_factory(
        judge_model="gemini-2.5-flash", model_generator="claude-haiku-4-5-20251001"
    )
    ind = independencia_del_juez(cfg)
    assert ind["misma_familia"] is False
    assert "y de familia" in ind["tipo"]


# --- La limitación viaja en el informe -------------------------------------

def _cfg_real(cfg_factory, juez="claude-sonnet-5", gen="claude-haiku-4-5-20251001"):
    return cfg_factory(judge_model=juez, model_generator=gen)


def test_la_descripcion_de_la_ejecucion_lleva_la_independencia(cfg_factory):
    """`descripcion` es lo que acaba en `resumen.json`, así que la limitación
    queda guardada con las cifras y no aparte de ellas."""
    d = descripcion(_cfg_real(cfg_factory))
    assert "independencia_del_juez" in d
    assert d["independencia_del_juez"]["misma_familia"] is True


def test_el_informe_avisa_cuando_el_juez_es_de_la_familia_del_generador(cfg_factory):
    cfg = _cfg_real(cfg_factory)
    texto = "\n".join(_seccion_independencia_juez(descripcion(cfg), con_juez=True))
    assert "Independencia solo de capacidad" in texto
    assert "se ancla en las métricas deterministas" in texto


def test_el_informe_avisa_cuando_la_familia_no_consta(cfg):
    """La fixture por defecto usa modelos de juguete, que es el caso de no
    saber. El informe tiene que decir que no consta, no concluir que hay
    independencia: afirmar la lectura favorable a partir de no saber es
    exactamente lo que este proyecto no se permite."""
    texto = "\n".join(_seccion_independencia_juez(descripcion(cfg), con_juez=True))
    assert "Sin determinar" in texto
    assert "caso peor" in texto
    assert "Independencia de capacidad y de familia" not in texto


def test_una_ejecucion_sin_juez_no_avisa_de_nada(cfg):
    """Sin juez no hay independencia que discutir, y el aviso solo haría ruido."""
    assert _seccion_independencia_juez(descripcion(cfg), con_juez=False) == []


# --- La clave propia del juez, también en Gemini ---------------------------

def _entorno_minimo(monkeypatch, **extra):
    base = {
        "ANTHROPIC_API_KEY": "clave-sistema",
        "ANTHROPIC_API_KEY_JUEZ": "clave-juez",
        "GEMINI_API_KEY": "clave-gemini",
        "TENANT_ID": "empresa_servicios",
    }
    for k in (
        "JUDGE_PROVIDER",
        "JUDGE_MODEL",
        "GEMINI_API_KEY_JUEZ",
        "ANTHROPIC_MODEL_GENERATOR",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in {**base, **extra}.items():
        monkeypatch.setenv(k, v)


def test_un_juez_de_gemini_sin_clave_propia_aborta(monkeypatch):
    from src import config as modulo

    _entorno_minimo(monkeypatch, JUDGE_PROVIDER="gemini", JUDGE_MODEL="gemini-2.5-flash")
    with pytest.raises(SystemExit, match="GEMINI_API_KEY_JUEZ"):
        modulo.load_config()


def test_un_juez_de_gemini_con_la_clave_de_los_embeddings_aborta(monkeypatch):
    """Dos variables apuntando a la misma clave aparentan una separación que el
    proveedor no puede hacer."""
    from src import config as modulo

    _entorno_minimo(
        monkeypatch,
        JUDGE_PROVIDER="gemini",
        JUDGE_MODEL="gemini-2.5-flash",
        GEMINI_API_KEY_JUEZ="clave-gemini",
    )
    with pytest.raises(SystemExit, match="la misma clave que GEMINI_API_KEY"):
        modulo.load_config()


def test_un_juez_de_gemini_con_clave_propia_arranca(monkeypatch):
    from src import config as modulo

    _entorno_minimo(
        monkeypatch,
        JUDGE_PROVIDER="gemini",
        JUDGE_MODEL="gemini-2.5-flash",
        GEMINI_API_KEY_JUEZ="clave-gemini-juez",
    )
    cfg = modulo.load_config()
    assert cfg.judge_gemini_api_key == "clave-gemini-juez"
    assert cfg.judge_gemini_api_key != cfg.gemini_api_key


def test_el_camino_de_anthropic_sigue_sin_exigir_clave_de_gemini(monkeypatch):
    """La exigencia de clave de Gemini no puede alcanzar al juez de Anthropic.

    Desde el 22-09-2026 hay que pedirlo explícitamente, porque el juez por
    defecto pasó a ser Gemini. Sigue importando: es la configuración con la que
    están medidas las 15 ejecuciones anteriores, así que tiene que seguir
    arrancando para poder reproducirlas.
    """
    from src import config as modulo

    _entorno_minimo(
        monkeypatch, JUDGE_PROVIDER="anthropic", JUDGE_MODEL="claude-sonnet-5"
    )
    cfg = modulo.load_config()
    assert cfg.judge_provider == "anthropic"
    assert cfg.judge_gemini_api_key == ""
