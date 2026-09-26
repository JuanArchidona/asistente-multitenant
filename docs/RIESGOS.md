# Registro de riesgos

> Esqueleto del capítulo de IA responsable y seguridad (el que absorbe el
> Módulo 4). Coloca los hallazgos medidos de `HALLAZGOS.md` en las
> estructuras que el módulo reconoce: la **matriz de Rumsfeld** (4.4), el
> **OWASP Top 10 para LLM** (4.3), **MITRE ATLAS** (4.3) y los dominios de
> **AIUC-1** (4.4). Abierto el 23-09-2026.
>
> Regla del registro: **cada fila cita la ejecución o el hallazgo que la
> respalda**, y `tests/test_riesgos.py` comprueba que cada `§N` citado existe
> en `HALLAZGOS.md` y que las diez casillas del OWASP tienen fila. Una fila sin
> evidencia es una opinión, y aquí no caben.
>
> La clasificación por el AI Act no está aquí: vive en `tenants/<id>.json`,
> bloque `ai_act`, porque cambia por inquilino. Ver §4.

## 1. Cómo leerlo

| Columna | Qué significa |
|---|---|
| Cuadrante | Matriz de Rumsfeld del 4.4. **CC** conocido-conocido (se prueba y se mide), **CD** conocido-desconocido (se vigila), **DC** desconocido-conocido (se evalúa activamente porque otros lo saben y nosotros no lo veíamos), **DD** desconocido-desconocido (botón rojo y plan) |
| OWASP | Casilla del Top 10 para LLM, 1 a 10; `—` si no encaja en ninguna |
| ATLAS | Técnica de MITRE ATLAS más cercana. **Verificados el 23-09-2026 contra ATLAS 5.6.0** (`atlas-data`, entradas modificadas hasta el 30-04-2026): los ocho identificadores existen; tres cambiaron de nombre (T0010 es ahora *AI Supply Chain Compromise*, T0029 *Denial of AI Service* y T0053 *AI Agent Tool Invocation*, antes *LLM Plugin Compromise*), y dos filas ganaron una técnica más precisa que no existía cuando se escribieron (T0055 *Unsecured Credentials* en R-04, T0070 *RAG Poisoning* en R-10). Volver a comprobar antes de la memoria si pasan meses: ATLAS renumera |
| AIUC-1 | Dominio del estándar: **A** datos y privacidad, **B** seguridad, **C** seguridad de las personas, **D** fiabilidad, **E** responsabilidad, **F** sociedad. El mapeo es a dominio, no a control concreto |
| Evidencia | Sección de `HALLAZGOS.md` (§) o documento que lo mide |
| Estado | **Medido** (hay cifra y ejecución), **Por construcción** (el diseño lo impide y hay test), **Parcial**, **Hueco** |

## 2. El registro

