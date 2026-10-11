# Módulo 5 — el enunciado del TFM, cómo se evalúa, y qué le falta a la memoria

> Análisis del Módulo 5 del máster («Proyecto final»), liberado en el campus
> en la semana del 6 de octubre y leído el 11-10-2026. Es el módulo que trae
> el enunciado y los criterios de evaluación que la tutoría del 22-09
> (`TUTORIA_2026-09-22.md`) anunció para «2-3 semanas». Recorrido por la app
> de Claude con Juan delante (encargo E-0018) y procesado aquí: el texto de
> las páginas, las diapositivas de la sesión y la grabación de la tutoría del
> 6 de octubre, transcrita entera en local.

## Dónde está el material, y por qué no está aquí

Por lo mismo que el del Módulo 4 (`MODULO_4.md`): es obra de un profesor y
este repositorio es público. Vive en
`Master/TFM/Documentación/Modulo5_campus/`, fuera de git:

| Fichero | Qué es |
|---|---|
| `Modulo5_campus.md` | Inventario de los 20 elementos de la sección y texto literal de cada página, incluido el enunciado (tarea `assign` 62999) |
| `Repaso y gestión de proyectos.pptx` / `.pdf` | Diapositivas de la sesión del 6-10 (34), exportadas de Google Slides |
| `Tutoria_2026-10-06_vimeo_1233612760_es-autogen.vtt` | Subtítulos automáticos de Vimeo, 1.594 entradas |
| `Tutoria_2026-10-06_transcripcion.txt` | Los mismos subtítulos agrupados por minuto (la app) |
| `Tutoria_2026-10-06_whisper.*` | Transcripción propia con `scripts/transcribir_material.py` (Whisper `large-v3-turbo` en CPU), para contrastar los pasajes de fechas y criterios |

La grabación dura 1 h 59 min. De ella interesan los primeros 5 minutos
(calendario y entrega) y el tramo 1:07-1:26 (qué se evalúa); el resto es
repaso del estado del sector, turno de preguntas y certificaciones.

## Lo que cambia: no hay defensa, hay entregas con feedback

**Ni el campus ni la tutoría mencionan una defensa oral, un tribunal ni una
demo en vivo.** La palabra no aparece en las páginas ni en la grabación. La
«defensa a finales de octubre» de este repositorio venía de la tutoría del
22-09, donde la pregunta era por la fecha y la respuesta fue el mes; el
formato nunca se confirmó (`TUTORIA_2026-09-22.md`, pregunta 8). Lo que hay:

- **El entregable es un documento.** El enunciado pide un «Documento
  explicativo (PDF preferiblemente)» y, si se llega más lejos, referencias
  al repositorio, a un flujo de n8n o a cualquier artefacto que evidencie el
  trabajo. El tutor, en la grabación (1:12): «en esencia es un documento de
  vuestras decisiones. Ese es el entregable mínimo».
- **Plazo: el 31 de octubre**, que es el cierre de actas, aceptado «hasta
  última hora». El tutor pide **idealmente el 27**, día de la sesión de
  cierre, para tener margen de ver la evaluación. Las tutorías se pueden
  pedir hasta el 31. La tarea del campus no muestra fecha.
- **Se puede entregar varias veces.** Cada entrega recibe feedback y
  **cuenta la mejor**. Esto cambia la estrategia: entregar pronto no es
  arriesgar, es comprar una ronda de corrección.
- **El máster se alargó una semana**: el cierre pasa del 20 al 27 de
  octubre. Las sesiones que quedan son la de un exalumno (13-10), la de una
  consultora boutique (20-10) y la de cierre (27-10).

El hueco `[PENDIENTE]` de la memoria (capítulo 10.2) se cierra así: no hay
formato de defensa que esperar. **Confirmado por Juan el 11-10: no habrá
presentación.** El documento y el repositorio son todo lo que se evalúa.

## Cómo se evalúa

Los criterios están en el propio enunciado (no hay rúbrica de Moodle), en
tres tramos:

| Nota | Condición, resumida del enunciado y de la grabación (1:24) |
|---|---|
| 5-7 | El documento refleja los conceptos clave de los cuatro módulos; la nota depende de la calidad de la solución y del detalle de la explicación |
| 7-9 | El proyecto está implementado y cumple criterios aunque no esté completo ni desplegado entero |
| 9-10 | Cumple con claridad todos los criterios **y puede consumirlo un tercero sin generar carga de mantenimiento**: monitorización, gestión del código y automatización de los pases a producción. En la grabación añade: mejoras futuras identificadas, rendimiento en producción vigilado con **LLM como juez sobre muestras aleatorias de las conversaciones reales**, y controles suficientemente fuertes |

