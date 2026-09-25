# Encargo a la app de Claude: token permanente de WhatsApp

> Hoja de instrucciones del encargo supervisado del 25-09-2026. La ejecuta la
> app de Claude con Claude in Chrome **con Juan delante**. El canal ya funciona
> (§51): lo único que falla es que el token de acceso es el temporal de 24 h
> que Meta generó el 24-09 hacia las 11:32, y **caduca hoy a esa hora**. Sin
> uno permanente, el servicio `asistente-whatsapp` seguirá recibiendo mensajes
> pero Meta rechazará las respuestas con `403 (#131005) Access denied`, que es
> exactamente lo que pasó el 24-09 antes de regenerarlo.
>
> **Sobre los secretos.** Misma regla que el 24-09: el token se pega
> **directamente en Render**, no se copia al registro (`registrar_tfm`), no se
> escribe en ningún fichero del repositorio y no se repite en el chat más de lo
> imprescindible. El 24-09 la app no tecleó ningún secreto y lo pegó Juan; ese
> reparto vale también hoy.

## Reglas para la app

- Modo **supervisado**: nada de esto se hace sin Juan en la conversación.
  Antes de cada paso que cambie algo (crear el usuario del sistema, asignar
  activos, generar el token, guardar en Render) decir qué se va a hacer y
  hacerlo solo si Juan no dice lo contrario.
- No inventar valores. Si un menú o un botón no aparece donde dice esta hoja,
  decir dónde se buscó y parar. El panel de Meta cambia de sitio las cosas: la
  hoja del 24-09 acertó el qué y falló el dónde tres veces.
- Anotar la **hora** al terminar cada fase.
- Si algo falla, registrar el fallo con el mensaje literal y en qué paso.

## Fase A: usuario del sistema en Meta (business.facebook.com)

1. Juan entra en <https://business.facebook.com/settings> con su cuenta. Es la
   **configuración del portfolio empresarial** que se creó el 24-09 sin
   verificar; si hay más de un portfolio, elegir el que tiene la app
   `asistente-multitenant-tfm`.
2. *Usuarios > Usuarios del sistema* (en inglés *Users > System users*).
   *Añadir*. Nombre: `asistente tfm sistema`, con espacios (Meta rechazó
   `asistente-tfm-sistema`: "demasiados guiones"). Rol: **Administrador**
   (con *Empleado* hace falta un paso más de asignación y no aporta nada aquí).
   Aceptar las condiciones si las pide.
3. Con el usuario creado, *Asignar activos* (*Add assets*):
   - **Apps** > `asistente-multitenant-tfm` > **Control total** (*Manage app*
     / *Develop app*). Guardar.
   - **Cuentas de WhatsApp** (*WhatsApp accounts*) > la WABA del número de
     pruebas > **Control total**. Guardar. Sin este activo el token se genera
     pero devuelve `403` al enviar.
4. *Generar nuevo token* (*Generate new token*):
   - App: `asistente-multitenant-tfm`.
   - Caducidad: **Nunca** (*Never*). Si el desplegable solo ofrece 60 días,
     elegir 60 días y anotarlo como abierto: cubre la defensa de octubre.
   - Permisos: marcar **`whatsapp_business_messaging`** y
     **`whatsapp_business_management`**. Nada más.
   - *Generar*. Meta lo muestra **una sola vez**: Juan lo copia. No se escribe
     en el chat.
5. Comprobación sin gastar nada: <https://developers.facebook.com/tools/debug/accesstoken>,
   pegar el token y *Debug*. Anotar lo que diga en **Expires** (debe ser
   `Never`) y que en *Scopes* aparecen los dos permisos. Esta es la única
   prueba de que el token es permanente; sin ella no se registra como tal.

Hora de fin de la fase A: anotar.

## Fase B: cambiar el token en Render (dashboard.render.com)

1. Juan entra en Render. Abrir el servicio **`asistente-whatsapp`**
   (URL `https://asistente-whatsapp-n2s9.onrender.com`).
2. *Environment* > editar **`WHATSAPP_TOKEN`** > pegar el nuevo valor >
   *Save changes*. Render **redespliega solo** al guardar variables: anotar la
   hora en que aparece el nuevo deploy y la hora de *Live*. Los dos anteriores
   tardaron 1 min 31 s y 1 min 22 s.
3. No tocar `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`,
   `WHATSAPP_APP_SECRET` ni `WHATSAPP_USUARIOS_JSON`: no cambian con el token.
4. Comprobar <https://asistente-whatsapp-n2s9.onrender.com/salud>: debe decir
   `ok` seguido del commit (`add840a` u otro más nuevo). Si el servicio estaba
   dormido, la primera carga tarda hasta un minuto: esperar y recargar.

Hora de fin de la fase B: anotar, con la duración del despliegue.

## Fase C: comprobar con dos mensajes reales

Es la misma prueba que ya pasó el 24-09 a las 12:03; hoy sirve para
demostrar que el token nuevo envía.

1. Juan, desde su WhatsApp, al número de pruebas de Meta:
   `¿Cuántos días de vacaciones tengo?`. Anotar hora de envío y de respuesta
   (reloj del teléfono). Debe citar el convenio colectivo.
2. `¿Cuál es la retribución bruta anual de Diego Ruíz?`. Debe denegar sin
   dar el dato y con la línea "Retenido por permiso".
3. Si no llega respuesta en dos minutos: *Logs* del servicio en Render. Lo que
   se busca es `403` o `(#131005)` (el token nuevo no tiene la WABA asignada:
   volver a A.3) o `(#131030)` (el número no está en la lista de destinatarios,
   que no debería haber cambiado).

## Fase D: registrar

Llamar a `registrar_tfm` citando este encargo (E-0010), con:

- **hecho**: horas de fin de cada fase, lo que dijo el depurador de tokens en
  *Expires* y *Scopes*, la duración del despliegue, qué devolvió `/salud`, y
  las horas y el contenido resumido de las dos respuestas de WhatsApp. Lo que
  falló, con el mensaje literal.
- **donde**: "usuario del sistema <nombre> en el portfolio de Meta; variable
  `WHATSAPP_TOKEN` del servicio asistente-whatsapp de Render". **Sin ningún
  valor secreto.**
- **abierto**: si el token es de 60 días en vez de permanente, con su fecha
  de caducidad; y cualquier paso que no se llegara a hacer.

Claude Code hace después lo que sigue: leer el registro de producción del
canal, anotar el resultado en `docs/CANAL_WHATSAPP.md` y `docs/HALLAZGOS.md`,
y preparar la prueba de aislamiento con un segundo número.
