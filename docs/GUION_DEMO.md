# Guion de la demostración

> Un recorrido reproducible por quien corrija o por cualquier tercero, sobre
> el servicio desplegado (`https://asistente-multitenant.onrender.com`) o en
> local. Se escribió el 23-09-2026 para una demostración en directo y se
> rehízo el 25-10-2026 tras una corrección simulada (E-0022) que lo ejecutó
> con los usuarios de evaluación y encontró tres bloques que un tercero no
> podía reproducir. Cada paso dice **qué se enseña**, **qué se hace** y **qué
> tiene que verse**; cada bloque se puede saltar sin romper el siguiente. Las
> consultas son literales y su comportamiento está medido.
>
> **Usuarios**: `eval_empleado` (sin roles) y `eval_direccion` (rol
> `rrhh_direccion`) en la empresa de servicios; `eval_comercial` (sin el rol `direccion`)
> y `eval_gerencia` (rol `direccion`) en la agencia inmobiliaria. Las
> contraseñas van en el comentario de la entrega del campus, no en este
> repositorio, que es público. En local, `usuarios.example.json` define
> usuarios equivalentes con la contraseña `cambiar`.

## 0. Antes de empezar (2 minutos)

- Abrir la interfaz. En Render el primer acceso tarda unos 32 s si el
  servicio dormía (§52), y la primera consulta de cada inquilino construye
  su índice (unos 15-20 s más); las siguientes tardan 3-6 s.
- El recorrido de los bloques 1 a 4b son nueve consultas y costó entre
  **0,064 y 0,069 USD** en las dos pasadas medidas el 25-10-2026 (§67, §68).
- Para el bloque 4c hace falta un teléfono dado de alta por el autor en el
  canal de WhatsApp; para el 5, una copia local del repositorio.

## 1. Un inquilino, un empleado, una pregunta (2 minutos)

**Qué se enseña:** el sistema funciona, cita la fuente y avisa de que es una IA.

- Entrar como `eval_empleado` (empresa de servicios).
- Señalar el aviso azul: es el artículo 50.1 del AI Act, y el texto lo declara
  el manifiesto del inquilino, no la interfaz.
- Preguntar: **"¿Cuántos días de vacaciones me corresponden al año?"**
- Debe verse: 23 días laborables citando `convenio_colectivo.md`; en la
  traza, `categoria: rrhh`, `confianza` y las fuentes con su distancia. El
  gasto acumulado está en la barra lateral, leído del registro de producción.
- Debajo de la respuesta aparece "Retenido por permiso:
  anexo_confidencial_plantilla.md" aunque la pregunta no lo pidiera: el anexo
  vive en la misma fuente y el filtro lo retiene en toda consulta a ella. La
  nota nombra el documento y no su contenido, por decisión (capítulo 2.4 de
  la memoria): quien pregunta sabe que existe y a quién pedirlo.

## 2. El control de acceso va dentro de la búsqueda (3 minutos)

**Qué se enseña:** la decisión de arquitectura central. El permiso se aplica
en el `where` de la búsqueda, no en el prompt; el modelo nunca ve lo que no
puede decir.

- Con `eval_empleado`, **en una conversación nueva** (Salir y volver a
  entrar), preguntar: **"¿Cuál es la retribución bruta anual de Diego
  Ruíz?"** (es el caso `auth-rrhh-01` del banco, con su contrapeso
  `conf-01`). Si se pregunta justo después de la de vacaciones, la memoria
  entre turnos la reescribe "según el convenio" y la respuesta dice que el
  dato no está en el contexto: tampoco hay fuga, pero la denegación es menos
  clara (capítulo 8.3 de la memoria).
- Debe verse: el sistema dice que no puede dar esa información; en la
  traza, `denegados_por_permiso` contiene `anexo_confidencial_plantilla.md`.
  No es que el modelo se haya negado: es que el fragmento no llegó al modelo.
- Salir. Entrar como `eval_direccion`. **La misma pregunta.** Debe verse la
  respuesta con el dato (68.000 euros) y el anexo citado.
