# CLAUDE.md — Asistente multi-tenant (TFM)

> Fuente única de verdad del proyecto. Si algo de una conversación contradice
> este documento o `docs/ALCANCE.md`, gana el documento.
>
> Este repositorio **parte de la entrega 3.3 del máster** y conserva su historia
> de commits. Los ficheros del banco de evaluación, el corpus del inquilino
> heredado y buena parte de `src/` vienen de allí. Lo anterior a
> `docs: add TFM scope and closed decisions` es la 3.3, no este proyecto.

## 1. Qué es

**Asistente interno multi-tenant de conocimiento y datos para empresas de
servicios profesionales.** Responde consultas combinando dos fuentes:

- **Documental**: RAG sobre el corpus propio de cada cliente.
- **Estructurada**: datos de negocio consultados por **MCP**.

```
entrada → clasificador → recuperación (documental | estructurada)
        → generación anclada → gobernanza → salida
```

Es el Trabajo Fin de Máster de Juan Archidona Ahijado (Máster en IA Generativa
Avanzada, The Bridge). Se defiende en **octubre de 2026**.

El criterio con el que se evalúa, del programa del máster: *"el objetivo del
proyecto no está únicamente en que el sistema funcione, sino en justificar cada
decisión técnica en términos de calidad, coste, escalabilidad, riesgo y
mantenimiento"*. **Ante cualquier propuesta, la pregunta es si se puede medir.
Una afirmación sin número no vale.**

## 2. Estado (2026-09-23)

Funciona de extremo a extremo con dos inquilinos, las dos ramas de recuperación
y control de acceso estructural. **832 tests en verde**, `ruff` limpio.

| Pieza | Estado |
|---|---|
| Inquilino como concepto de primera clase | Hecho |
| Aislamiento entre inquilinos (colección propia) | Hecho y probado |
| Rama documental (RAG heredado) | Hecho |
| Rama estructurada (MCP) | Hecho |
| Control de acceso en las dos ramas | Hecho y medido |
| Bancos de evaluación por inquilino | Hecho (53 + 38 casos) |
| Cobertura del riesgo en el banco | Hecha y medida (A 0,636 / C 0,778) |
| Contabilidad de coste del sistema y del juez | Hecha y medida, con clave propia por fin usada (§18) |
| Puente MCP con la app (consulta y registro) | Hecho, declarado en la app y probado contra exfiltracion (§19) |
| Observabilidad y coste en producción | Hecha: registro por inquilino, coste por consulta (§20) |
| Consulta de las dos ramas ante una categoría ambigua | Hecha y medida: cobertura del riesgo 0,778 → 1,0 (§22) |
| Verificación determinista de citas | Hecha y medida sobre las 22 ejecuciones guardadas: 0 citas inventadas (§23) |
| Clave propia del juez, también en el camino de Gemini | Hecha: antes usaba la de los embeddings (§24) |
| Juez de otra familia que el generador | Diseñado y no ejecutado: falta una segunda clave de Gemini (§24, §26) |
| Estabilidad del enrutador | Medida y **aplicada**: temperatura 0 por defecto desde el 22-09; la votación queda descartada por redundante (§27, ALCANCE §5.c) |
| Evaluación del juez | Hecha y completada: el número contradice su propio razonamiento, temperatura 0 no lo estabiliza y sus errores van todos en el mismo sentido (§30, §32) |
| Conmutación de proveedor a Gemini | Arreglada: era una forma y no un hecho; verificada de extremo a extremo (§29) |
| Canales (correo, WhatsApp) | Pendiente |
| Human-in-the-loop | Pendiente |
| Despliegue con autenticación y tope de gasto | Pendiente |
| Clasificador con modelo pequeño o afinado | Pendiente (bloque 3) |
| Alta cronometrada de un inquilino nuevo | Pendiente (bloque 4) |
| Análisis de IA responsable y AI Act (absorbe el Módulo 4) | **Esqueleto hecho** el 23-09: registro de riesgos y clasificación por inquilino; quedan los huecos ordenados de `docs/RIESGOS.md` §5. Es **requisito nombrado por el tutor** el 22-09 |
| Análisis de sesgos | **Hecho y medido** en la capa de recuperación y en el enrutado: ningún eje alcanza su suelo (§34). La capa de generación sigue sin medir |
| Buzón de encargos para la app | Hecho: `encargos_tfm`, y escribir en él no es herramienta MCP a propósito |
| Análisis del material del Módulo 4 | Hecho: `docs/MODULO_4.md`, con el mapa de huecos ordenado |
| Cadena de suministro (AIBOM) y plan de incidentes | **Hecho** el 23-09: `docs/AIBOM.md` generado y vigilado por test (destapó el §35: embeddings en retirada y sin coste contabilizado) y `docs/INCIDENTES.md`; falta el simulacro cronometrado |
| Retención y supresión del registro de producción | **Hecho y medido** el 23-09: `docs/RETENCION.md` (90 días, respuesta no guardada), `observabilidad_cli --borrar-usuario` y `--purgar-dias` con lápida; décimas de segundo sobre 10.000 líneas (§37) |
| Consumo de embeddings contabilizado | **Hecho** el 23-09: exacto en la ingesta (2.724 y 3.027 tokens por corpus), estimado en la consulta (14 tokens de media); aparte de los totales del chat y sin precio publicado (§37) |
| Derechos RGPD sobre el índice (borrado y rectificación) | **Medido** el 23-09: borrado efectivo en 1,46 s y 1,23 s, comprobado contra la colección (§36, `scripts/borrar_documento.py`); las consultas registradas no se borran (R-16) |
| Registro de riesgos y clasificación por el AI Act | **Hecho** el 23-09: `docs/RIESGOS.md` (23 riesgos con cuadrante de Rumsfeld, OWASP, ATLAS, AIUC-1 y evidencia, con test que impide citar hallazgos inexistentes) y bloque `ai_act` obligatorio en cada manifiesto, con la regla del artículo 6.3 codificada y el aviso del artículo 50 en la interfaz |