**El mecanismo importa tanto como los criterios.** El tutor lo describe
(0:02-0:03) como una rúbrica que se aplica «como si hubierais desarrollado
una skill»: un agente docente recorre el trabajo módulo a módulo y marca
qué está. Si eso es literal, el documento lo lee primero un modelo con una
lista de comprobación por módulo, y lo que no esté donde la lista lo busca
puede no contar aunque esté en otro capítulo. Y lo que no se puntúa: «no os
vamos a evaluar por cómo de bonito sea el proyecto», sino por si están las
decisiones y su porqué («si me ponéis Opus 5.5, la pregunta lógica sería por
qué»).

## Lo que pide cada módulo, contra lo que ya tiene la memoria

Resumen del enunciado y de las diapositivas 30-33, con dónde lo cubre
`MEMORIA.md` hoy:

| Módulo | Qué pide | Dónde está | Estado |
|---|---|---|---|
| 1 | Qué modelos y por qué (alineación con el propósito) | 3.3 | Cubierto, con cifras (§48, §57) |
| 1 | Configuración, forma de consumo, parámetros y prompts, incluidos los prompts de sistema candidatos | 2.4, 2.8, 4.4 | Cubierto; los prompts candidatos son el base y el endurecido (§31, §33) |
| 1 | Costes anticipados según niveles de uso | 5.4 | Cubierto: ficha por consultas al mes y por tipo de inquilino |
| 2 | Flujo de acciones, niveles de autonomía e intervención humana | 2.1, 2.6, HITL (§42) | Cubierto |
| 2 | Por qué el framework, controles intermedios | 3.1, 3.2, 2.7 | Cubierto y medido (§50) |
| 2 | **Si se usaron copilotos, cómo se integraron las instrucciones y la cadena de desarrollo** | Dos menciones (líneas 140 y 984) | **Hueco**: el enunciado lo pide expresamente y la memoria lo despacha en dos frases |
| 2 | Cómo un proceso de negocio se aterriza en proceso técnico | 1.1, 1.4 | Cubierto |
| 3 | Despliegue | 6.3, 2.9 | Cubierto: web, WhatsApp y correo, con autenticación |
| 3 | Cómo se evalúa ahora: tests y LLM como juez, o algún evaluador no subjetivo | 4 | Cubierto de sobra: banco, juez evaluado, métricas deterministas |
| 3 | **Cómo se sabe cómo va en producción** | 6.1 | **Parcial**: el registro da coste, latencia, enrutado y errores por consulta, pero nada evalúa la calidad de las respuestas reales. El tutor pide juez sobre muestras aleatorias |
| 3 | Plan B si cae el proveedor o la máquina (grabación, 1:15) | 3.3 (conmutación medida) | **Parcial**: la conmutación a Gemini es manual; el fallo se registra y se ve, pero el usuario no recibe una salida alternativa |
| 4 | Controles de seguridad implementados y análisis de riesgos | 7, `RIESGOS.md` | Cubierto: 24 riesgos, OWASP, ATLAS |
| 4 | **Agente o framework de red-teaming** para garantizar unos mínimos | 7.2 (banco con casos de inyección) | **Hueco**: no se usó ninguna herramienta de red-teaming; ya salió en la entrega 4.3 |
| 4 | Regulación aplicable (AI Act, RGPD) | 7.4, 7.5 | Cubierto |
| 4 | Permisos, autenticación y autorización | 2.7, 6.3 | Cubierto y medido |
| 4 | **Anonimización y enmascarado de datos en los prompts** | — | **Hueco**: la redacción actúa sobre lo que devuelven las herramientas, no sobre lo que escribe el usuario; ya salió en la entrega 4.2 |
| 4 | Envenenamiento de datos | R-10 | Cubierto en el registro |
| 9-10 | Gestión del código y pases a producción automatizados | `ci.yml`, `render.yaml` | **Parcial**: la CI pasa ruff y pytest en cada push y Render despliega solo en cada push, pero el despliegue no espera a que la CI esté en verde |

## Huecos, por valor y por coste

