"""Pruebas del canal de WhatsApp, sin red y sin modelo.

Lo que se prueba es lo que decide la arquitectura del canal: que el número
es la credencial y fija el inquilino, que un desconocido no llega al modelo,
que el aviso del artículo 50 va en la primera conversación y no en cada
mensaje, que la aprobación por texto pasa por el mismo `aprobar` de siempre,
que un reintento del webhook no produce dos respuestas, y que el teléfono no
aparece en ningún sitio más que en el destinatario.
"""
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]

from src.canal_whatsapp import (
    MAX_CARACTERES,
    TEXTO_NO_AUTORIZADO,
    TEXTO_SOLO_TEXTO,
    TEXTO_TOPE,
    CanalWhatsApp,
    Contacto,
    DirectorioTelefonos,
    MensajeEntrante,
    cargar_telefonos,
    extraer_mensajes,
    firma_valida,
    huella,
    normalizar_telefono,
    trocear,
)

AVISO = {"empresa_servicios": "Respuesta generada por una IA.", "agencia_inmobiliaria": "IA de Domara."}


class SistemaFalso:
    """Devuelve trazas prefijadas y registra con quién le hablan."""

    def __init__(self, tenant_id, trazas=None):
        self.tenant_id = tenant_id
        self.trazas = list(trazas or [])
        self.consultas = []
        self.aprobadas = []
        self.rechazadas = []
        self.pendientes = {"ACC-abc123"}

    def responder(self, consulta, usuario=None):
        self.consultas.append((consulta, usuario))
        if self.trazas:
            return self.trazas.pop(0)
        return {"respuesta": f"[{self.tenant_id}] respuesta a: {consulta}", "acciones_pendientes": []}

    def aprobar(self, id_accion, usuario=None):
        if id_accion not in self.pendientes:
            raise KeyError(id_accion)
        if usuario is not None and "direccion" not in usuario.roles:
            raise PermissionError("exige el rol 'direccion'")
        self.pendientes.discard(id_accion)
        self.aprobadas.append((id_accion, usuario.id))
        return {"resultado": '{"ok": true, "referencia": "VIS-901"}'}

    def rechazar(self, id_accion, usuario=None, motivo=""):
        if id_accion not in self.pendientes:
            raise KeyError(id_accion)
        self.pendientes.discard(id_accion)
        self.rechazadas.append((id_accion, usuario.id, motivo))
        return {}


def _directorio():
    return DirectorioTelefonos(numeros=[
        Contacto(telefono="34600000001", usuario="empleado", nombre="Empleado", tenant="empresa_servicios"),
        Contacto(telefono="+34 600 000 002", usuario="gerencia", tenant="agencia_inmobiliaria", roles=["direccion"]),
        Contacto(telefono="34600000003", usuario="comercial", tenant="agencia_inmobiliaria"),
    ])


def _canal(sistemas: dict, tope=(False, 0.0, 2.0), reloj=None):
    tiempos = {"t": 1000.0}

    def reloj_falso():
        return tiempos["t"]

    canal = CanalWhatsApp(
        _directorio(),
        fabrica_sistema=lambda t: sistemas[t],
        aviso_de=lambda t: AVISO[t],
        comprobar_tope=lambda: tope,
        reloj=reloj or reloj_falso,
    )
    canal._tiempos = tiempos
    return canal


def _msg(texto, telefono="34600000001", id_="wamid.1", tipo="text"):
    return MensajeEntrante(id=id_, telefono=telefono, tipo=tipo, texto=texto)


# --- Identidad: el número es la credencial ---------------------------------

def test_el_numero_fija_persona_e_inquilino():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios"),
                "agencia_inmobiliaria": SistemaFalso("agencia_inmobiliaria")}
    canal = _canal(sistemas)
    canal.procesar(_msg("¿vacaciones?", "34600000001", "a"))
    canal.procesar(_msg("¿cartera?", "34600000002", "b"))
    assert sistemas["empresa_servicios"].consultas[0][1].id == "empleado"
    persona = sistemas["agencia_inmobiliaria"].consultas[0][1]
    assert persona.id == "gerencia" and persona.roles == ["direccion"]


def test_un_numero_desconocido_no_llega_al_modelo_y_se_anota_por_huella():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios")}
    canal = _canal(sistemas)
    respuestas = canal.procesar(_msg("dame los salarios", "34699999999"))
    assert respuestas == [TEXTO_NO_AUTORIZADO]
    assert sistemas["empresa_servicios"].consultas == []
    assert canal.desconocidos[0]["huella"] == huella("34699999999")
    assert "34699999999" not in json.dumps(canal.desconocidos)


def test_el_telefono_se_normaliza_con_o_sin_prefijo_y_espacios():
    assert normalizar_telefono("+34 600 000 002") == "34600000002"
    assert _directorio().buscar("34600000002").usuario == "gerencia"
    assert _directorio().buscar("+34-600-000-002").usuario == "gerencia"


