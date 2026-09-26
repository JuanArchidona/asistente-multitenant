# Encargo: buzón dedicado para el canal de correo

> Hoja de instrucciones para conectar el canal de correo
> (`docs/CANAL_CORREO.md`) a un buzón real. La puede seguir Juan a mano o la
> app de Claude con Claude in Chrome **con Juan delante**, como los encargos
> E-0009 y E-0010. El canal ya funciona con correos simulados; lo único que
> falta es un buzón y sus credenciales.
>
> **Sobre los secretos.** La contraseña de aplicación se pega **directamente
> en Render**, no se copia al registro (`registrar_tfm`), no se escribe en
> ningún fichero del repositorio y no se repite en el chat. Quien la genera
> la pega; la app no la teclea.

## Decisiones ya tomadas (26-09-2026)

- **Cuenta de Gmail nueva y dedicada**, no el correo personal de Juan: el
  servidor lee la bandeja entera y responde en nombre del buzón.
- **La dirección del remitente es la credencial**, con lista cerrada: las
  direcciones autorizadas son las de Juan (una por inquilino que quiera
  probar), no las del buzón dedicado.
- **Gmail** porque escribe `Authentication-Results` (DKIM, SPF) en cada
  correo recibido, que es lo que el canal exige para atender.

## Fase A: la cuenta (Google, unos 10 minutos)

1. Crear una cuenta de Gmail nueva. Nombre sugerido:
   `asistente.multitenant.tfm@gmail.com` (si está ocupado, cualquier
   variante; anotar la que sea). No es necesario número de teléfono
   propio si Google no lo exige; si lo exige, es el de Juan.
2. Activar la **verificación en dos pasos** de esa cuenta
   (*Gestionar tu cuenta de Google > Seguridad > Verificación en dos
   pasos*). Sin ella Google no permite crear contraseñas de aplicación.
3. Crear una **contraseña de aplicación** (*Seguridad > Verificación en dos
   pasos > Contraseñas de aplicaciones*, o buscando "Contraseñas de
   aplicaciones" en el buscador de la cuenta). Nombre: `asistente-correo`.
   Google muestra 16 caracteres una sola vez: copiarlos para el paso B.2.
4. Comprobar que IMAP está permitido: en Gmail, *Configuración > Ver todos
   los ajustes > Reenvío y correo POP/IMAP > Habilitar IMAP*. En las cuentas
   nuevas suele estar habilitado; anotar cómo estaba.
5. Anotar la hora al terminar.

## Fase B: el servicio en Render (unos 10 minutos)

1. El servicio `asistente-correo` lo crea el blueprint `render.yaml` al
   sincronizarse y **falla a propósito** hasta que existan las credenciales,
   igual que hizo el de WhatsApp. En el dashboard: servicio
   `asistente-correo` > *Environment*.
2. Rellenar (valores marcados `sync: false` en el blueprint):
   - `CORREO_USUARIO`: la dirección de la cuenta creada en A.1.
   - `CORREO_CONTRASENA`: la contraseña de aplicación de A.3. **La pega
     Juan.**
   - `CORREO_USUARIOS_JSON`: la lista de direcciones autorizadas, con el
     formato de `correo.example.json`. Mínimo, una dirección de Juan para
     `empresa_servicios` sin roles (`usuario: "empleado"`) y otra, si tiene,
     para `agencia_inmobiliaria` con `roles: ["direccion"]` (`usuario:
     "gerencia"`). Los identificadores de usuario son los que aparecen en el
     registro de producción; las direcciones no aparecen nunca.
3. Guardar. Render redespliega solo (`autoDeploy` está en verdadero para
   este servicio). Anotar la hora de inicio y de *Live* del despliegue y su
   duración.
4. Abrir `https://asistente-correo-<sufijo>.onrender.com/salud` (la URL
   real la asigna Render; anotarla). Tiene que decir `ok <commit>` y, tras
   el primer sondeo, `ultimo_sondeo_hace_s=...`. Si dice `ultimo_error=`,
   copiar el texto literal: un `535` es credencial mal pegada; un
   `AUTHENTICATIONFAILED` de IMAP, lo mismo o IMAP deshabilitado.

## Fase C: los correos de prueba (con el reloj del correo)

Desde la dirección autorizada de `empresa_servicios`, al buzón dedicado:

1. Asunto `Consulta`, cuerpo `¿Cuántos días de vacaciones tengo?`. Anotar
   la hora de envío y la de la respuesta (cabecera `Date` de cada uno, que
   tiene precisión de segundo). La respuesta debe abrir con el aviso de IA
   entre corchetes, citar el convenio y terminar con "Retenido por permiso".
2. Responder a ese mismo hilo con `¿Cuál es la retribución bruta anual de
   Diego Ruíz?`. La respuesta debe denegar sin la cifra y **sin** el aviso
   de IA (misma conversación, menos de 24 h).
3. Desde una dirección que **no** esté en la lista, cualquier texto: debe
   llegar la frase "Esta dirección no está dada de alta" y en los *Logs* de
   Render una línea `remitente desconocido, huella ...`.
4. Si hay dirección de gerencia: `Registra una visita al inmueble
   INM-2026-147 el 2026-10-02 a las 10:00 para Marta Pérez Soria con Iván
   Belsué`; la respuesta propone y pide `APROBAR ACC-xxxxxx`. Responder con
   esa línea como primera línea. La respuesta debe traer la referencia
   `VIS-*`.
5. En los *Logs* de Render, copiar las líneas `[correo] mensaje ...` de cada
   correo: traen huella, inquilino y latencia interna. Ni la dirección ni el
   texto del correo aparecen; si aparecieran, es un fallo que hay que
   registrar.

## Fase D: registrar (sin secretos)

En `registrar_tfm` (o en la bitácora si lo hace Juan a mano): horas de A, B
y C; URL del servicio; duración del despliegue; las respuestas de C.1 a C.4
literales; las líneas de registro de C.5; lo que no salió como decía esta
hoja, con el mensaje literal. Nunca la contraseña, nunca las direcciones
personales en claro.

## Lo que no se hace

- No se conecta el correo personal de Juan.
- No se toca el servicio de WhatsApp ni el de la interfaz.
- No se registra ninguna dirección de una persona que no sea Juan.
