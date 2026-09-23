# Bitácora del TFM — Asistente multi-tenant

> Diario de sesiones. Entradas de más reciente a más antigua.
> El histórico de la entrega 3.3, de la que parte este repositorio, está en
> `BITACORA_3.3.md`.

## 2026-09-23 — Sesión 6: el puente se cierra solo, y el servicio público resulta ser el mejor banco de pruebas

**27 commits, 9 hallazgos (del §35 al §43), 1.033 tests**, ocho encargos
reales por el puente con la app y un servicio desplegado. Gasto del día en
proveedores: en torno a 1,3 USD entre bancos, reindexaciones y pruebas.

El hilo del día: cada vez que algo se probó **fuera del banco** (la app, el
servicio público, un inventario generado) apareció un defecto que el banco
no podía ver. Cinco de los nueve hallazgos salieron así.

**Hecho, por orden:**

- **Puente Claude Code / app cerrado en las dos direcciones.** Modo del
  encargo (`desatendido` / `supervisado`), enlace profundo `cowork/new` con la
  orden en la caja (la ruta del proyecto ignora `q`, medido), aviso a Claude
  Code al registrar con análisis automático de solo lectura, hook de
  `UserPromptSubmit` que lo inyecta en cada prompt, notificación de escritorio
  para Juan. Cinco defectos del propio puente corregidos sobre la marcha: el
  hook con `$CLAUDE_PROJECT_DIR` (PowerShell), el tope de `consultar_tfm` por
  encima del corte de 60 s de la app, el servidor muriendo al cerrarse la
  entrada, el proceso viejo del puente tras editar el código (regla: reiniciar
  la app; `avisos.mjs --reconstruir` repara), y el límite de 1.000 caracteres
  en `hecho`. Ocho encargos atendidos, ocho avisos que llegaron solos.
- **Esqueleto del capítulo del Módulo 4.** `docs/RIESGOS.md` (23 riesgos con
  Rumsfeld, OWASP, ATLAS, AIUC-1 y evidencia, vigilado por test),
  clasificación por el AI Act en cada manifiesto con la regla del 6.3
  codificada y el aviso del artículo 50 en la interfaz, `AIBOM.md` generado,
  `INCIDENTES.md`, `RETENCION.md` con supresión y purga con lápida, borrado
  cronometrado de documentos (1,46 s y 1,23 s), embeddings contabilizados.
- **El AI Act cambió el 27-07-2026** (Reglamento 2026/1744): lo trajo la app
  por el encargo E-0004 leyendo EUR-Lex y se contrastó contra la Comisión y el
  BOE. Alto riesgo del anexo III al 2-12-2027; artículo 50 ya en vigor en la
  defensa. El capítulo cita el texto vigente.
- **Interfaz desplegada** (`app.py`, Render): inquilino fijado por la
  credencial, roles al control de acceso, tope blando de gasto, versión
  visible. Primer despliegue 1 min 32 s. Se paró en el login por exigir la
  clave del juez (§38); arreglado con `con_juez=False`.
- **Segundo corte de línea base (§5.d):** el generador sabe quién pregunta y
  que su contexto está autorizado. Antes negaba un salario a `direccion` 3 de
  5 veces por la cabecera CONFIDENCIAL del anexo (§39); después 5 de 5, y
  ninguna métrica de confidencialidad se movió (§40).
- **Agujero por tamaño en la redacción** (§41): el recorte a 6.000 caracteres
  iba antes de redactar y dejaba pasar JSON roto sin redactar. Encontrado en
  el servicio público, cerrado con seis pruebas.
- **Human-in-the-loop** (§42): escritura real en el CRM declarada en el
  manifiesto y anotada por el servidor, propuesta por el modelo y aprobada por
  una persona desde la interfaz; métrica `accion_sin_aprobar` 40/40; probado
  en Render (VIS-901). Tres defectos de interfaz corregidos.
