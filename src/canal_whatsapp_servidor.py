"""Servidor del webhook de WhatsApp (API de WhatsApp Business de Meta).

Con la librería estándar a propósito: un webhook de dos rutas no justifica
meter un framework web en el AIBOM. Traduce HTTP a `CanalWhatsApp` y de
vuelta, y nada más.

    uv run python -m src.canal_whatsapp_servidor                     # sirve en $PORT (8080)
    uv run python -m src.canal_whatsapp_servidor --simular "¿vacaciones?" --desde 34600000001

Variables de entorno (ver `.env.example` y `docs/CANAL_WHATSAPP.md`):

- `WHATSAPP_TOKEN`: token de acceso de la app de Meta (para enviar).
- `WHATSAPP_PHONE_NUMBER_ID`: identificador del número emisor (el de pruebas).
- `WHATSAPP_VERIFY_TOKEN`: la palabra que Meta manda al suscribir el webhook.
- `WHATSAPP_APP_SECRET`: secreto de la app, para verificar la firma de cada
  webhook. **Sin él, el servidor no arranca**: un webhook sin firma acepta
  mensajes de cualquiera en nombre de cualquier número.
- `WHATSAPP_USUARIOS_JSON`: la lista de números autorizados (o
  `whatsapp.local.json` en disco).

Meta reintenta el webhook si no recibe 200 en pocos segundos, y una consulta
tarda entre tres y ocho. Por eso el servidor contesta 200 en cuanto ha leído
el cuerpo y procesa en un hilo; el canal recuerda los identificadores ya
procesados para que un reintento no genere una segunda respuesta.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import Sistema
from .canal_whatsapp import (
    CanalWhatsApp,
    MensajeEntrante,
    cargar_telefonos,
    extraer_mensajes,
    firma_valida,
    huella,
)
from .config import load_config
from .ingest import asegurar_indice
from .observabilidad import desde_config

VERSION_GRAPH = "v21.0"


class ClienteMeta:
    """Envía mensajes de texto por la API Graph. Solo `urllib`."""

    def __init__(self, token: str, phone_number_id: str, version: str = VERSION_GRAPH):
        self.url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
        self.token = token

    def enviar_texto(self, telefono: str, texto: str) -> dict:
        cuerpo = json.dumps(
            {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "text",
                "text": {"preview_url": False, "body": texto},
            }
        ).encode("utf-8")
        peticion = urllib.request.Request(
            self.url,
            data=cuerpo,
            method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(peticion, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detalle = error.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"Meta devolvió {error.code} al enviar: {detalle}") from error


class EnviadorConsola:
    """Para `--simular`: imprime en vez de enviar."""

    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    def enviar_texto(self, telefono: str, texto: str) -> dict:
        self.enviados.append((telefono, texto))
        print(f"--> a {huella(telefono)}:\n{texto}\n")
        return {"simulado": True}


def construir_canal() -> CanalWhatsApp:
    directorio = cargar_telefonos()
    if directorio.es_de_ejemplo:
        print("[whatsapp] AVISO: lista de números DE EJEMPLO (whatsapp.example.json).", file=sys.stderr)
    configs: dict = {}

    def config_de(tenant_id: str):
        if tenant_id not in configs:
            configs[tenant_id] = load_config(tenant_id, con_juez=False)
        return configs[tenant_id]

    def fabrica(tenant_id: str) -> Sistema:
        cfg = config_de(tenant_id)
        # El índice, antes que el sistema: en Render el disco es efímero y sin
        # esto la primera consulta real del canal terminó en NotFoundError
        # (24-09-2026, ver `asegurar_indice`).
        asegurar_indice(cfg, avisar=lambda m: print(f"[whatsapp] {m}", file=sys.stderr))
        return Sistema(cfg, registro=desde_config(cfg))

    def aviso(tenant_id: str) -> str:
        return config_de(tenant_id).tenant.ai_act.aviso_usuario

    def anotar_desconocido(fila: dict) -> None:
        print(f"[whatsapp] número no autorizado, huella {fila['huella']}", file=sys.stderr)

    return CanalWhatsApp(directorio, fabrica, aviso, registro_desconocidos=anotar_desconocido)


def atender(canal: CanalWhatsApp, enviador, mensaje: MensajeEntrante) -> float:
    """Procesa un mensaje y envía las respuestas. Devuelve la latencia total."""
    t0 = time.perf_counter()
    for texto in canal.procesar(mensaje):
        enviador.enviar_texto(mensaje.telefono, texto)
    return time.perf_counter() - t0


def crear_manejador(canal: CanalWhatsApp, enviador, verify_token: str, app_secret: str):
    class Manejador(BaseHTTPRequestHandler):
        def _responder(self, codigo: int, cuerpo: str = "", tipo: str = "text/plain") -> None:
            datos = cuerpo.encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", f"{tipo}; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, formato, *args):
            # Silencio a propósito: el log de acceso por defecto escribe IPs.
            return

        def do_GET(self):  # nombre que exige BaseHTTPRequestHandler
            url = urllib.parse.urlparse(self.path)
            if url.path == "/salud":
                # Con el commit desplegado (Render lo expone en RENDER_GIT_COMMIT):
                # sin esto no hay forma de saber desde fuera qué versión corre.
                return self._responder(200, f"ok {os.getenv('RENDER_GIT_COMMIT', 'local')[:7]}")
            if url.path != "/webhook":
                return self._responder(404, "no encontrado")
            q = urllib.parse.parse_qs(url.query)
            if q.get("hub.mode") == ["subscribe"] and q.get("hub.verify_token") == [verify_token]:
                return self._responder(200, q.get("hub.challenge", [""])[0])
            return self._responder(403, "verify token incorrecto")

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/webhook":
                return self._responder(404, "no encontrado")
            longitud = int(self.headers.get("Content-Length") or 0)
            cuerpo = self.rfile.read(longitud)
            if not firma_valida(app_secret, cuerpo, self.headers.get("X-Hub-Signature-256")):
                return self._responder(403, "firma inválida")
            try:
                payload = json.loads(cuerpo.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._responder(400, "cuerpo ilegible")
            mensajes = extraer_mensajes(payload)
            # 200 primero, trabajo después: Meta no espera a la respuesta del modelo.
            self._responder(200, "ok")
            for m in mensajes:
                threading.Thread(target=atender, args=(canal, enviador, m), daemon=True).start()

    return Manejador


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simular", help="Procesa este texto en local, sin servidor ni Meta.")
    p.add_argument("--desde", default=None, help="Número emisor del mensaje simulado.")
    p.add_argument("--puerto", type=int, default=int(os.getenv("PORT", "8080")))
    args = p.parse_args()

    canal = construir_canal()

    if args.simular:
        if not args.desde:
            sys.exit("--simular necesita --desde <número>")
        enviador = EnviadorConsola()
        mensaje = MensajeEntrante(
            id=f"sim-{int(time.time())}", telefono=args.desde, tipo="text", texto=args.simular
        )
        latencia = atender(canal, enviador, mensaje)
        print(f"[simulado] {len(enviador.enviados)} mensaje(s) en {latencia:.2f} s")
        return

    faltan = [
        v for v in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET")
        if not os.getenv(v, "").strip()
    ]
    if faltan:
        sys.exit(f"[whatsapp] Faltan variables de entorno: {', '.join(faltan)}. Ver docs/CANAL_WHATSAPP.md.")

    enviador = ClienteMeta(os.environ["WHATSAPP_TOKEN"], os.environ["WHATSAPP_PHONE_NUMBER_ID"])
    manejador = crear_manejador(
        canal, enviador, os.environ["WHATSAPP_VERIFY_TOKEN"], os.environ["WHATSAPP_APP_SECRET"]
    )
    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), manejador)
    print(f"[whatsapp] escuchando en :{args.puerto} (/webhook, /salud)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
