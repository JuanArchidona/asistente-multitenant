# Próximos pasos — tras la corrección de la 3.3

> Documento de roadmap, no de trabajo pendiente. La 3.3 está cerrada y calificada
> con 10/10 (2026-08-10). Lo que sigue recoge el feedback del profesor más las
> carencias que se ven en el propio banco, ordenado por lo que desbloquea más
> trabajo posterior. Mismo criterio que en la 3.1: no se reimplementa la entrega,
> se aplica hacia delante.

## Bloque A — Separar el coste del sistema del coste de evaluarlo (prioridad 1)

Es la recomendación explícita de la corrección: **un token de API para el agente
durante las pruebas y otro para el juez**.

### A1. El hueco concreto

`src/provider.py` contabiliza tokens y calcula coste, pero **solo del sistema
bajo prueba**. El gasto del juez lo gestiona DeepEval por dentro y nunca se
captura, así que los informes dicen "0,0021 USD por consulta" y no dicen nada de
lo que cuesta la evaluación. En la ejecución de esta entrega el sistema costó
unos 0,25 USD y el total de la jornada rondó los 6: la diferencia, que es casi
todo, es juez y generación sintética, y está sin atribuir.

### A2. Qué hacer

1. `ANTHROPIC_API_KEY_JUEZ` en `Config`, con caída a `ANTHROPIC_API_KEY` si no
   está definida, para que nada se rompa. `Juez` y el constructor de sintéticos
   usan esa; el sistema bajo prueba sigue con la principal.
2. Capturar el consumo del juez. DeepEval expone el coste por métrica
   (`metric.evaluation_cost`); acumularlo en el mismo `Uso` y reportarlo aparte
   en `resumen.json` e `informe.md`: coste del sistema, coste de la evaluación y
   coste por caso de cada uno.
3. Con las dos claves separadas, el panel de facturación de Anthropic ya
   distingue ambas líneas sin trabajo extra.

### A3. Para qué sirve, más allá de la contabilidad

Lo que señala el profesor: con el coste por caso del sistema medido sobre el
banco se puede **estimar el incremento de coste de un despliegue nuevo** antes de
hacerlo. Hoy tenemos coste por consulta de un modelo concreto; lo que falta es
usarlo como base de proyección al cambiar de modelo o al crecer el corpus. El
barrido ya compara calidad entre configuraciones: añadirle la columna de coste lo
convierte en una comparación calidad/precio, que es la que se lleva a una
decisión de producción.

## Bloque B — Revisión de seguridad (prioridad 2)

> **Destino: la entrega del Módulo 4**, que trata precisamente de seguridad. La
> revisión que apunta la corrección y el enunciado del módulo son el mismo
> trabajo, así que se hace allí y no aquí. La entrega del 4.x arrancará **a
> partir de este repo**, no de la plantilla vacía: el sistema bajo prueba, el
> corpus con material sensible y el banco ya están montados, y una entrega de
> seguridad necesita exactamente eso para tener algo a lo que atacar. El banco
> además sirve de red: cualquier medida que se añada se puede comprobar contra
> los 109 casos para ver si rompe algo.

"Ahora ya solo nos queda darle una vuelta desde el punto de vista de la
seguridad". El banco trata confidencialidad e inyección como **dimensiones de
calidad**: mide si el sistema filtra datos o se deja secuestrar. Una revisión de
seguridad es otra cosa y cubre lo que el banco no mira:

- **Superficie expuesta.** La app de la 3.1 no tenía autenticación ninguna
  mientras estuvo pública: cualquiera con el enlace consumía la cuota de API. Sin
  tope de gasto ni límite por sesión.
- **Custodia de secretos.** Claves en `.env` y en el panel de Render; sin
  rotación, sin scopes, sin auditoría de quién las usa.
- **El corpus como vector.** El acta con la inyección demuestra que un documento
  del corpus puede llevar instrucciones. Si la carga de actas está abierta a
  usuarios, **cualquiera puede escribir en el prompt del sistema** subiendo un
  PDF. El transcriptor la ignoró en la prueba, pero eso es una observación, no
  un control.
- **Control de acceso al contenido.** El anexo confidencial vive en el mismo
  índice que el resto: la única barrera entre un empleado cualquiera y los
  salarios es el prompt. Lo correcto es que la recuperación filtre por permisos
  del usuario, no que el generador se autocensure.
- **Trazabilidad.** Sin registro de quién preguntó qué, un incidente de fuga no
  se puede investigar.

Un buen punto de partida es OWASP Top 10 para aplicaciones LLM, recorriéndolo
contra este sistema y anotando cuáles aplican.

## Bloque C — Deuda del propio banco

Detectada al ejecutarlo, documentada en `docs/VALORACION_MVP.md`:

1. **Métricas con umbral en el extremo del rango.** Confidencialidad tiene el
   umbral en 1,0 y cambia de veredicto en el 50 % de los casos entre dos pasadas
   idénticas. Arreglo: promediar varias pasadas, o usar `Rubric` de G-Eval para
   fijar la escala, o quedarse con la comprobación literal como criterio.
2. **Validar el juez contra criterio humano.** Anotar a mano 20-30 casos y medir
   el acuerdo. Sin eso, la calidad del juez es una suposición razonable.
3. **Juez de familia distinta.** Ya soportado (`JUDGE_PROVIDER=gemini`); hoy no
   se usa por la cuota gratuita de Gemini (20 generaciones al día).
4. **Evaluación multivuelta.** El banco es de un turno, y la confidencialidad es
   bastante más difícil de sostener en conversación.
5. **Defectos menores del banco**: reescribir `front-03` (pregunta ambigua) y los
   literales de fecha del set sintético (`31/7` no casa con "31 de julio").

## Aplicable al TFM

- `evals/` es reutilizable tal cual salvo el golden set.
- Separar la ejecución del sistema de la evaluación desde el principio: permite
  reevaluar sin volver a pagar las llamadas, y ahí se ahorró una ejecución
  entera cuando hubo que arreglar el juez a mitad.
- Anclar el veredicto en métricas deterministas. El juez ayuda a leer, no a
  decidir.
- Dos claves de API desde el primer día, una para el sistema y otra para
  evaluarlo (bloque A).
- No relajar el banco después de ver los resultados.
