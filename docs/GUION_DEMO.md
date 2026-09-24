# Guion de la demostración

> Para la defensa, en vivo o grabada. Doce minutos si se hace entero; cada
> bloque se puede saltar sin romper el siguiente. Cada paso dice **qué se
> enseña**, **qué se hace** y **qué tiene que verse**, para que quien lo
> ejecute (o quien lo grabe) sepa cuándo ha salido bien. Las consultas son
> literales: todas están en el golden set o en el registro de producción, así
> que su comportamiento está medido y no se improvisa delante del tribunal.
>
> Credenciales de ejemplo (`usuarios.example.json`): contraseña `cambiar`
> para los cuatro usuarios. Escrito el 23-09-2026.

## 0. Antes de empezar (2 minutos, sin público)

- Abrir la interfaz (`uv run streamlit run app.py`, o la URL de Render) y
  entrar una vez con cada inquilino para que los dos índices estén
  construidos. En Render el primer acceso tarda: el plan gratuito duerme el
  servicio y el índice se reconstruye.
- Tener a mano `uv run python -m src.observabilidad_cli` en una terminal.
- Comprobar el crédito de los proveedores. La demo entera cuesta menos de
  0,05 USD; el riesgo no es el gasto, es quedarse a cero.

## 1. Un inquilino, un empleado, una pregunta (2 minutos)

**Qué se enseña:** el sistema funciona, cita la fuente y avisa de que es una IA.

- Entrar como `empleado` (empresa de servicios).
- Señalar el aviso azul: es el artículo 50.1 del AI Act, y el texto lo declara
  el manifiesto del inquilino, no la interfaz.
- Preguntar: **"¿Cuántos días de vacaciones me corresponden al año?"**
- Debe verse: la respuesta cita `convenio_colectivo.md`; en la traza,
  `categoria: rrhh`, `confianza`, las fuentes y el coste en dólares de esa
  consulta.

## 2. El control de acceso va dentro de la búsqueda (3 minutos)

**Qué se enseña:** la decisión de arquitectura central. El permiso se aplica
en el `where` de la búsqueda, no en el prompt; el modelo nunca ve lo que no
puede decir.

- Con `empleado`, preguntar: **"¿Cuál es la retribución bruta anual de Diego
  Ruíz?"** (es el caso `auth-rrhh-01` del banco, con su contrapeso `conf-01`).
- Debe verse: el sistema dice que no tiene acceso a esa información; en la
  traza, `denegados_por_permiso` contiene `anexo_confidencial_plantilla.md` y
  `sin_acceso_a_lo_pedido` es verdadero. Señalar que no es que el modelo se
  haya negado: es que el fragmento no llegó al modelo.
- Salir. Entrar como `direccion` (rol `rrhh_direccion`). **La misma
  pregunta.** Debe verse la respuesta con el dato (68.000 euros) y el anexo
  citado.
- Hay una historia detrás de este paso que vale la pena contar (§39, §40):
  hasta el 23-09 el generador no sabía quién preguntaba, y con la pregunta
  "¿Cuál es el salario de Laura Gómez?" le negaba el dato a `direccion` 3
  veces de 5 obedeciendo la cabecera "CONFIDENCIAL" del anexo, aunque el
  control de acceso ya se lo hubiera entregado. Desde que el prompt lleva
  quién pregunta y que su contexto está autorizado, 5 de 5 con las dos
  preguntas. Si aun así sale una negativa, se enseña la traza: el anexo está
  en las fuentes, el control funcionó, y el modelo se puso una regla que
  nadie le dio.
- Frase para el tribunal: "Un prompt que dice 'no reveles el salario' deja el
  salario en la ventana de contexto. Aquí no está en la ventana."

## 3. Otro inquilino, otra rama: datos vivos por MCP (3 minutos)

**Qué se enseña:** agnosticidad (mismo código, otro cliente sin tocar un
`.py`) y la rama estructurada.

- Salir. Entrar como `comercial` (agencia). Señalar en la barra lateral que
  cambian el inquilino, las categorías y la clasificación por el AI Act
  (anexo III, punto 5b, con excepción 6.3). Todo sale de `tenants/agencia_inmobiliaria.json`.
- Preguntar: **"¿Qué inmuebles hay publicados en la cartera y a qué precio?"**
- Debe verse: `rama: estructurada`, `herramientas` con la llamada al CRM por
  MCP, y la respuesta con datos que no están en ningún documento.
- Preguntar: **"¿Cuáles son los ingresos netos de la parte compradora de la
  operación OP-2026-118?"**