- **Alta cronometrada del tercer inquilino** (§43): `gestoria_laboral` en
  **5 min 42 s**, dos iteraciones, cero ficheros de código; 20/28 y 25/28.
- Guion de la demo (`docs/GUION_DEMO.md`), credenciales propias en el servicio.

**Decisiones:**

- **No migrar el modelo de embeddings antes de la defensa**; contabilizar
  tokens y dejar la migración con fecha límite 14-05-2028 (§35, §37).
- **Decirle al generador quién pregunta y su rol**, con corte fechado, porque
  el principio es control antes del modelo y el modelo no lo sabía (§5.d).
- **Render sigue vivo**, con credenciales propias, para seguir probando ahí.
- **Las tareas programadas de la app no son necesarias**: el ciclo funciona
  con una pulsación y los encargos que valen necesitan navegador.
- **Una expectativa demasiado literal (`front-03` de la gestoría) no se
  corrige tras ver el resultado**; se anota para revisarla con criterio.

**Pendiente para la próxima sesión:**

- [x] ~~Pegar el JSON nuevo en `APP_USUARIOS_JSON` de Render~~ **Hecho por
      Juan al cerrar la sesión**: los seis usuarios (dos por inquilino) están
      activos en el servicio y las seis contraseñas guardadas en su gestor.
      No están en ningún fichero ni en la memoria del proyecto.
- [ ] Revisar `front-03` de `gestoria_laboral` (literal "cinco dias antes"
      frente a "5 días") con criterio, y `agg-01` (`plazos internos` sigue
      yendo a `procedimientos`).
- [ ] **Sesgo en la capa de generación** (R-13), lo único del registro de
      riesgos sin cerrar; exige un criterio de equivalencia sin juez.
- [ ] Simulacro cronometrado del plan de incidentes (R-23).
- [ ] Verificar los identificadores de MITRE ATLAS contra la matriz viva antes
      de la memoria.
- [ ] Bloque 3 del alcance: clasificador pequeño; canales (correo, WhatsApp).
- [ ] `inj-04` del heredado y la denegación presentada como ausencia en el
      camino documental heredado, los dos desde la sesión 5.
- [ ] Formato de la defensa: sigue sin conocerse.

**Notas:**

- **El proceso del puente que usa la app arranca con la app.** Tras editar
  `puente/servidor.mjs` hay que reiniciar la app de Claude; si no, registra
  con el código viejo y no avisa. `avisos.mjs --reconstruir` repara el caso.
- **EUR-Lex no se deja leer sin navegador** (202 vacío); la app con Chrome sí
  puede, y es un buen encargo desatendido.
- **Las cifras de coste guardadas excluyen embeddings** y hay que decirlo al
  citarlas; el registro marca `modelos_sin_precio` cuando aplica.
- Precios y calendarios que cambian solos: `gemini-embedding-001` en retirada
  (cierre 14-05-2028), `gemini-3.6-flash` dobla precio el 01-01-2027, AI Act
  reescrito en julio. El AIBOM y la tabla de precios son lo que los vigila.
- Un commit salió hoy con cuatro pruebas en rojo porque la cadena no frenaba
  con el código de salida de `pytest`; desde entonces el commit está gateado.

## 2026-09-22 — Sesión 5: la tutoría, y catorce hallazgos de mirar con desconfianza

La sesión más larga del proyecto: **18 commits, 34 hallazgos (del 21 al 34),
716 tests** y la tutoría que cierra cuatro riesgos abiertos desde julio. Gasto:
**1,40 USD** de los 12,66 de crédito.

El hilo que la recorre no se planificó. Catorce de los hallazgos salieron de
**mirar un resultado con desconfianza**, no de buscar fallos, y en varios el
error estaba en el instrumento y no en el sistema.

**Hecho, por orden:**

