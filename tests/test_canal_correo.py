"""Pruebas del canal de correo, sin red y sin modelo.

Lo que se prueba es lo que decide la arquitectura del canal: que la dirección
es la credencial y fija el inquilino, que un desconocido no llega al modelo,
que un remitente sin autenticar (DKIM/SPF) tampoco, que el aviso del artículo
50 va en la primera conversación, que la aprobación por texto pasa por el
mismo `aprobar` de siempre, que un correo leído dos veces no produce dos
respuestas, que la respuesta enhebra en la conversación, y que la dirección
no aparece en ningún sitio más que en el destinatario.
"""
import email.message
import email.utils
import json
from pathlib import Path

import pytest

from src.canal_correo import (
    TEXTO_NO_AUTENTICADO,
    TEXTO_NO_AUTORIZADO,
    TEXTO_VACIO,
    CanalCorreo,
    Contacto,
    DirectorioDirecciones,
    MensajeCorreo,
    autenticacion_valida,
    cargar_direcciones,
    componer_respuesta,
    extraer_mensaje,
    huella,
    limpiar_cuerpo,
    normalizar_direccion,
)
from src.canal_whatsapp import TEXTO_TOPE

RAIZ = Path(__file__).resolve().parents[1]
AVISO = {"empresa_servicios": "Respuesta generada por una IA.", "agencia_inmobiliaria": "IA de Domara."}


class SistemaFalso:
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
    return DirectorioDirecciones(direcciones=[
        Contacto(direccion="empleado@ejemplo.es", usuario="empleado", nombre="Empleado", tenant="empresa_servicios"),
        Contacto(direccion="Gerencia <GERENCIA@Domara.example>", usuario="gerencia", tenant="agencia_inmobiliaria", roles=["direccion"]),
        Contacto(direccion="comercial@domara.example", usuario="comercial", tenant="agencia_inmobiliaria"),
    ])


def _canal(sistemas: dict, tope=(False, 0.0, 2.0), exigir_autenticacion=True):
    tiempos = {"t": 1000.0}
    canal = CanalCorreo(
        _directorio(),
        fabrica_sistema=lambda t: sistemas[t],
        aviso_de=lambda t: AVISO[t],
        comprobar_tope=lambda: tope,
        reloj=lambda: tiempos["t"],
        exigir_autenticacion=exigir_autenticacion,
    )
    canal._tiempos = tiempos
    return canal


def _msg(texto, remitente="empleado@ejemplo.es", id_="<m1@ejemplo.es>", autenticado=True, asunto="Consulta"):
    return MensajeCorreo(id=id_, remitente=remitente, asunto=asunto, texto=texto, autenticado=autenticado, referencias=[id_])


def _crudo(texto, desde="Empleado <empleado@ejemplo.es>", asunto="Consulta", autenticacion="mx.google.com; dkim=pass header.i=@ejemplo.es; spf=pass", html=None, referencias=None):
    m = email.message.EmailMessage()
    m["From"] = desde
    m["To"] = "asistente@ejemplo.es"
    m["Subject"] = asunto
    m["Message-ID"] = "<abc@ejemplo.es>"
    if referencias:
        m["References"] = referencias
        m["In-Reply-To"] = referencias.split()[-1]
    if autenticacion is not None:
        m["Authentication-Results"] = autenticacion
    if html is not None:
        m.set_content(html, subtype="html")
    else:
        m.set_content(texto)
    return m.as_bytes()


# --- Identidad: la dirección es la credencial -------------------------------

def test_la_direccion_fija_persona_e_inquilino():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios"), "agencia_inmobiliaria": SistemaFalso("agencia_inmobiliaria")}
    canal = _canal(sistemas)
    canal.procesar(_msg("¿vacaciones?", "empleado@ejemplo.es", "<a>"))
    canal.procesar(_msg("¿cartera?", "gerencia@domara.example", "<b>"))
    assert sistemas["empresa_servicios"].consultas[0][1].id == "empleado"
    assert sistemas["agencia_inmobiliaria"].consultas[0][1].roles == ["direccion"]
    assert len(sistemas["empresa_servicios"].consultas) == 1


