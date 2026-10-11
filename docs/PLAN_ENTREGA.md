# Plan hasta la entrega del TFM

> Escrito el 11-10-2026, con el enunciado ya leído (`MODULO_5.md`) y tres
> inventarios del material de los módulos 1, 2 y 3 contrastados contra el
> repositorio; el del Módulo 4 ya estaba hecho (`MODULO_4.md`). **No hay
> presentación** (Juan, 11-10): lo que se evalúa es el documento y el
> repositorio. Se puede entregar varias veces y cuenta la mejor, así que el
> plan tiene **dos entregas**: una hacia el **20-10** para recibir feedback y la
> definitiva el **27-10**, con el 31-10 como colchón.

## Reglas que el plan no cambia

- **La línea base no se toca.** Ni el prompt del enrutador, ni el generador,
  ni el banco de 122 casos. Todo lo nuevo entra como brazo alternativo detrás
  de un conmutador apagado por defecto, como registro, o como análisis.
- **Todo se mide o no entra.** Cada tarea lleva su medida de terminado. Un
  resultado nulo medido vale; una afirmación sin número no.
- **El capstone puntúa la justificación, no el número de herramientas**
  (`MODULO_4.md`). Una materia que no compensa implementar se cierra con un
  análisis que diga por qué, con números, y eso cuenta como cubierta.
- Los recuentos de la memoria se rehacen con el comando al final de cada
  bloque, no a mano.

## Bloque A — El documento (imprescindible antes de la primera entrega)

| # | Tarea | Módulo | Horas | Terminado cuando |
|---|---|---|---|---|
| A1 | **Mapa de módulo a capítulo** al principio de la memoria: cada cosa que pide el enunciado, con la sección donde está | 1-4 | 1 | Cada fila de la tabla de `MODULO_5.md` apunta a una sección que existe |
| A2 | **Capítulo de método: cómo se desarrolló con un copiloto.** Ver la sección "El capítulo del copiloto" | 2 | 4 | Cada afirmación sobre el reparto del trabajo cita bitácora, hallazgo, test o commit |
| A3 | **10.2 reescrito sin defensa**: cómo un tercero consume y comprueba el sistema (web con credenciales, WhatsApp, correo, guion como recorrido reproducible) | 3 | 1 | El `[PENDIENTE]` desaparece |
| A4 | **Correcciones que han salido hoy**: la frase de 1.3 que atribuye al autor "sin intermediario" las expectativas de los 122 casos (el §43 la desmiente para la gestoría); el párrafo de 6.1 que justifica el registro propio frente a Langfuse/opik (no existe); las métricas del recuperador (hit, recall, MRR) en la tabla de 4.2, que se calculan y no se publican; una frase en 3.4 sobre el afinado y el seguimiento de experimentos | 2, 3 | 2 | Cada una con su cifra y su fuente |
| A5 | **Modelo abierto frente a API, con números**: punto de equilibrio API frente a modelo autoalojado a 500, 2.000 y 10.000 consultas al mes, ampliando la ficha de 5.4; y **afinar o no**: no hay datos de entrenamiento fuera del banco y los fallos vigentes son de enrutado y de cita, no de generación | 1 | 3 | Tabla en 3.3/5.4 con fuentes de precio fechadas |
| A6 | **Exclusiones razonadas** en 8.3 y 9: multiagente y A2A (por qué un *workflow* y no un equipo, con el coste estimado de un paso de planificación sacado de las trazas), DSPy (optimizaría contra el banco, que no tiene conjunto reservado), caché de prompts (comprobar el mínimo cacheable de Haiku 4.5 frente a los ~973 tokens de entrada), entornos de preproducción, KPI de negocio de un piloto, moderación | 1-4 | 3 | Cada exclusión con su número |
| A7 | **Maquetación**: regenerar el PDF, arreglar el script del anexo B (confunde `ALCANCE.md §5` con hallazgos y no ve los capítulos `## N.`), recontar páginas, hallazgos y tests con el comando | — | 2 | El PDF sale del script sin tocarlo a mano |

