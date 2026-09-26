"""Canal de correo: la lógica, sin red y sin framework.

Punto 11 del bloque 2 de `docs/ALCANCE.md`. Es la tercera puerta al mismo
sistema, después de la web (`app.py`) y de WhatsApp (`canal_whatsapp.py`), y
decide lo mismo que ellas, porque lo decide la arquitectura y no el canal:

- **La dirección del remitente es la credencial.** Una lista cerrada dice qué
  persona hay detrás de cada dirección, de qué inquilino y con qué roles. Una
  dirección que no está en la lista recibe una frase fija y **no llega al
  modelo**: ni enrutado, ni recuperación, ni coste.
- **Un remitente se puede falsificar**, y eso WhatsApp no lo tenía: Meta
  verifica el número. Aquí lo verifica el servidor de correo que recibe el
  mensaje, y lo escribe en la cabecera `Authentication-Results` (DKIM, SPF).
  El canal exige que esa cabecera diga `pass`; un mensaje de una dirección
  autorizada sin autenticación se rechaza con una frase fija y se anota. Es
  el control de acceso del canal, como la firma del webhook lo es en WhatsApp.
- **El inquilino lo fija la dirección.** Dos direcciones de dos clientes nunca
  comparten `Sistema`.
- **El modelo nunca escribe.** Si propone una escritura, el canal la describe
  y pide que la persona conteste `APROBAR <id>` o `RECHAZAR <id>` en la
  primera línea de su respuesta; la misma aprobación humana de la web (§42).
- **Artículo 50 del AI Act**: el primer mensaje de cada conversación lleva el
  aviso que el inquilino declara en su manifiesto, y se repite si la
  conversación estuvo más de 24 horas en silencio.
- **La dirección no se escribe en ningún registro.** Al registro de producción
  va el identificador de usuario de la lista; las direcciones desconocidas o
  sin autenticar se anotan por su huella (SHA-256 recortado), no en claro.

Este módulo no sabe de IMAP ni de SMTP: recibe un correo crudo, lo convierte
en (remitente, texto, autenticado, hilo) y devuelve los textos que hay que
responder. El servidor (`canal_correo_servidor.py`) solo lee el buzón, llama
aquí y envía.
"""
import email
import email.message
import email.policy
import email.utils
import hashlib
import html
import json
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

from .acceso import tope_superado
from .canal_whatsapp import RE_ORDEN, TEXTO_TOPE
from .gobernanza import Usuario

FICHERO_DIRECCIONES = Path("correo.local.json")
FICHERO_EJEMPLO_DIRECCIONES = Path("correo.example.json")
VARIABLE_DIRECCIONES = "CORREO_USUARIOS_JSON"

# Tras este silencio, la conversación se considera nueva y el aviso del
# artículo 50 se repite. El mismo criterio que en WhatsApp.
SILENCIO_NUEVA_CONVERSACION_S = 24 * 3600
# Cuántos identificadores de mensaje se recuerdan: un sondeo que se solapa con
# el anterior, o un buzón que no marcó como leído, no deben producir dos
# respuestas al mismo correo.
MEMORIA_MENSAJES = 500
PREFIJO_ASUNTO = "Re: "
ASUNTO_POR_DEFECTO = "Tu consulta al asistente"

TEXTO_NO_AUTORIZADO = (
    "Esta dirección no está dada de alta en el asistente. Si crees que debería estarlo, "
    "pídelo a la persona responsable de tu empresa."
)
TEXTO_NO_AUTENTICADO = (
    "Tu mensaje llegó sin autenticación del remitente (DKIM o SPF) y no se ha atendido. "
    "Un correo se puede falsificar, y el asistente solo responde a mensajes cuyo origen ha "
    "verificado el servidor de correo."
)
TEXTO_VACIO = "El mensaje no traía texto que atender. Escribe tu consulta en el cuerpo del correo."

_RE_DIRECCION = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Donde empieza la cita del mensaje anterior en una respuesta. Se corta ahí:
# lo que viene después ya lo atendió el sistema, y si volviera a entrar en la
# consulta el modelo respondería dos veces a lo mismo.
_RE_CITA = re.compile(
    r"^\s*(On .+ wrote:|El .+ escribi[oó]:|-{2,}\s*(Original Message|Mensaje original)\s*-{2,}|De:\s.+|From:\s.+)\s*$",
    re.IGNORECASE,
)
_RE_ETIQUETAS = re.compile(r"<[^>]+>")
_RE_AUTENTICACION = re.compile(r"\b(dkim|spf)\s*=\s*pass\b", re.IGNORECASE)


