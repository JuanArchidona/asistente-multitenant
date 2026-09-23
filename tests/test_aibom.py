"""El AIBOM se genera, y la suite falla si lo que hay en `docs/` no es lo que
sale de los ficheros del repositorio. Es lo que convierte un inventario en
un dato en vez de en una lista que fue verdad el dia que se escribio."""
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _modulo():
    spec = importlib.util.spec_from_file_location("generar_aibom", RAIZ / "scripts" / "generar_aibom.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_el_aibom_de_docs_es_el_que_sale_del_repositorio():
    mod = _modulo()
    bom = mod.construir()
    assert (RAIZ / "docs" / "AIBOM.md").read_text(encoding="utf-8") == mod.markdown(bom)
    assert json.loads((RAIZ / "docs" / "aibom.json").read_text(encoding="utf-8")) == bom


def test_todo_paquete_tiene_version_y_origen():
    bom = _modulo().construir()
    libs = [c for c in bom["components"] if c["type"] == "library"]
    assert len(libs) > 50
    for c in libs:
        assert c["version"], c["name"]
        assert c["source"].startswith("https://"), c


def test_los_modelos_sin_precio_son_exactamente_los_conocidos():
    """Un modelo sin precio costaba cero en silencio (HALLAZGOS.md §28). El
    inventario es el sitio donde eso se ve antes de que cueste una ejecucion.

    Hoy hay UNO sin precio, y se afirma en vez de esconderse: el modelo de
    embeddings, cuyo coste no contabiliza nadie y cuyo precio ya no aparece en
    la pagina de precios del proveedor (HALLAZGOS.md §35). Si aparece otro, o
    si este deja de estarlo, la lista cambia y esta prueba lo dice."""
    bom = _modulo().construir()
    modelos = [c for c in bom["components"] if c["type"] == "machine-learning-model"]
    assert len(modelos) >= 4
    sin_precio = sorted(m["name"] for m in modelos if not m["price_usd_per_mtok"])
    assert sin_precio == ["gemini-embedding-001"], sin_precio


def test_los_modelos_cubren_los_cuatro_roles():
    bom = _modulo().construir()
    roles = {r for c in bom["components"] if c["type"] == "machine-learning-model" for r in c["roles"]}
    for necesario in ("ANTHROPIC_MODEL_ROUTER", "GEMINI_EMBED_MODEL", "JUDGE_MODEL", "BUILDER_MODEL"):
        assert necesario in roles, necesario


def test_cada_servidor_mcp_de_los_manifiestos_esta_en_el_inventario():
    bom = _modulo().construir()
    mcp = {c["name"] for c in bom["components"] if c.get("protocol") == "mcp"}
    for ruta in (RAIZ / "tenants").glob("*.json"):
        manifiesto = json.loads(ruta.read_text(encoding="utf-8"))
        for s in manifiesto.get("servidores_mcp", []):
            assert f"{manifiesto['id']}/{s['nombre']}" in mcp
    assert "puente/servidor.mjs" in mcp


def test_el_inventario_dice_que_node_no_esta_fijado():
    """Lo que no esta fijado se declara, no se esconde."""
    md = (RAIZ / "docs" / "AIBOM.md").read_text(encoding="utf-8")
    assert "sin fijar en el repositorio" in md.lower()
