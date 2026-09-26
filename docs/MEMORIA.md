---
title: "Asistente interno multi-tenant de conocimiento y datos para empresas de servicios profesionales"
subtitle: "Memoria técnica del Trabajo Fin de Máster — borrador 2"
author: "Juan Archidona Ahijado — Máster en IA Generativa Avanzada, The Bridge"
date: "26 de septiembre de 2026"
lang: es
---

> **Estado: borrador 2, revisado el 26-09-2026** tras dos lecturas hostiles
> de cifras (24-09: 35 correcciones; 26-09: 35 más, informe en
> `docs/REVISION_MEMORIA_2026-09-26.md`) y una lectura lineal de texto el
> mismo día (`docs/LECTURA_MEMORIA_2026-09-26.md`). Este bloque se quita
> al entregar. Estructura completa y
> cifras tomadas de `HALLAZGOS.md`, `ALCANCE.md` y `RIESGOS.md`; cada cifra
> lleva el hallazgo (§N) que la respalda y, cuando existe, la ejecución de
> `reports/`. Lo que está entre corchetes y en mayúsculas es un hueco que hay
> que cerrar antes de entregar. La rúbrica del TFM no se conoce todavía
> (llega con el Módulo 5, en torno al 6-13 de octubre); la estructura sigue
> las cinco características del proyecto que fija el programa del máster.

**Repositorio:** <https://github.com/JuanArchidona/asistente-multitenant>
**Servicio desplegado:** <https://asistente-multitenant.onrender.com>

## Resumen

Un asistente interno que responde consultas de los empleados de una empresa
de servicios profesionales combinando dos fuentes: la documentación propia
de la empresa, por recuperación aumentada (RAG), y sus datos de negocio,
por servidores MCP. El mismo código sirve a varios clientes (inquilinos)
sin tocar un fichero de Python: todo lo que distingue a uno vive en un
manifiesto declarativo. El control de acceso se aplica **antes** de que el
modelo vea nada, la única escritura la aprueba una persona, y cada decisión
que se defiende tiene una medida detrás; las que no la tienen lo dicen.

El proyecto parte de las entregas 2.1, 2.3, 3.1 y 3.3 del máster, que ya
cubrían cuatro de los seis pasos del flujo y traían un banco de evaluación
de 109 casos. Sobre esa base se construyeron, en cinco días de
construcción y dos de medidas de operación, siete piezas: la
multi-tenencia, la rama estructurada, la capa de control de acceso, la
observabilidad, la interfaz web autenticada y desplegada, el análisis de
IA responsable y un canal de WhatsApp. Todo el código y toda la
documentación se produjeron con un asistente de código dirigido por el
autor; el capítulo 1.3 dice qué es de quién y qué salvedad llevan las
cifras de tiempo.

Tres cifras que resumen lo que se defiende:

| Afirmación | Cifra | Dónde está medida |
|---|---|---|
| Dar de alta un cliente nuevo no exige código | **5 min 42 s**, cero ficheros `.py`, 25 de 28 casos de su banco en dos iteraciones; 27 de 28 tras revisar dos expectativas del banco | §43, §45 |
| El control de acceso está en la búsqueda, no en el prompt | Cobertura del riesgo **1,0** en la agencia; `fuga_literal` **10 de 10** en la línea base vigente; una fuga real encontrada y cerrada | §5, §8, §22, §40 |
| El evaluador también se evaluó | **4 de 24** veredictos del juez LLM eran falsos, y los cuatro en el mismo sentido; ninguna decisión del proyecto cuelga de él | §30, §32 |

## 1. Definición del problema y contexto de uso real

### 1.1 El problema

Una empresa de servicios profesionales (una gestoría, una agencia
inmobiliaria, una consultora) tiene su conocimiento repartido en dos
sitios que no se hablan: documentos (convenios, procedimientos, actas,
expedientes) y sistemas de datos (CRM, agenda, cartera). Un empleado que
pregunta "¿qué visitas tiene Iván el jueves?" necesita el CRM; uno que
pregunta "¿cuántos días de vacaciones me corresponden?" necesita el
convenio; y uno que pregunta "¿quiénes son las partes de la operación 118?"
necesita los dos, porque el dato vive en el expediente y en el CRM.

Un asistente que solo hace RAG responde lo que está escrito y se inventa
lo que no. Uno que solo llama herramientas no sabe de procedimientos. Y en
cualquiera de los dos, el problema que decide si se puede desplegar no es
la calidad de la respuesta sino **quién puede ver qué**: el convenio es
para todos, el anexo con los salarios es para dirección, y la solvencia de
un comprador es para quien lleva la operación.

El asistente tiene que servir a más de una empresa, porque una empresa de
servicios profesionales no paga un desarrollo a medida. Eso convierte el
aislamiento entre clientes en el primer requisito, y convierte "cuánto
cuesta dar de alta un cliente nuevo" en la cifra comercial que importa.

### 1.2 Punto de partida: lo heredado de las entregas del máster

El TFM no arranca de cero, y la decisión está razonada en `docs/ALCANCE.md`
§1: el criterio del capstone premia justificar con números, y justificar
con números es lo que produce el banco de evaluación de la entrega 3.3.
Partir de cero habría gastado el mes en reconstruir lo que ya estaba
medido. El tutor confirmó el 22-09-2026 que partir de entregas propias
calificadas es admisible y no exige declaración (`docs/TUTORIA_2026-09-22.md`).

| Paso del flujo | Estado al arrancar (20-09-2026) | Origen |
|---|---|---|
| Entrada (interfaz) | Streamlit desplegada en Render | 3.1 (10/10) |
| Clasificador | Hecho y medido: acierto, matriz de confusión, fallback | 2.3, 3.3 |
| Recuperación documental | Hecha y optimizada con un barrido de 11 configuraciones | 2.3, 3.3 |
| Recuperación estructurada | **No existía** | |
| Generación | Anclada al contexto, con cita de fuente | 2.3 |
| Guardarraíles | Parcial: el fallo estaba medido (2 fugas), no corregido | 3.3 |
| Salida | Un solo canal | 3.1 |
| Banco de evaluación | 109 casos, 13 métricas en 4 capas, CI (heredado tal cual en `evals/`) | 3.3 (10/10) |

Dos requisitos no funcionales del documento de concepto original ya
estaban cumplidos: latencia (3,8 s de media, 5,3 s p95, objetivo 3-8 s) y
coste (0,0021 USD por consulta, objetivo "céntimos"). Faltaban la PII y la
aprobación humana.

El repositorio conserva la historia de commits de la 3.3: lo anterior al
commit `docs: add TFM scope and closed decisions` es la entrega, no el TFM.

### 1.3 El criterio de evaluación, y el método que impone

El programa del máster define el Módulo 5 así: *"el objetivo del proyecto
no está únicamente en que el sistema funcione, sino en justificar cada
decisión técnica en términos de calidad, coste, escalabilidad, riesgo y
mantenimiento"*. De ahí sale la regla de trabajo de todo el proyecto:
**ante cualquier propuesta, la pregunta es si se puede medir; una
afirmación sin número no vale.**

Cinco reglas que se derivan y que el repositorio hace cumplir con tests:

- **No se relaja el banco.** Un caso se corrige cuando la expectativa era
  incorrecta, nunca cuando el resultado incomoda, y cada corrección se
  justifica por escrito en `HALLAZGOS.md` (§3, §45).
- **Nada de fallbacks silenciosos.** Si algo degrada (parseo fallido,
  recuperación vacía, servidor caído) se marca y se propaga. La confusión
  más cara es que "el CRM está caído" se lea como "no tengo esa
  información" (§46, §47).
- **La línea base heredada no se toca.** Un test compara el prompt del
  enrutador carácter a carácter con el de la 3.3; si cambia, las métricas
  de los 109 casos dejan de ser comparables.
- **Ninguna cifra sin su ejecución.** Cada número de esta memoria está en
  una carpeta de `reports/` o en un hallazgo que la cita.
- **Los cortes de línea base se fechan.** Cuando un valor por defecto cambia
  y las cifras de antes y de después dejan de ser comparables, queda
  escrito con fecha y con la escotilla que reproduce el comportamiento
  anterior. Hubo dos cortes, y el capítulo 4.4 los recoge.

**Cómo se trabajó, y cuánto es del autor.** El programa del máster
incorpora el uso profesional de la IA como herramienta de productividad, y
el tutor confirmó el 22-09-2026 que su uso en el TFM es libre. Este
proyecto lo usa sin reservas: el código, los tests, los documentos, la
búsqueda de las citas normativas del capítulo 7.4 y esta memoria se
escribieron con Claude Code, dirigido por el autor desde dos superficies
(capítulo 6.5). Lo que es del autor sin intermediario: las decisiones de
arquitectura y de línea base, las expectativas de los 122 casos del banco
y cada corrección de una expectativa, la aprobación de cada escritura, y
las decisiones que esta memoria fecha con nombre. El trabajo se cuenta en
sesiones, no en horas: cinco días de construcción y dos de medidas de
operación. Las cifras de tiempo de trabajo que la memoria da (5 min 42 s
el alta de un cliente, 19 min el prototipo de LangGraph) son tiempo del
asistente con el proyecto en contexto, y lo dicen donde aparecen. Un
tribunal que quiera saber qué habría costado a mano no encontrará aquí ese
número, porque no se midió.

**Cómo leer las cifras de esta memoria.** Siete convenciones que se usan
desde el Resumen:

- **§N** es un hallazgo de `docs/HALLAZGOS.md`: una medida con la
  ejecución que la respalda. **R-NN** es una fila del registro de riesgos
  (capítulo 7.1). `ALCANCE.md` §5.c y §5.d son secciones de ese fichero,
  siempre con el nombre delante.
- Una **ejecución** es una pasada del banco guardada en
  `reports/<etiqueta>/`; las etiquetas (`empresa_quien`, `agencia_hitl_v3`,
  `gestoria_agregacion_v2`) solo aparecen en las tablas de los capítulos
  4.2 y 5.4 y en el anexo. Fuera de ahí, "línea base vigente" es la
  ejecución de ese inquilino en esas tablas.
- Un **caso OK** es un caso del banco cuyas métricas pasan todas su
  umbral; las que no aplican al caso no penalizan y una traza en error
  falla siempre. "48 de 53" son casos OK sobre casos del banco.
- Las métricas son de **dos familias**: deterministas, que no varían
  entre pasadas y anclan todas las decisiones, y de juez LLM, que varían
  y de las que no cuelga ninguna (capítulo 4.1).
- La **cobertura del riesgo** es la fracción de casos con material
  protegido en juego que llegan de verdad al control de acceso; un caso
  que el enrutador manda a `otro` no prueba nada del control. Se publica
  con su denominador (capítulo 2.7).
- Un **corte de línea base** es un cambio de valor por defecto que hace
  no comparables las cifras de antes y de después; hubo dos, fechados en
  el capítulo 4.4, y "línea base vigente" quiere decir posterior a los
  dos.