def normalizar_direccion(bruto: str) -> str:
    """Solo la dirección, en minúsculas: `Ana <Ana@Ejemplo.es>` es `ana@ejemplo.es`."""
    _nombre, direccion = email.utils.parseaddr(bruto or "")
    return direccion.strip().lower()


def huella(direccion: str) -> str:
    """Lo único que se escribe de una dirección: 12 hexadecimales de su SHA-256."""
    return hashlib.sha256(normalizar_direccion(direccion).encode()).hexdigest()[:12]


class Contacto(BaseModel):
    direccion: str
    usuario: str = Field(min_length=1)
    nombre: str = ""
    tenant: str = Field(min_length=1)
    roles: list[str] = Field(default_factory=list)

    @field_validator("direccion")
    @classmethod
    def _direccion_valida(cls, valor: str) -> str:
        normal = normalizar_direccion(valor)
        if not _RE_DIRECCION.match(normal):
            raise ValueError(f"no es una dirección de correo: {valor!r}")
        return normal

    def como_usuario(self) -> Usuario:
        return Usuario(id=self.usuario, nombre=self.nombre or self.usuario, roles=list(self.roles))


class DirectorioDirecciones(BaseModel):
    """Lista cerrada de direcciones autorizadas."""

    direcciones: list[Contacto] = Field(min_length=1)
    es_de_ejemplo: bool = False

    def buscar(self, direccion: str) -> Contacto | None:
        objetivo = normalizar_direccion(direccion)
        for c in self.direcciones:
            if c.direccion == objetivo:
                return c
        return None


def cargar_direcciones(ruta: Path | str | None = None) -> DirectorioDirecciones:
    """La lista: la variable de entorno, el fichero local o el de ejemplo.

    Mismo orden y misma regla que los números de WhatsApp y los usuarios de la
    web: caer al de ejemplo es visible (`es_de_ejemplo`), nunca silencioso.
    """
    if ruta is None and os.getenv(VARIABLE_DIRECCIONES, "").strip():
        try:
            return DirectorioDirecciones.model_validate(json.loads(os.environ[VARIABLE_DIRECCIONES]))
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError(f"{VARIABLE_DIRECCIONES} no es una lista de direcciones válida: {error}") from error
    candidatos = [Path(ruta)] if ruta else [FICHERO_DIRECCIONES, FICHERO_EJEMPLO_DIRECCIONES]
    for candidato in candidatos:
        if candidato.is_file():
            try:
                datos = json.loads(candidato.read_text(encoding="utf-8"))
                directorio = DirectorioDirecciones.model_validate(datos)
            except (json.JSONDecodeError, ValidationError) as error:
                raise ValueError(f"{candidato} no es una lista de direcciones válida: {error}") from error
            if candidato == FICHERO_EJEMPLO_DIRECCIONES:
                directorio.es_de_ejemplo = True
            return directorio
    raise ValueError(
        f"No hay lista de direcciones: ni {VARIABLE_DIRECCIONES}, ni {FICHERO_DIRECCIONES}, "
        f"ni {FICHERO_EJEMPLO_DIRECCIONES}."
    )


# --- Correos entrantes ----------------------------------------------------

class MensajeCorreo(BaseModel):
    id: str
    remitente: str
    asunto: str = ""
    texto: str = ""
    # Lo que dijo el servidor de correo receptor sobre el origen (DKIM, SPF).
    autenticado: bool = False
    # Message-IDs del hilo, el propio incluido, para que la respuesta enhebre.
    referencias: list[str] = Field(default_factory=list)


def autenticacion_valida(cabeceras: list[str]) -> bool:
    """`Authentication-Results` con `dkim=pass` o `spf=pass`.

    La cabecera la escribe el servidor que recibe el correo (Gmail, en el
    despliegue), no el remitente, así que no se puede falsificar desde fuera
    del buzón. Sin ella, o con `fail`, el mensaje no se atiende.
    """
    return any(_RE_AUTENTICACION.search(c or "") for c in cabeceras)


