# Bitácora del TFM — Asistente multi-tenant

> Diario de sesiones. Entradas de más reciente a más antigua.
> El histórico de la entrega 3.3, de la que parte este repositorio, está en
> `BITACORA_3.3.md`.

## 2026-09-21 — Sesión 3: sincronización entre Claude Code y la app

Sesión corta, de proceso y no de código.

**Hecho:**
- Documentada en `CLAUDE.md` §9 la relación entre las dos superficies de
  trabajo: Claude Code escribe el estado, el proyecto de la app lo lee por la
  conexión de GitHub, y el flujo es de una sola dirección.
- Adelgazadas las instrucciones del proyecto de la app para que **no copien
  estado**. La primera versión, escrita el día 20, ya estaba desfasada el 21: no
  mencionaba la cobertura del riesgo ni la categoría `expedientes`. Ahora
  describen quién es el alumno, cómo hablarle y las reglas de navegador, y para
  el estado mandan a leer el repositorio.

**Detectado:**
- La sesión 2 no escribió entrada de bitácora. Se ha reconstruido desde los
  commits y desde `HALLAZGOS.md`. Es exactamente el fallo que `/cierre` existe
  para evitar: el código y los hallazgos quedaron bien anotados, pero el diario
  se saltó un día.

**Pendiente:**
- [ ] **Comprobar a qué repositorio apunta el proyecto MASTER IA TFM en la app.**
      El `CLAUDE.md` antiguo decía que estaba conectado a
      `multi-agent-support-platform`, retirado el día 20. Si no se repuntó a
      `asistente-multitenant`, la app lleva dos días leyendo un repo muerto sin
      avisar. Es configuración del conector y hay que mirarlo desde la app.

## 2026-09-20 (tarde) — Sesión 2: cobertura del riesgo y taxonomía del expediente

Entrada reconstruida a posteriori desde los commits `9ad6368` y `d0cfc68` y
desde `HALLAZGOS.md`: la sesión no la escribió.

**Hecho:**
- **Métrica de cobertura del riesgo** (`alcance_riesgo`). El hallazgo 9 contaba a
  mano cuántos casos de seguridad llegaban a la etapa donde el control actúa;
  ahora es una métrica del banco que lee la traza. **No puntúa**: un caso que no
  llega ya falla en `routing`, y penalizarlo dos veces movería `casos_ok`
  respecto a la línea base heredada. Comprobado reevaluando trazas guardadas: se
  reproducen 47/53 y 29/38.
- **Categoría propia para el expediente.** El solapamiento `procesos`/`cartera`
  no era un problema de redacción: el manifiesto decía que `procesos` es
  procedimiento y **no** el estado de un caso, y que `cartera` son datos vivos y
  **no** documentación. Un expediente es documentación de un caso concreto: la
  celda que la taxonomía declaraba vacía. El enrutador obedecía al manifiesto.

**Medido:**

| | Antes | Después |
|---|---|---|
| Inquilino C, casos que pasan | 29/38 | **33/38** |
| Cobertura del riesgo, C | 0,444 | **0,778** |
| Casos de seguridad que prueban algo, C | 3 | **6** |
| Inquilino A | Sin cambios | Sin cambios |

**Tres defectos destapados por el camino, los tres corregidos y escritos:**
1. La firma del índice **no cubría el corpus**. Mover un fichero de fuente no
   cambia ningún parámetro de configuración, así que la firma aguantaba, el banco
   reutilizaba la colección vieja y la fuente nueva volvía vacía incluso con el
   rol. El hallazgo 10 otra vez, en el eje que su arreglo dejó fuera.
2. La métrica de cobertura **leía ese vacío al revés**: una fuente cuyo único
   documento está restringido no devuelve nada precisamente porque el control
   actuó, y la métrica lo contaba como "no llegó al control". El recuperador
   publica ahora `denegados_por_permiso` con una consulta de solo metadatos, así
   que el texto restringido sigue sin salir del índice.
3. **Corpus y CRM compartían espacio de identificadores.** El mismo comprador
   existía en ambos con DNI e ingresos distintos, y `expediente 2026-118`
   colisionaba con un `OP-2026-118` diferente. Un caso de seguridad podía
   responderse con confianza **sobre la persona equivocada** y sin ningún literal
   prohibido presente. El generador declara ahora lo que usa el corpus y aborta
   si hay colisión.

**Decisión pendiente anotada:** dos casos de `cartera` siguen enrutando a
`expedientes`. Un intento de separarlos por convención de identificador arregló
tres y rompió seis (33/38 → 30/38) y se revirtió: los datos de las partes viven
de verdad en las dos fuentes, así que la ambigüedad está en el modelo de datos.
La salida es que una consulta ambigua **consulte las dos ramas** en vez de
elegir.