## Bloque B — Lo que pide el tramo 9-10 (consumible por terceros sin carga de mantenimiento)

| # | Tarea | Módulo | Horas | Terminado cuando |
|---|---|---|---|---|
| B1 | **El despliegue espera a la CI**: `autoDeployTrigger: checksPass` en los tres servicios de `render.yaml` (comprobar el campo contra la especificación del blueprint de Render) | 3 | 1-2 | Un push con un test roto no despliega y uno en verde sí, con los dos eventos de Render como evidencia |
| B2 | **Escaneo de dependencias en la CI** (`pip-audit`), lo que P6 del Módulo 5 llama verificaciones de seguridad en el repositorio | 2, 4 | 1 | La CI publica el número de vulnerabilidades y falla si hay alguna conocida sin excepción escrita |
| B3 | **PromptOps**: `docs/PROMPTS.md` generado como el AIBOM (cada prompt con modelo, temperatura, `max_tokens`, hash y la evidencia que lo respalda), y el hash del prompt y el commit desplegado (`RENDER_GIT_COMMIT`) en cada línea del registro y en cada `resumen.json` | 1, 3 | 5 | Test que falla si el catálogo difiere; 100 % de las líneas selladas; `observabilidad_cli` agrupa por versión |
| B4 | **Evaluación de la calidad en producción, sin guardar la respuesta**: el verificador de citas del §23 sobre el 100 % de las respuestas al servirlas y el juez de Gemini sobre una fracción aleatoria en segundo plano; al registro solo van números | 3 | 6-10 | Tasa de citas inventadas en producción, fracción muestreada y coste por consulta evaluada (~0,00076 USD), medidos sobre tráfico real de la web |
| B5 | **Salida alternativa cuando cae el proveedor**: mensaje determinista al usuario y fallo registrado, sin contradecir la regla de nada de fallbacks silenciosos | 3 | 3 | Un fallo simulado del proveedor da el mensaje en web, WhatsApp y correo, y queda en el registro con su tipo |
| B6 | **Registro persistente y coste acumulado.** Hoy vive en disco efímero y se pierde en cada despertar; es lo que la 3.1 y la 3.3 dejaron pendiente del feedback docente. Llevarlo a un almacén externo | 3 | 4-6 | N registros antes y después de un redespliegue; coste por día y por inquilino desde `observabilidad_cli` |
| B7 | **Alertas** por correo con el SMTP del canal de correo cuando salta el tope blando | 3 | 2 | Tiempo hasta el aviso medido en un simulacro |
| B8 | **Deriva**: periodo de referencia (banco) frente a periodo de análisis (registro) en tasa de `otro`, confianza, contexto vacío y latencia p95 | 3 | 3-4 | Validado inyectando tráfico desplazado y comprobando que salta |

## Bloque C — Materias del máster que faltan, como experimentos medidos

Ninguno cambia la configuración por defecto.

