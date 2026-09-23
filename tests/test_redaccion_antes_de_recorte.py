"""La redacción va antes del recorte, y lo no redactable no pasa (§41).

Lo que se vio en el servicio desplegado el 23-09-2026: un resultado de 6.028
caracteres se recortó a 6.000, dejó de ser JSON, la redacción no pudo
aplicarse y el texto pasó al modelo con una marca al lado. Aquí se fija que
un campo sensible situado más allá del recorte se redacta igual, que el
recorte se aplica a lo ya redactado, y que lo que no es JSON no llega al
modelo cuando la política exige redactar.
"""
import json

from src.agent import Sistema
from src.gobernanza import MARCA_RESTRINGIDO, MARCA_RETENIDA, TEXTO_RETENIDO, Usuario
from src.mcp_cliente import MAX_CARACTERES_RESULTADO, recortar_resultado
from src.tenant import cargar_tenant

AGENCIA = cargar_tenant("agencia_inmobiliaria")
COMERCIAL = Usuario(id="comercial", nombre="Comercial", roles=[])


class MCPFalso:
    """Devuelve un resultado grande con un campo sensible al FINAL."""

    def __init__(self, bruto: str):
        self.bruto = bruto
        self.llamadas: list[tuple[str, dict, bool]] = []

    def invocar(self, nombre: str, argumentos: dict, recortar: bool = True) -> str:
        self.llamadas.append((nombre, argumentos, recortar))
        return recortar_resultado(self.bruto) if recortar else self.bruto


def _resultado_grande() -> str:
    relleno = [{"referencia": f"INM-{i:04d}", "zona": "Actur", "precio_eur": 100000 + i} for i in range(200)]
    datos = {"inmuebles": relleno, "contacto": {"telefono": "+34 600 000 000", "dni": "12345678A"}}
    bruto = json.dumps(datos, ensure_ascii=False)
    assert len(bruto) > MAX_CARACTERES_RESULTADO
    assert bruto.index('"telefono"') > MAX_CARACTERES_RESULTADO, "el campo sensible tiene que estar mas alla del recorte"
    return bruto


def _ejecutor(cfg_agencia, mcp: MCPFalso, redactados: list[str]):
    sistema = Sistema(cfg_agencia, chat=object(), usuario=COMERCIAL)
    sistema._mcp = mcp
    return sistema._ejecutor(COMERCIAL, redactados)


def test_el_agente_pide_el_resultado_entero_y_redacta_antes_de_recortar(cfg_factory):
    cfg = cfg_factory(tenant=AGENCIA)
    mcp = MCPFalso(_resultado_grande())
    redactados: list[str] = []
    salida = _ejecutor(cfg, mcp, redactados)("crm__buscar_inmuebles", {"limite": 100})
    assert mcp.llamadas[0][2] is False, "el agente tiene que pedir el resultado sin recortar"
    assert "600 000 000" not in salida
    assert "12345678A" not in salida
    assert any("telefono" in r for r in redactados) and any("dni" in r for r in redactados)
    assert MARCA_RETENIDA not in redactados


def test_el_recorte_se_aplica_a_lo_ya_redactado(cfg_factory):
    cfg = cfg_factory(tenant=AGENCIA)
    mcp = MCPFalso(_resultado_grande())
    salida = _ejecutor(cfg, mcp, [])("crm__buscar_inmuebles", {"limite": 100})
    assert salida.endswith("[...resultado recortado...]")
    assert len(salida) <= MAX_CARACTERES_RESULTADO + len("\n[...resultado recortado...]")


def test_lo_que_no_es_json_no_llega_al_modelo_con_politica_de_campos(cfg_factory):
    cfg = cfg_factory(tenant=AGENCIA)
    mcp = MCPFalso("Texto libre con DNI 12345678A")
    redactados: list[str] = []
    salida = _ejecutor(cfg, mcp, redactados)("crm__buscar_inmuebles", {})
    assert salida == TEXTO_RETENIDO
    assert redactados == [MARCA_RETENIDA]


def test_un_resultado_pequeno_se_redacta_igual_que_antes(cfg_factory):
    cfg = cfg_factory(tenant=AGENCIA)
    mcp = MCPFalso(json.dumps({"dni": "12345678A", "zona": "Actur"}))
    redactados: list[str] = []
    salida = _ejecutor(cfg, mcp, redactados)("crm__detalle", {})
    assert json.loads(salida)["dni"] == MARCA_RESTRINGIDO
    assert redactados == ["dni"]


def test_recortar_resultado_deja_pasar_lo_corto_y_marca_lo_largo():
    assert recortar_resultado("corto") == "corto"
    largo = "x" * (MAX_CARACTERES_RESULTADO + 5)
    assert recortar_resultado(largo).endswith("[...resultado recortado...]")
