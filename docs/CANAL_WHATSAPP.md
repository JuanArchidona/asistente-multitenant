# Canal de WhatsApp

> Punto 13 del bloque 3 de `ALCANCE.md`: *canal de WhatsApp en entorno de
> pruebas*. Construido el 23-09-2026 y **probado con mensajes simulados**;
> la prueba en vivo está pendiente de la cuenta de pruebas de Meta, que solo
> puede crear Juan. Este documento dice qué hace el canal, qué decide, cómo
> se pone en marcha y qué se va a medir cuando esté conectado.

## Qué es y qué no

Es un segundo punto de entrada al **mismo sistema** que la interfaz web:
mismo `Sistema` por inquilino, mismo registro de producción, mismo control
de acceso, misma aprobación humana. No hay lógica de negocio en el canal;
si la hubiera, la web y WhatsApp responderían distinto a la misma persona.

No es un bot de WhatsApp con la cuenta personal de nadie. Usa la **API de
WhatsApp Business de Meta** con su número de pruebas gratuito; automatizar
una cuenta personal con librerías no oficiales viola las condiciones del
servicio y puede costar el número.

## Lo que decide la arquitectura

| Decisión | Por qué |
|---|---|
| **El número es la credencial.** Una lista cerrada (`whatsapp.local.json` o `WHATSAPP_USUARIOS_JSON`) dice qué persona, inquilino y roles hay detrás de cada número | Meta ya verifica el emisor. Lo que no puede hacer es decir de qué cliente es: eso lo fija la lista, igual que en la web lo fija la credencial. Dos números de dos clientes nunca comparten `Sistema` |
| **Un número desconocido no llega al modelo** | Recibe una frase fija, no cuesta una llamada y se anota por su huella SHA-256, no en claro |
| **El artículo 50 va en el primer mensaje** de cada conversación y se repite tras 24 horas de silencio | En la web el aviso está siempre en pantalla; en un chat, repetirlo en cada mensaje es ruido y no ponerlo nunca es incumplir |
| **La aprobación humana es por texto**: `APROBAR ACC-xxxxxx` o `RECHAZAR ACC-xxxxxx` | Pasa por el mismo `aprobar` y `rechazar` del agente (§42), con el mismo control de rol y el mismo registro. El modelo nunca ejecuta una escritura desde el canal |
| **La firma del webhook se verifica** con el secreto de la app y el servidor **no arranca sin él** | Sin firma, quien conozca la URL inyecta mensajes en nombre de un número autorizado. Es el control de acceso del canal |
| **Se contesta 200 antes de procesar** y se recuerdan los identificadores ya atendidos | Meta reintenta si no hay 200 en pocos segundos y una consulta tarda entre 3 y 8; sin memoria de identificadores, cada reintento sería una respuesta duplicada y una llamada pagada dos veces |
| **El teléfono no se escribe en el registro de producción** | Al registro va el identificador de usuario de la lista, como en la web. El número es dato personal de quien escribe, y el registro se conserva 90 días (`RETENCION.md`) |
| **Sin framework web**: `http.server` de la librería estándar | Dos rutas no justifican una dependencia nueva en el AIBOM |

## Puesta en marcha

### Lo que tiene que hacer Juan (una vez; en la práctica, 70 minutos)

> **Hecho el 24-09-2026** por la app de Claude con Juan delante (encargo
> E-0009). Los pasos de abajo eran los previstos; lo que Meta pidió de
> verdad está en la lista *Lo que no estaba en el guion*, al final de esta
> sección, y es lo que hay que leer antes de repetirlo.