Ordenados por lo que mueven de la nota frente a lo que cuestan antes del 27.
Ninguno toca la línea base: ni el enrutador, ni el generador, ni el banco.

1. **Un mapa de módulo a capítulo al principio de la memoria.** Una tabla de
   una página como la de arriba, con los cuatro módulos y la sección donde
   está cada cosa. Si quien corrige es un agente con una lista por módulo, es
   lo que más nota mueve por minuto invertido. Coste: documentación.
2. **Un capítulo corto sobre cómo se desarrolló con copilotos.** `CLAUDE.md`
   como especificación que manda sobre la conversación, las skills de sesión,
   los tests como puerta, las reglas (no relajar el banco, nada de fallbacks
   silenciosos) y el puente con la app de Claude. Ya existe todo; falta
   contarlo como metodología. **Decisión de Juan**: choca con la regla de no
   atribuir a Claude en los entregables, aunque lo que se pide no es autoría
   sino método, y la tutoría del 22-09 dijo que el uso de IA es libre.
3. **El despliegue espera a la CI.** Que Render despliegue cuando las
   comprobaciones de GitHub pasan, y no en cada push. Es el criterio literal
   del tramo 9-10 («automatización de los pases a producción»). Coste: una
   línea por servicio en `render.yaml`, a comprobar contra la documentación de
   Render, y un despliegue para verlo.
4. **Evaluación de la calidad en producción.** El registro no guarda la
   respuesta, a propósito (`RETENCION.md`), así que un juez sobre muestras
   reales choca con esa decisión. La alternativa que no la rompe es un
   **evaluador determinista en línea**: el verificador de citas del §23 se
   ejecuta sobre cada respuesta al servirla y se registra solo su resultado
   (citas inventadas sí/no, fuente citada sí/no). Es el «evaluador no
   subjetivo» que pide el módulo 3, en producción y sin guardar texto.
   Coste: código y pruebas, sin llamadas de pago.
5. **Red-teaming con una herramienta.** Una pasada de un framework de
   red-teaming contra el sistema local, con su informe en `reports/` y el
   resultado en el registro de riesgos. El enunciado lo nombra. Coste: horas
   y algo de API; elegir la herramienta es parte del trabajo.
6. **Salida alternativa cuando cae el proveedor.** Un mensaje determinista
   al usuario que dice que el servicio no está disponible y qué hacer, sin
   contradecir la regla de nada de fallbacks silenciosos: el fallo se sigue
   registrando, lo que cambia es que el usuario no se queda colgado.
7. **Enmascarado de datos personales en la consulta.** El de más coste y
   menos encaje: el sistema es interno, y quien pregunta está autenticado.
   Si entra, como análisis declarado en 9, no como código.

El capítulo 10.2 se reescribe en cualquier caso: sin defensa, la sección
pasa a ser cómo un tercero puede consumir y comprobar el sistema (la web con
credenciales, WhatsApp, el correo, y el guion de demostración como recorrido
reproducible), que es justo lo que mira el tramo 9-10.

## Calendario que sale de aquí

| Fecha | Qué |
|---|---|
| 13-10 | Sesión con un exalumno |
| Hacia el 20-10 | **Primera entrega**, para tener feedback a tiempo |
| 20-10 | Sesión de una consultora |
| 27-10 | Sesión de cierre. **Entrega ideal** según el tutor |
| 31-10 | Cierre de actas. Último día para entregar y para pedir tutoría |
| Tras el 31-10 | Revisar y apagar servicios (`CLAUDE.md` §8) |

## Lo demás del módulo

Las siete páginas P1-P7 recorren las fases de un proyecto sobre CRISP-DM
adaptado a LLM (entendimiento del negocio, datos, preparación del contexto,
modelado, evaluación y seguridad, despliegue continuo y monitorización).
No piden nada que el enunciado no pida; sirven para comprobar que la memoria
nombra cada fase. Dos referencias que coinciden con decisiones ya tomadas:
P7 nombra Langfuse y opik para observabilidad (el proyecto tiene registro
propio; la memoria aún no justifica en 6.1 por qué no una de esas, tarea A4
de `PLAN_ENTREGA.md`) y P6 nombra los análisis de seguridad en el
repositorio (Snyk); esto último entraría con el punto 3. El resto
(estrategia, transformar organizaciones, certificaciones, referencias) es
contenido de contexto sin efecto en la entrega.