| ID | Riesgo | Cuadrante | OWASP | ATLAS | AIUC-1 | Evidencia | Control | Estado y medida |
|---|---|---|---|---|---|---|---|---|
| R-01 | Inyección de instrucciones y jailbreak por la consulta del usuario | CC | 1 | AML.T0051.000, AML.T0054 | B | §20, §33 | Prompt endurecido con reglas medidas; control estructural detrás del prompt, para que una inyección que pase el prompt no pase el permiso | **Medido.** `fuga_literal` 8/10 base frente a 10/10 endurecido. Residual: `inj-04` va a `otro` y no llega al control (defecto de enrutado, §20) |
| R-02 | Divulgación de información confidencial a un usuario sin permiso | CC | 6 | AML.T0057 | A | §2, §5, §8, §9, §11, §22, §41 | Permiso **dentro del `where`** de la búsqueda y redacción de campos al salir de la herramienta, **antes del recorte**, y retención de lo que no se puede redactar; el modelo nunca ve lo que no puede decir | **Medido.** Cobertura del riesgo 0,636 (A) y 1,0 (C); `fuga_literal` 10/10; una fuga real (§5) medida y corregida; un agujero por tamaño (§41) encontrado en el servicio desplegado y cerrado con prueba |
| R-03 | Fuga entre inquilinos | CC | 6 | AML.T0057 | A | `tests/test_tenant.py`, §13 | Colección de Chroma por inquilino, no filtro por metadato; el id va en el nombre de la colección | **Por construcción.** Test que abre la colección del inquilino y no otra; §13 midió que dos fuentes del mismo inquilino compartían espacio de nombres |
| R-04 | Exfiltración de credenciales por un agente hijo (puente) | DC | 7 | AML.T0053, AML.T0055, AML.T0057 | B | §19 | `--restricted`, sin `Write`, lista de denegación sobre `.env` y `.git/config` | **Medido.** Sin la lista leía el `.env` entero (31 líneas con claves); con ella lo deniega y lo dice. Descubierto probando, no diseñando |
| R-05 | Alucinación: citas a documentos que no existen | CC | 9 | — | D | §23, §40 | Verificador determinista de citas, aplicable al pasado a coste cero | **Medido.** 588 de 588 citas resolubles en 22 ejecuciones, cero inventadas. El residual de la rama estructurada (no decía de qué herramienta salía cada dato) se cerró con el corte del 23-09: `cita_alguna_fuente` 0,83 → 0,96 en la agencia |
| R-06 | Sobre-dependencia del juez LLM como instrumento de medida | DC | 9 | — | D | §26, §30, §32, §33 | Ninguna decisión cuelga de una métrica de juez; el veredicto lo anclan métricas deterministas | **Medido.** 4 de 24 veredictos espurios, todos suspendiendo lo que debía aprobar; `casos_ok` con juez es un suelo; `temperature=0` descartado en silencio por el SDK |
| R-07 | Cambio de comportamiento del proveedor sin aviso (API, modelos retirados, parámetros ignorados) | CD | 5 | AML.T0010 | D | §26, §28, §29, §35 | Tabla de precios viva con test que recalcula desde tokens; conmutación de proveedor verificada de extremo a extremo; modelos con fecha en el identificador; el AIBOM lista cada modelo con su precio o sin él | **Medido, tres instancias.** `gemini-2.5-flash` retirado para proyectos nuevos; `claude-sonnet-5` descarta `temperature`; `gemini-embedding-001` en retirada (cierre anunciado el 14-05-2028) sin precio publicado y sin contabilizar. Cuarta instancia el 26-09: la conmutación a Gemini existe pero la cuota gratuita de la clave (20 peticiones al día) no sostiene un banco, 73 de 82 casos en 429 (§54); no es plan de contingencia sin clave de pago |
| R-08 | Coste descontrolado y denegación de servicio económica | CC | 4 | AML.T0034, AML.T0029 | E | §16, §17, §21, `DESPLIEGUE.md` | Prepago con recarga automática desactivada en los dos proveedores (tope duro); coste por consulta en el registro de producción; clave propia para el juez; tope blando `TOPE_GASTO_USD` en la interfaz, sobre el registro | **Medido.** Tope 12,66 USD; evaluar cuesta x11 funcionar; una pasada completa con juez 2,53 USD. Residual: el tope blando es un suelo (excluye embeddings y lo gastado fuera de la interfaz) y no hay límite por usuario ni por minuto. La puerta HTTP de Render aguanta 20 clientes a la vez sin degradarse y el pipeline 8 consultas en vuelo sin subir la latencia por consulta (§53), así que la denegación de servicio plausible es económica, no de capacidad |
| R-09 | Cadena de suministro: dependencias, modelos y servidores ajenos | CD | 5 | AML.T0010 | B | `AIBOM.md`, §35 | AIBOM generado desde `uv.lock`, `config.py`, `provider.py` y los manifiestos, con test que falla si difiere; servidores MCP como procesos aparte | **Por construcción, y ya rindió.** 12 paquetes directos y 142 transitivos fijados (10 y 119 al generarse; el grupo de la interfaz y el de LangGraph entraron después); al generarse destapó que el modelo de embeddings está en retirada y sin coste contabilizado (§35). Residual: la versión de Node del puente no está fijada, y el inventario lo dice |
| R-10 | Envenenamiento del corpus o del índice | CC | 3 | AML.T0070, AML.T0020 | B | `scripts/`, §10, §14 | Corpus sintético generado con semilla fija; firma del índice sobre corpus, política y esquema | **Por construcción, no medido como ataque.** Un cliente real trae su corpus y esta mitigación desaparece: hay que decirlo |
| R-11 | Índice obsoleto que responde vacío en vez de fallar | DC | — | — | D | §10, §14 | La firma del índice cubre corpus, política y esquema; un índice que no coincide se reconstruye | **Medido.** Costó una ejecución entera descubrir que la firma no cubría el corpus; el segundo eje (§14) apareció donde el arreglo del primero no llegaba |
| R-12 | Denegación presentada como ausencia ("no he encontrado documentación") | CC | 9 | — | D | §22, §47 | El camino mixto avisa al modelo de lo retenido; el documental, cuando el permiso vacía la recuperación, responde un mensaje determinista que dice que existe, a qué rol está restringido y a quién pedirlo | **Medido.** Cinco casos de la gestoría pasaban de "no he encontrado" a la denegación explícita sin filtrar nada (28/28 en `fuga_literal`); el heredado no tenía ningún caso vacío por permiso, así que no se movió. Residual decidido: con contexto parcial y algo retenido, el documental no avisa (14 casos del heredado; sería otro corte de línea base) |
| R-13 | Sesgo por género, edad, origen o discapacidad en recuperación, enrutado o generación | DC | — | — | F | §34, §44 | Banco de pares emparejados con control y suelo de ruido en las tres capas; en generación, cinco medidas deterministas sin juez con repeticiones; treinta y tres pruebas que comprueban el emparejamiento | **Medido en las tres capas.** Ningún eje alcanza el doble de su suelo en recuperación, enrutado ni generación; una hipótesis salida de los datos (matiz por origen, 2,00x con N=8) se midió aparte y cayó a 1,00x con N=24. Residual: dos de las cinco medidas de generación están saturadas, así que solo prueban que no hay negativa selectiva ni omisión; y sigue sin ser "no discrimina" |
| R-14 | Agencia excesiva: el sistema actúa sin supervisión humana | CC | 8 | — | C | §42, `reports/agencia_hitl_v3` | Las escrituras se declaran en el manifiesto y el servidor las anota; el cliente MCP no arranca si discrepan. El modelo nunca ejecuta una escritura: la propone, y una persona la aprueba o rechaza desde la interfaz, con registro de quién y cuándo. Métrica `accion_sin_aprobar` en todos los casos del banco | **Medido.** 40 de 40 casos sin escritura ejecutada; los 2 que piden escribir quedan propuestos y no ejecutados; `visitas_registradas.jsonl` no existe tras el banco. Residual: aprobar puede exigir un rol y hoy no lo exige en la agencia |
| R-15 | Encadenamiento de agentes sin persona en medio (Claude Code y la app) | CD | 8 | — | C | `SINCRONIZACION_SUPERFICIES.md` §7.6 | La cadena termina en Claude Code: el análisis automático es de solo lectura, la app no puede escribir en el buzón, y volver a encargar pasa por Juan | **Por construcción.** Cuatro encargos reales el 23-09 sin que ningún aviso generase un encargo |
| R-16 | Vigilancia: el registro de observabilidad guarda quién preguntó qué | CC | — | — | A | §20, §37, `RETENCION.md` | Política escrita (90 días, respuesta no guardada); supresión por usuario y purga por antigüedad, las dos con lápida que dice cuánto se quitó sin decir a quién; el resumen cuenta los borrados | **Medido.** Supresión y purga en un log de 10.000 líneas en décimas de segundo (§37). Residual: la purga es manual; la tensión con el artículo 12 se escribe, no se resuelve |
| R-17 | Derechos RGPD sobre el índice: borrado, oposición, actualización | CC | — | — | A | §36, `reports/borrado_*` | `scripts/borrar_documento.py`: retira el documento, reconstruye el índice y comprueba contra la colección que no queda ningún fragmento suyo; `--restaurar` mide la rectificación | **Medido.** Borrado efectivo en **1,46 s** (agencia) y **1,23 s** (heredado), cero fragmentos residuales y el resto intacto. Residual: es reconstrucción completa, crece con el corpus; las consultas registradas que citaron el documento no se borran (R-16) |
| R-18 | Transferencia internacional en cada llamada al proveedor | CC | — | — | A | `provider.py` | Corpus y datos sintéticos: hoy no viaja ningún dato real | **Hueco documental.** En producción exige base jurídica (cláusulas tipo o decisión de adecuación) y un DPA con el proveedor; no está escrito |
| R-19 | Enrutado inestable o erróneo que salta el control | CC | 6 | — | D | §1, §9, §12, §15, §27 | Temperatura 0 en el enrutador; grupos de solapamiento declarativos; taxonomía por inquilino | **Medido.** 3 casos inestables de 38 pasan a 0; cobertura del riesgo 0,778 a 1,0 con el solapamiento. Residual: 1 de 53 sigue variando; `inj-04` |
| R-20 | Salida insegura: la respuesta se ejecuta en algún sitio | CC | 2 | — | B | `agent.py` | La salida es texto para una persona; no alimenta ningún intérprete ni acción | **Por construcción.** Volverá a evaluarse si un canal (correo, WhatsApp) reenvía la salida |
| R-21 | Contenido inapropiado sin moderación | DC | — | — | C | `MODULO_4.md` | Categoría `otro` con prompt sin fuente para lo fuera de ámbito | **Hueco justificado.** Es el único guardarraíl de los nueve que falta; en un asistente interno sobre documentación propia el vector es la consulta, no el corpus, y R-01 lo cubre en parte. Justificar por qué no está vale tanto como ponerlo |
| R-22 | Robo del modelo | — | 10 | — | — | — | — | **No aplica.** No hay modelo propio |
| R-23 | Incidente sin plan: lo que no sabemos que no sabemos | DD | — | — | E | `INCIDENTES.md`, §19, §21, §28, §29 | Botón rojo en orden (revocar, parar, congelar evidencia, rotar); quién avisa a quién; todo incidente termina en un hallazgo; `scripts/simulacro_incidente.py` lo pulsa en frío | **Medido.** Simulacro del 23-09 (§46): fallo legible y registrado en 4,8 s, evidencia congelada con manifiesto en 1,65 s, vuelta en 8,47 s; la primera pulsación destapó que las consultas fallidas no dejaban rastro en el registro, y se corrigió. Residual: la mitad manual (revocar y rotar en las consolas) no está cronometrada y se decidió el 24-09 no hacerlo antes de la defensa, sin incidente que lo pida; sigue sin haber canal de aviso de usuarios |

