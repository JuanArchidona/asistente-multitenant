# Módulo 4 — qué aporta al TFM, y qué le falta al TFM

> Análisis del material del Módulo 4 del máster, leído el 22-09-2026. El tutor
> nombró la securización como requisito en la tutoría de ese día
> (`TUTORIA_2026-09-22.md`) y dijo que se puede avanzar sin esperar a que el
> módulo se libere. Esto es el mapa de por dónde.

## Dónde está el material, y por qué no está aquí

Los PDF viven en **`Master/Módulo 4/4.X/Documentación/`**, fuera de este
repositorio, siguiendo la convención que ya usa el resto del máster.

Estuvieron un rato en `docs/` y se sacaron por dos motivos, el primero de los
cuales no es discutible:

1. **Es material docente ajeno y este repositorio es público.** Commitearlo es
   redistribuir la obra de un profesor en un repositorio abierto que acompaña a
   una defensa. Citarlo es legítimo; publicarlo no.
2. **Son 38 MB de PDF** en un repositorio que por lo demás es texto, y git no
   olvida: entran en el historial para siempre aunque se borren después.

Además, la carpeta `4.1` que se pegó aquí era un **duplicado byte a byte** de la
que ya existía en `Master/Módulo 4/4.1/Documentación/` — 32 MB repetidos. Las de
4.2, 4.3 y 4.4 no existían en el máster y se han movido allí.

Hay una regla en `.gitignore` para que ningún PDF de `docs/` entre por descuido.

## Corrección: "securización" es más de lo que dije

En la tutoría concluí que securización significaba IA responsable y **no**
ciberseguridad, porque solo había mirado el apartado 4.1. Con los cuatro
apartados delante, eso era falso: **tres de los cuatro son ciberseguridad.**

| Apartado | Contenido | Naturaleza |
|---|---|---|
| **4.1** Reglamento y marco legal | Ética, principios, sesgos, regulación, DPO/AI Officer, Data Ethics Canvas | Ética y normativa |
| **4.2** Seguridad en los sistemas de IA | Autenticación, autorización, OAuth, RBAC, escalado de privilegios, CVE, gateways, herramientas maliciosas, poisoning, keyword stuffing, inyección de prompts | **Ciberseguridad** |
| **4.3** Guardrails y Red-teaming | OWASP Top 10 LLM, nueve tipos de guardarrail, sandboxing, red-teaming con LLM atacante, garak, MITRE ATLAS, DASF | **Ciberseguridad** |
| **4.4** Seguridad y gobierno para IA | AI Act art. 6, matriz de Rumsfeld, cadena de suministro, SBOM/AIBOM, derechos RGPD sobre el RAG, transferencias internacionales, atlas de riesgos, arquitectura de gobierno | **Gobierno y riesgo** |

## El mapa de aprovechamiento

### OWASP Top 10 para LLM (4.3)

Es el marco más directamente utilizable: da diez casillas y el proyecto puede
decir qué hay en cada una **con la ejecución que lo respalda**.

| # | Riesgo | Estado en el proyecto |
|---|---|---|
| 1 | Inyección de solicitudes (jailbreak) | **Medido.** Casos `inj-*` en los dos inquilinos; el prompt endurecido evita dos fugas que el base produce, 8/10 frente a 10/10 (§33) |
| 2 | Gestión de salida insegura | Parcial. La salida es texto y no se ejecuta en ningún sitio |
| 3 | Envenenamiento de datos | Mitigado por construcción: el corpus es sintético y se genera con semilla fija. No medido |
| 4 | Denegación de servicio | Parcial. Tope de gasto duro en los dos proveedores (§16) y reintentos con espera; no hay límite de peticiones |
| 5 | Cadena de suministro | **Hueco.** Hay `uv.lock` con dependencias fijadas, y nada más. El material trae el incidente de LiteLLM de marzo de 2026 y el concepto de **AIBOM** |
| 6 | Divulgación de información confidencial | **Lo más fuerte que tiene.** Permiso dentro del `where` de la búsqueda, redacción al salir de la herramienta, cobertura del riesgo medida, y una fuga real medida y corregida |
| 7 | Complementos no seguros | Parcial. Los servidores MCP son procesos aparte; la sesión hija del puente corre con `--restricted` y lista de denegación (§19), que es control de radio de impacto |
| 8 | Agencia excesiva | **Hueco.** Human-in-the-loop pendiente |
| 9 | Sobre-dependencia de LLM | **Medido, y es original.** Los §30, §32 y §33 son una demostración medida de sobre-dependencia **sobre el propio evaluador del proyecto**: el juez emite números que contradicen su razonamiento, y por eso ninguna decisión cuelga de él |
| 10 | Robo de modelos | No aplica: no hay modelo propio |

### Los nueve guardarrailes (4.3)

El material los enumera; el proyecto tiene **siete de los nueve**, y eso es una
afirmación citable:

| Guardarrail | En el proyecto |
|---|---|
| Contiene PII | Redacción al salir de la herramienta, por política declarativa |
| Sesgos | Medido en recuperación y enrutado (§34) |
| Alucinaciones | El verificador determinista de citas (§23): 588 de 588 citas resolubles, cero inventadas |
| Intención adversaria (jailbreak) | Casos `inj-*` y prompt endurecido |
| Off topic | La categoría `otro` y su prompt sin fuente |
| Inyección de prompt | Reglas del prompt endurecido, medidas |
| Filtro de palabras clave | `fuga_literal`, determinista y sin varianza |
| Edición | La redacción de campos sensibles |
| Moderación | **No hay** |

### La matriz de Rumsfeld (4.4)

Los cuatro cuadrantes con sus contramedidas, y el proyecto tiene material medido
en los cuatro. Este es probablemente **el mejor esqueleto para el capítulo**,
porque es el que convierte 34 hallazgos dispersos en una estructura.

| Cuadrante | Contramedida que pide el material | Lo que el proyecto pone |
|---|---|---|
| Conocidos-conocidos: alucinan, fallan las tools, sesgos, coste | Pruebas y mitigar las métricas | El banco de 91 casos, las métricas deterministas, la contabilidad de coste |
| Conocidos-desconocidos: **cambios de comportamiento del modelo (API)**, escalabilidad, coste | Vigilar métricas, despliegue continuo | **Dos instancias medidas**: `gemini-2.5-flash` retirado para proyectos nuevos (§29) y `claude-sonnet-5` dejando de aceptar `temperature` sin avisar (§26) |
| Desconocidos-conocidos: racista o inapropiado, exponer vulnerabilidades | Vigilar métricas de evaluación, evaluar vulnerabilidades activamente | El experimento de sesgo (§34) y la exfiltración que destapó la propia respuesta del puente (§19) |
| Desconocidos-desconocidos | Botón rojo, plan de mitigación | El tope de gasto prepago es un botón rojo de facto. **No hay plan de comunicación** |

### AI Act, artículo 6 (4.4)

El material pide clasificar el sistema por riesgo, y aquí hay un análisis que no
es trivial y que conviene que sea el núcleo del capítulo normativo:

> **El mismo sistema es de riesgo limitado o de alto riesgo según el inquilino,
> y el manifiesto es donde eso se declara.**