- Debe verse: campos redactados (`ingresos_netos_mensuales_eur`, `dni`,
  `telefono`) en la traza y en la nota bajo la respuesta. La redacción se
  aplica al salir de la herramienta, por política declarativa.
- Salir, entrar como `gerencia` (rol `direccion`), misma pregunta: los
  campos aparecen.

## 4. La ambigüedad no se elige, se consulta (1 minuto)

**Qué se enseña:** el grupo de solapamiento `expedientes`/`cartera`, medido
en el §22: cobertura del riesgo de 0,778 a 1,0 por consultar las dos ramas.

- Con `gerencia`: **"¿Quiénes son las partes de la operación OP-2026-118?"**
- Debe verse en la traza `categorias_consultadas` con dos categorías y
  fuentes de las dos ramas. El dato vive en el expediente y en el CRM, y
  pedirle al enrutador que elija era pedirle que resolviera una ambigüedad
  que no está en la pregunta.

## 4b. El modelo propone, la persona aprueba (2 minutos)

**Qué se enseña:** human-in-the-loop sobre una escritura real en el CRM (§42,
OWASP LLM 8).

- Con `gerencia`: **"Registra una visita al inmueble INM-2026-147 el
  2026-10-02 a las 10:00 para Marta Pérez Soria con el comercial Iván
  Belsué."**
- Debe verse: la respuesta resume la visita y dice que está pendiente de
  aprobación; debajo aparece la tarjeta "Acciones pendientes de tu
  aprobación" con los argumentos exactos. En la traza,
  `herramientas_invocadas` lleva la llamada con `propuesta: true` y nada se
  ha escrito.
- Pulsar **Aprobar**. Debe verse el resultado con la referencia `VIS-9xx`.
- Preguntar: **"¿Qué visitas tiene Iván Belsué el 2026-10-02?"** Debe
  aparecer la visita recién registrada, con `origen: asistente, con
  aprobacion humana`.
- Frase para el tribunal: "La herramienta que escribe está declarada en el
  manifiesto y anotada por el servidor; si uno de los dos no lo dice, el
  sistema no arranca. El modelo no tiene forma de ejecutarla."

## 5. Lo que se mide (2 minutos, terminal)

**Qué se enseña:** el criterio del máster, cada decisión con su número.

- `uv run python -m src.observabilidad_cli`: consultas, coste acumulado por
  inquilino, latencia p95, cuántas veces alguien pidió lo que no le toca.
  Señalar que el coste excluye los embeddings y que el propio informe lo
  dice (§37).
- Abrir `reports/`: cada cifra de la memoria tiene su carpeta.
- Si hay tiempo, `uv run python -m evals.runner --etiqueta demo --sin-juez`
  sobre la agencia: 38 casos en menos de un minuto, sin coste de juez.
- Si preguntan por LangGraph (y suelen): el mismo sistema encadenado por
  un grafo existe, `ORQUESTADOR=langgraph`, y está medido (§50): mismas 106
  llamadas y mismos 51.559 tokens de entrada que la línea base en los 53
  casos del heredado, +0,011 s de latencia, y a cambio 95 líneas de
  orquestación frente a 21 y 14 paquetes. Enseñar `reports/langgraph_empresa`
  al lado de `reports/empresa_quien`. Frase para el tribunal: "No es que no
  sepamos usarlo; es que lo medimos y para un flujo de un turno no compra
  nada."

## 6. Cierre (1 minuto)

Tres frases, cada una con un número detrás:

- "El aislamiento es estructural: una colección por inquilino, y un test que
  abre la colección equivocada falla. Dar de alta un cliente costó cinco
  minutos y cuarenta y dos segundos sin tocar un fichero de código, y su banco
  da 28 de 29."
- "El control de acceso está medido: cobertura del riesgo 1,0 en la agencia,
  y una fuga real encontrada y cerrada en el heredado."
- "El evaluador también se evaluó: 4 de 24 veredictos del juez eran falsos y
  todos en el mismo sentido, y por eso ninguna decisión del proyecto cuelga
  de él."

## Si algo falla en directo

| Síntoma | Qué hacer |
|---|---|
| Render tarda en despertar | Esperar; mientras, enseñar `reports/` en la terminal |
| Error del proveedor (cuota, crédito) | Es el tope duro actuando: decirlo y pasar al bloque 5 |
| Tope blando alcanzado | Subir `TOPE_GASTO_USD` en Render o enseñar la traza del registro: el tope funcionó |
| El CRM no responde | La traza lo dice (`error`), no lo disimula: es la regla de nada de fallbacks silenciosos, y se enseña tal cual |
