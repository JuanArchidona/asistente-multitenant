# Canal de correo

> Punto 11 del bloque 2 de `ALCANCE.md`: *canal de correo, de extremo a
> extremo*. Construido el 26-09-2026 con correos simulados y **pendiente de
> conectar a un buzón real**, que crea Juan (hoja en
> `docs/ENCARGO_CORREO_2026-09-26.md`). Este documento dice qué hace el canal,
> qué decide, en qué se diferencia de WhatsApp, cómo se pone en marcha y qué
> se va a medir cuando esté conectado.

## Qué es y qué no

Es la tercera puerta al mismo sistema, después de la interfaz web (`app.py`)
y de WhatsApp (`src/canal_whatsapp.py`). No hay una versión de correo del
asistente: hay un servidor que lee un buzón, convierte cada correo en una
consulta al `Sistema` del inquilino que corresponde, y devuelve la respuesta
como un correo enhebrado en la misma conversación. El enrutador, la
recuperación con el permiso en el `where`, la redacción de campos, el
generador, la aprobación humana y el registro de producción son los mismos
que en las otras dos puertas, y lo comprueban las mismas pruebas del banco.

Lo que **no** es: un buzón de atención al cliente. Solo responde a
direcciones de una lista cerrada, que son empleados del inquilino.

## Lo que decide la arquitectura

| Decisión | Por qué |
|---|---|
| **La dirección del remitente es la credencial.** Una lista cerrada (`correo.local.json` o `CORREO_USUARIOS_JSON`) dice qué persona, inquilino y roles hay detrás de cada dirección | Igual que el número en WhatsApp y la credencial en la web. Una dirección que no está recibe una frase fija y **no llega al modelo**: ni enrutado, ni recuperación, ni coste |
| **Se exige autenticación del remitente** (`Authentication-Results` con `dkim=pass` o `spf=pass`), y sin ella el correo de una dirección autorizada se rechaza con una frase fija y se anota por huella | Esta es la diferencia con WhatsApp: Meta verifica el número, pero un remitente de correo **se puede falsificar**. La cabecera la escribe el servidor que recibe el correo (Gmail en el despliegue), no quien lo envía, así que no se falsifica desde fuera del buzón. Es el control de acceso del canal, como la firma del webhook en WhatsApp (R-24) |
| **El inquilino lo fija la dirección.** Dos direcciones de dos clientes nunca comparten `Sistema` | Aislamiento estructural, el mismo del capítulo 2.3 de la memoria |
| **El modelo nunca escribe.** Una escritura propuesta se describe y se pide `APROBAR <id>` o `RECHAZAR <id>` **en la primera línea** de la respuesta | La misma aprobación humana de la web y de WhatsApp (§42); la primera línea, porque el resto del correo suele ser la cita del mensaje anterior |
| **Artículo 50 del AI Act** en el primer correo de cada conversación, y de nuevo tras 24 horas de silencio | El mismo criterio que en WhatsApp, con el aviso que declara cada manifiesto |
| **La dirección no se escribe en ningún registro.** Al registro de producción va el identificador de usuario de la lista; las direcciones desconocidas o sin autenticar se anotan por su huella (SHA-256 recortado) | La dirección es dato personal; la huella permite contar intentos sin guardar quién |
| **Un correo leído dos veces no produce dos respuestas.** El canal recuerda los `Message-ID` procesados, y el servidor lee con `BODY.PEEK[]` y marca como leído solo después de responder | Un sondeo que se solape con el anterior, o un fallo a mitad, no deben duplicar |
| **La respuesta enhebra** (`In-Reply-To`, `References`, `Re:` en el asunto) | Para que el cliente de correo la muestre debajo de la pregunta, y para que la orden de aprobación llegue con el hilo entero |
| **La cita del correo anterior y la firma se quitan antes de consultar** | Si volvieran a entrar, el modelo respondería dos veces a lo mismo; y la orden `APROBAR` viaja siempre encima de la cita |
| **Sin paquetes nuevos**: `imaplib`, `smtplib`, `email` y `http.server` | Un sondeo de un buzón no justifica una dependencia en el AIBOM |

## Lo que cambia respecto a WhatsApp, en corto

| | WhatsApp | Correo |
|---|---|---|
| Quién verifica al emisor | Meta, antes de llamar al webhook | El servidor de correo receptor, en `Authentication-Results`; el canal lo exige |
| Cómo llegan los mensajes | Webhook firmado (empuja Meta) | Sondeo IMAP cada 30 s (pregunta el servidor) |
| Latencia añadida por el canal | Ninguna | Hasta un intervalo de sondeo |
| Longitud | 4.096 caracteres, se trocea | Sin límite práctico, un solo correo |
| Aprobación | `APROBAR <id>` como mensaje | `APROBAR <id>` en la primera línea de la respuesta |
| En el plan gratuito de Render | El webhook despierta al servicio | **Nada lo despierta**: dormido, no sondea (ver límites) |

## Puesta en marcha

### Lo que tiene que hacer Juan (una vez)

