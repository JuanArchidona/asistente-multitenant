# Encargo a la app de Claude: leer la latencia interna de WhatsApp en Render

> Hoja de instrucciones del encargo supervisado del 27-09-2026. La ejecuta la
> app de Claude con Claude in Chrome **con Juan delante**. Motivo: la revisión
> hostil del 26-09 dejó una sola corrección sin aplicar, la M5
> (`docs/REVISION_MEMORIA_2026-09-26.md`): la memoria dice que el servidor de
> WhatsApp deja una línea por mensaje con su latencia interna, pero **nadie la
> ha leído nunca en producción**. La línea existe desde `39fd125` (25-09,
> 08:03), media hora después de los dos mensajes de control de E-0010, así
> que lo más probable es que en los Logs no haya ninguna todavía. De paso
> sustituye la única cifra de WhatsApp con N=1 y sin traza (5,1 s, M16).
>
> **Coste:** tres consultas reales, unos 0,006 USD de Anthropic.
>
> **Sobre los datos.** Las líneas del log llevan una **huella** del teléfono
> (SHA-256 recortado), nunca el número. Se pueden copiar literales al registro.
> El número de teléfono de Juan no se escribe en ningún sitio.

## Reglas para la app

- Modo **supervisado**: los mensajes los manda Juan desde su teléfono; la app
  lee y anota. No cambiar nada en Render: ni variables, ni redespliegues, ni
  el plan.
- No inventar valores. Si un menú no está donde dice la hoja, decir dónde se
  buscó y parar.
- Las horas, **con segundos** cuando la fuente los dé (los Logs de Render sí;
  el reloj de WhatsApp solo da minutos, y se anota así).
- Si algo falla, registrar el mensaje literal y en qué paso.

## Fase A: lo que ya hay en los Logs

1. <https://dashboard.render.com>, servicio **`asistente-whatsapp`**
   (`https://asistente-whatsapp-n2s9.onrender.com`), pestaña *Logs*.
2. Ampliar el intervalo al máximo que ofrezca (lo que retenga el plan
   gratuito) y buscar, por separado:
   - `[whatsapp] mensaje` (una línea por mensaje atendido),
   - `latencia=`,
   - `ERROR`,
   - `6.53` (la documentación del canal muestra `latencia=6.53 s` como
     ejemplo y no consta si salió de una lectura real o es ilustrativo).
3. Anotar cada línea encontrada, literal, con su sello de tiempo de Render.
   Si no hay ninguna, anotar "ninguna línea `[whatsapp] mensaje` desde <fecha
   más antigua visible>".
4. Anotar el último despliegue visible (*Events* o cabecera de *Logs*): hora y
   commit. Sirve para saber qué versión del código atiende la fase B.

## Fase B: tres mensajes reales

**No abrir la URL del servicio antes de empezar**: lo más probable es que esté
dormido, y el primer mensaje tiene que despertarlo para que se vea el coste
del despertar por separado de la latencia interna.

1. **En frío.** Juan manda desde su WhatsApp al número de pruebas de Meta:
   `¿Cuántos días de vacaciones tengo?`. Anotar la hora de envío (reloj del
   teléfono, minuto) y la de la respuesta. Debe citar el convenio colectivo.
   En los Logs: la hora de la primera línea de arranque tras el envío y la
   línea `[whatsapp] mensaje ... latencia=...` literal con su sello.
2. **En caliente.** Uno o dos minutos después, **la misma pregunta**. Misma
   anotación. La diferencia entre las dos latencias internas es lo que cuesta
   el primer mensaje de un proceso recién despierto.
3. **En caliente, denegación.** `¿Cuál es la retribución bruta anual de Diego
   Ruíz?`. Debe denegar sin dar el dato y con la línea "Retenido por permiso".
   Misma anotación.
4. Si alguno no responde en dos minutos: buscar `ERROR` en los Logs y anotar
   la línea literal. No reintentar más de una vez.

## Fase C: registrar

Llamar a `registrar_tfm` citando este encargo, con:

- Fase A: las líneas encontradas (o que no hay ninguna, y desde qué fecha), y
  si `6.53` aparece.
- Último despliegue visible: hora y commit.
- Fase B, por mensaje: hora de envío y de respuesta en el teléfono; línea del
  log literal con su sello de Render; si la respuesta cumple lo esperado
  (convenio citado; denegación sin dato y con "Retenido por permiso").
- Para el primer mensaje, además: hora de la primera línea de arranque en los
  Logs.
- Cualquier fallo con su mensaje literal.

**Sin el número de teléfono** en ningún campo.

## Qué hace Claude Code después (no es parte del encargo)

1. Anotar el hallazgo con las tres latencias internas, frío frente a caliente,
   y restarlas de la de extremo a extremo para separar canal y sistema.
2. Sustituir en la memoria la frase "la línea existe y no se ha leído" (M5) y
   la cifra de 5,1 s con N=1 (M16) por lo medido, y aclarar en
   `CANAL_WHATSAPP.md` si el `6.53` era real o ilustrativo.