def limpiar_cuerpo(texto: str) -> str:
    """El texto propio de un correo: sin la cita del anterior ni la firma."""
    lineas = []
    for linea in (texto or "").replace("\r\n", "\n").split("\n"):
        if _RE_CITA.match(linea):
            break
        if linea.strip() == "--":
            break
        if linea.lstrip().startswith(">"):
            continue
        lineas.append(linea)
    return "\n".join(lineas).strip()


def _texto_de(mensaje: email.message.EmailMessage) -> str:
    cuerpo = mensaje.get_body(preferencelist=("plain", "html"))
    if cuerpo is None:
        return ""
    contenido = cuerpo.get_content()
    if cuerpo.get_content_type() == "text/html":
        contenido = re.sub(r"(?is)<(script|style).*?</\1>", "", contenido)
        contenido = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", contenido)
        contenido = html.unescape(_RE_ETIQUETAS.sub("", contenido))
    return contenido


def extraer_mensaje(crudo: bytes) -> MensajeCorreo:
    """Un correo crudo (RFC 5322) convertido en lo que el canal necesita."""
    mensaje = email.message_from_bytes(crudo, policy=email.policy.default)
    id_mensaje = (mensaje.get("Message-ID") or "").strip() or f"<sin-id-{hashlib.sha256(crudo).hexdigest()[:16]}>"
    referencias: list[str] = []
    for cabecera in ("References", "In-Reply-To"):
        for ref in re.findall(r"<[^>]+>", mensaje.get(cabecera) or ""):
            if ref not in referencias:
                referencias.append(ref)
    if id_mensaje not in referencias:
        referencias.append(id_mensaje)
    return MensajeCorreo(
        id=id_mensaje,
        remitente=normalizar_direccion(mensaje.get("From") or ""),
        asunto=(mensaje.get("Subject") or "").strip(),
        texto=limpiar_cuerpo(_texto_de(mensaje)),
        autenticado=autenticacion_valida(mensaje.get_all("Authentication-Results") or []),
        referencias=referencias,
    )


def componer_respuesta(original: MensajeCorreo, texto: str, remitente_propio: str) -> email.message.EmailMessage:
    """La respuesta, enhebrada en la conversación del correo original."""
    respuesta = email.message.EmailMessage(policy=email.policy.default)
    respuesta["From"] = remitente_propio
    respuesta["To"] = original.remitente
    asunto = original.asunto or ASUNTO_POR_DEFECTO
    respuesta["Subject"] = asunto if asunto.lower().startswith("re:") else PREFIJO_ASUNTO + asunto
    respuesta["In-Reply-To"] = original.id
    respuesta["References"] = " ".join(original.referencias)
    respuesta["Date"] = email.utils.formatdate(localtime=True)
    respuesta["Message-ID"] = email.utils.make_msgid()
    respuesta.set_content(texto)
    return respuesta


# --- El canal -------------------------------------------------------------