- **"Por construcción"** quiere decir que el control existe por diseño y
  no se ha atacado ni medido. Se usa en el capítulo 7.2 y se dice cada
  vez.

### 1.4 Los tres inquilinos

Los tres son sintéticos: ningún dato real de ninguna empresa entra en el
repositorio, que es público. Lo que eso mitiga y lo que no está en el
capítulo 7.5.

| | `empresa_servicios` | `agencia_inmobiliaria` | `gestoria_laboral` |
|---|---|---|---|
| Qué es | Empresa de servicios heredada de las entregas | Domara Inmobiliaria, agencia ficticia de Zaragoza | Asesoría Marín y Lasheras, gestoría laboral y fiscal ficticia |
| Para qué está | Sostener el banco heredado como suite de regresión | Demostrar agnosticidad y la rama estructurada | Medir el alta de un cliente nuevo |
| Categorías | rrhh, desarrollo, actas, marca | cartera (estructurada), expedientes, procesos, normativa, comercial, actas | laboral, fiscal, clientes, procedimientos, actas |
| Corpus | 7 documentos | 10 documentos | 6 documentos |
| Banco | 53 casos | 40 casos | 29 casos |
| MCP | No | CRM propio, con una escritura aprobada por persona | No |
| Material de ataque | Anexo confidencial con salarios; acta con inyección de prompt | Expediente con DNI, ingresos y solvencia | Nóminas y datos de clientes |

La agencia se eligió por ser la más alejada estructuralmente del inquilino
heredado: allí los datos son mercado y operaciones, no políticas internas.
Un tercer inquilino de asesoría se descartó al principio para no dispersar
el esfuerzo y se construyó al final, cronometrado, como prueba de
agnosticidad (capítulo 8.1).

## 2. Diseño de la arquitectura

### 2.1 El flujo

```
entrada (interfaz, WhatsApp)
  → autenticación: la credencial fija el inquilino y los roles
  → clasificador: categoría y destino (documental | estructurado | ambos | otro)
  → recuperación
      documental:   búsqueda en la colección del inquilino, con el permiso dentro del where
      estructurada: llamada a herramientas de los servidores MCP del inquilino,
                    con redacción de campos al salir de la herramienta
  → generación anclada al contexto, que sabe quién pregunta
  → gobernanza de salida: verificación de citas, propuesta de escritura pendiente de aprobación
  → registro de producción: inquilino, usuario, categoría, coste, latencia, denegaciones
  → salida, con el aviso del artículo 50 del AI Act
```

Todo es Python sin framework de orquestación (capítulo 3.1). El código del
núcleo son unas 5.400 líneas en `src/`, `mcp_servers/` y `app.py`, con
1.124 tests que corren en menos de 20 segundos sin llamar a ningún
proveedor; son recuentos de `wc -l` y `pytest`, no hallazgos. Cuánto de
eso es nuevo y cuánto heredado se dice en el capítulo 1.2: la 3.3 traía el
clasificador, la recuperación, la generación y el banco; lo demás es de
este proyecto.

### 2.2 El inquilino como concepto de primera clase

Todo lo que distingue a un inquilino es declarativo y vive en
`tenants/<id>.json`: categorías con su descripción y su destino, grupos de
solapamiento, servidores MCP, escrituras que exigen aprobación, política
de acceso (documentos restringidos y campos sensibles, cada uno con el rol
que exige y el motivo) y clasificación por el AI Act. `src/tenant.py` lo
valida al cargar y falla si falta algo.

Fragmento del manifiesto de la agencia:

```json
{
  "id": "agencia_inmobiliaria",
  "categorias": [
    { "nombre": "cartera", "destino": "estructurado",
      "descripcion": "estado actual de un caso concreto: qué inmuebles hay publicados y a qué precio ..." },
    { "nombre": "expedientes", "fuente": "expedientes", "destino": "documental",
      "descripcion": "el expediente escrito de una operación concreta, citada por su número ..." }
  ],
  "solapamientos": [["expedientes", "cartera"]],
  "servidores_mcp": [{ "nombre": "crm", "comando": "python", "args": ["-m", "mcp_servers.agencia_crm"] }],
  "escrituras": ["crm__registrar_visita"],
  "politica": {
    "documentos_restringidos": [{ "archivo": "expediente_2026_118_confidencial.md", "requiere": "direccion" }],
    "campos_sensibles": [{ "campo": "ingresos_netos_mensuales_eur", "requiere": "direccion", "motivo": "Solvencia" }]
  },
  "ai_act": { "clasificacion": "transparencia_art_50", "puntos_anexo_iii": ["5b"],
              "excepcion_art_6_3": { "condicion": "a", "perfila_personas": false, "usos_excluidos": ["..."] } }
}
```

La consecuencia medible es el capítulo 8.1: si dar de alta un cliente
exige editar un `.py`, la costura está mal puesta. Se cronometró y no lo
exigió.

### 2.3 Aislamiento estructural

Cada inquilino tiene **su propia colección de Chroma**, con el
identificador en el nombre de la colección, en vez de un índice común
filtrado por metadato. Un filtro mal construido en una sola ruta de
consulta devuelve documentos de otro cliente sin que nada lo señale; una
colección distinta no puede. Hay un test que abre la colección del
inquilino y falla si abre otra (R-03). Lo que cuesta: una pasada de
embeddings por inquilino al indexar, entre 2.700 y 3.100 tokens en los
tres corpus (§37, §43), y ocho lectores concurrentes sobre una colección
no la frenan (0,25-0,31 s, §53). Lo que no se midió: cuántas colecciones
abiertas soporta un proceso ni cuánto ocupan en disco; el límite lo
declara el capítulo 9.

Dentro de un inquilino, dos fuentes distintas compartían espacio de
nombres de fragmentos (§13); se corrigió con el nombre de la fuente en el
identificador.

La firma del índice cubre corpus, política de acceso y esquema de
metadatos: un índice obsoleto no da error, devuelve vacío (§10), y costó
una ejecución entera descubrir que la firma no cubría el corpus (§14). Si
la firma no coincide, el índice se reconstruye.

### 2.4 El clasificador

Un prompt construido desde el manifiesto (contexto del enrutador,
categorías con sus descripciones) que devuelve categoría, destino y
confianza en JSON validado con Pydantic. Modelo por defecto:
`claude-haiku-4-5`, temperatura 0 desde el primer corte de línea base
(capítulo 4.4).

Tres decisiones medidas:

- **El enrutador es el primer cuello de botella de un cliente nuevo** (§1):
  la agencia arrancó con un acierto de 0,700 porque el corpus tenía
  expedientes con datos de clientes y ninguna categoría los nombraba; el
  enrutador no puede devolver lo que el prompt no describe. Añadir seis
  palabras a una descripción subió el acierto a 0,833 y los casos que pasan
  de 18/30 a 22/30. Tres iteraciones sobre las descripciones (§6) y una
  categoría nueva, `expedientes` (§12: de 29/38 a 33/38, cobertura del
  riesgo de 0,444 a 0,778), sin tocar el código.
- **La ambigüedad no se elige, se consulta** (§22). Cuando una consulta cae
  en un grupo de solapamiento declarado (`expedientes`/`cartera`), el
  sistema consulta las dos ramas en vez de pedirle al enrutador que
  resuelva una ambigüedad que no está en la pregunta. Cobertura del riesgo
  de 0,778 a **1,0** en la agencia. Precio: **+40 % de coste por caso y
  +0,5 s de latencia** en los casos del grupo, y crece con el tamaño del
  grupo, no con el número de grupos.
- **Temperatura 0 no es determinismo** (§15, §27). Con la configuración
  heredada, 4 de 38 casos cambiaban de categoría entre pasadas idénticas
  (§15), de ahí que el acierto se reporte con dispersión y que la
  temperatura pasara a 0. Medido con 910 llamadas y 0,57 USD (§27): 3
  casos inestables de 38 pasaron a 0 en la agencia y el acierto subió en los
  dos inquilinos, pero 1 de 53 sigue variando en el heredado y el generador
  sigue muestreando. La votación por autoconsistencia, estimada en 1,2 USD,
  quedó descartada por redundante. La memoria no promete reproducibilidad.

Un enrutador alternativo por embeddings, sin modelo de lenguaje, se
construyó y midió (capítulo 3.3): Haiku se queda.

### 2.5 La rama documental

Recuperación sobre la colección del inquilino, filtrada por fuente (la
categoría dice de qué fuente se lee) y **por permiso, dentro del `where`
de la búsqueda**. Los documentos restringidos de la política no se
recuperan para quien no tiene el rol: no es que el modelo no los cite, es
que no llegan a la ventana de contexto. El barrido de 11 configuraciones
de chunking, `top_k` y dimensiones del embedder viene de la 3.3 y no se
repitió: la configuración heredada es la línea base.

Cuando el permiso vacía la recuperación, el sistema responde un mensaje
determinista que dice que la documentación existe y a qué rol está
restringida (§47). Antes respondía "no he encontrado documentación", que
es la denegación presentada como ausencia (R-12): cinco casos de la
gestoría lo hacían y el heredado no tenía ninguno, por eso no se movió.

### 2.6 La rama estructurada por MCP

Los datos de negocio se consultan a través de **servidores MCP** que
declara el manifiesto, no de herramientas cableadas en el agente. El
cliente MCP (`src/mcp_cliente.py`) arranca cada servidor como proceso
aparte, descubre sus herramientas y las ofrece al modelo con tool-calling
nativo del SDK. El servidor de la agencia (`mcp_servers/agencia_crm.py`)
expone cinco herramientas sobre un CRM sintético generado con semilla fija.

Dos hallazgos que decidieron el diseño de esta rama:

- **La rama estructurada responde lo que ningún documento contiene** (§4):
  es el caso de uso que justifica que exista.
- **Y filtra todo, y el corpus no podía haberlo detectado** (§5): la
  primera versión devolvía DNI, teléfono e ingresos a cualquier usuario.
  Por eso la **redacción de campos sensibles se aplica al salir de la
  herramienta**, por política declarativa, antes de que el modelo lo vea.
- **Un control que depende del tamaño de la respuesta falla justo cuando
  hay más datos que proteger** (§41): el recorte a 6.000 caracteres iba
  antes de redactar y dejaba pasar JSON roto sin redactar; una respuesta de
  6.028 caracteres lo destapó en el servicio desplegado. Ahora la redacción
  va antes del recorte, y un resultado no estructurado con campos sensibles
  declarados se retiene y la traza lo dice.

### 2.7 Control de acceso antes del modelo

La decisión central del proyecto, y la que se defiende con más medidas:
**un prompt que dice "no reveles el DNI" deja el DNI en la ventana de
contexto**. El permiso va dentro del `where` de la búsqueda documental y
la redacción se aplica al salir de la herramienta estructurada. Lo que el
usuario no puede ver no llega al modelo.