- La historia detrás de este paso (§39, §40): hasta el 23-09 el generador no
  sabía quién preguntaba, y le negaba el dato a dirección 3 veces de 5
  obedeciendo la cabecera "CONFIDENCIAL" del anexo, aunque el control de
  acceso ya se lo hubiera entregado. Desde que el prompt lleva quién pregunta,
  5 de 5.
- La idea del bloque: un prompt que dice "no reveles el salario" deja el
  salario en la ventana de contexto. Aquí no está en la ventana.

## 3. Otro inquilino, otra rama: datos vivos por MCP (3 minutos)

**Qué se enseña:** agnosticidad (mismo código, otro cliente sin tocar un
`.py`) y la rama estructurada con redacción de campos.

- Salir. Entrar como `eval_comercial` (agencia). Cambian el inquilino, la
  clasificación por el AI Act de la barra lateral (anexo III, punto 5b, con
  excepción 6.3) y las categorías que sugiere el campo de pregunta. Todo sale
  de `tenants/agencia_inmobiliaria.json`.
- Preguntar: **"¿Qué inmuebles hay publicados en la cartera y a qué precio?"**
- Debe verse: en la traza, `herramientas_invocadas` con
  `crm__buscar_inmuebles` y una respuesta con datos que no están en ningún
  documento. La consulta cae en el grupo de solapamiento, así que
  `categorias_consultadas` lleva también `expedientes` (bloque 4). El
  resultado del CRM no cabe entero en lo que se le da al modelo: la traza
  lleva `resultados_recortados` y la respuesta termina con un aviso de que
  los datos se recortaron (§68). Si además el modelo llega al límite de
  salida, otro aviso y `respuesta_truncada` (§67). Antes del 25-10 los dos
  recortes eran silenciosos.
- Preguntar: **"¿Cuáles son los ingresos netos de la parte compradora de la
  operación OP-2026-110?"**
- Debe verse: la nota "Campos redactados" bajo la respuesta, con cinco
  campos: `parte_compradora.ingresos_netos_mensuales_eur`, `.dni`,
  `.telefono` y `.correo`, y `parte_vendedora.telefono`; y la respuesta diciendo que el dato existe y está restringido.
  La redacción se aplica al salir de la herramienta, por política
  declarativa, antes de que el modelo lo vea.
- Salir, entrar como `eval_gerencia`, misma pregunta: los campos aparecen
  (1.980 euros).

## 4. La ambigüedad no se elige, se consulta (1 minuto)

**Qué se enseña:** el grupo de solapamiento `expedientes`/`cartera`, medido
en el §22: cobertura del riesgo de 0,778 a 1,0 por consultar las dos ramas.

- Con `eval_gerencia`: **"¿Quiénes son las partes de la operación
  OP-2026-118?"**
- Debe verse en la traza `categorias_consultadas` con las dos categorías: la
  búsqueda en los expedientes y la llamada al CRM. Responde el expediente
  (`expediente_2026_118_confidencial.md`), y la respuesta dice que el CRM no
  tiene esa operación. Es lo esperado: el generador del CRM sintético excluye
  a propósito las operaciones y personas del corpus, para que nadie aparezca
  con datos distintos en las dos fuentes.
- La idea del bloque: el enrutador no puede saber por la pregunta si una
  operación está en el expediente, en el CRM o en los dos; pedirle que elija
  era pedirle que resolviera una ambigüedad que no está en la pregunta. El
  sistema consulta las dos y responde con la que tiene el dato.

## 4b. El modelo propone, la persona aprueba (2 minutos)

**Qué se enseña:** human-in-the-loop sobre una escritura real en el CRM (§42,
OWASP LLM 8).

- Con `eval_gerencia`: **"Registra una visita al inmueble INM-2026-147 el
  2026-12-15 a las 10:00 para Laura Espinosa Gil con el comercial Iván
  Belsué."**
- Debe verse: la respuesta resume la visita y dice que está pendiente de
  aprobación; debajo aparece la tarjeta "Acciones pendientes de tu
  aprobación" con los argumentos exactos. En la traza,
  `herramientas_invocadas` lleva la llamada con `propuesta: true` y nada se
  ha escrito. Si el modelo pide antes confirmar algún dato, contestar "Sí,
  confirmo": sin la tarjeta no se escribe nada.