def test_una_direccion_desconocida_no_llega_al_modelo_y_se_anota_por_huella():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios")}
    canal = _canal(sistemas)
    respuestas = canal.procesar(_msg("hola", "intruso@otro.example", "<x>"))
    assert respuestas == [TEXTO_NO_AUTORIZADO]
    assert sistemas["empresa_servicios"].consultas == []
    assert canal.desconocidos[0]["motivo"] == "desconocido"
    assert "intruso" not in json.dumps(canal.desconocidos)


def test_la_direccion_se_normaliza_con_nombre_y_mayusculas():
    assert normalizar_direccion("Ana <Ana@Ejemplo.ES>") == "ana@ejemplo.es"
    assert _directorio().buscar("gerencia@domara.example").usuario == "gerencia"


def test_una_direccion_invalida_no_entra_en_el_directorio():
    with pytest.raises(ValueError):
        Contacto(direccion="esto no es un correo", usuario="x", tenant="empresa_servicios")


def test_la_huella_no_es_la_direccion_y_es_estable():
    h = huella("Empleado <EMPLEADO@ejemplo.es>")
    assert h == huella("empleado@ejemplo.es") and len(h) == 12 and "ejemplo" not in h


# --- Autenticación del remitente: lo que WhatsApp no necesitaba ---------------

def test_un_remitente_autorizado_sin_autenticar_no_se_atiende_y_se_anota():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios")}
    canal = _canal(sistemas)
    assert canal.procesar(_msg("¿vacaciones?", autenticado=False)) == [TEXTO_NO_AUTENTICADO]
    assert sistemas["empresa_servicios"].consultas == []
    assert canal.desconocidos[0]["motivo"] == "sin_autenticar"


def test_sin_exigir_autenticacion_se_atiende_igual():
    sistemas = {"empresa_servicios": SistemaFalso("empresa_servicios")}
    canal = _canal(sistemas, exigir_autenticacion=False)
    canal.procesar(_msg("¿vacaciones?", autenticado=False))
    assert len(sistemas["empresa_servicios"].consultas) == 1


def test_la_cabecera_de_autenticacion_se_lee_como_la_escribe_gmail():
    assert autenticacion_valida(["mx.google.com; dkim=pass header.i=@ejemplo.es; spf=pass smtp.mailfrom=ejemplo.es"])
    assert autenticacion_valida(["mx.google.com; spf=pass"])
    assert not autenticacion_valida(["mx.google.com; dkim=fail; spf=softfail"])
    assert not autenticacion_valida([])


# --- Artículo 50 --------------------------------------------------------------

def test_el_aviso_va_en_la_primera_conversacion_y_no_en_cada_mensaje():
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    primera = canal.procesar(_msg("uno", id_="<1>"))[0]
    segunda = canal.procesar(_msg("dos", id_="<2>"))[0]
    assert primera.startswith(f"[{AVISO['empresa_servicios']}]")
    assert AVISO["empresa_servicios"] not in segunda


def test_el_aviso_se_repite_tras_un_dia_de_silencio():
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    canal.procesar(_msg("uno", id_="<1>"))
    canal._tiempos["t"] += 25 * 3600
    assert AVISO["empresa_servicios"] in canal.procesar(_msg("dos", id_="<2>"))[0]


# --- Aprobación humana por correo --------------------------------------------

def test_una_escritura_propuesta_se_describe_y_pide_aprobacion():
    traza = {"respuesta": "Propongo registrar la visita.", "acciones_pendientes": [
        {"id": "ACC-abc123", "herramienta": "crm__registrar_visita", "argumentos": {"inmueble": "INM-2026-147"}}]}
    canal = _canal({"agencia_inmobiliaria": SistemaFalso("agencia_inmobiliaria", [traza])})
    [texto] = canal.procesar(_msg("registra la visita", "gerencia@domara.example"))
    assert "NO la he ejecutado" in texto and "APROBAR ACC-abc123" in texto and "primera línea" in texto