| Mecanismo | Dónde actúa | Medida |
|---|---|---|
| Permiso en el `where` | Recuperación documental | Frente a la línea base heredada: 45/52 a 47/53 con fugas literales de 2 a 0 en el heredado, 27/36 a 29/38 y de 1 a 0 en la agencia, sin la caída de relevancia que costó endurecer el prompt en la 3.3 (§8). En la línea base vigente, `fuga_literal` 10 de 10 (§40) y cobertura del riesgo 0,636 en el heredado y 1,0 en la agencia (§11, §22). El detalle, en los capítulos 4.2 y 4.3 |
| Redacción de campos | Salida de cada herramienta MCP, antes del recorte | Línea base sin gobernanza: DNI, teléfono, correo e ingresos del comprador reproducidos (§5); tres de cuatro casos de confidencialidad de la agencia filtraban (§2). Después, 0. Agujero por tamaño cerrado (§41) |
| Denegación explícita | Camino documental vaciado por permiso | 5 casos de la gestoría; 6 de 6 casos con literal prohibido sin filtrar y 27 de 28 casos OK (§47) |
| El generador sabe quién pregunta | Prompt del generador, desde el segundo corte de línea base | De 2 de 5 a 5 de 5 al dar un dato autorizado a dirección (§39, §40; capítulo 2.8) |
| Escritura con aprobación humana | Herramientas declaradas como escritura | `accion_sin_aprobar` 40/40; ninguna visita escrita tras el banco (§42) |
| Verificación determinista de citas | Salida | 588 de 588 citas resolubles en 22 ejecuciones, cero inventadas (§23) |

La fuga real que citan el Resumen y las conclusiones es la de la rama
estructurada: la primera versión devolvía DNI, teléfono e ingresos a
cualquier usuario (§5), y su variante por tamaño (§41) apareció ya en el
servicio desplegado. Las dos fugas literales del heredado (§8) son la
línea base de la 3.3, medidas allí y cerradas aquí con el permiso en el
`where`.

**El modelo nunca escribe.** Una herramienta que escribe se declara en el
manifiesto (`escrituras`) y el servidor MCP la anota como no de solo
lectura; si discrepan, el cliente no arranca. El modelo la propone con sus
argumentos, una persona la aprueba o la rechaza desde la interfaz, y las
tres cosas quedan registradas (§42, OWASP LLM08).

La cobertura del riesgo (definida en el capítulo 1.3; §9, §11) es lo que
corrige la lectura optimista: de los 20 casos con material protegido en
juego, solo 11 llegaban al control (§11), así que "cero fugas sobre 17
casos" era en realidad "cero fugas sobre 9". Por eso la métrica publica su
denominador. El 0,636 del heredado son casos que no llegan al control
por fallo de enrutado, y subirlos es trabajo de enrutador, no de
gobernanza; uno de ellos, `inj-04`, se queda como residual documentado. Y
el tamaño de la muestra se dice: en el heredado la seguridad está medida
sobre los 7 casos que llegan al control, y en la agencia sobre 9. Son pocos,
y por eso cada uno está en la traza con su razón.

### 2.8 Generación anclada

El generador recibe el contexto ya filtrado, la política de respuesta
(base o endurecida; la vigente es la base, capítulo 4.3) y, desde el
segundo corte de línea base, **quién pregunta y que todo su contexto ya
pasó el control de acceso**. Antes no lo sabía y obedecía las
clasificaciones escritas dentro de los documentos: a dirección le negaba un
salario 3 veces de 5 aunque el control le hubiera entregado el anexo,
citando la cabecera "CONFIDENCIAL" del propio documento (§39). En esas
diez consultas el control estructural acertó el 100 % y el generador el
70 %: era un control de acceso que nadie le pidió, aplicado a ratos, y el
que sostenía la confidencialidad era el estructural. Después, 5 de 5, y
ninguna métrica de fuga se movió (§40). Con ese mismo corte la rama
estructurada pasó a citar la herramienta de la que sale cada dato; la
cifra y su inestabilidad entre pasadas están en el capítulo 4.2.

### 2.9 Interfaz y canales

- **Interfaz Streamlit** (`app.py`), desplegada en Render: usuario y
  contraseña, el inquilino lo fija la credencial, los roles van al control
  de acceso, aviso del artículo 50 al entrar, tope blando de gasto sobre el
  registro, tarjeta de acciones pendientes de aprobación.
- **WhatsApp** (`src/canal_whatsapp.py`, contra la API oficial de Meta): el
  número de teléfono es la credencial y fija el inquilino, aviso del
  artículo 50 en la primera conversación, aprobación humana por texto,
  firma del webhook obligatoria y el teléfono nunca entra en el registro.
  Está probado con 29 pruebas de mensajes simulados y **en vivo** con un
  número y dos preguntas (§51): la de vacaciones respondió como en la web
  y la del salario denegó sin el dato y sin fuga, en menos de un minuto
  cada una a precisión de minuto. Lo que no está medido: la latencia
  interna en producción (una sola consulta simulada, 5,1 s, sin traza), la
  aprobación por texto en vivo y el aislamiento con dos números reales,
  que se decidió no medir (capítulo 8.3). La puesta en marcha y sus
  tropiezos están en `docs/CANAL_WHATSAPP.md` y en el §51.
- **Correo** (`src/canal_correo.py`, sobre un buzón de Gmail dedicado): la
  dirección del remitente es la credencial, con la misma lista cerrada; y
  como un remitente de correo se puede falsificar, el canal exige que el
  servidor receptor haya verificado el origen (`Authentication-Results`
  con DKIM o SPF en `pass`, R-24), o rechaza el correo sin consultar. La
  aprobación va en la primera línea de la respuesta, la respuesta enhebra
  en la conversación y el sondeo del buzón es por IMAP con la librería
  estándar, sin paquetes nuevos. Probado con 34 pruebas de correos
  simulados y una consulta simulada contra el sistema real (5,26 s);
  pendiente de conectar al buzón, que se decidió crear (capítulo 8.3).
  Límite propio: en el plan gratuito de Render, dormido no sondea, y a
  diferencia de WhatsApp nada lo despierta (capítulo 9).

## 3. Selección y justificación de modelos, patrones y herramientas

Los cinco criterios del capstone se reparten por la memoria: la calidad
se mide en el capítulo 4, el coste en el 5, el riesgo en el 7, la
escalabilidad y el mantenimiento en el 8. Este capítulo justifica las
elecciones de patrón, de modelo y de herramienta, y remite a cada uno de
esos capítulos por la cifra.

### 3.1 Python sin framework frente a LangGraph

La orquestación es Python con tool-calling nativo del SDK del proveedor.
La comparación con LangGraph no se argumenta: **se midió** (§50). Se
construyó el mismo sistema encadenado por un grafo de LangGraph 1.2.12
(`src/orquestacion_langgraph.py`, activable con `ORQUESTADOR=langgraph`),
portando solo la orquestación: el enrutador, la recuperación con el
permiso en el `where`, el cliente MCP, la gobernanza y el generador son los
mismos métodos en los dos, y diez tests comprueban que con el mismo
proveedor falso los dos devuelven la misma traza y hacen las mismas
llamadas. Después se pasaron los dos bancos por el grafo, con predicción
escrita antes de instalar nada.

| | Python sin framework (línea base) | LangGraph |
|---|---|---|
| Heredado, 53 casos: casos OK | 48 | 47 |
| Heredado: `routing`, cobertura del riesgo | 0,9038 / 0,6364 | 0,9038 / 0,6364 |
| Heredado: latencia media por caso | 3,284 s | 3,295 s (+0,011 s) |
| Heredado: coste | 0,1051 USD | 0,1077 USD (+2,5 %, tokens de salida) |
| Agencia, 40 casos: casos OK, `routing`, escrituras sin aprobar | 31 / 0,825 / 0 de 40 | 31 / 0,825 / 0 de 40; trece casos por la rama mixta con herramientas MCP |
| Líneas de código de la orquestación | 21 | **95** (4,5 veces) |
| Paquetes nuevos en el lock | 0 | **14**, uno de ellos el cliente de la plataforma de observabilidad del proveedor del framework |
| Tests tocados | | 0 (10 nuevos) |
| Tiempo de reloj de construir y medir | | 19 min (el presupuesto de `ALCANCE.md` §4 era de 4 h), hechos por un asistente de código con el proyecto en contexto |

El caso que cambia en el heredado es el generador muestreando: mismas 106
llamadas y mismos 51.559 tokens de entrada en los dos.

Lo que la medida dice: para un flujo de un turno con una bifurcación, el
grafo reproduce exactamente las llamadas y no añade latencia medible, y a
cambio cuesta 4,5 veces más líneas de orquestación y 14 dependencias. De
ahí la lectura por los cinco criterios del capstone:

| Criterio | Python sin framework (elegido) | LangGraph |
|---|---|---|
| Calidad | Idéntica: mismos veredictos, mismas llamadas, mismos tokens de entrada (§50). La calidad la deciden prompts, control de acceso y banco, que son los mismos | Idéntica, medida |
| Coste | Cero dependencias de orquestación; ninguna capa entre el SDK y la contabilidad de tokens | +14 paquetes en el AIBOM (R-09); latencia y coste por consulta iguales |
| Escalabilidad | Lo que escala aquí es el número de inquilinos, y eso lo resuelve el manifiesto, no el orquestador | Igual: el manifiesto es ortogonal al framework |
| Riesgo | Superficie mínima: 21 líneas que se leen en una pantalla; el control de acceso está en el `where` y en la salida de la herramienta, no en el orquestador | Cadena de suministro: el material del Módulo 4 trae el incidente de LiteLLM de marzo de 2026; `langsmith` entra sin usarse |
| Mantenimiento | Todo cambio es visible en un diff de Python; la conmutación de proveedor se verificó de extremo a extremo (§29) sin adaptadores, con la salvedad de cuota del §54 | Cada versión del framework es un cambio de comportamiento que hay que volver a medir, y el proyecto ya midió tres cambios no anunciados de los proveedores en cinco días (capítulo 8.4) |
| Lo que se pierde | Persistencia de estado y reanudación entre pasos, visualización del grafo, paralelismo declarativo | Lo aporta, y este sistema no lo usa |

Lo que la medida no dice: nada sobre lo que LangGraph aporta cuando hay
estado entre turnos, interrupciones con reanudación o ramas paralelas,
porque este sistema no tiene nada de eso. Cuando el flujo tenga varios
turnos (capítulo 9), la comparación habrá que rehacerla, y la aprobación
humana del capítulo 2.7 sería el primer candidato.

### 3.2 Servidores MCP frente a herramientas cableadas

Un `tools=[...]` dentro del agente ata el sistema a la API de un cliente;
un servidor MCP lo convierte en contrato: el manifiesto dice qué servidor
arrancar, el servidor dice qué herramientas tiene y cuáles escriben, y el
cliente comprueba que las dos versiones coinciden. Dar de alta un cliente
con CRM propio es escribir su servidor, no tocar el agente.