El alcance completo, ordenado por prioridad y **con las líneas de corte ya
decididas**, está en `docs/ALCANCE.md` §4. La regla: se sacrifica alcance antes
que profundidad de la documentación.

## 3. Los dos inquilinos

| | `empresa_servicios` | `agencia_inmobiliaria` |
|---|---|---|
| Qué es | Empresa de servicios heredada de las entregas 2.3/3.1/3.3 | Domara Inmobiliaria, agencia ficticia de Zaragoza |
| Para qué está | Sostener el banco heredado como **suite de regresión** | Demostrar agnosticidad y la rama estructurada |
| Categorías | rrhh, desarrollo, actas, marca | cartera (estructurada), expedientes, procesos, normativa, comercial, actas |
| Corpus | 7 documentos | 10 documentos |
| Banco | 53 casos | 38 casos |
| MCP | No | `mcp_servers/agencia_crm.py` |

Ambos son **sintéticos**. Ningún dato real de ninguna empresa entra aquí: el
repositorio es público.

## 4. Decisiones cerradas, y por qué

- **Colección de Chroma por inquilino**, no un índice filtrado por metadato. El
  aislamiento tiene que ser estructural: un filtro mal construido en una sola
  ruta de consulta devuelve documentos de otro cliente sin que nada lo señale.
- **Servidores MCP**, no herramientas cableadas. Un `tools=[...]` dentro del
  agente ata el sistema a la API de un cliente; un servidor lo convierte en
  contrato.
- **Control de acceso antes del modelo.** El permiso va **dentro del `where`**
  de la búsqueda y la redacción se aplica al salir de la herramienta. Un prompt
  que dice "no reveles el DNI" deja el DNI en la ventana de contexto.
- **Python vanilla**, con un capítulo de justificación comparándolo con
  LangGraph. El capstone puntúa la justificación, no la herramienta.
