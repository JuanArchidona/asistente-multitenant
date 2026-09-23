"""Canal de WhatsApp: la lógica, sin red y sin framework.

Punto 13 del bloque 3 de `docs/ALCANCE.md`. Lo que decide la arquitectura,
igual que en la interfaz web (`app.py`), y no el canal:

- **El número de teléfono es la credencial.** Meta ya ha verificado que el
  mensaje sale de ese número; aquí se mira en una lista cerrada qué persona
  es, de qué inquilino y con qué roles. Un número que no está en la lista
  recibe una frase fija y **no llega al modelo**: ni enrutado, ni
  recuperación, ni coste.
- **El inquilino lo fija el número**, como en la web lo fija la credencial.
  Dos números de dos clientes nunca comparten `Sistema`.
- **El modelo nunca escribe.** Si propone una escritura, el canal la
  describe y pide que la persona conteste `APROBAR <id>` o `RECHAZAR <id>`;
  la misma aprobación humana de la web, por texto (§42).
- **Artículo 50 del AI Act**: el primer mensaje de cada conversación lleva
  el aviso que el inquilino declara en su manifiesto, y se repite si la
  conversación estuvo más de 24 horas en silencio.
- **El teléfono no se escribe en ningún registro.** Al registro de producción
  va el identificador de usuario de la lista, como en la web; los números
  desconocidos se anotan por su huella (SHA-256 recortado), no en claro.

Este módulo no sabe de HTTP: recibe (teléfono, texto, id de mensaje) y
devuelve los textos que hay que enviar. Así se prueba entero sin levantar
nada, y el servidor (`canal_whatsapp_servidor.py`) solo traduce.
"""
import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .acceso import tope_superado
from .gobernanza import Usuario

FICHERO_TELEFONOS = Path("whatsapp.local.json")
FICHERO_EJEMPLO_TELEFONOS = Path("whatsapp.example.json")
VARIABLE_TELEFONOS = "WHATSAPP_USUARIOS_JSON"

# Límite de un mensaje de texto en la API de WhatsApp.
MAX_CARACTERES = 4096
# Tras este silencio, la conversación se considera nueva y el aviso del
# artículo 50 se repite. Coincide con la ventana de servicio de WhatsApp.
SILENCIO_NUEVA_CONVERSACION_S = 24 * 3600
# Cuántos identificadores de mensaje se recuerdan para no procesar dos veces
# el mismo: Meta reintenta el webhook si no recibe un 200 a tiempo.
MEMORIA_MENSAJES = 500

_RE_ORDEN = re.compile(r"^\s*(aprobar|rechazar)\s+(ACC-[0-9a-f]{6})\s*$", re.IGNORECASE)

TEXTO_NO_AUTORIZADO = (
    "Este número no está dado de alta en el asistente. Si crees que debería estarlo, "
    "pídelo a la persona responsable de tu empresa."
)
TEXTO_SOLO_TEXTO = "Por ahora solo atiendo mensajes de texto."
TEXTO_TOPE = (
    "El asistente ha alcanzado su tope de gasto y no atiende más consultas hasta que se revise."
)


def normalizar_telefono(bruto: str) -> str:
    """Solo dígitos, sin '+' ni espacios: Meta manda '34612345678'."""
    return re.sub(r"\D", "", bruto or "")


def huella(telefono: str) -> str:
    """Lo único que se escribe de un número: 12 hexadecimales de su SHA-256."""
    return hashlib.sha256(normalizar_telefono(telefono).encode()).hexdigest()[:12]


class Contacto(BaseModel):
    telefono: str = Field(min_length=6)
    usuario: str = Field(min_length=1)
    nombre: str = ""
    tenant: str = Field(min_length=1)
    roles: list[str] = Field(default_factory=list)

    def como_usuario(self) -> Usuario:
        return Usuario(id=self.usuario, nombre=self.nombre or self.usuario, roles=list(self.roles))