Tres decisiones de ingeniería de la rama, con su medida (§7). Los
servidores se arrancan una vez, al construir el sistema (1,1 s), y se
mantienen abiertos: con 36 casos de banco, abrirlos por consulta habría
añadido unos 40 segundos y un proceso por pregunta. Las sesiones del SDK
se abren y se cierran en la misma tarea, porque repartirlas entre dos
revienta al salir. Y el prompt lleva la fecha del sistema, porque el
modelo no sabe qué día es.

Un MCP de terceros es además un riesgo de negocio: el de idealista existe
y está cerrado a clientes externos por política declarada (`ALCANCE.md`
§3), y por eso el sistema no depende de ninguno. Si un servidor MCP está
caído, la consulta falla y lo dice: la regla de nada de fallbacks
silenciosos (capítulo 1.3) está ahí precisamente para que "el CRM no
responde" no se lea como "no hay datos"; el simulacro del capítulo 6.4
mide el fallo del proveedor de modelos, no este, y el capítulo 9 lo
declara.

### 3.3 Modelos

| Función | Modelo | Por qué |
|---|---|---|
| Clasificador y generación | `claude-haiku-4-5` | Heredado de la 3.3 con su línea base medida; 0,00245 USD por caso sin juez en la ejecución del §17, y entre 0,0020 y 0,0041 por inquilino en las vigentes (capítulo 5.4) |
| Juez | `gemini-3.6-flash`, desde el primer corte de línea base | Otra familia que el generador y 5,5 veces más barato por evaluación que `claude-sonnet-5`; admite temperatura 0, aunque eso no lo estabiliza (§24, §26, §32) |
| Embeddings | `gemini-embedding-001`, 768 dimensiones | Heredado; en retirada con cierre anunciado el 14-05-2028 y sin precio publicado (§35). Decidido no migrar antes de la defensa: invalidaría el índice |
| Proveedor alternativo | `gemini-3.6-flash` para chat, vía `LLM_PROVIDER=gemini` | La conmutación era una forma y no un hecho hasta que se verificó de extremo a extremo (§29); con la clave gratuita no es contingencia (§54) |

**El clasificador pequeño, medido contra Haiku** (§48). Un enrutador por
embeddings de las descripciones de categoría, sin entrenamiento ni
dependencia nueva, conmutable con `ROUTER_KIND`, con umbral de `otro`
calibrado en el heredado y congelado antes de mirar a los otros
inquilinos:

| | Haiku | Embeddings |
|---|---|---|
| Acierto en transferencia (agencia y gestoría, 68 casos) | 0,882 | 0,735 |
| Latencia por consulta (heredado) | 1,12 s | 0,32 s |
| Coste de chat | Sí | Ninguno |
| Casos de riesgo que llegan al control | `inj-04` y varios `conf-*` van a `otro` | **13 de 13** |

Haiku se queda: doce puntos de acierto en categorías definidas por tipo de
documento (`actas`) y entre categorías vecinas pesan más que la velocidad.
Pero es la única configuración medida en la que `inj-04` llega al control,
y la línea de mejora que sale es dar ejemplos a las descripciones de los
inquilinos nuevos, no afinar un modelo; en el heredado eso sería tocar la
línea base (capítulo 1.3). La cascada (embeddings y Haiku solo en duda) iguala a
Haiku en muestra pero fuera manda al LLM el 75-88 % de las consultas.

Lo que no se comparó: el generador. `claude-haiku-4-5` genera porque la 3.3
lo heredó con su línea base, y su barrido de configuraciones comparó
recuperación (chunking, `top_k`, dimensiones), no modelos de generación. Un
modelo mayor de la misma familia costaría de 2 a 5 veces más por token
(capítulo 5.4) sin que ningún fallo vigente del banco sea de generación:
los catorce casos que fallan en el capítulo 4.2 son de enrutado o de cita.

La comparación con el generador de la otra familia se intentó con los dos
bancos documentales y murió de cuota: la clave de Gemini es del nivel
gratuito, 20 peticiones al día para `gemini-3.6-flash`, y 73 de los 82
casos terminaron en 429 tras cinco reintentos (§54). Los nueve que
llegaron a responder pasaron los nueve, y nueve casos de conocimiento no
son una comparativa. Queda bloqueada hasta que haya facturación en ese
proyecto (capítulo 8.3). La consecuencia para la justificación pesa más
que la cifra que falta: **la conmutación de proveedor no es un plan de
contingencia mientras la clave sea gratuita**; vale para una consulta
suelta y para el juez, que usa otra clave.

Un prerrutado determinista por identificador (OP-2026-118 va a
expedientes) se descartó con una cuenta de dos minutos (§25): los
identificadores viven donde el problema ya está resuelto, y la deriva
entre categorías vecinas es semántica, no de identificadores.

### 3.4 El resto de la pila

Cinco piezas heredadas del patrón del máster y una propia; ninguna con
alternativa medida, y por eso cada una dice qué se mediría si se cambiara:

- **`uv`** con `pyproject.toml`, `uv.lock` y `.python-version`; `ruff`.
  Mantenimiento y riesgo: el lock reproducible es la fuente del AIBOM
  (capítulo 7.6) y `--frozen` en Render garantiza que lo desplegado es lo
  inventariado. Heredado del patrón del máster; sin alternativa medida.
- **Pydantic** para toda salida estructurada del modelo. Calidad: una
  salida que no valida se marca y se propaga en vez de leerse como vacía,
  que es la regla de nada de fallbacks silenciosos aplicada al parseo.
- **ChromaDB** local persistente, una colección por inquilino. Coste:
  cero de infraestructura; riesgo: el aislamiento estructural del
  capítulo 2.3; límite: el índice vive en el disco del proceso, y en el
  plan gratuito de Render ese disco es efímero. Las dos primeras consultas
  reales del canal de WhatsApp dieron `NotFoundError` porque ese servidor
  no reconstruía el índice al arrancar, y se corrigió con una única
  función compartida por los tres puntos de entrada (§51). Un servicio
  vectorial gestionado se mediría en latencia y en precio por colección.
- **Streamlit** para la interfaz, **Render** para el despliegue
  (blueprint en `render.yaml`). Heredados de la 3.1 (10/10), coste cero
  en el plan gratuito, 1 min 32 s del blueprint al servicio vivo (§38); el
  precio es el despertar (§52) y que la interfaz no vale para un cliente
  (capítulo 9). Una API con FastAPI y un plan de pago se medirían en
  latencia de pared y en euros al mes (capítulo 5.4).
- **DeepEval** para las métricas de juez. Heredado de la 3.3; su defecto
  está medido, descarta `temperature=0` sin avisar en `claude-sonnet-5`
  (§26). Un G-Eval propio quitaría la dependencia y se descartó por tiempo.
- **Node sin dependencias** para el puente MCP con la app de Claude
  (capítulo 6.5). Riesgo: cero paquetes que inventariar en el único
  componente que lee el `.env` del autor (§19).

## 4. Evaluación

### 4.1 El banco

Tres bancos, uno por inquilino, sobre el mismo runner heredado de la 3.3:

| Banco | Casos | Dimensiones | Para qué |
|---|---|---|---|
| `empresa_servicios` | 53 | Las ocho de la 3.3 | Suite de regresión de la línea base |
| `agencia_inmobiliaria` | 40 | Las ocho más `accion` (dos casos, §42) | Medir lo nuevo: rama estructurada, solapamiento y escritura |
| `gestoria_laboral` | 29 | Las ocho | Medir el alta de un cliente |

Las métricas nuevas respecto a la 3.3 no son dimensiones: cobertura del
riesgo (§11), `accion_sin_aprobar` (§42) y la verificación determinista
de citas (§23) se calculan sobre las dimensiones que ya había.

Métricas en dos familias, y la distinción es la lección más cara de la 3.3
y de este proyecto:

- **Deterministas**: `routing`, `fuga_literal` (literales que no deben
  aparecer), `cobertura_riesgo`, `cita_alguna_fuente`, verificación de
  citas, `accion_sin_aprobar`. No varían entre pasadas. Anclan todos los
  veredictos del proyecto.
- **De juez LLM**: faithfulness, relevancia, confidencialidad. Varían
  entre pasadas idénticas (capítulo 4.3), cuestan 11 veces más que
  funcionar, y ninguna decisión cuelga de ellas.

La ejecución del sistema y la evaluación están separadas: las trazas se
guardan y se pueden reevaluar sin volver a pagar llamadas
(`--desde-trazas`). Eso permitió estrenar el verificador de citas sobre 22
ejecuciones del pasado (§23) y comprobar que un cambio del comparador no
movía ningún veredicto anterior (§47).

`pii_leakage` se retiró del banco (§30, §31): su escala se
invertía entre casos y penalizaba al sistema por nombrar a la persona
cuyos datos estaba protegiendo; una denegación correcta sacaba 0,00.
Afectaba a 17 casos, no a 6, porque era métrica por defecto de dos
dimensiones enteras.

### 4.2 Resultados en la línea base vigente

Ejecuciones sin juez, posteriores al segundo corte de línea base
(capítulo 4.4):

| Ejecución | Qué es | Casos OK | `routing` | Cobertura del riesgo | `cita_alguna_fuente` |
|---|---|---|---|---|---|
| `empresa_quien` | Banco heredado, 53 casos | 48 | 0,9038 | 0,6364 | 1,0 |
| `agencia_hitl_v3` | Agencia con los dos casos de escritura, 40 casos | 31 | 0,825 | 1,0 | 0,92 |
| `gestoria_agregacion_v2` | Gestoría tras el caso de agregación, 29 casos | 28 | 0,963 | 1,0 | 1,0 |

No hay un umbral de aceptación fijado de antemano. La regla es otra:
ninguna pasada baja respecto a la anterior sin que el motivo esté escrito,
y cada fila se lee contra su línea anterior, no contra un número.

**Heredado.** No se ha degradado con la multi-tenencia: 48 de 53, frente
a 49 con la línea anterior. Los cinco fallos son de enrutado y ninguno de
generación: `ooc-04`, el único de 53 que sigue variando a temperatura 0, y
cuatro casos de riesgo (`conf-02`, `conf-03`, `conf-05`, `inj-04`) que
Haiku manda a `otro` y no llegan al control; son exactamente el 0,636 de
cobertura del riesgo.

**Agencia.** 31 de 40 con los dos casos de escritura añadidos (§42) y
`accion_sin_aprobar` 40 de 40. La cita de la herramienta bajó de 0,96 en
la pasada anterior a 0,92, y el §42 avisa de que ese efecto no es estable
entre pasadas. Los nueve fallos: siete de enrutado entre categorías
vecinas (`procesos`, `normativa` y `comercial` entre sí; `cartera` a
`expedientes` en tres casos, que aun así llegan al control por el grupo
de solapamiento) y dos de cita en la rama estructurada, que responde
"según el CRM" sin nombrar la herramienta.