Está en `docs/ENCARGO_CORREO_2026-09-26.md`, en corto: crear una cuenta de
Gmail dedicada al asistente, activar la verificación en dos pasos, generar
una **contraseña de aplicación**, y pegar usuario, contraseña y la lista de
direcciones autorizadas en las variables del servicio `asistente-correo` de
Render. Las direcciones autorizadas son las de Juan: la misma persona con
varias direcciones puede probar varios inquilinos.

### Variables

| Variable | Qué es |
|---|---|
| `CORREO_USUARIO` | La dirección del buzón dedicado; también es el remitente de las respuestas |
| `CORREO_CONTRASENA` | Contraseña de aplicación de Gmail. Sin usuario y contraseña el servidor no arranca |
| `CORREO_IMAP_HOST`, `CORREO_SMTP_HOST`, `CORREO_SMTP_PUERTO` | `imap.gmail.com`, `smtp.gmail.com`, `587` (STARTTLS) |
| `CORREO_INTERVALO_S` | Cada cuántos segundos se mira el buzón; 30 por defecto |
| `CORREO_USUARIOS_JSON` | La lista de direcciones (formato `correo.example.json`); si falta, `correo.local.json`, y si tampoco, el de ejemplo, avisando |

### Ejecutar

```bash
# Sin buzón: un correo simulado con cabecera de autenticación, contra el sistema real
uv run python -m src.canal_correo_servidor --simular "¿Cuántos días de vacaciones tengo?" --desde empleado@ejemplo.es

# Con buzón: sondea y sirve /salud en $PORT
uv run python -m src.canal_correo_servidor
```

`/salud` devuelve el commit desplegado, cuánto hace del último sondeo, cuántos
correos se han atendido desde el arranque y el último error de sondeo si lo
hubo. Cada correo atendido deja **una línea** en la salida del proceso, sin la
dirección:

```
[correo] mensaje huella=3aec8df8baa6 tenant=empresa_servicios respuestas=1 latencia=5.26 s
[correo] remitente sin_autenticar, huella 9f1c...
```

**Medido en simulación el 26-09-2026**, un correo contra el sistema real
(`--simular`, sin buzón): la pregunta de vacaciones respondió en 5,26 s de
latencia interna con el aviso de IA, la cita del convenio y la línea
"Retenido por permiso" del anexo; 34 pruebas con correos simulados en
`tests/test_canal_correo.py`.

## Lo que se va a medir cuando esté conectado

| Medida | Cómo |
|---|---|
| **Latencia de extremo a extremo** | Desde que se envía el correo hasta que llega la respuesta, con la hora de las cabeceras `Date`; y por dentro, la de la línea de registro |
| **Coste por correo** | El del registro de producción; el buzón de Gmail es gratuito |
| **Rechazo de un remitente falsificado** | Un correo con el `From` de una dirección autorizada enviado desde un servidor que no firma: tiene que llegar con `dkim=fail` o sin `pass`, recibir la frase fija y no generar consulta |
| **Rechazo de una dirección desconocida** | Una dirección que no está en la lista escribe y recibe la frase fija; huella en la salida, nada en el registro |
| **Aprobación humana por correo** | Proponer una visita desde la dirección de gerencia, responder `APROBAR <id>` en la primera línea, y ver la referencia `VIS-*` y las tres líneas del registro (§42) |
| **Un correo, una respuesta** | Enviar dos veces el mismo correo (reenvío con el mismo `Message-ID`) y comprobar que solo hay una respuesta |

## Límites, y dónde están declarados

- **Dormido no sondea.** En el plan gratuito de Render el servicio se duerme
  sin tráfico HTTP (§52) y el hilo de sondeo se duerme con él; a diferencia
  de WhatsApp, un correo nuevo no lo despierta. Consecuencia: un correo
  enviado al servicio dormido se atiende cuando algo lo despierte, no a los
  30 s. Lo arregla el plan de pago (capítulo 5.4 de la memoria), no el
  código. Es un límite del despliegue, no del canal, y va al capítulo 9.
- **La autenticación depende del proveedor del buzón.** Si el buzón no
  escribiera `Authentication-Results`, todos los correos se rechazarían; con
  Gmail la escribe siempre. Un despliegue con otro proveedor tiene que
  comprobarlo antes.
- **Solo texto.** Los adjuntos se ignoran; un correo solo HTML se convierte
  a texto quitando etiquetas.
- **Un correo que no se puede responder se marca como leído igualmente**,
  con el fallo en la línea de registro: reintentarlo sin fin bloquearía el
  buzón.

## Riesgos que abre, y dónde están

- **Suplantación del remitente**: R-24 en `RIESGOS.md`, control por
  `Authentication-Results`; medido en simulación, pendiente en vivo.
- **Salida insegura** (R-20): la respuesta viaja por correo y puede acabar
  reenviada; sigue siendo texto para una persona, y el registro no guarda la
  respuesta.
- **Credenciales del buzón**: una contraseña de aplicación con acceso
  completo al buzón, en las variables de Render. Si se filtra, el plan de
  incidentes (`INCIDENTES.md`) aplica igual que a las claves de API: revocar
  en la cuenta de Google y cambiar en Render.