class DirectorioTelefonos(BaseModel):
    """Lista cerrada de números autorizados."""

    numeros: list[Contacto] = Field(min_length=1)
    es_de_ejemplo: bool = False

    def buscar(self, telefono: str) -> Contacto | None:
        objetivo = normalizar_telefono(telefono)
        for c in self.numeros:
            if normalizar_telefono(c.telefono) == objetivo:
                return c
        return None


def cargar_telefonos(ruta: Path | str | None = None) -> DirectorioTelefonos:
    """La lista: la variable de entorno, el fichero local o el de ejemplo.

    Mismo orden y misma regla que los usuarios de la web: caer al de ejemplo
    es visible (`es_de_ejemplo`), nunca silencioso.
    """
    if ruta is None and os.getenv(VARIABLE_TELEFONOS, "").strip():
        try:
            return DirectorioTelefonos.model_validate(json.loads(os.environ[VARIABLE_TELEFONOS]))
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError(f"{VARIABLE_TELEFONOS} no es una lista de números válida: {error}") from error
    candidatos = [Path(ruta)] if ruta else [FICHERO_TELEFONOS, FICHERO_EJEMPLO_TELEFONOS]
    for candidato in candidatos:
        if candidato.is_file():
            try:
                datos = json.loads(candidato.read_text(encoding="utf-8"))
                directorio = DirectorioTelefonos.model_validate(datos)
            except (json.JSONDecodeError, ValidationError) as error:
                raise ValueError(f"{candidato} no es una lista de números válida: {error}") from error
            if candidato == FICHERO_EJEMPLO_TELEFONOS:
                directorio.es_de_ejemplo = True
            return directorio
    raise ValueError(
        f"No hay lista de números: ni {VARIABLE_TELEFONOS}, ni {FICHERO_TELEFONOS}, "
        f"ni {FICHERO_EJEMPLO_TELEFONOS}."
    )


# --- Mensajes entrantes ---------------------------------------------------

class MensajeEntrante(BaseModel):
    id: str
    telefono: str
    tipo: str
    texto: str = ""


def extraer_mensajes(payload: dict) -> list[MensajeEntrante]:
    """Los mensajes de un webhook de la API de WhatsApp de Meta.

    El payload trae también acuses de entrega y lectura (`statuses`), que se
    ignoran. Un cuerpo que no tiene la forma esperada devuelve una lista
    vacía en vez de romper: al webhook hay que contestarle 200 igualmente.
    """
    salida = []
    if not isinstance(payload, dict):
        return salida
    entradas = payload.get("entry") or []
    for entrada in entradas if isinstance(entradas, list) else []:
        if not isinstance(entrada, dict):
            continue
        cambios = entrada.get("changes") or []
        for cambio in cambios if isinstance(cambios, list) else []:
            valor = (cambio.get("value") if isinstance(cambio, dict) else None) or {}
            mensajes = valor.get("messages") or [] if isinstance(valor, dict) else []
            for m in mensajes if isinstance(mensajes, list) else []:
                if not isinstance(m, dict):
                    continue
                tipo = m.get("type", "")
                texto = (m.get("text") or {}).get("body", "") if tipo == "text" else ""
                if m.get("id") and m.get("from"):
                    salida.append(
                        MensajeEntrante(id=m["id"], telefono=m["from"], tipo=tipo, texto=texto)
                    )
    return salida


def firma_valida(app_secret: str, cuerpo: bytes, cabecera: str | None) -> bool:
    """`X-Hub-Signature-256: sha256=<hmac>` del cuerpo crudo con el secreto de la app.

    Sin esto, cualquiera que conozca la URL puede inyectar mensajes en nombre
    de un número autorizado. Es el control de acceso del canal, y por eso el
    servidor no arranca sin secreto.
    """
    if not app_secret or not cabecera or not cabecera.startswith("sha256="):
        return False
    esperada = hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, cabecera[len("sha256="):])