def test_aprobar_en_la_primera_linea_pasa_por_el_aprobar_de_siempre():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    [texto] = canal.procesar(_msg("APROBAR ACC-abc123\n\nGracias.", "gerencia@domara.example"))
    assert sistema.aprobadas == [("ACC-abc123", "gerencia")]
    assert "VIS-901" in texto


def test_rechazar_por_correo():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    canal.procesar(_msg("rechazar ACC-abc123", "gerencia@domara.example"))
    assert sistema.rechazadas[0][:2] == ("ACC-abc123", "gerencia") and "correo" in sistema.rechazadas[0][2]


def test_quien_no_tiene_el_rol_no_aprueba():
    sistema = SistemaFalso("agencia_inmobiliaria")
    canal = _canal({"agencia_inmobiliaria": sistema})
    [texto] = canal.procesar(_msg("APROBAR ACC-abc123", "comercial@domara.example"))
    assert sistema.aprobadas == [] and "No puedes aprobar" in texto


# --- Robustez del canal --------------------------------------------------------

def test_un_correo_leido_dos_veces_no_produce_una_segunda_respuesta():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema})
    assert len(canal.procesar(_msg("uno", id_="<mismo>"))) == 1
    assert canal.procesar(_msg("uno", id_="<mismo>")) == []
    assert len(sistema.consultas) == 1


def test_un_correo_sin_texto_recibe_una_frase_fija():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema})
    assert canal.procesar(_msg("   \n  "))[0].endswith(TEXTO_VACIO)
    assert sistema.consultas == []


def test_con_el_tope_superado_no_se_consulta():
    sistema = SistemaFalso("empresa_servicios")
    canal = _canal({"empresa_servicios": sistema}, tope=(True, 2.5, 2.0))
    assert canal.procesar(_msg("¿vacaciones?"))[0].endswith(TEXTO_TOPE)
    assert sistema.consultas == []


def test_un_fallo_del_sistema_se_dice_y_no_tumba_el_canal():
    class Revienta(SistemaFalso):
        def responder(self, consulta, usuario=None):
            raise RuntimeError("proveedor caído")

    canal = _canal({"empresa_servicios": Revienta("empresa_servicios")})
    [texto] = canal.procesar(_msg("¿vacaciones?"))
    assert "RuntimeError" in texto and "no se pudo atender" in texto


def test_lo_retenido_y_lo_redactado_se_dicen_sin_nombrar_documentos():
    traza = {"respuesta": "R", "denegados_por_permiso": ["anexo_confidencial.md"], "campos_redactados": ["dni"], "acciones_pendientes": []}
    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios", [traza])})
    [texto] = canal.procesar(_msg("¿salario?"))
    assert "Retenido por permiso: 1 documento" in texto and "anexo_confidencial" not in texto and "dni" in texto


def test_el_sistema_de_cada_inquilino_se_construye_una_vez():
    construidos = []

    def fabrica(t):
        construidos.append(t)
        return SistemaFalso(t)

    canal = CanalCorreo(_directorio(), fabrica, lambda t: AVISO[t], comprobar_tope=lambda: (False, 0, 2))
    canal.procesar(_msg("a", id_="<1>"))
    canal.procesar(_msg("b", id_="<2>"))
    canal.procesar(_msg("c", "gerencia@domara.example", "<3>"))
    assert construidos == ["empresa_servicios", "agencia_inmobiliaria"]


# --- Parseo del correo --------------------------------------------------------