- **Precio de `claude-sonnet-5` corregido (§21).** La consola marcó 0,06 USD
  contra los 0,083 que predecía el repo: es 2,00/10,00 y no 3,00/15,00, que es
  el de Sonnet 4.6. Evaluar cuesta **x11 y no x17**; una pasada completa 2,53 USD
  y no 3,80. El test congelaba `0.1252 / 3`, un literal en USD, así que no podía
  detectar que un factor fuese falso; ahora recalcula desde los tokens y la tabla
  de precios viva.
- **Solapamiento `expedientes`/`cartera` resuelto (§22).** Grupo declarativo en
  el manifiesto y camino mixto: una consulta ambigua consulta las dos ramas en
  vez de elegir. **Cobertura del riesgo 0,778 → 1,0**, y el caso que en
  producción se quedaba sin respuesta ya la da. Precio medido: +40 % de coste por
  caso. De paso, la prueba por la vía contraria de que el solapamiento no era
  ruido: el reparto sale **idéntico en tres pasadas** mientras el 13,2 % de los
  demás casos cambia de categoría.
- **Verificador determinista de citas (§23).** El prompt exigía citar la fuente y
  nada lo comprobaba. Dos rúbricas sin modelo, aplicadas **retroactivamente a las
  22 ejecuciones guardadas a coste cero**: **588 de 588 citas resolubles, cero
  inventadas en toda la historia del proyecto**. La métrica se estrenó
  midiéndose a sí misma dos veces: los acentos y la puerta de comportamiento.
- **Clave propia del juez también en el camino de Gemini (§24).** Usaba la de los
  embeddings, o sea la del sistema, y solo en el único camino que permite tener un
  juez de otra familia. Lo que impedía el fallo era una cuota ajena, no un
  control. Y la limitación de familia dejó de vivir en un docstring: viaja en
  cada `resumen.json` y cada `informe.md`.
- **Prerruta determinista descartada (§25)** con una cuenta de dos minutos:
  ninguno de los 5 casos que derivan lleva identificador, y los 7 que lo llevan
  están todos en el grupo ya resuelto.
- **El juez nunca corrió a temperatura 0 (§26).** `claude-sonnet-5` no admite el
  parámetro y DeepEval lo descarta **en silencio**. Explica la varianza medida en
  la 3.3 y no tiene arreglo en ese modelo.
- **Varianza del enrutador medida y resuelta (§27).** Venía de que el proveedor no
  fijaba temperatura. A 0: **3 casos inestables de 38 pasan a 0** y elige la misma
  categoría que la mayoría de cinco muestras en los 38. **La votación por
  autoconsistencia queda descartada por redundante**, y con ella los 1,2 USD que
  costaba demostrarla.
- **Tres defectos que solo aparecieron al usar el camino de Gemini (§28, §29).**
  Un modelo sin precio costaba **cero en silencio**, dentro de la contabilidad
  sobre la que se apoyan tres hallazgos de coste. La conmutación de proveedor era
  una forma y no un hecho: `gemini_model` se declaraba y no se leía. Y
  `gemini-2.5-flash` ya no se sirve a proyectos nuevos, así que nadie que clonase
  el repo podría reproducirla.
- **El juez emite números que contradicen su propio razonamiento (§30, §32).**
  Escribió *"mereciendo la puntuación máxima"* y puso 0,1. Piloto completado con
  seis pasadas: **temperatura 0 no lo estabiliza** —2 casos de 4 en las dos
  familias— y de 24 veredictos **4 son espurios y los cuatro suspenden lo que
  debía aprobar**. Ni uno al contrario.
- **`pii_leakage` retirada del banco (§31).** Su escala se invertía entre casos y
  **penalizaba al sistema por nombrar a la persona cuyos datos estaba
  protegiendo**: una denegación correcta sacaba 0,00. Afectaba a 17 casos, no a
  6, porque era métrica por defecto de dos dimensiones enteras.