- **Todo lo que distingue a un inquilino es declarativo**: categorías, fuentes,
  servidores MCP y política de acceso viven en `tenants/<id>.json`. Si dar de
  alta un cliente exige editar un `.py`, la costura está mal puesta — y eso se
  mide cronometrando el alta al final del proyecto.

## 5. Reglas de trabajo

- **No se relaja el banco.** Se corrige un caso cuando la expectativa era
  incorrecta, nunca cuando el resultado incomoda. Cada corrección se justifica
  por escrito en `docs/HALLAZGOS.md`.
- **Nada de fallbacks silenciosos.** Si algo degrada —parseo fallido,
  recuperación vacía, servidor caído— se marca y se propaga. La confusión más
  cara es que "el CRM está caído" se lea como "no tengo esa información".
- **La línea base heredada no se toca.** Hay un test que compara el prompt del
  enrutador carácter a carácter con el de la 3.3; si cambia, las métricas de los
  109 casos dejan de ser comparables.
- **Sin emoticonos** en código, documentos, commits ni interfaz.
- **Sin atribución a Claude** en commits ni entregables.
- Commits en inglés, conventional commits. Documentación en español.
- Ningún dato personal real, en ningún sitio.

## 6. Estructura

```
corpus/<tenant>/<fuente>/*.md      Documentos de cada inquilino
datos/<tenant>/crm.json            Datos de negocio sintéticos (generados)
tenants/<tenant>.json              Manifiesto: categorías, solapamientos, MCP, política
mcp_servers/                       Servidores MCP por inquilino
scripts/                           Generadores reproducibles (semilla fija)
src/
  tenant.py       Inquilino: categorías, destinos, servidores, política
  gobernanza.py   Control de acceso: permisos y redacción
  mcp_cliente.py  Cliente MCP (hilo con bucle propio)
  agent.py        Orquestación y bifurcación de ramas
  router.py       Enrutador (prompt construido desde el manifiesto)
  retriever.py    Recuperación filtrada por fuente y por permiso
  provider.py     Abstracción de proveedor, con tool-calling
evals/            Banco: datasets por inquilino, métricas, runner, barrido
reports/          Evidencia de cada ejecución
docs/
  ALCANCE.md      Decisiones cerradas y alcance por bloques
  HALLAZGOS.md    Hallazgos medidos, con la ejecución que los respalda
  RIESGOS.md      Registro de riesgos: Rumsfeld, OWASP, ATLAS, AIUC-1, evidencia
  MODULO_4.md     Qué aporta el Módulo 4 y qué falta; artículo 6 con citas
```

## 7. Comandos

```bash
uv sync --group judge
uv run pytest                                      # 832 tests, sin llamadas a API
uv run ruff check src evals tests mcp_servers scripts

uv run python -m src.ingest_cli                    # indexa el inquilino activo
TENANT_ID=agencia_inmobiliaria uv run python -m src.ingest_cli

uv run python -m evals.runner --etiqueta X --sin-juez   # banco sin coste de juez
uv run python scripts/generar_crm_agencia.py            # regenera el CRM sintético

uv run python -m src.main "tu consulta"                # consulta real: SÍ se registra
uv run python -m src.observabilidad_cli                # qué ha pasado en producción
```

`TENANT_ID` selecciona el inquilino; por defecto, `empresa_servicios`.

**Al cambiar el corpus, la política de acceso o el esquema de metadatos hay que
reindexar.** La firma del índice cubre las tres cosas —el corpus desde §14, que
es cuando costó una ejecución entera descubrir que faltaba—, pero conviene
saberlo: un índice obsoleto no da error, devuelve vacío (`docs/HALLAZGOS.md` §10
y §14).

## 8. Riesgos abiertos

- **Resuelto en la tutoría del 22-09** (`docs/TUTORIA_2026-09-22.md`), que era
  la vía abierta para los cuatro riesgos que el campus no permitía cerrar:
  **partir de entregas propias ya calificadas es admisible y no hay que
  declararlo**, el **uso de IA es libre**, la defensa es **a finales de octubre**
  y el **enunciado y la rúbrica llegan al desbloquearse el Módulo 5, al acabar
  el 4, en 2-3 semanas** (en torno al 6-13 de octubre). El planteamiento del
  proyecto le pareció bien tal cual.