**También medido:** con tres ejecuciones del mismo prompt, **4 de 38 casos
cambian de categoría entre pasadas idénticas** y el acierto del enrutador oscila
0,079. Los nueve casos de seguridad enrutan igual siempre, así que la cobertura
se puede leer de una sola pasada y el acierto global no.

## 2026-09-20 — Sesión 1: reorientación del TFM y construcción del núcleo

Primera sesión del TFM tras dos meses sin tocarlo. Sesión larga: se reorientó el
proyecto y se construyeron el multi-tenant, la rama estructurada y la capa de
gobernanza.

### Decisiones

- **El TFM no arranca de cero.** Parte del sistema acumulado en las entregas
  2.1, 2.3, 3.1 y 3.3, que ya cubría cuatro de los seis pasos del flujo objetivo
  y traía un banco de 109 casos. Repositorio nuevo y público,
  `asistente-multitenant`, conservando la historia de commits de la 3.3.
- **Dos inquilinos**: la empresa heredada (regresión) y una agencia
  inmobiliaria construida completa. Se descartó un tercero de asesoría para
  concentrar el esfuerzo.
- **Python vanilla** con capítulo de justificación frente a LangGraph.
- **Rama estructurada por MCP**, no por herramientas cableadas.
- **Control de acceso estructural**, no por prompt.
- El análisis del **Módulo 4** se produce dentro del TFM.
- Canales: correo real y WhatsApp en pruebas. Slack descartado.
- Detalle completo en `ALCANCE.md`.

### Hecho

1. Credenciales: dos claves de Anthropic separadas, sistema y juez, siguiendo el
   feedback de la 3.3. La anterior estaba revocada o vencida.
2. Verificado que el MCP de idealista **no es consumible desde código**: su
   documentación dice que solo funciona con el conector aprobado para Claude.
   Solicitado acceso a la API oficial; fuente externa real será el Catastro.
3. Inquilino como concepto de primera clase, con aislamiento por colección.
4. Segundo inquilino completo: corpus, banco de 38 casos y CRM sintético
   reproducible.
5. Bancos de evaluación por inquilino, con invariantes que se ejecutan sobre
   cualquier inquilino que exista.
6. Rama estructurada: servidor MCP del CRM con cinco herramientas, cliente MCP y
   bifurcación en el agente.
7. Capa de gobernanza: permisos dentro de la búsqueda y redacción de campos
   sensibles en los resultados de herramienta.

### Medido

| Métrica | Resultado |
|---|---|
| Inquilino A, casos que pasan | 45/52 (3.3) → **47/53** |
| Inquilino A, fugas literales | 2 → **0** |
| Inquilino C, casos que pasan | 18/30 → **29/38** |
| Inquilino C, fugas literales | 1 → **0** |
| Tests | 322 → **574**, todos en verde |
| Coste de una pasada del banco | ~0,10 USD por inquilino, sin juez |

Diez hallazgos anotados en `HALLAZGOS.md`, cada uno con la ejecución que lo
respalda. Los dos que más van a pesar en la memoria:

- **Arreglar el enrutado destapó fugas que estaban escondidas.** El sistema
  parecía seguro porque fallaba antes de llegar al punto donde se equivoca.
- **Una métrica de seguridad agregada es engañosa por construcción.** Solo seis
  de los doce casos de seguridad llegaron a la etapa donde el control actúa; el
  resto está en verde por no haber recuperado nada.

### Pendiente para la próxima sesión

- [ ] Métrica de **cobertura del riesgo**: qué proporción de los casos de
      seguridad llega a la etapa donde el control actúa. Es barata y arregla el
      punto ciego del hallazgo 9.
- [ ] Solapamiento `procesos` / `cartera` en el inquilino C: ensucia seis casos
      y no se arregla con más palabras en el prompt. Probablemente haya que
      sacar el expediente del corpus documental.
- [ ] Observabilidad y coste acumulado en producción (bloque 2).
- [ ] Canal de correo de extremo a extremo (bloque 2).
- [ ] Despliegue en Render con autenticación y tope de gasto (bloque 1, punto 3).
- [ ] Tope de gasto en la cuenta de Anthropic, antes de exponer nada.

### Notas

- El entorno arrastra activado el `.venv` del repositorio anterior, así que `uv`
  avisa en cada comando. Lo ignora y usa el correcto.
- `reports/` guarda cinco ejecuciones de esta sesión: `agencia_base`,
  `agencia_v2`, `agencia_v3`, `agencia_v4` y `empresa_gobernanza`. Son la
  evidencia de los hallazgos y no se borran.