**Gestoría.** 28 de 29, montada en menos de seis minutos (capítulo 8.1),
tras corregir dos expectativas del banco (§45) y recuperar un caso de
agregación de dos documentos (§49). El fallo que queda es del sistema: su
`ooc-04`, que comparte identificador con el del heredado y no es el mismo
caso.

### 4.3 Evaluar al evaluador

El feedback de la 3.3 pedía evaluar también al juez y su estabilidad. Se
hizo, y el resultado cambia cómo se lee cualquier métrica de juez:

- **El juez muestrea aunque el código diga `temperature=0`** (§26):
  `claude-sonnet-5` no admite el parámetro y DeepEval lo descarta sin
  avisar. Explica la varianza medida en la 3.3.
- **El número contradice su propio razonamiento** (§30), en dos familias con
  el mismo prompt y las mismas trazas: Anthropic escribió *"mereciendo la
  puntuación máxima"* y emitió 0,1; Gemini, a temperatura 0, escribió
  *"cumple exactamente"* y emitió 0,1. No es la temperatura ni la familia:
  es pedir número y justificación en la misma respuesta.
- **La temperatura no le hace nada y sus errores van en un solo sentido**
  (§32, un piloto de 4 casos por 6 pasadas): de 24 veredictos, 4 son espurios y **los cuatro
  suspenden lo que debía aprobar**. Consecuencia: `casos_ok` de una pasada
  con juez es un suelo, y promediar pasadas empeora la cifra en vez de
  cancelar el error. La única corrección conocida es la mayoría de tres,
  y el proyecto no la automatiza (capítulo 8.3): cuando se pasa el juez,
  se pasa tres veces y se lee la mayoría con su razón, y las cifras
  vigentes del capítulo 4.2 no lo usan.
- **La comparación base/endurecido no la puede decidir el juez** (§33): 5 y
  6 casos de 10 cambian de veredicto entre tres pasadas idénticas. La decide
  `fuga_literal`: la política base filtra el salario individual de un
  empleado y un dato de salud citando el anexo confidencial, la endurecida
  no filtra ninguno de los dos; **8/10 frente a 10/10**. Eso se midió
  sobre trazas anteriores al control de acceso. La política vigente es la
  base: la endurecida costó relevancia en la 3.3 (§8), y con el permiso
  dentro del `where` la base ya no filtra nada en la línea base vigente
  (10 de 10, §40). El prompt dejó de ser el control.

Dos reglas salen de ahí y se aplican en toda la memoria: una puntuación de
juez no se lee sin su razón, y ninguna decisión del proyecto cuelga de una
métrica de juez.

Dos limitaciones que quedan. El juez de la 3.3 compartía familia con el
generador (`claude-sonnet-5` juzgando a `claude-haiku-4-5`); `Config`
impide que sean el mismo modelo, no la misma familia. Desde que se midió
(§24) la limitación viaja en cada `resumen.json` y en cada informe, y el
juez por defecto es de otra familia. Y el juez no se validó contra
anotación humana: se evaluó contra sí mismo, repitiendo pasadas, y contra
las métricas deterministas.

### 4.4 Cortes de línea base, con fecha

Dos veces cambió un valor por defecto y las cifras de antes y de después
dejaron de ser comparables. Quedan escritos porque es lo único que impide
citar dos cifras que miden configuraciones distintas.

| Corte | Qué cambió | Qué compra | Qué no compra | Escotilla |
|---|---|---|---|---|
| 22-09-2026 (`ALCANCE.md` §5.c) | Temperatura del enrutador a 0; juez por defecto a `gemini-3.6-flash` | 3 casos inestables de 38 pasan a 0; independencia de familia; juez 5,5 veces más barato | Determinismo (1 de 53 sigue variando); estabilidad del juez | `ROUTER_TEMPERATURE=defecto`, `JUDGE_PROVIDER=anthropic` |
| 23-09-2026 (`ALCANCE.md` §5.d) | El generador recibe quién pregunta y que su contexto está autorizado | 2 de 5 a 5 de 5 al dar un dato autorizado; la rama estructurada cita la herramienta | Nada frente a una fuga real: eso lo garantiza la búsqueda | `GEN_QUIEN_PREGUNTA=0` |

Se decidieron antes de conocer la rúbrica, y a propósito: una decisión
que invalida la comparación con las ejecuciones anteriores necesita tiempo
para volver a medir, y entre la rúbrica y la defensa no lo habrá.

### 4.5 Lo que el banco enseñó sobre el método

Seis veces el error estaba en el instrumento y no en el sistema, y las
seis se corrigieron por escrito antes de sacar conclusiones: dos defectos
del banco de la agencia (§3), la mitad de los casos de seguridad que no
probaban nada (§11), la métrica de PII invertida (§31), dos casos de la
gestoría (§45), un comparador que no ignoraba el énfasis de markdown (§47)
y un literal con el número en letra (§49). Una séptima apareció al final:
un caso de robustez aprobaba a un sistema que no había respondido (§54).
La regla es no relajar el banco tras ver los resultados; cada corrección
cita por qué la expectativa era incorrecta.

Y una regla de método que salió del propio proyecto: **una predicción
escrita antes de mirar convierte una cifra en una medida** (§21). La
corrección del precio del juez se hizo escribiendo tres resultados
posibles antes de abrir la consola del proveedor, y la consola marcó uno
de los tres. La otra regla, que una hipótesis que sale de los datos no se
confirma con los mismos datos, está donde se aprendió (capítulo 7.3).

## 5. Coste

### 5.1 Lo que cuesta funcionar y lo que cuesta medir

| Concepto | Cifra | Hallazgo |
|---|---|---|
| Consulta sin juez | 0,00245 USD | §17, corregido en §21 |
| Caso con juez | 0,0278 USD | §17, §21 |
| **Evaluar frente a funcionar** | **11 veces más** | §17 |
| Pasada completa de dos bancos con juez | 2,53 USD, el 20 % del crédito | §17 |
| Pasada completa sin juez | 0,25 USD los dos bancos | `ALCANCE.md` §5.d |
| Evaluación con juez Anthropic / Gemini | 0,00417 / 0,00076 USD, y son suelos (G-Eval de una llamada) | §32 |
| Pasada completa de los dos bancos con el juez nuevo | 0,73 USD (una de Anthropic) o 0,40 USD (tres de Gemini), como mínimo | §32 |
| Experimento de sesgo, las tres capas | 0,0046 USD (recuperación y enrutado) y 0,27 USD (generación, 336 respuestas) | §34, §44 |
| Solapamiento consultando dos ramas | +40 % por caso en el grupo, +0,5 s | §22 |
| Demo completa de la defensa | menos de 0,05 USD, estimación a partir del coste por consulta; no medida | `GUION_DEMO.md` |

Hay tres cifras de coste por consulta en esta memoria y miden cosas
distintas: 0,0021 USD (capítulo 1.2) es la del documento de concepto,
medida en la 3.1 sobre el sistema heredado; 0,00245 USD (§17) es la del
banco heredado el 21-09, antes de los dos cortes de línea base; y las de la
ficha del capítulo 5.4 (0,00198 a 0,00406 USD) son las de las ejecuciones
vigentes de cada inquilino. Al citar una, decir cuál. Los dos defectos que
la propia contabilidad tuvo están en el capítulo 8.4.

### 5.2 Tope de gasto y una clave por fin

- **Tope duro**: cuentas de prepago en los dos proveedores con recarga
  automática desactivada, 12,66 USD de crédito en Anthropic a fecha de la
  última medida (§16). Una fuga a pleno ritmo de un solo proceso, 115
  consultas por minuto con ocho en vuelo (§53), gasta 13,7 USD por hora y
  lo agotaría en 55 minutos. El riesgo que queda es el contrario: quedarse
  sin crédito en la defensa.
- **Tope blando**: `TOPE_GASTO_USD` en la interfaz, sobre el registro de
  producción. Es un suelo: excluye embeddings y lo gastado fuera de la
  interfaz, y no hay límite por usuario ni por minuto (R-08).
- **Una clave para el sistema y otra para el juez**, el feedback de la 3.3
  aplicado desde el scaffold: separa en facturación lo que cuesta el
  sistema de lo que cuesta evaluarlo. La clave del juez estaba en todas
  partes menos donde importaba (§18) y en el camino de Gemini usaba la de
  los embeddings (§24) hasta que se arregló.

### 5.3 Lo que la contabilidad no ve

`reports/` mide el banco, no el proyecto: la contabilidad propia no ve un
22 % del gasto de la clave (llamadas de desarrollo fuera del runner,
reintentos del SDK) (§16). Y los embeddings se cuentan pero no se
convierten a dólares porque el modelo ya no aparece en la página de
precios (§35, §37): exactos en la ingesta (2.724 y 3.027 tokens por
corpus), estimados en la consulta (14 tokens de media, a 4,20 caracteres
por token medidos sobre 91 consultas). Al citar un coste, la memoria dice
que excluye los embeddings.

### 5.4 La ficha comercial: qué cuesta un cliente nuevo

`ALCANCE.md` §5 fija como activos del TFM dos cifras comerciales: lo que
cuesta dar de alta un cliente y lo que cuesta atenderlo cada mes. La
primera está en el capítulo 8.1. La segunda sale de la contabilidad de
tokens de las ejecuciones
vigentes de cada inquilino, que es la mejor aproximación que hay al tráfico
real: cada banco es una mezcla de consultas cortas, largas, de una rama y
de las dos.

| Inquilino | Ejecución | Coste por consulta | Tokens de entrada por consulta | Latencia media / p95 |
|---|---|---|---|---|
| `empresa_servicios` (solo documental) | `empresa_quien` | 0,00198 USD | 973 | 3,28 s / 4,36 s |
| `gestoria_laboral` (solo documental) | `gestoria_agregacion` | 0,00211 USD | 1.130 | 2,95 s / 4,01 s |
| `agencia_inmobiliaria` (documental y estructurada, con grupo de solapamiento y dos casos de escritura) | `agencia_hitl_v3` | 0,00406 USD | 2.671 | 4,09 s / 5,73 s |

La agencia cuesta el doble por consulta que los inquilinos solo
documentales, y la causa está en los tokens de entrada: la rama
estructurada mete en el contexto el resultado de las herramientas, y el
grupo de solapamiento consulta las dos ramas (§22). Es el precio de
responder lo que ningún documento contiene.

Ficha mensual, a los precios vigentes de `claude-haiku-4-5` (1,00 / 5,00 USD
por millón de tokens):

| Consultas al mes | Inquilino documental (0,00198 USD) | Inquilino con rama estructurada (0,00406 USD) |
|---|---|---|
| 500 | 1,0 USD | 2,0 USD |
| 2.000 | 4,0 USD | 8,1 USD |
| 10.000 | 19,8 USD | 40,6 USD |

Lo que la ficha no incluye, y hay que decir al presentarla:

- **Embeddings.** Unos 14 tokens de media por consulta (91 consultas del
  golden set, §37), sin precio
  publicado para el modelo actual. Al precio de su sucesor (0,20 USD por
  millón) serían tres millonésimas de dólar por consulta: no cambia la
  ficha, pero se declara.
- **Infraestructura.** En el despliegue actual el servicio corre en el
  plan gratuito de Render, que duerme antes de 20 minutos sin tráfico y
  tarda entre 32 y 61 s en despertar (capítulo 6.6). El plan de pago más
  barato que lo elimina, Starter, cuesta 7 USD al mes por servicio (precio
  de fuentes secundarias a 26-09-2026): 14 USD al mes para la interfaz y
  el canal, coste fijo independiente del volumen que se suma aparte. Es
  también lo que haría persistente el registro de producción (capítulo
  6.1).
- **Evaluación.** Mantener el banco cuesta entre 0,06 y 0,16 USD por
  inquilino y pasada sin juez y, si se pasa el juez, en torno a 0,40 USD
  las tres pasadas de Gemini sobre dos bancos (§32). Es coste por cambio,
  no por
  consulta: se paga cuando se toca algo, no cuando se usa.
- **Lo que la contabilidad no ve** (capítulo 5.3): un 22 % de gasto de
  desarrollo y reintentos fuera del runner. En producción ese gasto no
  existe, pero la cifra de desarrollo del proyecto sí lo lleva.
- **Cambios de precio del proveedor.** `gemini-3.6-flash`, el proveedor
  alternativo, dobla su precio el 1 de enero de 2027 (§29). La tabla de
  precios del repositorio es viva y un test recalcula desde tokens.
- **El volumen es supuesto.** Las tres filas de la ficha mensual (500,
  2.000 y 10.000 consultas) son órdenes de magnitud para una plantilla de
  diez a cien personas, no una medida: ningún inquilino real ha usado el
  sistema.

## 6. Control en producción: observabilidad, operación y despliegue

### 6.1 El registro de producción

Cada consulta real deja una línea en el registro del inquilino: usuario,
categoría, rama, fuentes, documentos denegados por permiso, campos
redactados, tokens, coste en dólares y latencia (§20). Las que fallan
quedan con `_fallo` y su tipo de error desde que la primera pulsación del
simulacro de incidentes destapó que no dejaban rastro (§46). El registro
no guarda la respuesta. `observabilidad_cli` resume por inquilino:
consultas, coste acumulado, latencia p95, cuántas veces alguien pidió lo
que no le toca; y aplica la política de retención del capítulo 6.2. Nadie
recibe una alerta: el tope blando se comprueba al consultar y no avisa, y
es un límite declarado (capítulo 9).

En el despliegue actual el registro vive en el disco efímero del plan
gratuito de Render y no sobrevive a un reinicio del servicio. La política
de retención del capítulo 6.2 está medida en local y es un requisito del
despliegue de pago (capítulo 5.4), no una propiedad del actual.

### 6.2 Retención y supresión

`RETENCION.md`: 90 días, respuesta no guardada, supresión por usuario y
purga por antigüedad, las dos con lápida que dice cuánto se quitó sin
decir a quién. Medidas en menos de 0,05 s (0,048 y 0,040 s) sobre un
registro de 10.000 líneas (§37). La tensión entre la trazabilidad que pide el artículo 12 del
AI Act y el riesgo de vigilancia del Módulo 4 se escribe, no se resuelve
(R-16).

### 6.3 Despliegue

Render, desde `render.yaml`: primer despliegue en 1 min 32 s (§38). Se
paró en el login por exigir la clave del juez, que la interfaz no usa;
arreglado. Seis usuarios, dos por inquilino, en `APP_USUARIOS_JSON`; las
contraseñas solo las tiene el autor, y dar de alta o de baja un usuario
exige cambiar esa variable y redesplegar. Cuatro hallazgos (§38, §39, §41,
§42) salieron de probar el servicio desplegado y no el banco; el §41 es la
fuga por tamaño del capítulo 2.6.

### 6.4 Plan de incidentes, pulsado en frío

`INCIDENTES.md` define el botón rojo en orden (revocar, parar, congelar
evidencia, rotar), quién avisa a quién, y que todo incidente termina en un
hallazgo. `scripts/simulacro_incidente.py` lo pulsa: **14,95 s** el botón
rojo completo (fallo legible y registrado en 4,8 s, evidencia congelada
con manifiesto en 1,65 s, vuelta en 8,47 s) (§46). La primera pulsación
destapó que las consultas fallidas no dejaban rastro. La mitad manual del
plan, revocar y rotar la clave en las consolas y en Render, no está
cronometrada y se decidió no hacerlo antes de la defensa: no hay incidente
que lo pida, y rotar credenciales en el mes de la defensa solo para medir
es más riesgo que dato. Queda declarada como estimación, unos cinco
minutos, no como medida.

### 6.5 Dos superficies y un puente

El proyecto se desarrolló desde Claude Code y desde la app de Claude,
unidos por un puente MCP local propio: utillaje del autor, no del sistema
(`docs/SINCRONIZACION_SUPERFICIES.md`). Se menciona por un hallazgo: al
montarlo, la sesión de solo lectura que la app abría sobre el repositorio
podía leer el `.env` con las claves (§19). Es la fila R-04 del registro de
riesgos y la prueba de que confinar a un directorio no es confinar a lo
que se puede enseñar.

### 6.6 Carga y arranque en frío

Ocho consultas a la vez sobre un mismo `Sistema` tardan lo que una: p50
entre 3,16 y 3,32 s en concurrencia 1, 2, 4 y 8, el lote 5,7 veces más
rápido, 0 errores, y el enrutado y el permiso iguales que en secuencial
(§53). La rama estructurada paga entre 0 y medio segundo a cuatro en
vuelo. La puerta HTTP de una instancia gratuita aguanta 20 clientes a la
vez sin moverse: 216 peticiones, máximo 0,19 s. Dos de 64 consultas de la
primera pasada superaron 11 s dentro de una llamada al proveedor y la
segunda pasada no lo repitió; la causa no se vio.

El plan gratuito duerme antes de 20 minutos sin tráfico (Render documenta
15) y despertar cuesta 32 s la interfaz y 42-61 s el servicio de WhatsApp;
despierto, menos de 0,2 s, y ninguna petición se pierde mientras despierta
(§52). Lo que estas dos medidas no cubren está en el capítulo 9.

## 7. Gobernanza, seguridad e IA responsable

Este capítulo absorbe el Módulo 4 del máster, por decisión confirmada en
la tutoría (capítulo 1.2), que además nombró la securización como
requisito. El material del módulo no entra en el repositorio (es obra de
un profesor y el repositorio es público); se cita desde `MODULO_4.md`.

### 7.1 El registro de riesgos

`RIESGOS.md` tiene 24 filas, cada una con cuadrante de la matriz de
Rumsfeld, casilla del OWASP Top 10 para LLM, técnica de MITRE ATLAS
(verificadas contra la matriz 5.6.0), dominio de AIUC-1, evidencia
(hallazgo o test), control y estado. Un test comprueba que cada hallazgo
citado existe y que las diez casillas del OWASP tienen fila: una fila sin
evidencia es una opinión.

| Cuadrante | Contramedida del Módulo 4 | Lo que el proyecto pone |
|---|---|---|
| Conocidos-conocidos | Pruebas y métricas | El banco, las métricas deterministas, la contabilidad de coste (14 filas) |
| Conocidos-desconocidos | Vigilar, despliegue continuo | Precios vivos con test, conmutación verificada y condicionada a una clave de pago (§54), AIBOM (R-07, R-09, R-15) |
| Desconocidos-conocidos | Evaluar vulnerabilidades activamente | Cinco filas que salieron de mirar con desconfianza (R-04, R-06, R-11, R-13, R-21); en tres de ellas el error estaba en el instrumento (capítulo 4.5) |
| Desconocidos-desconocidos | Botón rojo y plan | Tope prepago, plan escrito y pulsado en frío (R-23) |

### 7.2 OWASP Top 10 para LLM

| # | Riesgo | Estado |
|---|---|---|
| 1 | Inyección de instrucciones | Medido con los ocho casos `inj-*` del banco (cuatro en el heredado, dos en la agencia, dos en la gestoría) y la cobertura del riesgo: los que llegan al control no filtran ningún literal prohibido; `inj-04` no llega y es el residual (capítulo 2.7) |
| 2 | Salida insegura | Por construcción: texto para una persona; se reevaluará con los canales |
| 3 | Envenenamiento de datos | Por construcción, no medido como ataque: corpus sintético con semilla. Un cliente real trae su corpus y la mitigación desaparece |
| 4 | Denegación de servicio | Por construcción: tope duro (prepago sin recarga) y blando; una fuga a pleno ritmo gasta 13,7 USD por hora (115 consultas por minuto con ocho en vuelo, §53). Sin límite por usuario ni por minuto; la puerta HTTP aguanta 20 clientes a la vez y el pipeline 8 en vuelo sin degradarse (§53), así que la denegación plausible es económica, no de capacidad |
| 5 | Cadena de suministro | Por construcción: AIBOM generado y vigilado por test; destapó el §35 al generarse |
| 6 | Divulgación de información confidencial | Lo más fuerte del proyecto: permiso en el `where`, redacción, cobertura del riesgo, una fuga real cerrada, aislamiento por colección |
| 7 | Complementos no seguros | Por construcción: servidores MCP como procesos aparte. Medido solo en el puente del autor: sin lista de denegación la sesión hija leía el `.env` entero (§19) |
| 8 | Agencia excesiva | Medido: 40 de 40 sin escritura sin aprobar (§42) |
| 9 | Sobredependencia | Medido, y sobre el propio evaluador: el juez emite números que contradicen su razonamiento (§30, §32) |
| 10 | Robo de modelo | No aplica |

Donde la tabla dice "por construcción" no hay medida: el control existe
por diseño y no se ha atacado. Son las filas 2, 3, 5 y 7.

De los nueve guardarraíles que enumera el material, el proyecto tiene
ocho (la tabla de `MODULO_4.md` los recorre uno a uno). Falta la
moderación de contenido, y el hueco está justificado: en un asistente
interno sobre documentación propia el vector es la consulta, la inyección
lo cubre en parte y la categoría `otro` filtra lo que está fuera de
ámbito.

### 7.3 Sesgo, medido en tres capas

Pares de consultas emparejadas que solo difieren en un rasgo (género,
edad, origen, discapacidad), con grupo de control y suelo de ruido:

| Capa | Cómo | Resultado | Hallazgo |
|---|---|---|---|
| Recuperación | Distancia de embeddings entre pares emparejados, con control de ruido | Ningún eje alcanza el doble de su suelo; sin emparejar, `discapacidad` daba un rango 75 veces mayor y era una afirmación falsa | §34 |
| Enrutado | Categoría asignada en seis variantes de nombre | Estable | §34 |
| Generación | Cinco medidas deterministas sin juez, ocho repeticiones por variante | Ningún eje por encima del suelo; dos medidas saturadas | §44 |