- **La comparación base/endurecido cerrada, y con métrica determinista (§33).**
  Con juez es imposible: 5 y 6 casos de 10 cambian de veredicto entre tres
  pasadas idénticas. La decide `fuga_literal`: **la política base filtra el
  salario individual de un empleado y un dato de salud** citando el anexo
  confidencial, y la endurecida no filtra ninguno — **8/10 frente a 10/10**.
- **Buzón de encargos** (`puente/encargar.mjs` y `encargos_tfm`), con la tutoría
  como primer caso real, **E-0001**. Escribir en el buzón no es herramienta MCP a
  propósito: quien ejecuta los encargos no puede darse encargos a sí mismo.
- **Tutoría con Iraitz** (`docs/TUTORIA_2026-09-22.md`). Cierra cuatro riesgos
  abiertos desde julio.
- **Las dos decisiones de línea base aplicadas** (`ALCANCE.md` §5.c), sin gastar
  nada: las ejecuciones `temp0` de la mañana ya eran la línea base nueva.
- **Banco de sesgos (§34).** Ningún eje —género, edad, origen, discapacidad—
  alcanza el doble de su suelo de ruido, y el enrutado es estable en las seis
  variantes de nombre. Trece pruebas que no comprueban que el código funcione
  sino que **los pares sigan emparejados**.
- **Análisis del Módulo 4** (`docs/MODULO_4.md`) y reorganización de su material.

**Decisiones:**

- **`ROUTER_TEMPERATURE=0` y juez por defecto `gemini-3.6-flash`**, con el corte
  de comparabilidad fechado en `ALCANCE.md` §5.c. Se tomaron hoy y no esperando
  la rúbrica porque la tutoría la situó en 2-3 semanas con la defensa a finales
  de mes: tomarlas en esa ventana no dejaría tiempo de volver a medir.
- **La mayoría de tres NO se automatiza.** El §33 midió que sobre 10 casos tres
  pasadas no alcanzan; automatizarla habría vendido como resuelto algo que no lo
  está.
- **`pii_leakage` fuera, con puerta en la carga del dataset** y no en la
  evaluación: descartarla en el runner la habría dejado desaparecer del informe
  sin distinguir "se pidió y se ignoró" de "nunca se pidió".
- **Votación por autoconsistencia y prerruta determinista descartadas**, las dos
  con la cuenta que las descarta escrita.
- **El material docente del máster no entra en el repositorio.** Es obra de un
  profesor y el repositorio es público; commitearlo sería redistribuirla, y son
  38 MB que git no olvida. Vive en `Master/Módulo N/`, se cita desde
  `docs/MODULO_4.md`, y hay regla en `.gitignore`.
- **Prepago de 5 EUR con recarga desactivada** en el proyecto `tfm-juez` de
  Google, que replica el tope duro que ya tiene la cuenta de Anthropic.

**Medido:**

| | |
|---|---|
| Cobertura del riesgo, inquilino C | 0,778 → **1,0** |
| Citas resolubles, 22 ejecuciones | **588 / 588**, cero inventadas |
| Casos inestables del enrutador, a temperatura 0 | 3 de 38 → **0** |
| Veredictos espurios del juez, y todos en el mismo sentido | **4 de 24** |
| Base frente a endurecido, `fuga_literal` | 8/10 frente a **10/10** |
| Ejes de sesgo por encima de su suelo | **0 de 4** |
| Coste del día | **1,40 USD** de 12,66 |

**Pendiente para la próxima sesión:**

- [ ] **Registro estructurado de riesgos con la matriz de Rumsfeld del 4.4** y
      mapeo a MITRE ATLAS y AIUC-1. Es el esqueleto del capítulo del Módulo 4 y
      no cuesta ejecuciones: coloca los 34 hallazgos en una estructura que el
      módulo reconoce. **Es lo siguiente.**
