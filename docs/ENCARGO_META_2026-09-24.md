# Encargo a la app de Claude: alta en Meta y primera prueba en vivo de WhatsApp

> Hoja de instrucciones del encargo supervisado del 24-09-2026. La ejecuta la
> app de Claude con Claude in Chrome **con Juan delante**: Juan inicia sesión,
> pasa las verificaciones y recibe los códigos; la app navega, rellena y
> comprueba. Lo que hay que construir ya existe (`src/canal_whatsapp_servidor.py`,
> servicio `asistente-whatsapp` en Render); esto es conectarlo a Meta y
> mandar el primer mensaje real.
>
> **Sobre los secretos.** Juan decidió el 24-09-2026 que no hay problema en
> que un token o un secreto aparezca en pantalla durante este encargo. Aun
> así: los valores se pegan **directamente en Render**, no se copian al
> registro (`registrar_tfm`), no se escriben en ningún fichero del
> repositorio y no se repiten en el chat más de lo imprescindible.

## Reglas para la app

- Modo **supervisado**: nada de esto se hace sin Juan en la conversación.
  Antes de cada paso que cambie algo (crear la app de Meta, guardar
  variables, desplegar, guardar el webhook), decir qué se va a hacer y
  hacerlo solo si Juan no dice lo contrario.
- No inventar valores. Si un identificador no aparece donde se espera, decir
  dónde se buscó y parar.
- Anotar la **hora** (la que muestre el reloj del sistema o el propio
  dashboard) al terminar cada fase: es lo que después se mide.
- Si algo falla, registrar el fallo con el mensaje literal y en qué paso.
  Un encargo que se registra a medias vale más que uno que no se registra.

## Fase A: la app de Meta (developers.facebook.com)

1. Juan entra en <https://developers.facebook.com> con su cuenta y pasa la
   verificación en dos pasos si la hay.
2. *My Apps > Create App*. Tipo **Business**. Nombre sugerido:
   `asistente-multitenant-tfm`. Contacto: el correo de Juan. Sin portfolio de
   negocio si no lo pide como obligatorio.
3. En el panel de la app, *Add product* > **WhatsApp** > *Set up*.
4. En *WhatsApp > API Setup*:
   - Anotar el **Phone number ID** del número de pruebas (*From*). Es un
     número largo, no el teléfono.
   - En *To*, **añadir el número personal de Juan** como destinatario de
     pruebas. Meta manda un código por WhatsApp a ese teléfono; Juan lo lee y
     la app lo introduce.
   - Generar el **token de acceso temporal** (botón *Generate access token*;
     caduca en 24 horas, suficiente para la primera prueba). Copiarlo para
     la fase B. Si Juan quiere uno permanente para la defensa, es *Business
     Settings > System users*; no hace falta hoy.
5. En *App Settings > Basic*: mostrar el **App Secret** (*Show*) y copiarlo
   para la fase B.
6. Elegir una palabra de verificación cualquiera (por ejemplo tres palabras
   sin espacios) y guardarla para las fases B y C: es `WHATSAPP_VERIFY_TOKEN`.

Hora de fin de la fase A: anotar.

## Fase B: variables y despliegue en Render (dashboard.render.com)

1. Juan entra en Render. Abrir el servicio **`asistente-whatsapp`** (aparece
   en rojo o suspendido: es lo esperado, no tiene credenciales todavía).
2. *Environment*. Rellenar estas variables con los valores de la fase A:
   - `WHATSAPP_TOKEN`: el token de acceso.
   - `WHATSAPP_PHONE_NUMBER_ID`: el Phone number ID.
   - `WHATSAPP_VERIFY_TOKEN`: la palabra elegida.
   - `WHATSAPP_APP_SECRET`: el App Secret.
   - `WHATSAPP_USUARIOS_JSON`: la lista de números autorizados, en una sola
     línea, con el número personal de Juan **en formato internacional sin
     el signo más ni espacios** (España: `34` seguido de los nueve dígitos).
     Primera prueba como empleado sin privilegios del inquilino heredado:

     ```
     {"numeros":[{"telefono":"34XXXXXXXXX","usuario":"juan_whatsapp","nombre":"Juan (pruebas WhatsApp)","tenant":"empresa_servicios","roles":[]}]}
     ```

   - `ANTHROPIC_API_KEY` y `GEMINI_API_KEY`: las mismas que ya tiene el
     servicio `asistente-multitenant`. Se copian de allí (Render las muestra
     en su *Environment*).
   Guardar.
3. *Manual Deploy > Deploy latest commit*. Anotar la hora de inicio y la de
   *Live*. El primer despliegue del otro servicio tardó 1 min 32 s (§38).
4. Comprobar que responde: abrir
   <https://asistente-whatsapp-n2s9.onrender.com/salud> (Render añade un sufijo al nombre; la URL exacta está en el dashboard del servicio). Tiene que decir `ok`.
   Si el servicio no arranca, *Logs* dirá `[whatsapp] Faltan variables de
   entorno: ...` con cuáles: es la comprobación de arranque, no un error del
   despliegue.

Hora de fin de la fase B: anotar, con la duración del despliegue.

## Fase C: el webhook en Meta

1. Volver a la app de Meta: *WhatsApp > Configuration > Webhook > Edit*.
2. *Callback URL*: `https://asistente-whatsapp-n2s9.onrender.com/webhook` (la URL del servicio en Render, más `/webhook`).
   *Verify token*: la palabra de la fase A. *Verify and save*. Meta llama al
   servicio con un `hub.challenge`; si el servicio está dormido (plan
   gratuito) la primera llamada puede tardar unos 30 s en responder y Meta
   puede dar error: esperar medio minuto y repetir.
3. En *Webhook fields*, **suscribir `messages`** (*Subscribe*).

Hora de fin de la fase C: anotar.

## Fase D: el primer mensaje real

1. Juan, desde su WhatsApp, escribe al número de pruebas de Meta (el *From*
   de la fase A): `¿Cuántos días de vacaciones tengo?`. Anotar la hora de
   envío con el reloj del teléfono.
2. Debe llegar primero el aviso de que se habla con una IA (artículo 50, en
   el primer mensaje de cada conversación) y después la respuesta, que cita
   `convenio_colectivo.md`. Anotar la hora de llegada.
3. Si no llega nada en un minuto: *Logs* del servicio en Render. Lo que se
   busca es una línea con la consulta recibida, o un error de firma
   (`X-Hub-Signature-256`), o nada (el webhook no está llegando: revisar C).
4. Segundo mensaje, para el control de acceso: `¿Cuál es la retribución
   bruta anual de Diego Ruíz?`. Como empleado sin privilegios debe recibir
   una denegación explícita, no el dato.

## Fase E: registrar

Llamar a `registrar_tfm` citando este encargo, con:

- **hecho**: las horas de fin de cada fase, la duración del despliegue, si
  `/salud` respondió, si el webhook se verificó a la primera, las dos horas
  del primer mensaje (envío y respuesta) y qué contestó el sistema en las
  dos preguntas (resumido). Lo que falló, con el mensaje literal.
- **donde**: "variables en el servicio asistente-whatsapp de Render; app de
  Meta <nombre>". **Sin ningún valor secreto.**
- **abierto**: lo que no se llegó a hacer, y si el token es el temporal de
  24 horas (entonces caduca mañana y hay que regenerarlo antes de la
  siguiente prueba).

Claude Code hace después lo que sigue: leer el registro de producción del
canal, medir la latencia de extremo a extremo contra la interna, repetir con
un segundo número de otro inquilino y escribir el hallazgo.
