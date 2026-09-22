"""Pruebas de que la conmutacion de proveedor es un hecho y no una forma.

`docs/ALCANCE.md` y la memoria apoyan una parte de la justificacion tecnica en
que el proveedor es una abstraccion conmutable. Lo era en la forma —dos clases
con la misma interfaz— y no en el hecho: `Config.gemini_model` se declaraba y
**no se consultaba en ningun sitio**, asi que con `LLM_PROVIDER=gemini` el
sistema llamaba a Gemini pasandole nombres de modelo de Anthropic.

No lo tapaba un fallo del codigo, lo tapaba que nadie lo ejecutase. Estas
pruebas lo ejecutan sin llamar a ninguna API, que es lo que las hace correr en
CI: lo que se comprueba es que el modelo que se le pasa al cliente sea del
proveedor que se ha elegido.
"""
import pytest

from src.config import load_config


def _entorno(monkeypatch, **extra):
    base = {
        "ANTHROPIC_API_KEY": "clave-sistema",
        "ANTHROPIC_API_KEY_JUEZ": "clave-juez",
        "GEMINI_API_KEY": "clave-gemini",
        # Obligatoria desde que el juez por defecto es Gemini (22-09-2026).
        "GEMINI_API_KEY_JUEZ": "clave-gemini-juez",
        "TENANT_ID": "empresa_servicios",
        # Juez explicito de Anthropic. Desde el 22-09-2026 el juez por defecto
        # es Gemini, y con `LLM_PROVIDER=gemini` los dos caerian en el mismo
        # modelo: `Config` lo rechaza, y con razon. Estas pruebas van del
        # sistema, no del juez, asi que se le saca del medio a proposito. La
        # colision tiene su propia prueba mas abajo.
        "JUDGE_PROVIDER": "anthropic",
        "JUDGE_MODEL": "claude-sonnet-5",
    }
    for k in (
        "LLM_PROVIDER",
        "GEMINI_MODEL",
        "GEMINI_MODEL_ROUTER",
        "GEMINI_MODEL_GENERATOR",
        "ANTHROPIC_MODEL_ROUTER",
        "ANTHROPIC_MODEL_GENERATOR",
        "JUDGE_PROVIDER",
        "JUDGE_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in {**base, **extra}.items():
        monkeypatch.setenv(k, v)


def test_con_anthropic_los_modelos_son_de_anthropic(monkeypatch):
    _entorno(monkeypatch)
    cfg = load_config()
    assert cfg.provider == "anthropic"
    assert cfg.model_router.startswith("claude")
    assert cfg.model_generator.startswith("claude")


def test_con_gemini_los_modelos_son_de_gemini(monkeypatch):
    """El fallo que esta prueba fija: aqui salian nombres `claude-*`, y la
    llamada moria con un 404 del lado de Google."""
    _entorno(monkeypatch, LLM_PROVIDER="gemini")
    cfg = load_config()
    assert cfg.provider == "gemini"
    assert cfg.model_router.startswith("gemini")
    assert cfg.model_generator.startswith("gemini")


def test_el_modelo_por_defecto_de_gemini_es_uno_que_un_proyecto_nuevo_puede_usar(
    monkeypatch,
):
    """`gemini-2.5-flash` devuelve 404 'no longer available to new users' en
    cualquier proyecto de Google creado despues de su retirada. Dejarlo por
    defecto hacia irreproducible la conmutacion para quien clonase el repo, que
    es publico y acompana a una defensa."""
    _entorno(monkeypatch, LLM_PROVIDER="gemini")
    cfg = load_config()
    assert not cfg.model_router.startswith("gemini-2.5")


def test_se_puede_fijar_un_modelo_distinto_para_enrutador_y_generador(monkeypatch):
    """El enrutador puede ser mas pequeno que el generador, que es justo el
    patron que el proyecto usa con Anthropic."""
    _entorno(
        monkeypatch,
        LLM_PROVIDER="gemini",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_MODEL_ROUTER="gemini-3.1-flash-lite",
    )
    cfg = load_config()
    assert cfg.model_router == "gemini-3.1-flash-lite"
    assert cfg.model_generator == "gemini-3.6-flash"


def test_todo_modelo_por_defecto_tiene_precio(monkeypatch):
    """Sin precio, el coste de una ejecucion sale mas bajo de lo que es. Desde
    el §28 eso se declara en vez de valer cero, pero un modelo que el proyecto
    usa por defecto no deberia llegar a declararse: es un precio que falta."""
    from src.provider import PRECIOS

    for proveedor in ("anthropic", "gemini"):
        _entorno(monkeypatch, LLM_PROVIDER=proveedor)
        cfg = load_config()
        assert cfg.model_router in PRECIOS, f"{cfg.model_router} sin precio"
        assert cfg.model_generator in PRECIOS, f"{cfg.model_generator} sin precio"


def test_el_juez_por_defecto_tambien_tiene_precio(monkeypatch):
    from src.provider import PRECIOS

    _entorno(monkeypatch)
    assert load_config().judge_model in PRECIOS


def test_el_sistema_y_el_juez_en_gemini_colisionan_y_se_rechaza(monkeypatch):
    """Consecuencia real del cambio de defecto del 22-09-2026.

    El juez por defecto pasa a ser `gemini-3.6-flash` y el modelo de chat por
    defecto de Gemini es el mismo, asi que `LLM_PROVIDER=gemini` sin tocar nada
    mas deja al juez evaluando su propio texto. `Config` lo rechaza en el
    arranque, que es lo correcto: un modelo que se juzga a si mismo se aprueba.

    Se fija como prueba porque es la primera piedra con la que va a tropezar
    quien conmute el proveedor para el capitulo de comparativa, y el mensaje de
    error tiene que decirle que cambie el juez.
    """
    _entorno(monkeypatch, LLM_PROVIDER="gemini")
    monkeypatch.delenv("JUDGE_PROVIDER", raising=False)
    monkeypatch.delenv("JUDGE_MODEL", raising=False)

    with pytest.raises(SystemExit, match="JUDGE_MODEL"):
        load_config()


def test_los_defectos_del_juez_son_los_decididos_el_22_09(monkeypatch):
    """Los defectos son una decision de linea base, no un descuido.

    Gemini es el unico juez con independencia de familia respecto al generador
    (HALLAZGOS.md 24) y cuesta 5,5 veces menos por evaluacion (32), lo que hace
    asequible repetirlo. Lo que NO compra es estabilidad: el 32 y el 33 midieron
    que ni la temperatura ni la mayoria de tres la resuelven.
    """
    _entorno(monkeypatch)
    monkeypatch.delenv("JUDGE_PROVIDER", raising=False)
    monkeypatch.delenv("JUDGE_MODEL", raising=False)

    cfg = load_config()
    assert cfg.judge_provider == "gemini"
    assert cfg.judge_model == "gemini-3.6-flash"
    # Y sigue sin poder ser el modelo del generador.
    assert cfg.judge_model != cfg.model_generator


def test_la_temperatura_del_enrutador_es_cero_por_defecto(monkeypatch):
    """La otra decision de linea base del 22-09-2026 (HALLAZGOS.md 27)."""
    _entorno(monkeypatch)
    monkeypatch.delenv("ROUTER_TEMPERATURE", raising=False)

    assert load_config().router_temperature == 0.0


def test_se_puede_volver_a_no_enviar_temperatura(monkeypatch):
    """La escotilla no es adorno: es lo unico que permite reproducir una cifra
    de las 15 ejecuciones anteriores al cambio, que corrieron sin enviar el
    parametro. Sin ella, esas cifras dejarian de ser reproducibles."""
    _entorno(monkeypatch, ROUTER_TEMPERATURE="defecto")
    assert load_config().router_temperature is None

    _entorno(monkeypatch, ROUTER_TEMPERATURE="none")
    assert load_config().router_temperature is None


def test_una_temperatura_que_no_es_un_numero_falla_en_el_arranque(monkeypatch):
    """Un valor mal escrito no puede caer en silencio al valor por defecto: se
    leeria como que la configuracion se aplico."""
    _entorno(monkeypatch, ROUTER_TEMPERATURE="cero")
    with pytest.raises(SystemExit, match="ROUTER_TEMPERATURE"):
        load_config()


def test_la_rama_estructurada_falla_ruidosamente_sin_tool_calling():
    """Gemini no implementa tool-calling en este proyecto. Que lo diga en vez de
    devolver vacio es la diferencia entre 'el CRM no esta disponible' y 'no
    tengo ese dato'."""
    from src.provider import ChatProvider

    with pytest.raises(NotImplementedError, match="no implementa tool-calling"):
        ChatProvider().completar_con_herramientas("s", "u", "m", [], lambda *_: "")