- **Lo que sigue sin saberse:** el **formato de la defensa** —duración, si hay
  demo en vivo, si hay tribunal— no se abordó, y de eso depende si hace falta
  dejar el despliegue público funcionando o basta con una grabación.
- **La rúbrica llega tarde para decidir línea base, y eso cambia la
  estrategia.** Entre que aparece (6-13 de octubre) y la defensa (finales de
  mes) hay una o dos semanas. Tomar en esa ventana una decisión que **invalida
  la comparación con las ejecuciones anteriores** no deja tiempo de volver a
  medir. Por eso las decisiones de línea base **se toman ahora**: lo que la
  rúbrica puede cambiar es cómo se presentan las cifras, no qué configuración es
  la buena.
- **La securización es un requisito nombrado por el tutor**, no una prioridad
  media del bloque 2, y **sí incluye ciberseguridad**. El análisis completo del
  material está en `docs/MODULO_4.md`; en corto: de los cuatro apartados del
  módulo, el 4.1 es ética y normativa y **el 4.2, 4.3 y 4.4 son seguridad,
  guardarrailes, red-teaming y gobierno del riesgo**. La primera lectura, hecha
  solo con el 4.1 delante, concluyó que no era ciberseguridad y era falsa.
  El proyecto cubre **7 de los 9 guardarrailes** que enumera el 4.3 y tiene
  material medido en los diez riesgos del OWASP Top 10 para LLM o en la mayoría;
  los huecos ordenados están al final de `MODULO_4.md`.
- **El material docente del máster no entra en este repositorio.** Es obra de un
  profesor y el repositorio es público, así que commitearlo sería
  redistribuirla, y son decenas de MB que git no olvida. Vive en
  `Master/Módulo N/N.X/Documentación/` y se cita desde `docs/MODULO_4.md`. Hay
  una regla en `.gitignore` para que no vuelva a entrar por descuido.
- **El tope de gasto ya existe y el riesgo se ha invertido.** La cuenta es de
  prepago, 12,66 USD de crédito y **recarga automática desactivada**: es un tope
  duro y el peor caso de una fuga se agota solo en una hora. Lo que hay que
  vigilar ahora es lo contrario, quedarse sin crédito en la defensa. **No activar
  la recarga automática**: es lo único que rompería el tope. Ver §16.
- **Evaluar cuesta 11 veces más que funcionar**: 0,0278 USD por caso con juez
  frente a 0,00245 USD sin él, y 2,53 USD una pasada completa de los dos
  inquilinos — el 20 % del crédito. La pasada con juez es un acto deliberado, no
  una rutina (§17, con las cifras corregidas en §21: el repo tenía el precio de
  `claude-sonnet-5` un 50 % alto y todo lo derivado de él salía inflado).
- **`reports/` mide el banco, no el proyecto.** La contabilidad propia no ve un
  22 % del gasto de su clave: llamadas de desarrollo fuera de `evals.runner` y
  reintentos del SDK. Afecta a la ficha de coste de `ALCANCE.md` §5, que tiene
  que decir cuál de las dos cosas mide (§16).
- **Cobertura del riesgo: 0,636 en A y 0,778 en C.** Resuelto lo que se podía
  resolver enrutando (§12). Lo que queda son casos que no llegan al control por
  fallo de enrutado, y subirlos es trabajo de enrutador, no de gobernanza.
- **El solapamiento `expedientes`/`cartera` está resuelto, y el riesgo que
  queda es el precio.** Una consulta que cae en un grupo de solapamiento
  declarado consulta las dos ramas en vez de elegir (§22): cobertura del riesgo
  0,778 → **1,0**, y el caso que en producción se quedaba sin respuesta ya la
  da. El precio medido es **+40 % de coste por caso y +0,5 s de latencia** en
  los casos del grupo, y hay que vigilarlo si se declaran más grupos: el coste
  crece con el tamaño del grupo, no con el número de grupos.