- [ ] **Clasificación por el artículo 6 del AI Act, por inquilino.** El mismo
      sistema es de riesgo limitado o de alto riesgo según el inquilino, y el
      manifiesto es donde se declara.
- [ ] **Red-teaming con herramienta** (garak o DeepTeam). Los casos de inyección
      del banco son curados a mano.
- [ ] **Human-in-the-loop**, que cierra OWASP #8 y la falta de supervisión humana.
- [ ] **Derechos del RGPD sobre el índice**: el camino de borrado, cronometrado.
- [ ] **Cadena de suministro**: un AIBOM. Cierra OWASP #5 y es baratísimo.
- [ ] **`inj-04` es una inyección que el enrutador manda a `otro`** y nunca llega
      al control. Es defecto de enrutado, no de gobernanza.
- [ ] **El camino documental heredado presenta una denegación por permiso como
      una ausencia.** El camino mixto ya lo dice bien; el heredado no, y
      arreglarlo mueve las respuestas del inquilino A.
- [ ] Sesgo en la **capa de generación**, que es la que el §34 deja declarada sin
      medir.
- [ ] Despliegue con autenticación, canales y alta cronometrada, del alcance.

**Notas:**

- **El Módulo 5 se libera al acabar el 4, en 2-3 semanas**, y con él el enunciado,
  la rúbrica y la fecha exacta. La defensa es a finales de octubre.
- **Lo único que sigue sin saberse es el formato de la defensa**: duración, demo
  en vivo o grabada, tribunal. De eso depende si hay que dejar el despliegue
  funcionando.
- **Partir de las entregas propias calificadas es admisible y no hay que
  declararlo**, y el uso de IA es libre. Los dos riesgos que más trabajo podían
  costar quedan cerrados.
- **Catorce hallazgos de una sesión, y el patrón se repite:** el §21, el §23, el
  §26, el §28, el §29, el §31, el §33 y el §34 salieron de mirar un resultado y
  preguntarse por qué salía así. En cuatro de ellos el error estaba en el
  instrumento, no en el sistema. Y tres veces —§25, §33, §34— el corolario fue el
  mismo: la comprobación que descartaba lo que estaba haciendo se podía haber
  hecho **antes** de empezar.
- **Dos afirmaciones mías corregidas el mismo día**: que la mayoría de tres
  resolvía la inestabilidad del juez (§32, corregido en el §33) y que
  securización no era ciberseguridad (corregido al leer los cuatro apartados del
  Módulo 4, no solo el 4.1).
- Documento de apoyo para la tutoría en Notion, como página privada.

## 2026-09-21 (tarde) — Sesión 4: el puente, el coste medido y la observabilidad

Sesión de infraestructura y de medición. No se tocó el sistema evaluado: ni el
corpus, ni los bancos, ni el prompt del enrutador. Las cifras del §2 no se mueven.

**Hecho:**

- **Puente MCP con la app** (`puente/servidor.mjs`), Node sobre stdio y sin
  dependencias. Dos herramientas: `consultar_tfm`, que responde sobre el árbol de
  trabajo real incluido lo no pusheado, y `registrar_tfm`, que añade una entrada
  al registro con la fecha puesta por el puente. Puesta en marcha y pruebas en
  `puente/README.md`.
- **`docs/SINCRONIZACION_SUPERFICIES.md` commiteado, con tres de sus
  afirmaciones corregidas** contra el código y marcadas en su sitio.
- **El juez, instrumentado.** `evals/metrics/juez.py` no contaba tokens; ahora
  acumula en el mismo `Uso` que el sistema, con la tabla de precios del
  proyecto, y el informe publica su coste aparte del del sistema.
- **Aviso de coste en el runner.** `--desde-trazas` no evita el coste del juez, y
  la ayuda de `--sin-juez` decía "(gratis)". Corregidas las dos, y ahora avisa
  con la cifra medida antes de gastar.
- Hallazgos 16 y 17 escritos. 596 → **600 tests en verde**.