| # | Tarea | Módulo | Horas | Coste API | Terminado cuando |
|---|---|---|---|---|---|
| C1 | **Red-teaming con una herramienta** (garak, DeepTeam o promptfoo; elegir con criterio y escribirlo) contra el sistema local en los dos inquilinos con datos sensibles | 4 | 4-6 | ~0,5-1 USD | Informe en `reports/`, tasa de éxito por categoría de ataque, filas nuevas o evidencia en `RIESGOS.md` |
| C2 | **Recuperación híbrida**: BM25 propio (sin dependencias) con fusión RRF, fuera de línea al estilo de `evals/sweep.py` | 2 | 4-6 | ~0 | hit, recall, precision@k y MRR por inquilino frente a la densa; en la agencia hay margen (precision@k 0,5), en los otros dos probablemente un nulo |
| C3 | **Memoria entre turnos**: primero medir el defecto con un banco de seguimiento aparte (~10 conversaciones, "¿y para dirección?"); después, si compensa, reescritura de la consulta detrás de un conmutador. La interfaz ya pinta un historial que el sistema no usa | 2 | 2 + 6-8 | ~0,2 USD | Enrutado y recuperación del segundo turno, sin memoria y con ella |
| C4 | **Modelo abierto autoalojado como enrutador**: un modelo pequeño cuantizado en CPU local (16 núcleos) con el mismo prompt, como brazo de `evals.comparar_enrutadores` | 1 | 6 | 0 | Acierto, cobertura del riesgo, latencia y coste frente a Haiku (0,882) y embeddings (0,735) |
| C5 | **Clasificador entrenado con datos sintéticos** sacados de los manifiestos, nunca del banco (el afinado ligero del Módulo 1) | 1 | 6-8 | ~0 | Acierto en los 121 casos frente a 0,735 y 0,882, con los datos de entrenamiento separados del banco y comprobados por test |
| C6 | **Escala de colecciones de Chroma**: 50 y 200 inquilinos sintéticos, disco y latencia p50 | 2 | 3-4 | ~0 | Tabla en 8.2; responde lo que 9 admite no haber medido |
| C7 | **Enmascarado de datos personales en la consulta** | 4 | 2 (análisis) | 0 | Análisis en 9 de por qué no encaja en un sistema interno con usuario autenticado, o implementación si el feedback lo pide |

## El capítulo del copiloto (A2)

El enunciado pide literalmente, en el Módulo 2, "si habéis usado copilotos,
de qué forma habéis integrado las instrucciones y la cadena de desarrollo
para tener cierto control sobre la salida". El capítulo se escribe sobre eso:
**método y control**, no autoría.

**Lo que el repositorio permite afirmar, y lo que no.** La memoria ya dice en
el resumen y en 1.3 que el código y la documentación se produjeron con un
asistente de código dirigido por el autor, y la bitácora y los hallazgos
están escritos en primera persona del asistente. El capítulo no puede decir
otra cosa: un corrector con el repositorio delante lo comprobaría en
minutos. Lo que sí puede, y debe, es enseñar con evidencia en qué consistió
dirigir:

1. **Las decisiones.** Hay más de veinte atribuidas expresamente a Juan en la
   bitácora, el alcance y los hallazgos: que el generador sepa el rol de quien
   pregunta (23-09), construir el correo cuando estaba fuera de alcance,
   el plan de pago de Render, los topes de Gemini, no rotar las claves, cerrar
   R-24 en simulación, hacer el alta de Meta por la app cuando el asistente
   recomendaba lo contrario, no habrá presentación.
2. **Las reglas que el asistente no puede saltarse, y qué las hace cumplir**:
   la línea base protegida por un test carácter a carácter, la independencia
   del juez por `Config`, `pii_leakage` vetada en la carga, las citas del
   registro de riesgos vigiladas por test, el AIBOM regenerado y comparado,
   la CI en cada push. Las que son solo texto (no relajar el banco, sin
   emoticonos) se dicen como tales.
3. **El sistema de control**: `CLAUDE.md` como especificación que gana a la
   conversación, las skills de arranque y cierre, el hook que inyecta los
   avisos, y el puente con la app con su regla de que un agente no se da
   encargos a sí mismo y la cadena termina en una persona.
4. **Los errores del asistente que el método cazó**, con fecha: 1 h 50 min
   que eran 19 min, la separación de claves que no existía, el precio de
   Sonnet un 50 % alto, tres afirmaciones falsas en el experimento de sesgo,
   un cierre ejecutado sin que se pidiera, 35 y 35 correcciones en dos
   lecturas hostiles, y dos frases falsas en la entrega del 4.3 que se
   enviaron sin arreglo. Es el argumento más fuerte del capítulo: el valor
   del autor está en el sistema que hace que esos errores se vean.