- **El juez comparte familia con el generador**: `claude-sonnet-5` juzgando a
  `claude-haiku-4-5`. `Config` impide que sean el mismo modelo, no que sean de
  la misma familia, y esa es la configuración con la que está medido todo el
  banco. Desde el §24 la limitación viaja en cada `resumen.json` y en cada
  `informe.md` en vez de vivir en un docstring, y el experimento que la mide
  está diseñado: faltan una segunda clave de Gemini y 0,22 USD.
- **La rama estructurada no dice de qué herramienta sale cada dato.** Responde
  "según la búsqueda en el CRM" cuando el prompt pide la herramienta, y con
  cinco publicadas eso no permite volver a la llamada que produjo el número. Es
  el único defecto que el verificador de citas encontró, cuesta dos casos del
  banco de la agencia y no afecta al heredado (§23).
- **El camino documental heredado sigue presentando una denegación como una
  ausencia.** Si el permiso retiene todo lo recuperado, responde "no he
  encontrado documentación relevante". El camino mixto ya lo dice bien; el
  heredado no, y arreglarlo mueve las respuestas de los casos de
  confidencialidad del inquilino A, así que es una medición aparte (§22).
- **Línea base cortada el 22-09-2026, con fecha y por escrito**
  (`docs/ALCANCE.md` §5.c). La temperatura del enrutador pasa a **0.0** por
  defecto y el juez por defecto a **`gemini-3.6-flash`**. Las métricas de antes
  y de después **no son comparables**, y esa es la única razón por la que el
  corte está documentado: para no citar en la memoria dos cifras que miden
  configuraciones distintas. `ROUTER_TEMPERATURE=defecto` y
  `JUDGE_PROVIDER=anthropic` reproducen el comportamiento viejo.
- **Con el juez por defecto en Gemini, `LLM_PROVIDER=gemini` colisiona**: los
  dos caen en `gemini-3.6-flash` y el juez evaluaría su propio texto. `Config`
  lo rechaza en el arranque y lo dice. Es la primera piedra de quien conmute el
  proveedor para el capítulo de comparativa.
- **Temperatura 0 no es determinismo garantizado**: 1 caso de 53 sigue variando
  en el inquilino heredado. Y no hace determinista al banco, porque el generador
  sigue muestreando (§27). No prometer reproducibilidad en la memoria.
- **El número del juez puede contradecir su propio razonamiento**, y está
  medido en dos familias con el mismo prompt y las mismas trazas: Anthropic
  escribió *"mereciendo la puntuación máxima"* y emitió 0,1; Gemini, **a
  temperatura 0**, escribió *"cumple exactamente"* y emitió 0,1 (§30). No es la
  temperatura ni la familia: es pedir número y justificación en la misma
  respuesta. Dos reglas que salen de ahí: una puntuación de juez no se lee sin
  su razón, y ninguna decisión del proyecto cuelga de una métrica de juez.
- **`pii_leakage` está retirada del banco** desde el 22-09-2026, decidido con
  los números delante (§30, §31). Su escala se invertía entre casos y penalizaba
  al sistema **por nombrar a la persona cuyos datos estaba protegiendo**: una
  denegación correcta sacaba 0,00. Afectaba a 17 casos, no a 6, porque era
  métrica por defecto de dos dimensiones enteras. Un caso que la pida ya no
  carga.
- **La comparación base/endurecido está cerrada, y con métrica determinista**
  (§31, §33). Rehacerla con juez es imposible: 5 y 6 casos de 10 cambian de
  veredicto entre tres pasadas idénticas. La decide `fuga_literal`, que no
  varía: **la política base filtra el salario individual de un empleado y un
  dato de salud** citando el anexo confidencial, y la endurecida no filtra
  ninguno de los dos — 8/10 frente a 10/10. Eso es lo citable en la memoria.