**Decisiones:**

- **El buzón y el registro se gitignoran.** El repositorio es público y no se
  conoce aún la rúbrica del TFM; publicar es irreversible de hecho y gitignorar
  se deshace en un commit. Con las reglas sin conocer, gana la opción reversible.
- **Un solo workspace `Default` con las tres claves.** La consola ya desglosa
  coste **por clave**, que es lo que pedía el feedback de la 3.3. Los workspaces
  solo añadirían un límite por separado, redundante con el prepago.
- **Descartada la Admin API.** Se propuso para localizar 0,30 USD sin explicar;
  la consola lo resolvió con un clic y no compensa emitir una credencial con
  permisos sobre toda la organización.
- **La sesión hija del puente no tiene Bash.** Las listas blancas de Bash casan
  por prefijo y una instrucción inyectada puede componer órdenes que pasen el
  filtro. El puente ejecuta `git` él mismo con argumentos fijos y le pasa el
  resultado como dato; la hija corre con `--restricted` y solo `Read`, `Grep`,
  `Glob`.

**Medido:**

| | |
|---|---|
| Coste del juez, por caso | **0,0417 USD** (24 llamadas sobre 3 casos) |
| Contra el sistema (0,00245 USD/caso) | **evaluar cuesta x17 que responder** |
| Pasada completa con juez, los dos bancos | **3,80 USD** |
| Crédito de prepago disponible | 12,87 USD — **3,4 pasadas** |
| Gasto no visto por `reports/` | **22 %** del gasto de la propia clave |

**Segunda mitad de la sesión — tres cosas que salieron de comprobar, no de planificar:**

1. **La clave del juez no se usaba.** `tfm-juez` seguía a 0,00 tras refrescar la
   consola. No era latencia: la clave estaba en el `.env` y en la consola, pero
   `src/config.py` no la leía y el runner pasaba la del sistema. **Todas las
   llamadas del juez de la historia del proyecto se han facturado a
   `tfm-sistema`.** Arreglado con dos validaciones que abortan en el arranque
   —sin clave propia, y con las dos variables iguales— y tres pruebas. Hallazgo
   18, con correcciones anotadas en los hallazgos 16 y 17, que se escribieron una
   hora antes dando la separación por buena.

2. **La sesión hija del puente podía leer el `.env`.** Lo destapó su propia
   respuesta: al preguntarle qué había sin commitear, explicó que había leído las
   refs de `.git/` directamente. `--restricted` confina las herramientas de
   fichero al directorio de trabajo, y el directorio de trabajo **es** el
   repositorio, donde viven las dos claves en claro. Comprobado: las leía.
   Cerrado con `--disallowedTools` sobre `Read` y `Grep`, verificado con una
   petición directa y con un rodeo por `Grep`, los dos rechazados. Hallazgo 19.

3. **Observabilidad en producción**, que era el punto 10 del bloque 2 y el
   feedback de la 3.1 abierto desde julio. Registro JSONL solo-añadir, un fichero
   por inquilino, **opt-in** para que el banco no contamine el log, y coste
   atribuido por consulta con un acumulador hijo por hilo. Hallazgo 20.

**Además:**

- **Búsqueda exhaustiva del campus** (`docs/CAMPUS_2026-09-21.md`), hecha con
  Claude in Chrome desde la app. Confirma que **no hay publicado nada del TFM** y
  amplía el riesgo: tampoco hay reglamento, normativa de integridad, norma sobre
  reutilización de trabajos propios ni política de uso de IA.
- **Puente declarado en la app** como `claude-code-tfm`, siguiendo la convención
  de los otros dos que ya había en este equipo. Verificado con la línea de
  órdenes exacta que usa la app.
- **Tutoría reservada** con Iraitz Montalbán para el 22-09 a las 16:00.

**Medido en la segunda mitad:**