## 3. Vista por cuadrante de Rumsfeld

| Cuadrante | Contramedida que pide el 4.4 | Filas | Lo que el proyecto pone |
|---|---|---|---|
| Conocidos-conocidos | Pruebas y métricas | R-01, R-02, R-03, R-05, R-08, R-10, R-12, R-14, R-16, R-17, R-18, R-19, R-20 | Los bancos, 122 casos en tres inquilinos, las métricas deterministas, la contabilidad de coste |
| Conocidos-desconocidos | Vigilar métricas, despliegue continuo | R-07, R-09, R-15 | Precios vivos con test, conmutación verificada, AIBOM generado y vigilado por test (R-09) |
| Desconocidos-conocidos | Evaluar vulnerabilidades activamente | R-04, R-06, R-11, R-13, R-21 | Los hallazgos que salieron de **mirar con desconfianza**: cuatro de ellos tenían el error en el instrumento, no en el sistema |
| Desconocidos-desconocidos | Botón rojo y plan | R-23 | El tope de gasto, el plan escrito y **pulsado en frío** (§46) |

## 4. Clasificación por el AI Act: en el manifiesto, no aquí

El análisis está en `MODULO_4.md`, sección del artículo 6, con las citas
literales y el calendario vigente tras el Reglamento (UE) 2026/1744. La
conclusión es que **el mismo sistema cae en casillas distintas según el
inquilino**, y por eso la clasificación se declara en `tenants/<id>.json`,
bloque `ai_act`, y la valida `src/tenant.py` al cargar:

- `puntos_anexo_iii`: qué puntos del anexo III toca el corpus o los datos del
  inquilino. Vacío si ninguno.
- `excepcion_art_6_3`: si se alega que, aun tocando el anexo III, el sistema no
  es de alto riesgo. Exige la condición del apartado 3 (a, b, c o d), la
  justificación, los **usos excluidos** que la sostienen y la declaración de
  que **no perfila personas**, porque el último párrafo del 6.3 dice que el
  perfilado siempre es alto riesgo. El validador rechaza una excepción con
  perfilado, y rechaza tocar el anexo III sin excepción ni clasificación de
  alto riesgo.
- `aviso_usuario`: el texto con el que se cumple el artículo 50.1. Lo imprime
  `src/main.py` delante de cada respuesta.

Lo que el validador impone es el apartado 4 del artículo 6: quien alegue la
excepción *"documentará su evaluación"*. Aquí la documentación es el manifiesto
y la evaluación es un `ValueError` si falta.

| Inquilino | Anexo III | Clasificación declarada | Por qué |
|---|---|---|---|
| `empresa_servicios` | Punto 4 (empleo y gestión de trabajadores): el corpus tiene salarios y evaluaciones individuales | Transparencia del artículo 50, con excepción 6.3(a) | Consulta documental de procedimiento; el anexo confidencial se retiene por permiso; los usos de evaluación de personas están excluidos y escritos |
| `agencia_inmobiliaria` | Punto 5(b) (solvencia de personas físicas): los expedientes traen ingresos y solvencia acreditada | Transparencia del artículo 50, con excepción 6.3(a) | El sistema reproduce lo que consta en el expediente, no evalúa la solvencia ni decide la admisión; los ingresos se redactan salvo a dirección |