def test_extraer_un_correo_de_texto_plano_con_autenticacion():
    m = extraer_mensaje(_crudo("¿Cuántos días de vacaciones tengo?"))
    assert m.remitente == "empleado@ejemplo.es" and m.asunto == "Consulta"
    assert m.texto == "¿Cuántos días de vacaciones tengo?" and m.autenticado is True
    assert m.id == "<abc@ejemplo.es>" and m.referencias == ["<abc@ejemplo.es>"]


def test_sin_cabecera_de_autenticacion_el_correo_no_esta_autenticado():
    assert extraer_mensaje(_crudo("hola", autenticacion=None)).autenticado is False


def test_la_cita_del_correo_anterior_y_la_firma_se_quitan():
    texto = "APROBAR ACC-abc123\n\nEl vie, 26 sept 2026, Asistente escribió:\n> He propuesto una escritura\n> Responde APROBAR\n-- \nJuan"
    assert limpiar_cuerpo(texto) == "APROBAR ACC-abc123"
    assert limpiar_cuerpo("Pregunta\n\nOn Fri, Sep 26, 2026 Bot wrote:\n> algo") == "Pregunta"


def test_un_correo_solo_html_se_convierte_en_texto():
    m = extraer_mensaje(_crudo(None, html="<html><body><p>¿Qué <b>día</b> se paga la nómina?</p><style>p{}</style></body></html>"))
    assert m.texto == "¿Qué día se paga la nómina?"


def test_las_referencias_del_hilo_se_conservan():
    m = extraer_mensaje(_crudo("APROBAR ACC-abc123", referencias="<r1@ejemplo.es> <r2@ejemplo.es>"))
    assert m.referencias == ["<r1@ejemplo.es>", "<r2@ejemplo.es>", "<abc@ejemplo.es>"]


def test_la_respuesta_enhebra_en_la_conversacion():
    original = extraer_mensaje(_crudo("¿vacaciones?", referencias="<r1@ejemplo.es>"))
    respuesta = componer_respuesta(original, "23 días.", "asistente@ejemplo.es")
    assert respuesta["To"] == "empleado@ejemplo.es" and respuesta["From"] == "asistente@ejemplo.es"
    assert respuesta["Subject"] == "Re: Consulta"
    assert respuesta["In-Reply-To"] == "<abc@ejemplo.es>"
    assert respuesta["References"] == "<r1@ejemplo.es> <abc@ejemplo.es>"
    assert respuesta.get_content().strip() == "23 días."


def test_una_respuesta_a_un_re_no_duplica_el_prefijo():
    original = MensajeCorreo(id="<a>", remitente="x@ejemplo.es", asunto="Re: Consulta", referencias=["<a>"])
    assert componer_respuesta(original, "ok", "bot@ejemplo.es")["Subject"] == "Re: Consulta"


# --- Directorio ----------------------------------------------------------------

def test_la_lista_de_ejemplo_se_carga_y_se_marca(monkeypatch):
    monkeypatch.delenv("CORREO_USUARIOS_JSON", raising=False)
    monkeypatch.chdir(RAIZ)
    monkeypatch.setattr("src.canal_correo.FICHERO_DIRECCIONES", Path("no-existe.local.json"))
    d = cargar_direcciones()
    assert d.es_de_ejemplo and {c.tenant for c in d.direcciones} >= {"empresa_servicios", "agencia_inmobiliaria", "gestoria_laboral"}


def test_la_variable_de_entorno_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("CORREO_USUARIOS_JSON", json.dumps({"direcciones": [
        {"direccion": "a@b.es", "usuario": "u", "tenant": "empresa_servicios"}]}))
    d = cargar_direcciones()
    assert not d.es_de_ejemplo and d.buscar("A@B.ES").usuario == "u"


def test_una_lista_invalida_falla_con_mensaje(monkeypatch):
    monkeypatch.setenv("CORREO_USUARIOS_JSON", '{"direcciones": []}')
    with pytest.raises(ValueError, match="CORREO_USUARIOS_JSON"):
        cargar_direcciones()