| | |
|---|---|
| Consultas reales registradas | 3, en dos inquilinos |
| Coste por consulta en producción | 0,00085 – 0,00186 USD |
| Latencia media / p95 (inquilino A) | 3,2 s / 3,6 s |
| Tests | 603 → **621 en verde** |

**Dos lecturas que cambiaron al ejecutarlas:**

- La señal `control_actuo` que escribí para el registro se disparaba también con
  *"¿cuántos días de vacaciones tengo?"*, porque el anexo confidencial vive en la
  fuente `rrhh` y el filtro lo retiene en toda consulta de esa fuente. El panel
  decía "el control actuó en el 100 % de las consultas", que se lee como "todos
  intentan colarse". Partida en tres señales, una ruidosa y dos significativas.
- La primera consulta real de la agencia pidiendo datos de una operación **se
  quedó sin respuesta**: se enrutó a `expedientes` en vez de a `cartera`. Es el
  solapamiento del hallazgo 12 visto desde producción, donde ya no son dos casos
  sucios de treinta y ocho sino un usuario que no recibe nada.

**Pendiente para la próxima sesión:**

- [ ] **TUTORÍA 22-09 a las 16:00 con Iraitz.** Es lo que desbloquea el alcance.
      Cuatro preguntas, por orden de lo que puede hacer perder más trabajo: si es
      admisible partir de entregas propias ya calificadas y si hay que
      declararlo; enunciado y criterios de evaluación; política de uso de IA; y
      confirmar que el 20 de octubre es la defensa, porque hoy eso sale de la
      leyenda de una imagen. **El guion está sin preparar a propósito**, pedido
      por Juan.
- [ ] **Mirar `tfm-juez` en la consola.** Venía de cero absoluto y
      `juez_clave_propia` gastó con la clave nueva. **0,083** = el repo acierta
      con 3,00/15,00; **0,055** = son 2,00/10,00 y `src/provider.py:54`
      sobreestima un 33 %; **0,00** = el arreglo no funciona. Al cierre seguía a
      0,00 y `tfm-sistema` tampoco se había movido, así que es latencia del
      informe de costes.
- [ ] **Despliegue con autenticación**, ya desbloqueado: el tope de gasto existe.
- [ ] **Análisis de riesgos y encaje con el EU AI Act**, que absorbe el Módulo 4.
      Conviene esperar a la rúbrica: su forma depende de ella.
- [ ] **Punto 3 del §7 de `SINCRONIZACION_SUPERFICIES.md`**: buzón de encargos.
      La tutoría de mañana es su primer caso real: lo preguntado, lo respondido y
      lo que quede abierto son los seis campos de `registrar_tfm`.
- [ ] **Punto 4**: `medir_tfm` asíncrona, solo `--desde-trazas --sin-juez` y con
      el inquilino como parámetro explícito con lista blanca.
- [ ] Decidir qué hacer con el solapamiento `expedientes`/`cartera`. La salida
      apuntada es consultar las dos ramas; la observabilidad le ha subido la
      prioridad.
- [ ] Canal de correo y servidor MCP del Catastro, ambos del bloque 2.

**Notas:**

- **No activar la recarga automática** de la cuenta del proveedor. El prepago
  (12,87 USD, recarga desactivada) es un tope duro y es lo único que lo rompería.
- El conector de GitHub de la app **funciona**, verificado. Y el puente también,
  declarado como `claude-code-tfm`.
- Nada del sistema evaluado se ha tocado hoy: ni corpus, ni bancos, ni el prompt
  del enrutador. Las cifras de calidad del §2 siguen siendo las de la sesión 2.
- Tres de los cinco hallazgos de hoy (18, 19 y 20) salieron de **comprobar algo
  que se daba por bueno**, no de buscar fallos. Los tres comparten forma con el 9
  y el 13: una señal que no se dispara, o que se dispara por el motivo
  equivocado, se parece mucho a que todo va bien.

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