def test_la_huella_no_es_el_numero_y_es_estable():
    assert huella("+34 600 000 001") == huella("34600000001")
    assert len(huella("34600000001")) == 12
    assert "600000001" not in huella("34600000001")


# --- Artículo 50 ------------------------------------------------------------

def test_el_aviso_va_en_la_primera_conversacion_y_no_en_cada_mensaje():
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    primera = canal.procesar(_msg("hola", id_="1"))
    segunda = canal.procesar(_msg("otra", id_="2"))
    assert primera[0].startswith(f"[{AVISO['empresa_servicios']}]")
    assert AVISO["empresa_servicios"] not in segunda[0]


def test_el_aviso_se_repite_tras_un_dia_de_silencio():
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    canal.procesar(_msg("hola", id_="1"))
    canal._tiempos["t"] += 25 * 3600
    tercera = canal.procesar(_msg("¿sigues ahí?", id_="3"))
    assert tercera[0].startswith(f"[{AVISO['empresa_servicios']}]")


# --- Human-in-the-loop por texto ------------------------------------------

def test_una_escritura_propuesta_se_describe_y_pide_aprobacion():
    traza = {"respuesta": "Puedo registrar la visita.", "acciones_pendientes": [
        {"id": "ACC-abc123", "herramienta": "crm__registrar_visita", "argumentos": {"inmueble": "INM-1"}, "usuario": "gerencia"}
    ]}
    sistema = SistemaFalso("agencia_inmobiliaria", [traza])
    canal = _canal({"agencia_inmobiliaria": sistema})
    (texto,) = canal.procesar(_msg("registra una visita", "34600000002"))
    assert "NO la he ejecutado" in texto
    assert "APROBAR ACC-abc123" in texto and "RECHAZAR ACC-abc123" in texto
    assert sistema.aprobadas == []


def test_aprobar_por_texto_pasa_por_el_aprobar_de_siempre():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    (texto,) = canal.procesar(_msg("aprobar acc-ABC123", "34600000002"))
    assert sistema.aprobadas == [("ACC-abc123", "gerencia")]
    assert "aprobada por gerencia" in texto and "VIS-901" in texto
    assert sistema.consultas == [], "una orden no es una consulta: no pasa por el modelo"


def test_rechazar_por_texto():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    (texto,) = canal.procesar(_msg("RECHAZAR ACC-abc123", "34600000002"))
    assert sistema.rechazadas[0][:2] == ("ACC-abc123", "gerencia")
    assert "rechazada" in texto


def test_quien_no_tiene_el_rol_no_aprueba():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    (texto,) = canal.procesar(_msg("APROBAR ACC-abc123", "34600000003"))
    assert sistema.aprobadas == []
    assert "No puedes aprobar" in texto


def test_aprobar_algo_que_no_existe_lo_dice():
    canal = _canal({"agencia_inmobiliaria": SistemaFalso("agencia_inmobiliaria")})
    (texto,) = canal.procesar(_msg("APROBAR ACC-ffffff", "34600000002"))
    assert "No hay ninguna acción pendiente" in texto


# --- Robustez del canal ----------------------------------------------------

def test_un_reintento_del_webhook_no_produce_una_segunda_respuesta():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema})
    assert canal.procesar(_msg("hola", id_="wamid.X")) != []
    assert canal.procesar(_msg("hola", id_="wamid.X")) == []
    assert len(sistema.consultas) == 1


def test_un_mensaje_que_no_es_texto_recibe_una_frase_fija():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema})
    assert canal.procesar(_msg("", tipo="image")) == [TEXTO_SOLO_TEXTO]
    assert sistema.consultas == []


def test_con_el_tope_superado_no_se_consulta():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema}, tope=(True, 2.4, 2.0))
    (texto,) = canal.procesar(_msg("¿vacaciones?"))
    assert texto.endswith(TEXTO_TOPE)
    assert sistema.consultas == []


def test_un_fallo_del_sistema_se_dice_y_no_tumba_el_canal():
    class Revienta(SistemaFalso):
        def responder(self, consulta, usuario=None):
            raise PermissionError("401")

    canal = _canal({"empresa_servicios": Revienta("empresa_servicios")})
    (texto,) = canal.procesar(_msg("¿vacaciones?"))
    assert "no se pudo atender (PermissionError)" in texto


def test_lo_retenido_y_lo_redactado_se_dicen_sin_nombrar_documentos():
    traza = {"respuesta": "Hay documentación restringida.", "denegados_por_permiso": ["anexo_confidencial.md"],
             "campos_redactados": ["dni"], "acciones_pendientes": []}
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios", [traza])})
    (texto,) = canal.procesar(_msg("¿salarios?"))
    assert "Retenido por permiso: 1 documento" in texto
    assert "anexo_confidencial" not in texto
    assert "Campos redactados: dni" in texto


def test_el_sistema_de_cada_inquilino_se_construye_una_vez():
    creados = []

    def fabrica(t):
        creados.append(t)
        return SistemaFalso(t)

    canal = CanalWhatsApp(_directorio(), fabrica, lambda t: AVISO[t], comprobar_tope=lambda: (False, 0, 2))
    canal.procesar(_msg("a", "34600000002", "1"))
    canal.procesar(_msg("b", "34600000003", "2"))
    canal.procesar(_msg("c", "34600000001", "3"))
    assert creados == ["agencia_inmobiliaria", "empresa_servicios"]