Un asistente interno de conocimiento sobre procedimientos y normativa cae en
la obligación de transparencia del **artículo 50.1**: *"los sistemas de IA
destinados a interactuar directamente con personas físicas se diseñen y
desarrollen de forma que las personas físicas de que se trate estén informadas
de que están interactuando con un sistema de IA"*. La etiqueta "riesgo
limitado" es doctrinal, no aparece en el artículo. Aplica desde el **2 de
agosto de 2026** (regla general del artículo 113), así que **ya está en
aplicación en la fecha de la defensa**. Pero el corpus del inquilino heredado
incluye **datos de plantilla con salarios individuales y evaluaciones de
desempeño**, y el **anexo III, punto 4** ("Empleo, gestión de los trabajadores
y acceso al autoempleo") sitúa en **alto riesgo** los sistemas destinados a
*"supervisar y evaluar el rendimiento y el comportamiento"* o a decidir sobre
promoción o rescisión. Si el asistente se usara para apoyar decisiones sobre
personas, cambia de categoría. La vía de salida es el **artículo 6.3**: no es
de alto riesgo un sistema del anexo III que *"no plantee un riesgo importante
de causar un perjuicio a la salud, la seguridad o los derechos fundamentales"*,
por ejemplo por hacer una *"tarea de procedimiento limitada"*, y quien lo
alegue *"documentará su evaluación"* (apartado 4). Esa documentación es
exactamente el manifiesto del inquilino.

**El calendario cambió el 27 de julio de 2026, y hay que citarlo con el texto
vigente.** El Reglamento (UE) 2026/1744, de 8 de julio de 2026 (el "Ómnibus
digital sobre IA", DO L de 24 de julio de 2026), reescribió el artículo 113:
las obligaciones de los sistemas de alto riesgo del anexo III pasan del 2 de
agosto de 2026 al **2 de diciembre de 2027**, y las de los sistemas integrados
en productos del anexo I al 2 de agosto de 2028. Para la clasificación por
inquilino eso significa que, en octubre de 2026, el artículo 50 obliga y el
capítulo III de alto riesgo todavía no; la clasificación se defiende como
diseño anticipado, no como cumplimiento exigible. Fuentes: texto original en
EUR-Lex (`eur-lex.europa.eu/eli/reg/2024/1689/oj`), consolidado a 27-07-2026
(`CELEX:02024R1689-20260727`, que "no surte efecto jurídico" y remite al DO),
Ómnibus en EUR-Lex (`OJ:L_202601744`) y en el BOE (`DOUE-L-2026-81147`), y
la página de la Comisión sobre el marco regulatorio de la IA, que confirma las
dos fechas nuevas. Las citas literales las trajo la app de Claude el
23-09-2026 leyendo EUR-Lex (encargo E-0004 del puente); la existencia del
Ómnibus y las fechas se contrastaron desde Claude Code contra la Comisión y el
BOE, porque EUR-Lex no se deja leer desde un proceso sin navegador.

Que eso se pueda decidir **por inquilino** y quede escrito en
`tenants/<id>.json` es un argumento de arquitectura que sale directamente de una
decisión ya cerrada por otro motivo.

### Derechos del RGPD sobre el RAG (4.4)

El material lo dice sin rodeos: un RAG almacena datos que pueden referirse a
individuos, así que aplican el **derecho a borrado, a oposición y a
actualización**. Y las trazas requieren **gestión de datos y minimización de
accesos**.

**Hueco, y con una salida que el proyecto ya tiene a medias.** No hay mecanismo
de borrado, pero la firma del índice hace el camino tratable: se borra el
documento, la firma cambia, el índice se reconstruye. Eso es **medible** —
cuánto tarda un borrado efectivo— y encaja con el alta cronometrada del bloque 4.

Y el registro de observabilidad (§20), que guarda **quién preguntó qué**, es a la
vez la evidencia de trazabilidad que pide el artículo 12 y un riesgo de
vigilancia del catálogo del 4.1. Esa tensión conviene escribirla, no resolverla
a favor de lo cómodo.

### Transferencias internacionales, RGPD capítulo 5 (4.4)

Cada llamada al proveedor transfiere información. El material lo ilustra con un
diagrama de flujos UE → EE. UU. → China.

Aquí el proyecto tiene la mitigación **tomada y documentada desde el principio**:
ningún dato personal real entra en el sistema, los dos inquilinos son sintéticos
y el repositorio es público precisamente porque no hay nada que proteger. Lo que
falta es **decirlo como lo que es**: una medida de cumplimiento del capítulo 5, no
una comodidad de desarrollo.

## Lo que el material valida de lo ya hecho

No todo son huecos. Cuatro decisiones del proyecto aparecen en el material como
la práctica recomendada, y eso se puede citar:

- **"Las herramientas (y servidores MCP) son el punto clave en la autorización
  de acciones"** (4.2). Es literalmente la decisión cerrada de usar servidores
  MCP y no herramientas cableadas, y la de poner el control de acceso antes del
  modelo.
- **Gateways con políticas de acceso, guardarrailes y human-in-the-loop** (4.2)
  es la capa de gobernanza del proyecto, menos el HITL.
- **El estudio de Bloomberg sobre discriminación en contratación** (4.2), que
  varía nombres por raza y género sobre currículums idénticos, es **el mismo
  diseño de pares emparejados** del §34. Coincidencia útil: el experimento no se
  inventó mirando el material, y valida el método.
- **"Evaluate agents: LLM judges, Tracing"** (4.3 y 4.4). El proyecto lo hace y
  además va un paso más allá: **evalúa al juez**, que es lo que el §30 al §33
  documentan.

## Los huecos, por orden de lo que aporta cerrarlos

1. ~~**Registro estructurado de riesgos con la matriz de Rumsfeld y el atlas de
   riesgos.**~~ **HECHO** el 23-09-2026: `docs/RIESGOS.md`, 23 filas con
   cuadrante, casilla OWASP, técnica ATLAS, dominio AIUC-1, evidencia y
   estado, y `tests/test_riesgos.py` que falla si una fila cita un hallazgo
   inexistente o una casilla del OWASP se queda sin fila.
2. ~~**Clasificación por el artículo 6, por inquilino.**~~ **HECHO** el
   23-09-2026: bloque `ai_act` en `tenants/<id>.json`, validado por
   `src/tenant.py` con la regla del 6.3 codificada (tocar el anexo III sin
   excepción documentada no valida; perfilar personas no admite excepción), y
   el aviso del artículo 50 impreso por `src/main.py` delante de cada
   respuesta. Los dos inquilinos tocan el anexo III (puntos 4 y 5b) y alegan la
   excepción 6.3(a) con sus usos excluidos por escrito.
3. **Red-teaming con herramienta.** Los casos de inyección del banco son
   curados a mano. `garak` o DeepTeam los generan, y el material los nombra. Es
   la diferencia entre "probé lo que se me ocurrió" y "probé una batería
   estándar".
4. **Human-in-the-loop.** Cierra OWASP #8 y la falta de supervisión humana del
   catálogo del 4.1, y ya estaba en el alcance.
5. **Derechos del RGPD sobre el índice**: el camino de borrado, cronometrado.
6. **Cadena de suministro**: un AIBOM y la constatación de que las dependencias
   están fijadas. Baratísimo y cierra OWASP #5.
7. **Moderación**, que es el único guardarrail de los nueve que falta y
   probablemente el menos pertinente en un asistente interno. Justificar por qué
   no está vale tanto como ponerlo.

## Lo que no hay que hacer

El material es una mina de herramientas —Guardrails OSS, LiteLLM, garak,
DeepTeam, E2B, AIBOM— y la tentación es integrarlas para demostrar amplitud.
**El capstone puntúa la justificación, no el número de herramientas.** De esa
lista, la que aporta evidencia que el proyecto no puede producir de otra forma
es el red-teaming automatizado; el resto se cita como alternativa evaluada y
descartada, con el motivo.