def trocear(texto: str, maximo: int = MAX_CARACTERES) -> list[str]:
    """Parte un texto largo por párrafos, y si no hay más remedio por caracteres."""
    if len(texto) <= maximo:
        return [texto]
    trozos, actual = [], ""
    for parrafo in texto.split("\n\n"):
        candidato = f"{actual}\n\n{parrafo}" if actual else parrafo
        if len(candidato) <= maximo:
            actual = candidato
            continue
        if actual:
            trozos.append(actual)
        while len(parrafo) > maximo:
            trozos.append(parrafo[:maximo])
            parrafo = parrafo[maximo:]
        actual = parrafo
    if actual:
        trozos.append(actual)
    return trozos


# --- El canal -------------------------------------------------------------

class CanalWhatsApp:
    """Convierte mensajes en consultas y respuestas en mensajes.

    `fabrica_sistema(tenant_id)` devuelve el `Sistema` (con registro) de ese
    inquilino; se llama una vez por inquilino y se cachea, como en la web.
    `aviso_de(tenant_id)` devuelve el texto del artículo 50 del inquilino.
    """

    def __init__(
        self,
        directorio: DirectorioTelefonos,
        fabrica_sistema,
        aviso_de,
        comprobar_tope=tope_superado,
        reloj=time.time,
        registro_desconocidos=None,
    ):
        self.directorio = directorio
        self._fabrica = fabrica_sistema
        self._aviso_de = aviso_de
        self._tope = comprobar_tope
        self._reloj = reloj
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

    def _conversacion_nueva(self, telefono: str) -> bool:
        ahora = self._reloj()
        anterior = self._ultimo_contacto.get(telefono)
        self._ultimo_contacto[telefono] = ahora
        return anterior is None or ahora - anterior > SILENCIO_NUEVA_CONVERSACION_S

    def _anotar_desconocido(self, telefono: str) -> None:
        fila = {"huella": huella(telefono), "ts": self._reloj()}
        self.desconocidos.append(fila)
        if self._registro_desconocidos is not None:
            self._registro_desconocidos(fila)

    def procesar(self, mensaje: MensajeEntrante) -> list[str]:
        """Los textos que hay que enviar a ese número, en orden. Puede ser ninguno."""
        if self._ya_procesado(mensaje.id):
            return []
        telefono = normalizar_telefono(mensaje.telefono)
        contacto = self.directorio.buscar(telefono)
        if contacto is None:
            self._anotar_desconocido(telefono)
            return [TEXTO_NO_AUTORIZADO]
        if mensaje.tipo != "text" or not mensaje.texto.strip():
            return [TEXTO_SOLO_TEXTO]

        persona = contacto.como_usuario()
        prefijo = f"[{self._aviso_de(contacto.tenant)}]\n\n" if self._conversacion_nueva(telefono) else ""

        orden = _RE_ORDEN.match(mensaje.texto)
        if orden:
            return trocear(prefijo + self._ejecutar_orden(contacto, persona, orden))

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
                f"Responde APROBAR {accion['id']} o RECHAZAR {accion['id']}."
            )
        return trocear(prefijo + "\n\n".join(partes))

    def _ejecutar_orden(self, contacto: Contacto, persona: Usuario, orden) -> str:
        verbo, id_accion = orden.group(1).lower(), orden.group(2).upper()
        # El id se genera con `token_hex`, que es minúscula; el regex lo acepta
        # en cualquier caja y aquí se normaliza para buscarlo.
        id_accion = "ACC-" + id_accion[4:].lower()
        sistema = self.sistema(contacto.tenant)
        try:
            if verbo == "aprobar":
                resultado = sistema.aprobar(id_accion, usuario=persona)
                return (
                    f"Acción {id_accion} aprobada por {persona.id} y ejecutada.\n"
                    f"Resultado: {resultado['resultado'][:600]}"
                )
            sistema.rechazar(id_accion, usuario=persona, motivo="rechazada por WhatsApp")
            return f"Acción {id_accion} rechazada por {persona.id}. No se ha ejecutado nada."
        except KeyError:
            return f"No hay ninguna acción pendiente con id {id_accion}: o ya se decidió, o nunca se propuso."
        except PermissionError as error:
            return f"No puedes aprobar esa acción: {error}"
