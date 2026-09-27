# Encargo a la app de Claude: facturación del proyecto de Gemini

> Hoja de instrucciones del encargo supervisado del 27-09-2026. La ejecuta la
> app de Claude con Claude in Chrome **con Juan delante**. Motivo: la
> comparativa del generador con Gemini quedó bloqueada el 26-09 (§54) porque
> `GEMINI_API_KEY` es del nivel gratuito, 20 peticiones al día a
> `gemini-3.6-flash`, y 73 de 82 casos murieron en 429. Juan decidió activar
> la facturación el 26-09. Esta hoja la activa; la medición la hace después
> Claude Code, no la app.
>
> **Sobre los secretos.** Ninguna clave de API se copia al registro
> (`registrar_tfm`), al chat ni a ningún fichero. No hace falta crear ni
> copiar claves nuevas: la facturación se activa sobre el proyecto de la clave
> que ya existe, y la clave no cambia. Si en algún paso la consola ofrece
> generar una clave nueva, **no**.
>
> **Sobre el dinero.** La cuenta de facturación de Google es **pospago**, al
> contrario que la de Anthropic (prepago con tope duro, §16). Por eso la fase C
> no es opcional: sin presupuesto con alertas no hay nada que avise de una
> fuga. El gasto esperado del proyecto es de unos 0,40 USD.

## Reglas para la app

- Modo **supervisado**: antes de cada paso que cambie algo (vincular una
  cuenta de facturación, dar de alta un medio de pago, crear un presupuesto)
  decir qué se va a hacer y hacerlo solo si Juan no dice lo contrario.
- **Los datos de pago los teclea Juan**, nunca la app.
- No inventar valores. Si un menú o botón no está donde dice esta hoja, decir
  dónde se buscó y parar. Las consolas de Google cambian de sitio las cosas.
- Anotar la **hora** al terminar cada fase.
- Si algo falla, registrar el mensaje literal y en qué paso.

## Fase A: identificar el proyecto de la clave (aistudio.google.com)

1. Juan entra en <https://aistudio.google.com/apikey> con la cuenta con la que
   creó las claves del máster.
2. La lista muestra cada clave con su **proyecto de Google Cloud** y su
   **nivel** (*Free* o *Tier 1*, a veces como *Plan: Free of charge*). El
   proyecto usa dos claves de Gemini:
   - `GEMINI_API_KEY`: la del sistema (generador, enrutador y embeddings).
     **Es la que hay que pasar a pago.**
   - `GEMINI_API_KEY_JUEZ`: la del juez (`tfm-juez` o parecido). Corrió seis
     pasadas el 22-09 (§32), así que puede estar ya en otro proyecto.
3. Juan identifica cuál es cuál comparando los cuatro últimos caracteres que
   muestra la consola con los de su `.env`; **la app no lee ni escribe esos
   caracteres en el registro**. Anotar solo: nombre e identificador del
   proyecto de cada clave, y el nivel que muestra cada una.
4. Si las dos claves están en **el mismo proyecto**, decirlo y seguir: la
   facturación afectará a las dos, y eso rompe la separación de coste
   sistema/juez que pidió el feedback de la 3.3. No se arregla hoy, pero hay
   que saberlo.

## Fase B: activar la facturación en ese proyecto

1. En la fila de `GEMINI_API_KEY`, el enlace *Set up billing* / *Configurar
   facturación* (o *Upgrade*). Si no aparece: <https://console.cloud.google.com/billing>,
   seleccionando antes el proyecto de la fase A arriba a la izquierda.
2. Si Juan ya tiene una cuenta de facturación de Google Cloud, **vincular el
   proyecto a ella**. Si no, crearla: datos de pago los mete Juan.
   Si ofrece crédito de prueba gratuito, aceptar lo que Juan decida y anotarlo.
3. Volver a <https://aistudio.google.com/apikey> y comprobar que el nivel de
   `GEMINI_API_KEY` ya no es *Free* (lo esperado: *Tier 1*). Puede tardar unos
   minutos en reflejarse; esperar hasta cinco y recargar.

## Fase C: presupuesto con alertas (obligatoria)

1. <https://console.cloud.google.com/billing/budgets>, en la cuenta de
   facturación de la fase B. *Crear presupuesto*.
2. Nombre `tfm-gemini`. Ámbito: **solo el proyecto de la fase A**, todos los
   servicios.
3. Importe fijo: **5 EUR** al mes (o 5 USD, según la moneda de la cuenta).
4. Umbrales de alerta: **50 %, 90 % y 100 %** del gasto real, con aviso por
   correo a Juan.
5. Si la consola ofrece un **tope de gasto del proyecto** en AI Studio
   (*Spend cap* o similar), ponerlo en 5 y anotar que existe; si no existe,
   anotar que no. Un presupuesto de Google **avisa pero no corta**: lo que
   limite de verdad es lo que conviene saber.

## Fase D: registrar

Llamar a `registrar_tfm` citando este encargo, con:

- Hora de cierre de cada fase.
- Proyecto (nombre e identificador) de cada una de las dos claves y si son el
  mismo.
- Nivel de `GEMINI_API_KEY` antes y después.
- Cuenta de facturación: nueva o existente; crédito de prueba, sí o no.
- Presupuesto: importe, moneda, umbrales; y si existe tope duro en AI Studio.
- Cualquier fallo con su mensaje literal.

**Sin secretos**: ni claves, ni fragmentos de claves, ni datos de pago.

## Qué hace Claude Code después (no es parte del encargo)

1. Una llamada suelta a `gemini-3.6-flash` que confirme que el 429 del nivel
   gratuito ha desaparecido (regla del §54).
2. Los dos bancos documentales con `LLM_PROVIDER=gemini
   JUDGE_PROVIDER=anthropic --sin-juez`, **un solo worker**, contra
   `empresa_quien` (48/53) y `gestoria_agregacion_v2` (28/29).
3. Anotar en la ficha de coste que los embeddings de producción pasan a
   facturarse en ese proyecto (hoy se contabilizan sin precio, §37).