- **Al juez la temperatura no le hace nada y sus errores van en un solo
  sentido** (§32, piloto completado con 6 pasadas). Temperatura 0 deja la misma
  inestabilidad que muestrear —2 casos de 4 en las dos familias— y de 24
  veredictos, 4 son espurios y **los cuatro suspenden lo que debía aprobar**.
  Ni uno al contrario. Consecuencia: **`casos_ok` de una pasada con juez es un
  suelo**, y promediar pasadas empeora la cifra en vez de cancelar el error. La
  única corrección conocida es la mayoría de tres, que da 4 de 4 en los dos
  brazos.
- **El juez recomendado pasa a ser `gemini-3.6-flash` repetido tres veces**: es
  5,5 veces más barato por evaluación, así que tres pasadas cuestan menos que
  una de `claude-sonnet-5`, y es además el único con independencia de familia
  (§24). Cambiarlo por defecto es decisión de línea base y está sin tomar.
- **Los costes de juez del proyecto son suelos**: 0,00417 y 0,00076 USD por
  evaluación se midieron con `confidencialidad`, un G-Eval de una llamada,
  mientras `faithfulness` descompone la respuesta y cuesta varias. Una pasada
  completa de los dos bancos sale por 0,73 USD (Anthropic) o 0,40 USD (tres
  pasadas de Gemini) **como mínimo** (§32).
- **El juez muestrea aunque el código diga `temperature=0`.** `claude-sonnet-5`
  no admite el parámetro y DeepEval lo descarta sin avisar (§26). Explica la
  varianza del juez medida en la 3.3, y no tiene arreglo en este modelo: la
  única vía a un juez repetible es el juez de Gemini, que es además el de otra
  familia.

- **El modelo de embeddings está en retirada, y desde el 23-09 su consumo se
  contabiliza pero no se convierte a dólares** (§35, §37). `gemini-embedding-001`
  cierra el 14-05-2028 con sucesor `gemini-embedding-2` y ya no aparece en la
  página de precios. `src/embeddings.py` cuenta tokens (exactos en la ingesta,
  estimados en la consulta a 4,20 caracteres por token, medido sobre las 91
  consultas del golden set) y los registra aparte de los totales del chat, así
  que ninguna cifra de coste guardada cambia. **Decidido el 23-09: no se
  migra antes de la defensa**, porque invalidaría el índice y movería las
  métricas de recuperación; queda como decisión de línea base pendiente con
  fecha límite. Al citar un coste, decir que excluye los embeddings.
- **El calendario del AI Act cambió el 27-07-2026 y el capítulo tiene que
  citar el texto vigente.** El Reglamento (UE) 2026/1744 (Ómnibus digital
  sobre IA) retrasa las obligaciones de alto riesgo del anexo III al **2 de
  diciembre de 2027**; el artículo 50 (informar de que se interactúa con una
  IA) aplica desde el 2 de agosto de 2026 y ya rige en la defensa. La
  clasificación por inquilino se presenta como diseño anticipado, no como
  cumplimiento exigible. Contrastado el 23-09 contra la Comisión y el BOE;
  citas literales y fuentes en `docs/MODULO_4.md`, sección del artículo 6.
- **El resultado de sesgo es nulo en una capa, no una ausencia de sesgo.**
  Ningún eje —género, edad, origen, discapacidad— alcanza el doble de su suelo
  de ruido en la recuperación, y el enrutado es estable en las seis variantes de
  nombre (§34). Pero **la capa de generación no se ha medido**, y presentar esto
  como "el sistema no discrimina" sería la falsa objetividad que el propio
  Módulo 4 enumera como riesgo. Medir la generación exige un criterio de
  equivalencia de contenido entre respuestas con nombres distintos, y montarlo
  con juez choca con los §30, §32 y §33.
- **El experimento de sesgo se equivocó tres veces antes de acertar**, y las
  tres afirmaciones intermedias eran falsas, concretas y alarmantes (§34). De
  ahí las trece pruebas que comprueban que los pares sigan emparejados: son la
  única condición de la que depende que la cifra signifique algo. Si se añaden
  ejes o variantes, esas pruebas son lo que impide repetir el error.