# --- Troceado ---------------------------------------------------------------

def test_los_mensajes_largos_se_trocean_por_parrafos():
    parrafo = "x" * 3000
    trozos = trocear(f"{parrafo}\n\n{parrafo}")
    assert len(trozos) == 2 and all(len(t) <= MAX_CARACTERES for t in trozos)


def test_un_parrafo_mas_largo_que_el_maximo_se_corta_igualmente():
    trozos = trocear("y" * (MAX_CARACTERES * 2 + 10))
    assert len(trozos) == 3 and "".join(trozos) == "y" * (MAX_CARACTERES * 2 + 10)


# --- El webhook de Meta -----------------------------------------------------

PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{"id": "1", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp",
        "messages": [
            {"from": "34600000001", "id": "wamid.A", "timestamp": "1", "type": "text", "text": {"body": "¿vacaciones?"}},
            {"from": "34600000001", "id": "wamid.B", "timestamp": "2", "type": "image", "image": {"id": "9"}},
        ],
        "statuses": [{"id": "wamid.Z", "status": "delivered"}],
    }}]}],
}


def test_extraer_mensajes_del_payload_de_meta():
    mensajes = extraer_mensajes(PAYLOAD)
    assert [m.id for m in mensajes] == ["wamid.A", "wamid.B"]
    assert mensajes[0].texto == "¿vacaciones?" and mensajes[0].tipo == "text"
    assert mensajes[1].tipo == "image" and mensajes[1].texto == ""


def test_un_payload_sin_mensajes_o_malformado_da_lista_vacia():
    assert extraer_mensajes({"entry": [{"changes": [{"value": {"statuses": []}}]}]}) == []
    assert extraer_mensajes({}) == []
    assert extraer_mensajes({"entry": "basura"}) == []


def test_la_firma_del_webhook_se_verifica_con_el_secreto():
    cuerpo = json.dumps(PAYLOAD).encode()
    buena = "sha256=" + hmac.new(b"secreto", cuerpo, hashlib.sha256).hexdigest()
    assert firma_valida("secreto", cuerpo, buena)
    assert not firma_valida("otro", cuerpo, buena)
    assert not firma_valida("secreto", cuerpo + b" ", buena)
    assert not firma_valida("secreto", cuerpo, None)
    assert not firma_valida("", cuerpo, buena), "sin secreto no hay verificación posible"


# --- La lista de números ------------------------------------------------------

def test_la_lista_de_ejemplo_se_carga_y_se_marca(monkeypatch):
    monkeypatch.delenv("WHATSAPP_USUARIOS_JSON", raising=False)
    directorio = cargar_telefonos("whatsapp.example.json")
    assert directorio.es_de_ejemplo, "usar el fichero de ejemplo se marca siempre, como en la web"
    assert {c.tenant for c in directorio.numeros} == {"empresa_servicios", "agencia_inmobiliaria", "gestoria_laboral"}


def test_la_variable_de_entorno_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("WHATSAPP_USUARIOS_JSON", json.dumps({"numeros": [
        {"telefono": "34611111111", "usuario": "u", "tenant": "empresa_servicios"}
    ]}))
    assert cargar_telefonos().buscar("34611111111").usuario == "u"


def test_una_lista_invalida_falla_con_mensaje(monkeypatch):
    monkeypatch.setenv("WHATSAPP_USUARIOS_JSON", '{"numeros": []}')
    with pytest.raises(ValueError):
        cargar_telefonos()


# --- El servidor construye el índice antes que el sistema (24-09-2026) ------


def test_el_servidor_asegura_el_indice_antes_de_crear_el_sistema(monkeypatch):
    """Las dos primeras consultas reales del canal en Render terminaron en
    NotFoundError porque el disco es efímero y nadie construía el índice:
    `app.py` y el banco lo hacían, el servidor no. Aquí se fija el orden."""
    import src.canal_whatsapp_servidor as srv

    orden: list[str] = []
    cfg = SimpleNamespace(tenant=SimpleNamespace(id="empresa_servicios", ai_act=SimpleNamespace(aviso_usuario="aviso")))
    monkeypatch.setattr(srv, "load_config", lambda tenant_id, con_juez=True: cfg)
    monkeypatch.setattr(srv, "asegurar_indice", lambda c, avisar=None: orden.append("indice"))
    monkeypatch.setattr(srv, "desde_config", lambda c: None)
    monkeypatch.setattr(srv, "Sistema", lambda c, registro=None: orden.append("sistema") or object())
    monkeypatch.setenv("WHATSAPP_USUARIOS_JSON", (RAIZ / "whatsapp.example.json").read_text("utf-8"))

    canal = srv.construir_canal()
    canal.sistema("empresa_servicios")
    assert orden == ["indice", "sistema"]