- Pulsar **Aprobar**. Debe verse el resultado con la referencia `VIS-9xx` y
  `origen: asistente, con aprobacion humana`.
- Preguntar: **"¿Qué visitas tiene Iván Belsué el 2026-12-15?"** Debe
  aparecer la visita recién registrada (la agenda no muestra el origen). El CRM vive en el disco del servicio y vuelve a su
  estado generado en cada despliegue.
- La idea del bloque: la herramienta que escribe está declarada en el
  manifiesto y anotada por el servidor; si uno de los dos no lo dice, el
  sistema no arranca. El modelo no tiene forma de ejecutarla.

## 4c. El mismo sistema por WhatsApp (1 minuto, con un teléfono dado de alta)

**Qué se enseña:** el canal no es otro sistema; el número es la credencial
y fija el inquilino (§51, `docs/CANAL_WHATSAPP.md`).

- Desde el teléfono registrado como empleado del heredado: **"¿Cuántos días
  de vacaciones tengo?"**. Debe llegar el aviso de que se habla con una IA
  (artículo 50, solo en la primera conversación) y la misma respuesta que
  en la web, citando el convenio.
- **"¿Cuál es la retribución bruta anual de Diego Ruíz?"**: denegación sin
  el dato y la línea "Retenido por permiso". Es el mismo control que en el
  bloque 2.
- En *Logs* del servicio de Render aparece una línea por mensaje con huella,
  inquilino y latencia interna; el teléfono no sale.

## 5. Lo que se mide (2 minutos, terminal)

**Qué se enseña:** el criterio del máster, cada decisión con su número.

- `uv run python -m src.observabilidad_cli`: consultas, coste acumulado por
  inquilino, latencia p95, cuántas veces alguien pidió lo que no le toca.
  El coste excluye los embeddings y el propio informe lo dice (§37). Leer
  el registro de producción exige la URL de su base, que solo tiene el autor.
- Abrir `reports/`: cada cifra de la memoria tiene su carpeta.
- Con claves propias, `uv run python -m evals.runner --etiqueta demo --sin-juez`
  sobre la agencia: 40 casos en menos de un minuto, sin coste de juez.
- LangGraph: el mismo sistema encadenado por un grafo existe,
  `ORQUESTADOR=langgraph`, y está medido (§50): mismas 106 llamadas y mismos
  51.559 tokens de entrada que la línea base en los 53 casos del heredado,
  +0,011 s de latencia, y a cambio 95 líneas de orquestación frente a 21 y
  14 paquetes. `reports/langgraph_empresa` al lado de `reports/empresa_quien`.

## 6. Cierre (1 minuto)

Tres frases, cada una con un número detrás:

- "El aislamiento es estructural: una colección por inquilino, y un test que
  abre la colección equivocada falla. Dar de alta un cliente costó cinco
  minutos y cuarenta y dos segundos sin tocar un fichero de código, y su banco
  da 28 de 29."
- "El control de acceso está medido: cobertura del riesgo 1,0 en la agencia,
  y una fuga real encontrada y cerrada en la rama estructurada."
- "El evaluador también se evaluó: 4 de 24 veredictos del juez eran falsos y
  todos en el mismo sentido, y por eso ninguna decisión del proyecto cuelga
  de él."

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| Render tarda en despertar | Esperar unos 32 s; la primera consulta de cada inquilino tarda además lo que cuesta construir su índice |
| WhatsApp no contesta en un minuto | El servicio estaba dormido y Meta reintenta el webhook: la respuesta llega |
| Error del proveedor (cuota, crédito) | El mensaje dice qué pasó y a quién acudir (§63): es el tope duro actuando |
| Tope blando alcanzado | La interfaz deja de consultar y lo dice: el tope funcionó |
| El CRM no responde | La traza lo dice (`error`), no lo disimula: es la regla de nada de fallbacks silenciosos |