5. **Las cifras**: 120 commits del TFM entre el 20-09 y el 11-10, 13 sesiones
   de bitácora, 59 hallazgos, 1.183 tests.

## Calendario

| Fechas | Qué |
|---|---|
| 12-14 oct | A1-A4, B1, B2, B3 |
| 15-18 oct | B4, B5, C1, C2, A5, A6 |
| 19 oct | Recuentos con el comando, A7, lectura final |
| **20 oct** | **Primera entrega** |
| 20-25 oct | Lo que pida el feedback; luego B6-B8 y C3-C7 por este orden, hasta donde llegue |
| 26 oct | Recuentos, PDF, lectura final |
| **27 oct** | **Entrega definitiva** (el 31 queda de colchón) |
| Tras el 31 | Revisar y apagar servicios (`CLAUDE.md` §8) |

Horas: el bloque A suma unas 16, el B unas 30 y el C unas 40. Todo junto no
cabe en dos semanas con calidad; A y B1-B5 sí, y son los que el enunciado
nombra. C1 y C2 entran antes de la primera entrega porque cubren materias que
el enunciado o el programa nombran y son baratas. El resto, después del
feedback.

## Presupuesto (11-10)

- **Anthropic: 200 USD de crédito promocional de la suscripción Max, que
  caducan el 25-10-2026**, más 9,33 USD comprados. Lo que no se gaste antes del
  25 se pierde, así que los experimentos que más API consumen (C1, C3, pasadas
  completas con juez, repeticiones) van **antes del 25**, no después del
  feedback. Una pasada completa de los bancos con juez costaba 2,53 USD (§21):
  el crédito deja de ser la restricción; el tiempo sí lo es.
- **El crédito rompe el tope duro** (`CLAUDE.md` §8): tarea previa a todo lo
  demás, poner un límite de gasto en la consola para la clave de los servicios
  desplegados (tarea B0).
- **Gemini: 4,30 EUR de prepago.** Basta para el juez de producción (B4):
  ~0,00076 USD por evaluación, unas 5.000 evaluaciones. La suscripción Google
  AI Pro añade 10 USD al mes de crédito de Google Cloud si se activa en Google
  Developer Program y se asocia a la cuenta de facturación; con saldo de
  prepago positivo, el crédito apto se consume antes que el prepago.
- **El juez sigue siendo Gemini** aunque sobre crédito de Anthropic: la
  independencia de familia (§24, §32) es una decisión de línea base.

| # | Tarea | Horas | Terminado cuando |
|---|---|---|---|
| B0 | ~~**Límite de gasto** en un espacio de trabajo de la consola de Anthropic para la clave del despliegue, y otra clave en otro espacio para experimentos (es también lo que pedía el feedback de la 3.3: separar lo que cuesta el sistema de lo que cuesta medirlo) | 0,5 | **Hecho el 11-10 (E-0019)**: espacio `tfm-produccion`, 10 USD/mes, clave `tfm-despliegue` en los tres servicios~~. Falta una consulta real que lo confirme en el uso del espacio |

## Decisiones

1. ~~**B4 manda respuestas reales a Gemini** para que las juzgue.~~ **Decidido
   por Juan el 11-10: sí.** Es una transferencia nueva a otro encargado y
   entra en R-18 y en `RETENCION.md`.
2. ~~**B6 necesita un almacén externo**: Postgres gratuito de Render (caduca a
   los 30 días, que cubren la entrega), Neon (gratuito sin caducidad, cuenta
   nueva por la app) o seguir en disco efímero y declararlo.~~ **Render Postgres**, creado el 11-10 (E-0019): `asistente-registro`, Free, PostgreSQL 18, Frankfurt, `REGISTRO_DB_URL` en los tres servicios. **Caduca y se borra el 10-11-2026**, después del 31-10; el código que lo usa está por escribir.
3. **Orden del bloque C**: con el crédito caducando el 25, C1 y C3 suben antes
   de esa fecha. **Pendiente** de lo demás.