class CanalCorreo:
    """Convierte correos en consultas y respuestas en correos.

    `fabrica_sistema(tenant_id)` devuelve el `Sistema` (con registro) de ese
    inquilino; se llama una vez por inquilino y se cachea, como en la web y en
    WhatsApp. `aviso_de(tenant_id)` devuelve el texto del artículo 50.
    `exigir_autenticacion` solo se apaga en pruebas locales sin servidor de
    correo delante; en el despliegue va encendido.
    """

    def __init__(
        self,
        directorio: DirectorioDirecciones,
        fabrica_sistema,
        aviso_de,
        comprobar_tope=tope_superado,
        reloj=time.time,
        registro_desconocidos=None,
        exigir_autenticacion: bool = True,
    ):
        self.directorio = directorio
        self._fabrica = fabrica_sistema
        self._aviso_de = aviso_de
        self._tope = comprobar_tope
        self._reloj = reloj
        self._exigir_autenticacion = exigir_autenticacion
        self._sistemas: dict = {}
        self._ultimo_contacto: dict[str, float] = {}
        self._procesados: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()
        self.desconocidos: list[dict] = []
        self._registro_desconocidos = registro_desconocidos

    def sistema(self, tenant_id: str):
        with self._lock:
            if tenant_id not in self._sistemas:
                self._sistemas[tenant_id] = self._fabrica(tenant_id)
            return self._sistemas[tenant_id]

    def _ya_procesado(self, id_mensaje: str) -> bool:
        with self._lock:
            if id_mensaje in self._procesados:
                return True
            self._procesados[id_mensaje] = None
            while len(self._procesados) > MEMORIA_MENSAJES:
                self._procesados.popitem(last=False)
            return False

    def _conversacion_nueva(self, direccion: str) -> bool:
        ahora = self._reloj()
        anterior = self._ultimo_contacto.get(direccion)
        self._ultimo_contacto[direccion] = ahora
        return anterior is None or ahora - anterior > SILENCIO_NUEVA_CONVERSACION_S

    def _anotar(self, direccion: str, motivo: str) -> None:
        fila = {"huella": huella(direccion), "motivo": motivo, "ts": self._reloj()}
        self.desconocidos.append(fila)
        if self._registro_desconocidos is not None:
            self._registro_desconocidos(fila)

    def procesar(self, mensaje: MensajeCorreo) -> list[str]:
        """Los textos que hay que responder a ese correo. Casi siempre uno; puede ser ninguno."""
        if self._ya_procesado(mensaje.id):
            return []
        direccion = normalizar_direccion(mensaje.remitente)
        contacto = self.directorio.buscar(direccion)
        if contacto is None:
            self._anotar(direccion, "desconocido")
            return [TEXTO_NO_AUTORIZADO]
        if self._exigir_autenticacion and not mensaje.autenticado:
            self._anotar(direccion, "sin_autenticar")
            return [TEXTO_NO_AUTENTICADO]
        if not mensaje.texto.strip():
            return [TEXTO_VACIO]

        persona = contacto.como_usuario()
        prefijo = f"[{self._aviso_de(contacto.tenant)}]\n\n" if self._conversacion_nueva(direccion) else ""

        primera_linea = next((ln for ln in mensaje.texto.splitlines() if ln.strip()), "")
        orden = RE_ORDEN.match(primera_linea)
        if orden:
            return [prefijo + self._ejecutar_orden(contacto, persona, orden)]

        superado, _gastado, _tope = self._tope()
        if superado:
            return [prefijo + TEXTO_TOPE]

        sistema = self.sistema(contacto.tenant)
        try:
            traza = sistema.responder(mensaje.texto, usuario=persona)
        except Exception as error:  # noqa: BLE001 -- frontera de canal: el fallo ya está registrado (§46)
            return [prefijo + f"La consulta no se pudo atender ({type(error).__name__}). Vuelve a intentarlo más tarde."]

        partes = [traza["respuesta"]]
        if traza.get("denegados_por_permiso"):
            partes.append(
                f"(Retenido por permiso: {len(traza['denegados_por_permiso'])} documento(s) "
                "que tu rol no alcanza.)"
            )
        if traza.get("campos_redactados"):
            partes.append(f"(Campos redactados: {', '.join(traza['campos_redactados'])}.)")
        for accion in traza.get("acciones_pendientes") or []:
            partes.append(
                f"He propuesto una escritura y NO la he ejecutado: {accion['herramienta']} "
                f"con {json.dumps(accion['argumentos'], ensure_ascii=False)}.\n"
                f"Responde a este correo con APROBAR {accion['id']} o RECHAZAR {accion['id']} "
                "en la primera línea."
            )
        return [prefijo + "\n\n".join(partes)]

    def _ejecutar_orden(self, contacto: Contacto, persona: Usuario, orden) -> str:
        verbo, id_accion = orden.group(1).lower(), orden.group(2).upper()
        id_accion = "ACC-" + id_accion[4:].lower()
        sistema = self.sistema(contacto.tenant)
        try:
            if verbo == "aprobar":
                resultado = sistema.aprobar(id_accion, usuario=persona)
                return (
                    f"Acción {id_accion} aprobada por {persona.id} y ejecutada.\n"
                    f"Resultado: {resultado['resultado'][:600]}"
                )
            sistema.rechazar(id_accion, usuario=persona, motivo="rechazada por correo")
            return f"Acción {id_accion} rechazada por {persona.id}. No se ha ejecutado nada."
        except KeyError:
            return f"No hay ninguna acción pendiente con id {id_accion}: o ya se decidió, o nunca se propuso."
        except PermissionError as error:
            return f"No puedes aprobar esa acción: {error}"