# --- El servidor: sondeo, respuesta y línea de registro -------------------------

class _BuzonFalso:
    def __init__(self, crudos):
        self.pendientes = list(enumerate(crudos))
        self.leidos = []

    def no_leidos(self):
        return [(str(i).encode(), c) for i, c in self.pendientes]

    def marcar_leido(self, uid):
        self.leidos.append(uid)
        self.pendientes = [(i, c) for i, c in self.pendientes if str(i).encode() != uid]


class _EnviadorMemoria:
    def __init__(self):
        self.enviados = []

    def enviar(self, mensaje):
        self.enviados.append(mensaje)


def test_un_ciclo_atiende_responde_marca_y_deja_una_linea_sin_direccion():
    import io

    from src import canal_correo_servidor as servidor

    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    buzon = _BuzonFalso([_crudo("¿Cuántos días de vacaciones tengo?")])
    enviador = _EnviadorMemoria()
    salida = io.StringIO()
    n = servidor.ciclo(canal, buzon, enviador, "asistente@ejemplo.es", salida)
    assert n == 1 and buzon.leidos == [b"0"] and buzon.pendientes == []
    [respuesta] = enviador.enviados
    assert respuesta["To"] == "empleado@ejemplo.es" and "respuesta a: ¿Cuántos días" in respuesta.get_content()
    linea = salida.getvalue()
    assert "tenant=empresa_servicios" in linea and "respuestas=1" in linea and "latencia=" in linea
    assert "empleado@ejemplo.es" not in linea and huella("empleado@ejemplo.es") in linea


def test_un_fallo_al_enviar_queda_en_la_linea_y_el_correo_no_se_marca_como_leido():
    import io

    from src import canal_correo_servidor as servidor

    class Falla(_EnviadorMemoria):
        def enviar(self, mensaje):
            raise RuntimeError("SMTP 535 credenciales")

    canal = _canal({"empresa_servicios": SistemaFalso("empresa_servicios")})
    buzon = _BuzonFalso([_crudo("hola")])
    salida = io.StringIO()
    servidor.ciclo(canal, buzon, Falla(), "asistente@ejemplo.es", salida)
    assert "ERROR RuntimeError" in salida.getvalue() and "535" in salida.getvalue()
    # Se marca igualmente: reintentar sin fin un correo que no se puede responder
    # bloquearía el buzón; el fallo queda en la línea, que es lo que se lee.
    assert buzon.leidos == [b"0"]


def test_el_servidor_asegura_el_indice_antes_de_crear_el_sistema(monkeypatch):
    from src import canal_correo_servidor as servidor

    orden = []
    cfg = type("Cfg", (), {"tenant": type("T", (), {"ai_act": type("A", (), {"aviso_usuario": "IA"})()})()})()
    monkeypatch.setattr(servidor, "load_config", lambda tenant_id, con_juez: cfg)
    monkeypatch.setattr(servidor, "asegurar_indice", lambda c, avisar=None: orden.append("indice"))
    monkeypatch.setattr(servidor, "desde_config", lambda c: None)
    monkeypatch.setattr(servidor, "Sistema", lambda c, registro=None: orden.append("sistema") or SistemaFalso("empresa_servicios"))
    monkeypatch.setattr(servidor, "cargar_direcciones", _directorio)
    canal = servidor.construir_canal()
    canal.sistema("empresa_servicios")
    assert orden == ["indice", "sistema"]


def test_la_simulacion_produce_un_correo_autenticado_del_remitente_indicado(monkeypatch):
    from src import canal_correo_servidor as servidor

    monkeypatch.setenv("CORREO_USUARIO", "asistente@ejemplo.es")
    m = extraer_mensaje(servidor._correo_simulado("hola", "empleado@ejemplo.es"))
    assert m.remitente == "empleado@ejemplo.es" and m.autenticado and m.texto == "hola"