Lo que **no** se afirma: que el sistema no discrimina. Dos de las cinco
medidas de generación están saturadas y solo prueban que no hay negativa
selectiva ni omisión de datos; presentarlo como ausencia de sesgo sería la
falsa objetividad que el propio módulo enumera como riesgo. El propio
experimento produjo tres afirmaciones falsas, concretas y alarmantes
antes de la correcta (§34), todas por pares mal emparejados; por eso
trece pruebas comprueban que los pares sigan emparejados
(`tests/test_sesgo.py`), y veinte más la capa de generación. Y una
hipótesis que salió de leer las respuestas (matiz por origen, 2,00x con 8
tiradas) cayó a 1,00x con 24: una hipótesis que sale de los datos no se
confirma con los mismos datos.

### 7.4 AI Act: el mismo sistema, una casilla por inquilino

Un asistente que interactúa con personas cae en la obligación de
transparencia del **artículo 50.1**, en aplicación desde el 2 de agosto de
2026 y por tanto vigente en la defensa; el aviso lo declara cada
manifiesto y lo muestra la interfaz. Pero el corpus del inquilino heredado
tiene salarios y evaluaciones individuales (anexo III, punto 4, empleo) y
los expedientes de la agencia tienen ingresos y solvencia de personas
físicas (punto 5b). Si el asistente se usara para evaluar personas o
decidir su admisión, sería de alto riesgo.

La salida es el **artículo 6.3**: no es de alto riesgo un sistema del anexo
III que hace una tarea de procedimiento limitada, y quien lo alegue
documentará su evaluación (apartado 4). Esa documentación es el bloque
`ai_act` del manifiesto, que exige la condición alegada, la justificación,
los usos excluidos y la declaración de que no perfila personas (el último
párrafo del 6.3 dice que el perfilado siempre es alto riesgo); el
validador rechaza una excepción con perfilado y rechaza tocar el anexo III
sin excepción ni clasificación de alto riesgo.

**El calendario cambió el 27 de julio de 2026** y la memoria cita el texto
vigente: el Reglamento (UE) 2026/1744 (Ómnibus digital sobre IA) retrasa
las obligaciones de alto riesgo del anexo III al **2 de diciembre de 2027**.
En octubre de 2026 el artículo 50 obliga y el capítulo III no; la
clasificación por inquilino se defiende como diseño anticipado, no como
cumplimiento exigible. Las citas literales se tomaron de EUR-Lex y se
contrastaron contra la Comisión y el BOE (fuentes en `MODULO_4.md`).

### 7.5 RGPD sobre el RAG

- **Borrado y rectificación** (§36): `scripts/borrar_documento.py` retira un
  documento, reconstruye el índice y comprueba contra la colección que no
  queda ningún fragmento suyo. **1,46 s** en la agencia, **1,23 s** en el
  heredado, cero fragmentos residuales, el resto intacto. Es reconstrucción
  completa, crece con el corpus. Lo que no cubre: las consultas registradas
  que citaron el documento (R-16).
- **Retención del registro**: capítulo 6.2.
- **Transferencias internacionales y lo que producción exigiría**: en el
  estado actual no viaja ningún dato real porque los tres inquilinos son
  sintéticos, así que el riesgo está mitigado por el dato, no por el
  contrato. Con un cliente real, cada consulta manda fragmentos de sus
  documentos y de su CRM a proveedores fuera de la Unión. En ese esquema
  la empresa cliente es la responsable del tratamiento, quien opera el
  asistente es encargado y cada proveedor de modelos, subencargado; y eso
  exige base jurídica para la transferencia (cláusulas tipo o decisión de
  adecuación), un contrato de encargado con cada proveedor, un registro de
  actividades de tratamiento y, si el uso tocara el anexo III sin la
  excepción del 6.3, una evaluación de impacto. Nada de eso está escrito:
  es el hueco R-18, y la memoria lo declara en vez de darlo por hecho.

### 7.6 Cadena de suministro

`AIBOM.md` se genera desde `uv.lock`, `config.py`, `provider.py` y los
manifiestos, con un test que falla si difiere: 12 paquetes directos y 142
transitivos fijados, todos los grupos opcionales incluidos, y cada modelo
con su precio o con la marca de que no lo tiene. La primera vez que se
generó destapó que el modelo de embeddings está en retirada y costaba
cero (§35). Residual: la versión de Node del puente no está
fijada, y el inventario lo dice.

## 8. Escalabilidad y mantenimiento

### 8.1 Dar de alta un cliente nuevo, cronometrado

La prueba medida de agnosticidad (§43): `gestoria_laboral` en **5 min
42 s**, dos iteraciones, **cero ficheros de código**: un manifiesto, seis
documentos de corpus y un banco de 28 casos escrito antes de la primera
pasada.

| Momento | Casos OK | Qué pasó |
|---|---|---|
| Primera pasada | 20 de 28 | Acierto del enrutador 0,769; los cinco fallos de enrutado, todos a `procedimientos` |
| Segunda pasada, 65 s después | 25 de 28 | Tres descripciones de categoría reescritas; acierto 0,923, cobertura del riesgo de 0,857 a 1,0 |
| Revisión en frío del banco (§45) | 27 de 28 | Dos de los tres rojos eran expectativas incorrectas del banco, no del sistema |
| Un caso de agregación de dos documentos añadido (§49) | 28 de 29 | El banco vigente del capítulo 4.2 |

El control de acceso y la clasificación por el AI Act vienen gratis con el
manifiesto. Sin banco, `procedimientos` habría llegado a producción con un
77 % de acierto. Dos salvedades que la cifra declara: el alta la hizo un
asistente de código con el proyecto en contexto, y en un cliente real el
banco de 28 casos lo escribe quien conoce el negocio, no quien monta el
sistema; ese tiempo no está medido.

Lo que el alta enseña sobre el sistema: el enrutador es el primer cuello
de botella de un cliente nuevo (§1, §43) y se resuelve reescribiendo
descripciones, no código.

### 8.2 Lo que cuesta escalar lo que ya hay

Tres cosas crecen con el sistema, dos medidas y una declarada. El coste de
un grupo de solapamiento crece con el tamaño del grupo: +40 % por caso del
grupo (§22). El borrado RGPD es reconstrucción completa del índice y crece
con el corpus (§36). Y cambiar el manifiesto de un inquilino en producción
(una categoría nueva, una política más estricta) obliga a reindexar,
porque la firma del índice cubre la política (capítulo 2.3), e invalida la
comparación con el banco anterior de ese inquilino: el alta está medida,
el cambio no. Cuántos inquilinos aguanta un proceso tampoco se midió; el
límite conocido es Chroma abriendo una colección por inquilino.

### 8.3 Lo que no está, y por qué

Lo decidido en contra y lo que sigue abierto, en una sola tabla para que
no haya que buscarlo en dos sitios:

| Qué | Decisión o estado | Cuándo |
|---|---|---|
| Migrar embeddings a `gemini-embedding-2` | Decidido no antes de la defensa: invalida el índice y mueve las métricas de recuperación (§35) | Antes del 14-05-2028 |
| Mayoría de tres del juez por defecto | Decidido no automatizarla (§32, §33): sobre 10 casos tres pasadas no bastan; repetir es un acto deliberado | Cerrado en el primer corte |
| Denegación explícita en el caso parcial | Decidido no hacerlo antes de la defensa: 14 casos del heredado y otro corte de línea base (§47) | Tras la defensa |
| `inj-04` | Residual: arreglarlo es tocar el prompt del enrutador heredado, que es la línea base | No se hace |
| Aislamiento por número y aprobación por texto de WhatsApp en vivo | Decidido no medir: mismo mecanismo que la credencial web, fijado por las pruebas simuladas (§51) | Tras la defensa, si se pide |
| Comparar el generador con Gemini | **Abierto.** Bloqueado por la cuota gratuita de la clave (§54); exige facturación en el proyecto de Google | Cuando haya clave de pago |
| Rotar las claves de API y cronometrar la mitad manual del plan de incidentes | Decidido no hacerlo antes de la defensa: no hay incidente que lo pida (capítulo 6.4) | Tras la defensa |
| Conectar el canal de correo a un buzón real | **Abierto.** Construido y probado en simulación; falta la cuenta de Gmail dedicada y sus credenciales en Render (`docs/ENCARGO_CORREO_2026-09-26.md`) | Cuando exista el buzón |
| Conectores a CRM comerciales; despliegue íntegramente local; omnicanalidad más allá de tres canales | Fuera del alcance (`ALCANCE.md` §7) | No se hace |

### 8.4 Mantenimiento frente a proveedores que cambian solos

Cuatro instancias medidas (R-07): `gemini-2.5-flash` retirado para
proyectos nuevos (§29), `claude-sonnet-5` descartando `temperature` sin
avisar (§26), `gemini-embedding-001` en retirada sin precio publicado
(§35) y la cuota gratuita de Gemini agotando un banco entero (§54). Y dos
defectos de la propia contabilidad: la tabla de precios heredada de la 3.3
tenía el de `claude-sonnet-5` un 50 % alto y todo lo derivado salía
inflado (§21), y un modelo sin precio costaba cero hasta que el registro
pasó a marcar `modelos_sin_precio` (§28). Las mitigaciones: tabla de
precios viva con un test que recalcula desde tokens, modelos con fecha en
el identificador, AIBOM, y la conmutación de proveedor verificada (§29) y
condicionada, desde el §54, a una clave de pago.

## 9. Límites y lo que queda fuera

Tres bloques: lo que el banco no mide, lo que el despliegue no es todavía
y lo que queda fuera por decisión. Lo decidido con fecha vive en el
capítulo 8.3 y aquí solo se remite.

**Lo que el banco no mide.**

- **Un solo turno.** No hay evaluación conversacional de varios turnos.
- **Lo escribió quien construyó el sistema, y no hay conjunto reservado.**
  Las descripciones de categoría de la agencia se afinaron en tres
  iteraciones sobre el mismo banco (§6); el umbral del enrutador por
  embeddings sí se calibró en un inquilino y se aplicó a otros (§48), pero
  para Haiku no hay separación. Lo más parecido a una transferencia es el
  alta de la gestoría: un banco nuevo, escrito antes de la primera pasada.
- **Sin anotación humana** del acuerdo con el juez (capítulo 4.3).
- **El envenenamiento del corpus** no está medido como ataque: la
  mitigación es que el corpus es sintético, y desaparece con un cliente
  real. **El fallo del servidor MCP** tampoco: la regla lo hace visible,
  pero no se ha simulado (capítulo 3.2).
- **El generador no se comparó** con ningún otro modelo (capítulos 3.3 y
  8.3).

**Lo que el despliegue no es todavía.**

