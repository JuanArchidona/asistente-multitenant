"""Servidor del canal de correo: IMAP para leer, SMTP para responder, `/salud` para Render.

Con la librería estándar a propósito, como el de WhatsApp: `imaplib`,
`smtplib` y `http.server`. No entra ningún paquete nuevo en el AIBOM.

    uv run python -m src.canal_correo_servidor                          # sondea el buzón y sirve /salud en $PORT
    uv run python -m src.canal_correo_servidor --simular "¿vacaciones?" --desde empleado@ejemplo.es

Variables de entorno (ver `.env.example` y `docs/CANAL_CORREO.md`):

- `CORREO_USUARIO`: la dirección del buzón dedicado (también es el remitente).
- `CORREO_CONTRASENA`: contraseña de aplicación de ese buzón. **Sin usuario y
  contraseña el servidor no arranca**: no hay nada que sondear.
- `CORREO_IMAP_HOST` (`imap.gmail.com`), `CORREO_SMTP_HOST` (`smtp.gmail.com`),
  `CORREO_SMTP_PUERTO` (`587`, con STARTTLS).
- `CORREO_INTERVALO_S`: cada cuántos segundos se mira el buzón (`30`).
- `CORREO_USUARIOS_JSON`: la lista de direcciones autorizadas (o
  `correo.local.json` en disco).

El correo no tiene webhook: hay que preguntar. El servidor abre una conexión
IMAP por sondeo, lee los mensajes sin leer con `BODY.PEEK[]` (para que un
fallo a mitad no los deje marcados), atiende cada uno, responde por SMTP
enhebrando en la conversación, y solo entonces los marca como leídos. En el
plan gratuito de Render el servicio se duerme sin tráfico HTTP y el sondeo se
duerme con él: eso es un límite del plan, no del canal, y `docs/CANAL_CORREO.md`
lo declara.
"""
import argparse
import email.message
import email.utils
import imaplib
import os
import smtplib
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import Sistema
from .canal_correo import (
    CanalCorreo,
    MensajeCorreo,
    cargar_direcciones,
    componer_respuesta,
    extraer_mensaje,
    huella,
    normalizar_direccion,
)
from .config import load_config
from .ingest import asegurar_indice
from .observabilidad import desde_config

INTERVALO_POR_DEFECTO_S = 30.0


class BuzonIMAP:
    """Lee el buzón. Una conexión por sondeo: es más simple que mantenerla viva
    y Gmail las corta igualmente a los pocos minutos sin actividad."""

    def __init__(self, host: str, usuario: str, contrasena: str, carpeta: str = "INBOX"):
        self.host, self.usuario, self.contrasena, self.carpeta = host, usuario, contrasena, carpeta

    def _abrir(self) -> imaplib.IMAP4_SSL:
        conexion = imaplib.IMAP4_SSL(self.host)
        conexion.login(self.usuario, self.contrasena)
        conexion.select(self.carpeta)
        return conexion

    def no_leidos(self) -> list[tuple[bytes, bytes]]:
        """`(uid, correo crudo)` de cada mensaje sin leer, sin marcarlo."""
        conexion = self._abrir()
        try:
            _estado, datos = conexion.uid("search", None, "UNSEEN")
            uids = datos[0].split() if datos and datos[0] else []
            salida = []
            for uid in uids:
                _estado, partes = conexion.uid("fetch", uid, "(BODY.PEEK[])")
                for parte in partes or []:
                    if isinstance(parte, tuple) and len(parte) >= 2 and isinstance(parte[1], bytes):
                        salida.append((uid, parte[1]))
                        break
            return salida
        finally:
            conexion.logout()

    def marcar_leido(self, uid: bytes) -> None:
        conexion = self._abrir()
        try:
            conexion.uid("store", uid, "+FLAGS", "(\\Seen)")
        finally:
            conexion.logout()