Y la consecuencia del calendario: en octubre de 2026 el artículo 50 obliga y el
capítulo III de alto riesgo no (2 de diciembre de 2027). La clasificación se
defiende como diseño anticipado, y la excepción 6.3 como la documentación que
el apartado 4 exigirá entonces.

## 5. Los huecos, por orden de lo que cuesta cerrarlos

1. ~~**R-09, AIBOM**~~ **Hecho** el 23-09: `AIBOM.md` generado y vigilado por
   test. Destapó el §35 al generarse.
2. ~~**R-23, plan de incidentes**~~ **Escrito y simulado** el 23-09:
   `INCIDENTES.md` y `scripts/simulacro_incidente.py`; 14,95 s el botón rojo
   completo, y un agujero del registro cerrado por el camino (§46).
3. **R-07 y §35, el modelo de embeddings**: el coste **ya se contabiliza**
   (§37: exacto en la ingesta, estimado en la consulta) y sigue sin precio
   publicado. La migración a `gemini-embedding-2` queda **decidida en contra
   antes de la defensa** (23-09): invalidaría el índice y movería las
   métricas de recuperación; se documenta como pendiente con fecha límite
   14-05-2028.
4. ~~**R-17, borrado cronometrado**~~ **Medido** el 23-09: 1,46 s y 1,23 s, con
   comprobación contra la colección (§36).
5. ~~**R-16, retención del registro de observabilidad**~~ **Hecho y medido**
   el 23-09: `RETENCION.md`, supresión y purga con lápida (§37).
6. ~~**R-14, human-in-the-loop**~~ **Hecho y medido** el 23-09: escritura
   declarada, propuesta y aprobada por una persona; 40 de 40 sin escritura sin
   aprobar (§42).
7. ~~**R-13, sesgo en generación**~~ **Medido** el 23-09: criterio de
   equivalencia sin juez (cinco medidas deterministas, repeticiones y suelo
   por control), nulo en los cuatro ejes; la hipótesis que salió de mirar los
   datos se midió aparte y no se sostuvo (§44). Residual declarado: dos
   medidas saturadas.

## 6. Mantenimiento

Cada hallazgo nuevo de `HALLAZGOS.md` que hable de un riesgo entra aquí como
evidencia de una fila existente o como fila nueva. `tests/test_riesgos.py`
falla si una fila cita un `§` que no existe o si alguna casilla del OWASP se
queda sin fila: es lo que impide que el registro se quede viejo sin que nadie
lo note.