- **La interfaz vale para una demostración, no para un cliente**, y lo dice
  en pantalla: contraseñas con SHA-256 y sal, comparación en tiempo
  constante, pero sin límite de intentos, sin caducidad de sesión, sin
  límite de gasto por usuario (R-08) y sin alta de usuarios sin
  redesplegar (capítulo 6.3).
- **El registro de producción vive en un disco efímero** y no sobrevive a
  un reinicio del plan gratuito (capítulo 6.1).
- **Nadie recibe alertas**: el tope blando es un suelo, se comprueba al
  consultar, y no hay límite por usuario ni por minuto.
- **La moderación de contenido** no existe (capítulo 7.2).
- **Los embeddings no se convierten a dólares** (capítulo 5.3).
- **De la carga solo se midió un proceso y una puerta** (capítulo 6.6). Sin
  medir: consultas reales concurrentes contra Render, el techo de hilos, la
  CPU del plan gratuito y la reconstrucción del índice tras un reinicio.
  Que lo que escala sea el número de inquilinos es una afirmación de diseño
  con una medida (el alta), no una de rendimiento.
- **WhatsApp** está probado en vivo con un número y dos preguntas; la
  latencia interna en producción no se ha leído (capítulo 2.9). **Correo**
  está probado solo en simulación, y su servicio, dormido en el plan
  gratuito, no sondea el buzón hasta que algo lo despierte.

**Lo que queda fuera por decisión** está en la tabla del capítulo 8.3, con
su motivo y su fecha.

**Para pasar de demostración a piloto**, por este orden: plan de pago con
disco persistente para el registro, límites por usuario y por minuto, alta
de usuarios sin redesplegar, moderación de contenido, y el corpus real de
un cliente con su propia evaluación de envenenamiento y su contrato de
encargado (capítulo 7.5).

## 10. Documentación técnica y preparación de la defensa

### 10.1 Cómo está documentado el proyecto

La documentación no es un anexo del código: es donde viven las decisiones,
y el código la hace cumplir con tests. Siete ficheros, cada uno con una
función que no se solapa con la de los demás:

| Fichero | Qué es | Quién lo hace cumplir |
|---|---|---|
| `CLAUDE.md` | Fuente única de verdad: qué es el sistema, estado, decisiones cerradas, reglas de trabajo, riesgos abiertos | Si una conversación lo contradice, gana el fichero |
| `docs/ALCANCE.md` | Por qué se reorientó el proyecto, alcance por bloques con líneas de corte decididas de antemano, cortes de línea base fechados con su escotilla | Las escotillas tienen prueba |
| `docs/HALLAZGOS.md` | 54 hallazgos medidos, cada uno con la ejecución que lo respalda, y los que corrigen a otro lo dicen; el capítulo 4.5 dice lo que enseñaron sobre el método | El registro de riesgos no puede citar un hallazgo que no exista |
| `docs/RIESGOS.md` | 24 riesgos con Rumsfeld, OWASP, ATLAS, AIUC-1, evidencia y estado | `tests/test_riesgos.py`: cada `§` citado existe y las diez casillas del OWASP tienen fila |
| `docs/AIBOM.md` | Inventario de dependencias, modelos y precios | Generado por script; el test falla si difiere del generado |
| `docs/BITACORA.md` | Diario de sesiones: hecho, decidido, pendiente | La sesión siguiente arranca leyéndola |
| `reports/<etiqueta>/` | Evidencia de cada ejecución: `resumen.json`, `informe.md`, trazas | Versionados a propósito: una cifra sin carpeta no es un dato |

Y tres más de operación, cada uno con lo medido dentro: `INCIDENTES.md`
(botón rojo, 14,95 s), `RETENCION.md` (90 días, supresión en menos de
0,05 s) y `DESPLIEGUE.md` (usuarios, topes, Render).

### 10.2 La defensa

Si la defensa incluye una demostración, `docs/GUION_DEMO.md` la fija:
quince minutos en ocho bloques, más dos de calentamiento sin público,
cada uno con qué se enseña, qué se hace y qué tiene que verse. Las
consultas son literales del golden set o del registro de producción, así
que su comportamiento está medido y no se improvisa delante del tribunal.
Los tres bloques centrales son los tres argumentos de las conclusiones: el
control de acceso dentro de la búsqueda con la misma pregunta desde dos
roles, la rama estructurada con datos que no están en ningún documento, y
la escritura propuesta por el modelo y aprobada por una persona. El guion
incluye qué hacer si algo falla en directo: cada fallo posible se enseña
como lo que es, porque la regla de nada de fallbacks silenciosos vale
también para la demo.

[PENDIENTE: formato de la defensa (duración, demo en vivo, tribunal), que
decide si el servicio de Render sigue vivo o basta una grabación. Coste de
la demo entera: menos de 0,05 USD; el riesgo no es el gasto, es quedarse
sin crédito.]

## 11. Conclusiones

Lo que se defiende, en tres frases con su número:

1. **El aislamiento es estructural**: una colección por inquilino, y un
   test que abre la colección equivocada falla. Dar de alta un cliente
   cuesta 5 min 42 s y ningún fichero de código.
2. **El control de acceso está antes del modelo y está medido**: cobertura
   del riesgo 1,0 en la agencia, `fuga_literal` 10 de 10 en la línea base
   vigente, una fuga real
   encontrada y cerrada en el heredado, y ninguna escritura sin una persona
   que la apruebe.
3. **El evaluador también se evaluó**: 4 de 24 veredictos del juez eran
   falsos y todos en el mismo sentido, y por eso ninguna decisión del
   proyecto cuelga de él. Las decisiones las anclan métricas que no varían.

La aportación propia frente a la entrega de la que parte, en una frase:
convertir un RAG de una empresa en un sistema multi-tenant con dos ramas
en el que el control de acceso es estructural, y demostrar con el
cronómetro que un cliente nuevo no cuesta código.

Y lo que el proyecto aprendió sobre método, que vale más que cualquier
cifra: siete veces el error estaba en el instrumento y no en el sistema;
tres afirmaciones sobre sesgo fueron falsas antes de que una fuera cierta;
y una hipótesis que sale de los datos no se confirma con los mismos datos.
Lo que se haría distinto: reservar desde el primer día un conjunto de
casos que nadie mira hasta el final, y comprobar la cuota de cada
proveedor antes de apoyar una justificación en su conmutación.

## Anexo A. Cómo reproducirlo

```bash
git clone https://github.com/JuanArchidona/asistente-multitenant
uv sync --group judge --group app
cp .env.example .env            # claves: sistema, juez, embeddings
uv run pytest                   # 1124 tests con el grupo langgraph, sin llamadas a API
uv run python -m src.ingest_cli # indexa el inquilino activo (TENANT_ID)
uv run python -m evals.runner --etiqueta prueba --sin-juez   # banco sin juez, menos de un minuto
uv run streamlit run app.py
```

Cada cifra de esta memoria tiene su carpeta en `reports/<etiqueta>/` con
`resumen.json`, `informe.md` y las trazas. Las escotillas de línea base
(`ROUTER_TEMPERATURE=defecto`, `JUDGE_PROVIDER=anthropic`,
`GEN_QUIEN_PREGUNTA=0`) reproducen las cifras anteriores a cada corte.

## Anexo B. Índice de hallazgos por capítulo

Los 54 hallazgos de `docs/HALLAZGOS.md`, con los capítulos de esta memoria
que los citan (todos los que lo hacen, no solo el principal; regenerado
desde las citas `§N` del texto). Cada hallazgo nombra la ejecución de
`reports/` que lo respalda o dice que no la tiene.

| Capítulo | Hallazgos citados |
|---|---|
| Resumen | §5, §8, §22, §30, §32, §40, §43, §45 |
| 1.3 El criterio de evaluación, y el método que impone | §3, §45, §46, §47 |
| 2.3 Aislamiento estructural | §10, §13, §14, §37, §43, §53 |
| 2.4 El clasificador | §1, §6, §12, §15, §22, §27 |
| 2.5 La rama documental | §47 |
| 2.6 La rama estructurada por MCP | §4, §5, §41 |
| 2.7 Control de acceso antes del modelo | §2, §5, §8, §9, §11, §22, §23, §39, §40, §41, §42, §47 |
| 2.8 Generación anclada | §39, §40 |
| 2.9 Interfaz y canales | §51 |
| 3.1 Python sin framework frente a LangGraph | §29, §50, §54 |
| 3.2 Servidores MCP frente a herramientas cableadas | §7 |
| 3.3 Modelos | §17, §24, §25, §26, §29, §32, §35, §48, §54 |
| 3.4 El resto de la pila | §19, §26, §38, §51, §52 |
| 4.1 El banco | §11, §23, §30, §31, §42, §47 |
| 4.2 Resultados en la línea base vigente | §42, §45, §49 |
| 4.3 Evaluar al evaluador | §8, §24, §26, §30, §32, §33, §40 |
| 4.5 Lo que el banco enseñó sobre el método | §3, §11, §21, §31, §45, §47, §49, §54 |
| 5.1 Lo que cuesta funcionar y lo que cuesta medir | §17, §21, §22, §32, §34, §44 |
| 5.2 Tope de gasto y una clave por fin | §16, §18, §24, §53 |
| 5.3 Lo que la contabilidad no ve | §16, §35, §37 |
| 5.4 La ficha comercial: qué cuesta un cliente nuevo | §22, §29, §32, §37 |
| 6.1 El registro de producción | §20, §46 |
| 6.2 Retención y supresión | §37 |
| 6.3 Despliegue | §38, §39, §41, §42 |
| 6.4 Plan de incidentes, pulsado en frío | §46 |
| 6.5 Dos superficies y un puente | §19 |
| 6.6 Carga y arranque en frío | §52, §53 |
| 7.1 El registro de riesgos | §54 |
| 7.2 OWASP Top 10 para LLM | §19, §30, §32, §35, §42, §53 |
| 7.3 Sesgo, medido en tres capas | §34, §44 |
| 7.5 RGPD sobre el RAG | §36 |
| 7.6 Cadena de suministro | §35 |
| 8.1 Dar de alta un cliente nuevo, cronometrado | §1, §43, §45, §49 |
| 8.2 Lo que cuesta escalar lo que ya hay | §22, §36 |
| 8.3 Lo que no está, y por qué | §32, §33, §35, §47, §51, §54 |
| 8.4 Mantenimiento frente a proveedores que cambian solos | §21, §26, §28, §29, §35, §54 |
| 9. Límites y lo que queda fuera | §6, §48 |

Hallazgos que corrigen a otro, y que hay que leer juntos: §21 corrige las
cifras en dólares de §17 y §18 (un 50 % altas); §33 matiza §31 y §32 (la
mayoría de tres no generaliza); §41 corrige una condición no escrita de
§8; §47 cierra lo que §22 dejó abierto y cambia su decisión; §22 ejecuta
lo que §12 dejó pendiente; §44 completa §34; §45 revisa §43 sin mover su
cifra.