1. En [developers.facebook.com](https://developers.facebook.com) crear una
   **app de tipo Business** y añadirle el producto **WhatsApp**. Meta asigna
   un **número de pruebas** gratuito y un `Phone number ID`.
2. En *API Setup*, añadir tu número personal como **destinatario de
   pruebas** (hasta cinco) y confirmar el código que llega por WhatsApp.
3. Generar un **token de acceso**. El temporal caduca en 24 horas y sirve
   para la primera prueba. El que queda es el de **usuario del sistema**
   desde *Business Settings*: usuario con rol administrador, la app y la
   WABA asignadas con control total, token con caducidad *Nunca* y solo los
   permisos `whatsapp_business_messaging` y `whatsapp_business_management`.
   Se comprueba en el depurador de tokens de Meta (*Caduca: Nunca*), y no
   se da por permanente sin esa comprobación. Hecho el 25-09-2026 (E-0010).
4. Anotar el **App Secret** (*App Settings > Basic*).
5. Elegir una palabra cualquiera como `WHATSAPP_VERIFY_TOKEN`.
6. Desplegar el servicio (abajo) y, en *Configuration > Webhook*, poner la
   URL `https://<servicio>/webhook`, la palabra de verificación, y
   suscribir el campo `messages`.
7. Pasar los cuatro valores por variables de entorno, **nunca por el
   chat ni por el repositorio**.

**Lo que no estaba en el guion, y Meta exigió el 24-09-2026:**

- El flujo actual de Meta no pregunta el tipo de app: pregunta el **caso de
  uso** ("Conecta con los clientes a través de WhatsApp"), y ese caso exige
  un **portfolio empresarial**; vale uno sin verificar. Las condiciones se
  aceptan dos veces (app y Cloud API).
- **Sin publicar la app, solo llegan los webhooks de prueba del panel.** Los
  mensajes reales no llegan aunque el webhook esté verificado. Publicar
  exige una **URL de política de privacidad**; se redactó una a partir de
  este documento y de `RETENCION.md` y se publicó como página pública desde
  la app de Claude. Con un cliente real esa política tiene que ser la del
  cliente, en su dominio.
- Publicada la app, los mensajes **tampoco llegan hasta suscribir la cuenta
  de WhatsApp Business (WABA) a la app**: `POST /{WABA_ID}/subscribed_apps`
  con el token, desde una terminal. El panel no lo hace solo.
- Un token temporal generado antes de publicar puede devolver `403 (#131005)
  Access denied` al enviar; se regenera después de publicar.
- **Del usuario del sistema, el 25-09-2026:** Meta rechaza el nombre con
  guiones ("Los nombres del perfil no pueden tener demasiados guiones"), así
  que el usuario se llama `asistente tfm sistema`, con espacios. Pide
  aceptar una política de no discriminación antes de crearlo. El depurador
  de tokens **pone el token en la URL** (`?access_token=...`) y queda en el
  historial del navegador: hay que borrar esa entrada después. El token
  temporal anterior no se revocó a mano; caduca solo.
- La URL del servicio la asigna Render con sufijo:
  `https://asistente-whatsapp-n2s9.onrender.com`. `/salud` responde `ok` y
  el commit desplegado.
- El webhook de prueba del panel usa un número ficticio; el servicio lo
  rechaza como no autorizado (huella en la salida) y, al intentar contestarle
  la frase fija, Meta devuelve `400 (#131030)` porque en modo de pruebas solo
  se puede escribir a los destinatarios registrados. No es un fallo del canal:
  es el comportamiento previsto (un número desconocido recibe una frase
  fija) contra una restricción del número de pruebas.
- **Y el fallo propio**: las dos primeras consultas reales devolvieron
  `NotFoundError`, porque el servidor no construía el índice de Chroma y el
  disco de Render es efímero. `app.py` y el banco lo hacían; el servidor no.
  Corregido el mismo día (`asegurar_indice` en `src/ingest.py`, que llaman
  los tres puntos de entrada) y reproducido antes en local con un
  `CHROMA_PATH` vacío; `HALLAZGOS.md` §51.

Tiempos medidos por la app ese día (hora de Madrid): fase A (Meta) hasta las
10:20; despliegue en Render 1 min 31 s y, tras cambiar el token, 1 min 22 s;
webhook verificado a la primera a las 10:51; primer mensaje real que llegó
al servicio, 11:27, recibido a las 11:28:18; primera respuesta (con el
NotFoundError) a las 11:35, en el mismo minuto que la pregunta.

El 25-09-2026, el cambio al token de usuario del sistema (E-0010, también por
la app de Claude con Juan delante): encargo abierto a las 07:15, usuario
creado a las 07:21, activos asignados a las 07:24, token emitido a las
07:25:25 (*Caduca: Nunca*, tipo *System User*), despliegue en Render de
1 min 35 s con `/salud` en `ok 3fe6161` a las 07:31:25, y las dos preguntas
de control respondidas en el mismo minuto (07:32 y 07:33): vacaciones
citando el convenio, salario denegado con "Retenido por permiso". Dieciocho
minutos de reloj en total, sin ningún `403`.

El mismo día se midió lo que cuesta despertar el servicio en el plan
gratuito (§52): **42-61 s** la primera petición tras 20 minutos sin tráfico
(52 s tras una noche), menos de 0,2 s las siguientes, y ningún webhook se
pierde mientras despierta: espera. Por eso el guion de la demo manda una
pregunta al canal antes de empezar.

### Variables

```
WHATSAPP_TOKEN=            # token de acceso de la app
WHATSAPP_PHONE_NUMBER_ID=  # id del número emisor de pruebas
WHATSAPP_VERIFY_TOKEN=     # la palabra que Meta manda al suscribir el webhook
WHATSAPP_APP_SECRET=       # secreto de la app: verifica la firma de cada webhook
WHATSAPP_USUARIOS_JSON=    # la lista de números (formato: whatsapp.example.json)
```

### Ejecutar

```bash
uv run python -m src.canal_whatsapp_servidor                 # escucha en $PORT (8080)
uv run python -m src.canal_whatsapp_servidor --simular "¿Cuántos días de vacaciones tengo?" --desde 34600000001
```

`--simular` procesa un mensaje en local con el sistema real y sin Meta: es
lo que se usó para medir antes de tener credenciales. Cuesta una consulta.

En Render, `render.yaml` declara un segundo servicio (`asistente-whatsapp`)
con el mismo repositorio y este arranque. El blueprint se sincroniza solo
con cada push, así que el servicio **ya existe y aparece en rojo**: se creó
al publicar el fichero y falló a propósito porque no tenía las variables de
arriba (el servidor sale con `[whatsapp] Faltan variables de entorno: ...`).
Está con `autoDeploy: false` para que no vuelva a intentarlo con cada push;
cuando existan las credenciales, se rellenan en el servicio y se despliega a
mano desde el dashboard. Hasta entonces se puede suspender. En local, para que Meta llegue
al portátil hace falta un túnel (`ngrok http 8080`), y la URL cambia en cada
arranque.

## Lo que se va a medir cuando esté conectado

| Medida | Cómo |
|---|---|
| **Aislamiento por número** | Dos números de dos inquilinos preguntan lo mismo; las respuestas citan corpus distintos y el registro las atribuye a usuarios distintos |
| **Latencia de extremo a extremo** | Desde que se envía el mensaje hasta que llega la respuesta, con el reloj del teléfono; y por dentro, la del sistema, que ya está en la traza |
| **Coste por mensaje** | El del registro de producción; el de WhatsApp es cero en la ventana de servicio de 24 horas del número de pruebas |
| **Aprobación humana por texto** | Proponer una visita, `APROBAR`, y ver la referencia `VIS-*` en el CRM y las tres líneas en el registro (§42) |
| **Rechazo de un número desconocido** | Un tercer número escribe y recibe la frase fija; en el registro no hay consulta y en la salida del servidor hay una huella |

**Medido el 24-09-2026 tras el redespliegue** (§51): las dos preguntas de
la hoja respondieron en el mismo minuto de enviarse, la de vacaciones con
la misma respuesta que la web y la del salario con la denegación sin el
dato; aviso de IA en el primer mensaje; la línea "Retenido por permiso" en
las dos. Sin medir todavía: la latencia interna, el aislamiento con dos
números y la aprobación por texto en vivo.

**La latencia interna no se podía leer, y desde el 25-09-2026 sí.** El
servidor la calculaba en `atender` y el hilo del webhook la tiraba; el
registro de producción la guarda, pero en el disco efímero de Render, que en
el plan gratuito no tiene consola. Ahora cada mensaje deja **una línea en la
salida del proceso**, que es lo que enseñan los *Logs* de Render:

```
[whatsapp] mensaje huella=cdbfd7222d15 tenant=empresa_servicios respuestas=1 latencia=6.53 s
[whatsapp] mensaje huella=... tenant=agencia_inmobiliaria ERROR RuntimeError: Meta devolvió 403 al enviar: ... tras 4.10 s
```

La latencia es del webhook recibido a la última respuesta entregada a Meta:
incluye enrutado, recuperación, generación y el envío, y excluye el tramo
Meta-teléfono en los dos sentidos. Restada de la de extremo a extremo del
reloj del teléfono, da lo que cuesta el canal frente a lo que cuesta el
sistema. Lleva huella e inquilino, nunca el teléfono; un fallo al enviar
queda con su tipo y su mensaje recortado en vez de morir en el hilo.

## Riesgos que abre, y dónde están

- **Transferencia internacional (R-18)**: cada mensaje pasa por Meta. Con
  datos sintéticos no importa; con un cliente real exige base jurídica y
  las condiciones de tratamiento de WhatsApp Business. Está en el registro.
- **Vigilancia (R-16)**: el registro ya no guarda solo quién preguntó, sino
  que la persona escribió desde un teléfono. El teléfono no se guarda; la
  correspondencia número-usuario vive en la lista, que es configuración.
- **Suplantación**: la firma del webhook cubre el camino Meta-servidor; el
  camino persona-teléfono depende de que el teléfono sea de quien dice. Es
  el mismo supuesto que hace un banco con un SMS, y se escribe, no se
  resuelve.
- **Coste**: un número autorizado puede preguntar sin límite. El tope blando
  de la interfaz aplica también aquí (`TOPE_GASTO_USD`), y el duro es el
  prepago. No hay límite por número ni por minuto, como tampoco lo hay por
  usuario en la web (R-08).