## 9. Superficies de trabajo y cómo se sincronizan

El proyecto se trabaja desde dos sitios. **Sobre el estado del proyecto el flujo
es de una sola dirección**; sobre el trabajo por hacer, desde el 22-09-2026 hay
un canal de vuelta.

| | Claude Code | Proyecto **MASTER IA TFM** en la app de Claude |
|---|---|---|
| Para qué | Todo el desarrollo: código, corpus, bancos, mediciones, documentación | Lo que Claude Code no puede hacer |
| Concretamente | | Tareas de navegador con Claude in Chrome (formularios, altas), discusión de diseño, redacción de material |
| Sobre el estado | **Lo escribe** | **Lo lee**, por la conexión de GitHub al repositorio |
| Encargos | **Los escribe**, con `node puente/encargar.mjs`, declarando el modo (`desatendido` o `supervisado`) y abriendo la app con `--abrir` si hace falta a Juan | **Los lee**, con `encargos_tfm`; los desatendidos, la tarea programada del proyecto |
| Registro de lo hecho | **Lo lee**, en `puente/REGISTRO_APP.md` | **Lo escribe**, con `registrar_tfm` |
| Avisos de que algo ha vuelto | **Los recibe** en cada prompt por el hook de `.claude/settings.json`, con un análisis automático ya hecho; los cierra con `puente/avisos.mjs --atendido` | **Los provoca** al registrar, sin hacer nada más |

Los ficheros del puente **no están versionados** y por eso no los ve el
conector de GitHub: toda lectura desde la app pasa obligatoriamente por el
puente. Escribir en el buzón es lo único que la app no puede hacer, y es
deliberado: quien ejecuta los encargos no puede darse encargos a sí mismo. Y
**la cadena termina en Claude Code**: un aviso nunca genera un encargo nuevo
por sí solo; si la acción es volver a encargar, pasa por Juan. Desde el
23-09-2026 el ciclo está montado y medido en simulación; lo que falta medir con
la app son dos cosas, un encargo ejecutado desde el enlace profundo y uno
desatendido registrado por la tarea programada. El detalle está en
`docs/SINCRONIZACION_SUPERFICIES.md` §7.6 y `puente/README.md`.

**El repositorio es la fuente de verdad y la app no.** Sus instrucciones de
proyecto lo dicen: ante una contradicción, gana lo que haya aquí. Y por el mismo
motivo, **esas instrucciones no copian estado**. Describen quién es el alumno,
cómo hablarle, las reglas de estilo y las reglas de navegador; para saber cómo
está el proyecto mandan a leer este fichero. Un estado copiado deriva en días:
ya pasó con la primera versión, escrita el 20 de septiembre y desfasada el 21.

### Lo que sostiene la sincronización

`/cierre` al terminar la jornada. Escribe la entrada de bitácora, actualiza este
documento y hace commit y push. **Sin ese push, la app no se entera del estado**
y la siguiente sesión de Claude Code arranca con un mapa viejo. Lo que no está
en el repositorio no existe.

El buzón y el registro son la excepción y no la contradicen: viven fuera de git
a propósito, así que no se sincronizan por push sino por el puente, y lo que
llega por ahí **no es estado del proyecto sino trabajo pendiente o rastro de lo
hecho**. Cuando algo del registro afecta al alcance, se traslada a mano a
`docs/ALCANCE.md` o a este documento desde Claude Code, que es lo que mantiene
la dirección única sobre el estado.

### Al cambiar de repositorio

Si el proyecto se mueve a otro repo —ya pasó una vez, al retirar
`multi-agent-support-platform`— hay que **repuntar la conexión de GitHub del
proyecto de la app**. Si no, sigue leyendo un repositorio muerto sin dar ningún
aviso.

## 10. Mantenimiento

Al cerrar un avance relevante: actualizar la sección 2, anotar el hallazgo
medido en `docs/HALLAZGOS.md` citando su ejecución, y commitear junto al código.