class EnviadorSMTP:
    """Envía la respuesta. STARTTLS en el 587, que es lo que Gmail acepta con
    contraseña de aplicación."""

    def __init__(self, host: str, puerto: int, usuario: str, contrasena: str):
        self.host, self.puerto, self.usuario, self.contrasena = host, puerto, usuario, contrasena

    def enviar(self, mensaje: email.message.EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.puerto, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(self.usuario, self.contrasena)
            smtp.send_message(mensaje)


class EnviadorConsola:
    """Para `--simular`: imprime en vez de enviar."""

    def __init__(self):
        self.enviados: list[email.message.EmailMessage] = []

    def enviar(self, mensaje: email.message.EmailMessage) -> None:
        self.enviados.append(mensaje)
        print(f"--> a {huella(mensaje['To'])} [{mensaje['Subject']}]:\n{mensaje.get_content()}\n")


def construir_canal(exigir_autenticacion: bool = True) -> CanalCorreo:
    directorio = cargar_direcciones()
    if directorio.es_de_ejemplo:
        print("[correo] AVISO: lista de direcciones DE EJEMPLO (correo.example.json).", file=sys.stderr)
    configs: dict = {}

    def config_de(tenant_id: str):
        if tenant_id not in configs:
            configs[tenant_id] = load_config(tenant_id, con_juez=False)
        return configs[tenant_id]

    def fabrica(tenant_id: str) -> Sistema:
        cfg = config_de(tenant_id)
        # El índice antes que el sistema, por lo que costó no hacerlo en
        # WhatsApp (§51): en Render el disco es efímero.
        asegurar_indice(cfg, avisar=lambda m: print(f"[correo] {m}", file=sys.stderr))
        return Sistema(cfg, registro=desde_config(cfg))

    def aviso(tenant_id: str) -> str:
        return config_de(tenant_id).tenant.ai_act.aviso_usuario

    def anotar(fila: dict) -> None:
        print(f"[correo] remitente {fila['motivo']}, huella {fila['huella']}", file=sys.stderr)

    return CanalCorreo(
        directorio, fabrica, aviso, registro_desconocidos=anotar, exigir_autenticacion=exigir_autenticacion
    )


def atender(canal: CanalCorreo, enviador, mensaje: MensajeCorreo, remitente_propio: str) -> tuple[int, float]:
    """Procesa un correo y envía las respuestas. Devuelve cuántas y la latencia
    interna: del correo leído a la última respuesta entregada al SMTP."""
    t0 = time.perf_counter()
    enviados = 0
    for texto in canal.procesar(mensaje):
        enviador.enviar(componer_respuesta(mensaje, texto, remitente_propio))
        enviados += 1
    return enviados, time.perf_counter() - t0


def atender_y_anotar(canal: CanalCorreo, enviador, mensaje: MensajeCorreo, remitente_propio: str, salida=None) -> None:
    """Atiende y deja UNA línea en la salida del proceso, sin la dirección:
    huella e inquilino, respuestas enviadas y latencia; o el error."""
    salida = salida if salida is not None else sys.stderr
    direccion = normalizar_direccion(mensaje.remitente)
    contacto = canal.directorio.buscar(direccion)
    quien = f"huella={huella(direccion)} tenant={contacto.tenant if contacto else 'desconocido'}"
    t0 = time.perf_counter()
    try:
        enviados, latencia = atender(canal, enviador, mensaje, remitente_propio)
    except Exception as error:  # noqa: BLE001 -- frontera del hilo de sondeo
        print(
            f"[correo] mensaje {quien} ERROR {type(error).__name__}: {str(error)[:200]} "
            f"tras {time.perf_counter() - t0:.2f} s",
            file=salida,
        )
        return
    print(f"[correo] mensaje {quien} respuestas={enviados} latencia={latencia:.2f} s", file=salida)


def ciclo(canal: CanalCorreo, buzon, enviador, remitente_propio: str, salida=None) -> int:
    """Un sondeo: cada correo sin leer se atiende y se marca. Devuelve cuántos."""
    atendidos = 0
    for uid, crudo in buzon.no_leidos():
        mensaje = extraer_mensaje(crudo)
        atender_y_anotar(canal, enviador, mensaje, remitente_propio, salida)
        buzon.marcar_leido(uid)
        atendidos += 1
    return atendidos


def bucle_sondeo(canal, buzon, enviador, remitente_propio: str, intervalo_s: float, parar: threading.Event, estado: dict, salida=None) -> None:
    salida = salida if salida is not None else sys.stderr
    while not parar.is_set():
        try:
            n = ciclo(canal, buzon, enviador, remitente_propio, salida)
            estado["ultimo_sondeo"] = time.time()
            estado["mensajes"] = estado.get("mensajes", 0) + n
            estado["ultimo_error"] = ""
        except Exception as error:  # noqa: BLE001 -- un sondeo que falla no para el siguiente, pero se dice
            estado["ultimo_error"] = f"{type(error).__name__}: {str(error)[:200]}"
            print(f"[correo] sondeo ERROR {estado['ultimo_error']}", file=salida)
        parar.wait(intervalo_s)


def crear_manejador(estado: dict):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            return

        def do_GET(self):  # nombre que exige BaseHTTPRequestHandler
            url = urllib.parse.urlparse(self.path)
            if url.path != "/salud":
                self.send_response(404)
                self.end_headers()
                return
            commit = os.getenv("RENDER_GIT_COMMIT", "local")[:7]
            hace = time.time() - estado["ultimo_sondeo"] if estado.get("ultimo_sondeo") else None
            cuerpo = (
                f"ok {commit} ultimo_sondeo_hace_s={hace:.0f} mensajes={estado.get('mensajes', 0)}"
                if hace is not None
                else f"ok {commit} sin_sondeo_todavia"
            )
            if estado.get("ultimo_error"):
                cuerpo += f" ultimo_error={estado['ultimo_error']}"
            datos = cuerpo.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

    return Manejador


def _correo_simulado(texto: str, desde: str, asunto: str = "Consulta") -> bytes:
    mensaje = email.message.EmailMessage()
    mensaje["From"] = desde
    mensaje["To"] = os.getenv("CORREO_USUARIO", "asistente@ejemplo.es")
    mensaje["Subject"] = asunto
    mensaje["Message-ID"] = email.utils.make_msgid()
    # Simula lo que escribiría el servidor de correo receptor.
    mensaje["Authentication-Results"] = "mx.ejemplo.es; dkim=pass; spf=pass"
    mensaje.set_content(texto)
    return mensaje.as_bytes()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", help="texto de un correo simulado; no toca ningún buzón")
    ap.add_argument("--desde", default="empleado@ejemplo.es", help="remitente del correo simulado")
    ap.add_argument("--puerto", type=int, default=int(os.getenv("PORT", "8080")))
    ap.add_argument("--intervalo", type=float, default=float(os.getenv("CORREO_INTERVALO_S", INTERVALO_POR_DEFECTO_S)))
    args = ap.parse_args()

    remitente_propio = os.getenv("CORREO_USUARIO", "asistente@ejemplo.es")

    if args.simular:
        canal = construir_canal()
        enviador = EnviadorConsola()
        mensaje = extraer_mensaje(_correo_simulado(args.simular, args.desde))
        atender_y_anotar(canal, enviador, mensaje, remitente_propio)
        return

    usuario, contrasena = os.getenv("CORREO_USUARIO", ""), os.getenv("CORREO_CONTRASENA", "")
    if not usuario or not contrasena:
        sys.exit("[correo] Faltan CORREO_USUARIO o CORREO_CONTRASENA: sin buzón no hay nada que sondear.")
    buzon = BuzonIMAP(os.getenv("CORREO_IMAP_HOST", "imap.gmail.com"), usuario, contrasena)
    enviador = EnviadorSMTP(
        os.getenv("CORREO_SMTP_HOST", "smtp.gmail.com"), int(os.getenv("CORREO_SMTP_PUERTO", "587")), usuario, contrasena
    )
    canal = construir_canal()
    estado: dict = {}
    parar = threading.Event()
    hilo = threading.Thread(
        target=bucle_sondeo, args=(canal, buzon, enviador, remitente_propio, args.intervalo, parar, estado), daemon=True
    )
    hilo.start()

    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), crear_manejador(estado))
    print(f"[correo] sondeando {buzon.host} cada {args.intervalo:.0f} s; /salud en :{args.puerto}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        servidor.server_close()


if __name__ == "__main__":
    main()
