---
title: "Asistente interno multi-tenant de conocimiento y datos para empresas de servicios profesionales"
subtitle: "Memoria técnica del Trabajo Fin de Máster — borrador 1"
author: "Juan Archidona Ahijado — Máster en IA Generativa Avanzada, The Bridge"
date: "24 de septiembre de 2026"
lang: es
---

> **Estado: borrador 1, abierto el 24-09-2026.** Estructura completa y
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
de diseño tiene una medida detrás.

El proyecto parte de las entregas 2.1, 2.3, 3.1 y 3.3 del máster, que ya
cubrían cuatro de los seis pasos del flujo y traían un banco de evaluación
de 109 casos. Sobre esa base se construyeron en cuatro semanas la
multi-tenencia, la rama estructurada, la capa de gobernanza, la
observabilidad, el despliegue con autenticación, el análisis de IA
responsable, la interfaz web autenticada y un canal de WhatsApp.

Tres cifras que resumen lo que se defiende:

| Afirmación | Cifra | Dónde está medida |
|---|---|---|
| Dar de alta un cliente nuevo no exige código | **5 min 42 s**, cero ficheros `.py`, 27 de 28 casos de su banco a la tercera iteración | §43, §45 |
| El control de acceso está en la búsqueda, no en el prompt | Cobertura del riesgo **1,0** en la agencia; `fuga_literal` **10/10**; una fuga real encontrada y cerrada | §8, §22, §33 |
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
| Banco de evaluación | 109 casos, 13 métricas en 4 capas, CI | 3.3 (10/10) |

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
  anterior (§4.4 de esta memoria).

### 1.4 Los tres inquilinos

Los tres son sintéticos: ningún dato real de ninguna empresa entra en el
repositorio, que es público. Eso es además una medida de cumplimiento del
capítulo 5 del RGPD (transferencias internacionales), no una comodidad de
desarrollo (§7.6).

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
agnosticidad (§8.1).

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
núcleo son unas 5.200 líneas en `src/`, `mcp_servers/` y `app.py`, con
1.107 tests que corren en 11 segundos sin llamar a ningún proveedor.

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
inquilino y falla si abre otra (R-03).

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
`claude-haiku-4-5`, temperatura 0 desde el 22-09-2026 (§4.4).

Tres decisiones medidas:

- **El enrutador es el primer cuello de botella de un cliente nuevo** (§1):
  la agencia arrancó con un acierto de 0,700 porque el corpus tenía
  expedientes con datos de clientes y ninguna categoría los nombraba; el
  enrutador no puede devolver lo que el prompt no describe. Añadir seis
  palabras a una descripción subió el acierto a 0,833 y los casos que pasan
  de 18/30 a 22/30. Tres iteraciones sobre las descripciones (§6) y una
  categoría nueva, `expedientes` (§12: de 29/38 a 33/38, cobertura del
  riesgo de 0,444 a 0,778), sin tocar el código. Y el enrutador tampoco
  repite (§15): 4 de 38 casos cambiaban de categoría entre pasadas idénticas
  con la configuración heredada, de ahí que el acierto se reporte con
  dispersión y que la temperatura pasara a 0.
- **La ambigüedad no se elige, se consulta** (§22). Cuando una consulta cae
  en un grupo de solapamiento declarado (`expedientes`/`cartera`), el
  sistema consulta las dos ramas en vez de pedirle al enrutador que
  resuelva una ambigüedad que no está en la pregunta. Cobertura del riesgo
  de 0,778 a **1,0** en la agencia. Precio: **+40 % de coste por caso y
  +0,5 s de latencia** en los casos del grupo, y crece con el tamaño del
  grupo, no con el número de grupos.
- **Temperatura 0 no es determinismo** (§27, 910 llamadas y 0,57 USD): 3
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
  herramienta**, por política declarativa, antes de que el modelo lo vea, y
  **antes del recorte** por tamaño: el recorte a 6.000 caracteres iba antes
  de redactar y dejaba pasar JSON roto sin redactar; una respuesta de 6.028
  caracteres lo destapó en el servicio desplegado (§41). Ahora un resultado
  no estructurado con campos sensibles declarados se retiene y la traza lo
  dice: un control que depende del tamaño de la respuesta falla justo cuando
  hay más datos que proteger.

### 2.7 Gobernanza: el control va antes del modelo

La decisión central del proyecto, y la que se defiende con más medidas:
**un prompt que dice "no reveles el DNI" deja el DNI en la ventana de
contexto**. El permiso va dentro del `where` de la búsqueda documental y
la redacción se aplica al salir de la herramienta estructurada. Lo que el
usuario no puede ver no llega al modelo.

| Mecanismo | Dónde actúa | Medida |
|---|---|---|
| Permiso en el `where` | Recuperación documental | Contra la línea base: heredado 45/52 a 47/53 con fugas literales de 2 a 0; agencia 27/36 a 29/38 con fugas de 1 a 0, y sin la caída de relevancia (0,880 a 0,778) que costó endurecer el prompt en la 3.3 (§8). `fuga_literal` 10/10 con política endurecida (§33); cobertura del riesgo 0,636 (heredado) y 1,0 (agencia) (§11, §22) |
| Redacción de campos | Salida de cada herramienta MCP, antes del recorte | Línea base sin gobernanza: DNI, teléfono, correo e ingresos del comprador reproducidos (§5); tres de cuatro casos de confidencialidad de la agencia filtraban (§2). Después, 0. Agujero por tamaño cerrado (§41) |
| Denegación explícita | Camino documental vaciado por permiso | 5 casos de la gestoría, 28/28 en `fuga_literal` (§47) |
| El generador sabe quién pregunta | Prompt del generador, desde el 23-09 | De 2 de 5 a 5 de 5 al dar un dato autorizado a dirección (§39, §40) |
| Escritura con aprobación humana | Herramientas declaradas como escritura | `accion_sin_aprobar` 40/40; ninguna visita escrita tras el banco (§42) |
| Verificación determinista de citas | Salida | 588 de 588 citas resolubles en 22 ejecuciones, cero inventadas (§23) |

**El modelo nunca escribe.** Una herramienta que escribe se declara en el
manifiesto (`escrituras`) y el servidor MCP la anota como no de solo
lectura; si discrepan, el cliente no arranca. El modelo la propone con sus
argumentos, una persona la aprueba o la rechaza desde la interfaz, y las
tres cosas quedan registradas (§42, OWASP LLM08).

La medida "cobertura del riesgo" merece explicación (§9, §11): una medida
de seguridad solo vale si la consulta llegó al punto de riesgo. Un caso de
inyección que el enrutador manda a `otro` no prueba que el control
funcione, prueba que no se le llegó a exigir. De los 20 casos con material
protegido en juego, solo 11 llegaban al control (§11): "cero fugas sobre 17
casos" era en realidad "cero fugas sobre 9". Por eso la métrica publica su
denominador. El 0,636 del heredado son casos que no llegan al control
por fallo de enrutado, y subirlos es trabajo de enrutador, no de
gobernanza; uno de ellos, `inj-04`, se queda como residual documentado.

### 2.8 Generación anclada

El generador recibe el contexto ya filtrado, la política de respuesta
(base, endurecida) y, desde el 23-09-2026, **quién pregunta y que todo su
contexto ya pasó el control de acceso**. Antes no lo sabía y obedecía las
clasificaciones escritas dentro de los documentos: a dirección le negaba un
salario 3 veces de 5 aunque el control le hubiera entregado el anexo,
citando la cabecera "CONFIDENCIAL" del propio documento (§39). Es un
control de acceso que nadie le pidió, aplicado a ratos. Después, 5 de 5, y
ninguna métrica de confidencialidad se movió (§40).

La rama estructurada cita ahora de qué herramienta sale cada dato:
`cita_alguna_fuente` de 0,83 a 0,96 en la agencia (§40), aunque el §42
matiza que ese 0,96 era una pasada y no es estable entre pasadas. En las
diez consultas del §39 el control estructural acertó el 100 % y el
generador el 70 %: el control era lo que sostenía la confidencialidad, y
ninguna métrica de fuga se movió con el cambio.

### 2.9 Observabilidad y coste en producción

Cada consulta real deja una línea en el registro del inquilino: usuario,
categoría, rama, fuentes, documentos denegados por permiso, campos
redactados, tokens, coste en dólares, latencia. Desde el 23-09 las
consultas que revientan también quedan, con su tipo de error (§46): la
primera pulsación del simulacro de incidentes destapó que no dejaban
rastro. `src.observabilidad_cli` resume por inquilino, cuenta cuántas veces
alguien pidió lo que no le toca, y aplica la política de retención (§6.2).

### 2.10 Interfaz y canales

- **Interfaz Streamlit** (`app.py`), desplegada en Render: usuario y
  contraseña, el inquilino lo fija la credencial, los roles van al control
  de acceso, aviso del artículo 50 al entrar, tope blando de gasto sobre el
  registro, tarjeta de acciones pendientes de aprobación.
- **WhatsApp** (`src/canal_whatsapp.py`, contra la API oficial de Meta): el
  número de teléfono es la credencial y fija el inquilino, aviso del
  artículo 50 en la primera conversación, aprobación humana por texto, firma
  del webhook obligatoria, el teléfono nunca entra en el registro. 25
  pruebas con mensajes simulados; 5,1 s una consulta contra el sistema real.
  [PENDIENTE: prueba en vivo con la cuenta de pruebas de Meta.]
- **Correo**: no construido; queda fuera (capítulo 9).

## 3. Selección y justificación de modelos, patrones y herramientas

### 3.1 Python sin framework frente a LangGraph

La orquestación es Python con tool-calling nativo del SDK del proveedor.
La comparación con LangGraph se hace aquí en términos de lo que el
capstone puntúa, no de preferencia. [PENDIENTE: decidir con Juan si se
construye el prototipo de media jornada que pase el banco heredado; si no,
este capítulo se sostiene argumentado, como prevé `ALCANCE.md` punto 14.]

| Criterio | Python sin framework (elegido) | LangGraph |
|---|---|---|
| Calidad | El flujo es una función; cada paso tiene un test unitario sin proveedor. 1.107 tests en 11 s | El grafo aporta estructura, pero cada nodo sigue siendo la misma llamada; la calidad la deciden prompts, control de acceso y banco, que serían idénticos |
| Coste | Cero dependencias de orquestación; el AIBOM lista 10 paquetes directos y 119 transitivos (§7.7). Ninguna capa entre el SDK y la contabilidad de tokens | Añade el framework y sus transitivas; la contabilidad de tokens pasa por sus callbacks |
| Escalabilidad | Lo que escala aquí es el número de inquilinos, y eso lo resuelve el manifiesto, no el orquestador | Igual: el manifiesto es ortogonal al framework |
| Riesgo | Superficie mínima: el control de acceso está en el `where` y en la salida de la herramienta, sitios que se leen en una pantalla. Sin fallbacks del framework que traguen errores | Riesgo de cadena de suministro (R-09): el material del Módulo 4 trae el incidente de LiteLLM de marzo de 2026. Comportamientos por defecto (reintentos, recorte) que hay que auditar |
| Mantenimiento | Todo cambio es visible en un diff de Python. La conmutación de proveedor se verificó de extremo a extremo (§29) sin adaptadores | Cada cambio de versión del framework es un cambio de comportamiento que hay que volver a medir con el banco, y el proyecto ya midió tres cambios no anunciados de los proveedores en cuatro semanas (§8.4) |
| Lo que se pierde | Persistencia de estado y reanudación entre pasos, visualización del grafo, paralelismo declarativo | |

Lo que se pierde no lo necesita este sistema: el flujo es de un turno, sin
estado entre consultas, y la única bifurcación (documental, estructurada,
ambas) es un `if` sobre el destino del manifiesto. Cuando el flujo tenga
varios turnos con estado (capítulo 9), la comparación habrá que rehacerla.

### 3.2 Servidores MCP frente a herramientas cableadas

Un `tools=[...]` dentro del agente ata el sistema a la API de un cliente;
un servidor MCP lo convierte en contrato: el manifiesto dice qué servidor
arrancar, el servidor dice qué herramientas tiene y cuáles escriben, y el
cliente comprueba que las dos versiones coinciden. Dar de alta un cliente
con CRM propio es escribir su servidor, no tocar el agente.

Tres decisiones de ingeniería de la rama, con su medida (§7): los
servidores se arrancan una vez, al construir el sistema (1,1 s), y se
mantienen abiertos en vez de abrirse por consulta, porque con 36 casos de
banco la alternativa habría añadido unos 40 segundos y un proceso por
pregunta; las sesiones del SDK se abren y se cierran en la misma tarea,
porque repartirlas entre dos revienta al salir; y el prompt lleva la fecha
del sistema, porque el modelo no sabe qué día es y "esta semana" acababa
pidiendo el rango al usuario. Riesgo de negocio medido: el servidor MCP oficial
de idealista existe y está cerrado a clientes externos (403 en el
`initialize`, política declarada en su documentación); depender de un MCP
de terceros es un riesgo de negocio, no técnico, y por eso el código del
TFM no llama a idealista (`ALCANCE.md` §3).

### 3.3 Modelos

| Función | Modelo | Por qué |
|---|---|---|
| Clasificador y generación | `claude-haiku-4-5` | Heredado de la 3.3 con su línea base medida; 0,00245 USD por caso sin juez en la ejecución del §17, y entre 0,0020 y 0,0037 por inquilino en las vigentes (capítulo 5.4) |
| Juez | `gemini-3.6-flash`, desde el 22-09 | Otra familia que el generador, 5,5 veces más barato por evaluación que `claude-sonnet-5`, y el único que admite temperatura 0 de verdad (§24, §26, §32) |
| Embeddings | `gemini-embedding-001`, 768 dimensiones | Heredado; en retirada con cierre anunciado el 14-05-2028 y sin precio publicado (§35). Decidido no migrar antes de la defensa: invalidaría el índice |
| Proveedor alternativo | `gemini-3.6-flash` para chat, vía `LLM_PROVIDER=gemini` | La conmutación era una forma y no un hecho hasta el §29; verificada de extremo a extremo |

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
y la línea de mejora que sale es dar ejemplos a las descripciones, no
afinar un modelo. La cascada (embeddings y Haiku solo en duda) iguala a
Haiku en muestra pero fuera manda al LLM el 75-88 % de las consultas.

Un prerrutado determinista por identificador (OP-2026-118 va a
expedientes) se descartó con una cuenta de dos minutos (§25): los
identificadores viven donde el problema ya está resuelto y la deriva del
13,2 % es semántica.

### 3.4 El resto de la pila

- **`uv`** con `pyproject.toml`, `uv.lock` y `.python-version`; `ruff`.
- **Pydantic** para toda salida estructurada del modelo.
- **ChromaDB** local persistente, una colección por inquilino.
- **Streamlit** para la interfaz, **Render** para el despliegue
  (blueprint en `render.yaml`).
- **DeepEval** para las métricas de juez, con el hallazgo de que descarta
  `temperature=0` sin avisar en `claude-sonnet-5` (§26).
- **Node sin dependencias** para el puente MCP con la app de Claude
  (capítulo 6.4).

## 4. Evaluación

### 4.1 El banco

Tres bancos, uno por inquilino, sobre el mismo runner heredado de la 3.3:

| Banco | Casos | Dimensiones | Para qué |
|---|---|---|---|
| `empresa_servicios` | 53 | Las ocho de la 3.3 más cobertura del riesgo | Suite de regresión de la línea base |
| `agencia_inmobiliaria` | 40 | Las mismas más rama estructurada, solapamiento y escritura | Medir lo nuevo |
| `gestoria_laboral` | 29 | Las mismas | Medir el alta de un cliente |

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

`pii_leakage` se retiró del banco el 22-09-2026 (§30, §31): su escala se
invertía entre casos y penalizaba al sistema por nombrar a la persona
cuyos datos estaba protegiendo; una denegación correcta sacaba 0,00.
Afectaba a 17 casos, no a 6, porque era métrica por defecto de dos
dimensiones enteras.

### 4.2 Resultados en la línea base vigente

Ejecuciones del 23 y el 24-09-2026, sin juez, tras el segundo corte de línea base:

| Ejecución | Casos OK | `routing` | Cobertura del riesgo | `cita_alguna_fuente` |
|---|---|---|---|---|
| `empresa_quien` (53) | 48 | 0,9038 | 0,6364 | 1,0 |
| `agencia_quien` (38) | 32 | 0,8421 | 1,0 | 0,96 |
| `gestoria_agregacion_v2` (29) | 28 | 0,963 | 1,0 | 1,0 |

Lo que dicen: el heredado no se ha degradado con la multi-tenencia (49 con
la línea anterior; el que baja es `ooc-04`, el 1 de 53 que sigue variando a
temperatura 0); la agencia sube tres casos porque la rama estructurada cita
ahora la herramienta; la gestoría, montada en menos de seis minutos, da 28
de 29 tras corregir dos expectativas del banco (§45), recuperar un caso de
agregación real de dos documentos (§49) y quedarse con un fallo real del
sistema (`ooc-04`).

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
  (§32, seis pasadas): de 24 veredictos, 4 son espurios y **los cuatro
  suspenden lo que debía aprobar**. Consecuencia: `casos_ok` de una pasada
  con juez es un suelo, y promediar pasadas empeora la cifra en vez de
  cancelar el error. La única corrección conocida es la mayoría de tres.
- **La comparación base/endurecido no la puede decidir el juez** (§33): 5 y
  6 casos de 10 cambian de veredicto entre tres pasadas idénticas. La decide
  `fuga_literal`: la política base filtra el salario individual de un
  empleado y un dato de salud citando el anexo confidencial, la endurecida
  no filtra ninguno de los dos; **8/10 frente a 10/10**.

Dos reglas salen de ahí y se aplican en toda la memoria: una puntuación de
juez no se lee sin su razón, y ninguna decisión del proyecto cuelga de una
métrica de juez.

La limitación que queda: el juez de la 3.3 compartía familia con el
generador (`claude-sonnet-5` juzgando a `claude-haiku-4-5`); `Config`
impide que sean el mismo modelo, no la misma familia. Desde el §24 la
limitación viaja en cada `resumen.json` y en cada informe, y el juez por
defecto es de otra familia.

### 4.4 Cortes de línea base, con fecha

Dos veces cambió un valor por defecto y las cifras de antes y de después
dejaron de ser comparables. Quedan escritos porque es lo único que impide
citar dos cifras que miden configuraciones distintas.

| Corte | Qué cambió | Qué compra | Qué no compra | Escotilla |
|---|---|---|---|---|
| 22-09-2026 (`ALCANCE.md` §5.c) | Temperatura del enrutador a 0; juez por defecto a `gemini-3.6-flash` | 3 casos inestables de 38 pasan a 0; independencia de familia; juez 5,5 veces más barato | Determinismo (1 de 53 sigue variando); estabilidad del juez | `ROUTER_TEMPERATURE=defecto`, `JUDGE_PROVIDER=anthropic` |
| 23-09-2026 (§5.d) | El generador recibe quién pregunta y que su contexto está autorizado | 2 de 5 a 5 de 5 al dar un dato autorizado; la rama estructurada cita la herramienta | Nada frente a una fuga real: eso lo garantiza la búsqueda | `GEN_QUIEN_PREGUNTA=0` |

Se decidieron antes de conocer la rúbrica, y a propósito: entre que
aparece (6-13 de octubre) y la defensa hay una o dos semanas, y una
decisión que invalida la comparación con las ejecuciones anteriores no deja
tiempo de volver a medir. La rúbrica puede cambiar cómo se presentan las
cifras, no qué configuración es la buena.

### 4.5 El banco descubrió sus propios defectos

Cinco veces el error estaba en el instrumento y no en el sistema, y
las cinco se corrigieron por escrito antes de sacar conclusiones: dos
defectos del banco de la agencia (§3), la mitad de los casos de seguridad
que no probaban nada (§11), la métrica de PII invertida (§31), dos casos de
la gestoría (§45) y un comparador que no ignoraba el énfasis de markdown
(§47). La regla es no relajar el banco tras ver los resultados; cada
corrección cita por qué la expectativa era incorrecta.

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
| Demo completa de la defensa | menos de 0,05 USD | `GUION_DEMO.md` |

La primera cifra de la 3.3 tenía el precio de `claude-sonnet-5` un 50 %
alto y todo lo derivado salía inflado (§21). La tabla de precios es viva y
un test recalcula desde tokens; un modelo sin precio en la tabla costaba
cero hasta el §28, y ahora el registro marca `modelos_sin_precio`.

### 5.2 Tope de gasto y una clave por fin

- **Tope duro**: cuentas de prepago en los dos proveedores con recarga
  automática desactivada. 12,66 USD de crédito en Anthropic; el peor caso de
  una fuga se agota solo en una hora. El riesgo se ha invertido: lo que hay
  que vigilar es quedarse sin crédito en la defensa (§16).
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
primera está en el capítulo 8.1: 5 min 42 s de trabajo y cero ficheros de
código. La segunda sale de la contabilidad de tokens de las ejecuciones
vigentes de cada inquilino, que es la mejor aproximación que hay al tráfico
real: cada banco es una mezcla de consultas cortas, largas, de una rama y
de las dos.

| Inquilino | Ejecución | Coste por consulta | Tokens de entrada por consulta | Latencia media / p95 |
|---|---|---|---|---|
| `empresa_servicios` (solo documental) | `empresa_quien` | 0,00198 USD | 973 | 3,28 s / 4,36 s |
| `gestoria_laboral` (solo documental) | `gestoria_agregacion` | 0,00211 USD | 1.130 | 2,95 s / 4,01 s |
| `agencia_inmobiliaria` (documental y estructurada, con grupo de solapamiento) | `agencia_quien` | 0,00372 USD | 2.379 | 4,10 s / 5,59 s |

La agencia cuesta 1,9 veces más por consulta que los inquilinos solo
documentales, y la causa está en los tokens de entrada: la rama
estructurada mete en el contexto el resultado de las herramientas, y el
grupo de solapamiento consulta las dos ramas (§22). Es el precio de
responder lo que ningún documento contiene.

Ficha mensual, a los precios vigentes de `claude-haiku-4-5` (1,00 / 5,00 USD
por millón de tokens):

| Consultas al mes | Inquilino documental (0,0020 USD) | Inquilino con rama estructurada (0,0037 USD) |
|---|---|---|
| 500 | 1,0 USD | 1,9 USD |
| 2.000 | 4,0 USD | 7,4 USD |
| 10.000 | 19,8 USD | 37,2 USD |

Lo que la ficha no incluye, y hay que decir al presentarla:

- **Embeddings.** Entre 12 y 15 tokens por consulta (§37), sin precio
  publicado para el modelo actual. Al precio de su sucesor (0,20 USD por
  millón) serían tres millonésimas de dólar por consulta: no cambia la
  ficha, pero se declara.
- **Infraestructura.** El servicio corre hoy en el plan gratuito de Render,
  que duerme sin tráfico. Un plan de pago es un coste fijo independiente del
  volumen y se suma aparte.
- **Evaluación.** Mantener el banco cuesta entre 0,06 y 0,14 USD por
  inquilino y pasada sin juez, y en torno a 0,40 USD las tres pasadas de
  juez de Gemini sobre dos bancos (§32). Es coste por cambio, no por
  consulta: se paga cuando se toca algo, no cuando se usa.
- **Lo que la contabilidad no ve** (capítulo 5.3): un 22 % de gasto de
  desarrollo y reintentos fuera del runner. En producción ese gasto no
  existe, pero la cifra de desarrollo del proyecto sí lo lleva.
- **Cambios de precio del proveedor.** `gemini-3.6-flash`, el proveedor
  alternativo, dobla su precio el 1 de enero de 2027 (§29). La tabla de
  precios del repositorio es viva y un test recalcula desde tokens.

## 6. Observabilidad, operación y despliegue

### 6.1 El registro de producción

Una línea por consulta en el registro del inquilino, con coste, latencia,
categoría, fuentes, denegaciones y campos redactados; las consultas que
fallan quedan con `_fallo` y su tipo de error (§46). `observabilidad_cli`
resume por inquilino: consultas, coste acumulado, latencia p95, cuántas
veces alguien pidió lo que no le toca. El registro no guarda la respuesta.

### 6.2 Retención y supresión

`RETENCION.md`: 90 días, respuesta no guardada, supresión por usuario y
purga por antigüedad, las dos con lápida que dice cuánto se quitó sin
decir a quién. Medidas en décimas de segundo sobre un registro de 10.000
líneas (§37). La tensión entre la trazabilidad que pide el artículo 12 del
AI Act y el riesgo de vigilancia del Módulo 4 se escribe, no se resuelve
(R-16).

### 6.3 Despliegue

Render, desde `render.yaml`: primer despliegue en 1 min 32 s (§38). Se
paró en el login por exigir la clave del juez, que la interfaz no usa;
arreglado. Seis usuarios, dos por inquilino, en `APP_USUARIOS_JSON`; las
contraseñas solo las tiene el autor. El servicio público resultó ser el
mejor banco de pruebas: cinco de los nueve hallazgos del 23-09 salieron de
probar fuera del banco, y tres de ellos (§39, §41, §42) en el servicio
desplegado.

### 6.4 Plan de incidentes, pulsado en frío

`INCIDENTES.md` define el botón rojo en orden (revocar, parar, congelar
evidencia, rotar), quién avisa a quién, y que todo incidente termina en un
hallazgo. `scripts/simulacro_incidente.py` lo pulsa: **14,95 s** el botón
rojo completo (fallo legible y registrado en 4,8 s, evidencia congelada
con manifiesto en 1,65 s, vuelta en 8,47 s) (§46). La primera pulsación
destapó que las consultas fallidas no dejaban rastro. [PENDIENTE: la mitad
manual, revocar y rotar en las consolas, con reloj.]

### 6.5 Cómo se trabajó: dos superficies y un puente

El proyecto se desarrolló desde Claude Code y desde la app de Claude, con
un puente MCP local propio (`puente/`) que da a la app lo que el conector
de GitHub no puede: el árbol sin pushear, un buzón de encargos y un
registro de lo hecho, con un canal de vuelta que avisa a Claude Code en su
siguiente prompt. La regla que no se negocia es que la cadena termina en
una persona: un aviso nunca genera un encargo. Al montarlo se descubrió que
la sesión hija podía leer el `.env` con las claves (§19), y de ahí salió la
fila R-04 del registro de riesgos. El patrón está documentado aparte y es
trasladable a cualquier proyecto (`docs/SINCRONIZACION_SUPERFICIES.md`).

## 7. Gobernanza, seguridad e IA responsable

Este capítulo absorbe el Módulo 4 del máster, por decisión del 20-09
confirmada por el tutor el 22-09, que además nombró la securización como
requisito. El material del módulo no entra en el repositorio (es obra de
un profesor y el repositorio es público); se cita desde `MODULO_4.md`.

### 7.1 El registro de riesgos

`RIESGOS.md` tiene 23 filas, cada una con cuadrante de la matriz de
Rumsfeld, casilla del OWASP Top 10 para LLM, técnica de MITRE ATLAS
(verificadas contra la matriz 5.6.0), dominio de AIUC-1, evidencia
(hallazgo o test), control y estado. Un test comprueba que cada hallazgo
citado existe y que las diez casillas del OWASP tienen fila: una fila sin
evidencia es una opinión.

| Cuadrante | Contramedida del Módulo 4 | Lo que el proyecto pone |
|---|---|---|
| Conocidos-conocidos | Pruebas y métricas | El banco, las métricas deterministas, la contabilidad de coste (13 filas) |
| Conocidos-desconocidos | Vigilar, despliegue continuo | Precios vivos con test, conmutación verificada, AIBOM (R-07, R-09, R-15) |
| Desconocidos-conocidos | Evaluar vulnerabilidades activamente | Lo que salió de mirar con desconfianza: cuatro de esos hallazgos tenían el error en el instrumento y no en el sistema (R-04, R-06, R-11, R-13, R-21) |
| Desconocidos-desconocidos | Botón rojo y plan | Tope prepago, plan escrito y pulsado en frío (R-23) |

### 7.2 OWASP Top 10 para LLM

| # | Riesgo | Estado |
|---|---|---|
| 1 | Inyección de instrucciones | Medido: `fuga_literal` 8/10 base frente a 10/10 endurecido (§33); residual `inj-04` |
| 2 | Salida insegura | Por construcción: texto para una persona; se reevaluará con los canales |
| 3 | Envenenamiento de datos | Por construcción, no medido como ataque: corpus sintético con semilla. Un cliente real trae su corpus y la mitigación desaparece |
| 4 | Denegación de servicio | Medido: tope duro y blando; sin límite por usuario ni por minuto |
| 5 | Cadena de suministro | Por construcción: AIBOM generado y vigilado por test; destapó el §35 al generarse |
| 6 | Divulgación de información confidencial | Lo más fuerte del proyecto: permiso en el `where`, redacción, cobertura del riesgo, una fuga real cerrada, aislamiento por colección |
| 7 | Complementos no seguros | Medido: servidores MCP como procesos aparte; `--restricted` y lista de denegación en el puente (§19) |
| 8 | Agencia excesiva | Medido: 40 de 40 sin escritura sin aprobar (§42) |
| 9 | Sobre-dependencia | Medido, y sobre el propio evaluador: el juez emite números que contradicen su razonamiento (§30, §32) |
| 10 | Robo de modelo | No aplica |

De los nueve guardarraíles que enumera el material, el proyecto tiene
siete; falta la moderación de contenido (hueco justificado: en un
asistente interno sobre documentación propia el vector es la consulta, y
la inyección lo cubre en parte) y la categoría `otro` hace de filtro de
fuera de ámbito.

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
falsa objetividad que el propio módulo enumera como riesgo. El experimento
se equivocó tres veces antes de acertar (§34), con afirmaciones
intermedias falsas, concretas y alarmantes; de ahí las trece pruebas que
comprueban que los pares sigan emparejados (`tests/test_sesgo.py`), y las
veinte de la capa de generación. Y una hipótesis
que salió de leer las respuestas (matiz por origen, 2,00x con 8 tiradas)
cayó a 1,00x con 24: una hipótesis que sale de los datos no se confirma
con los mismos datos.

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
cumplimiento exigible. Las citas literales las trajo la app de Claude
leyendo EUR-Lex y se contrastaron contra la Comisión y el BOE (fuentes en
`MODULO_4.md`).

### 7.5 RGPD sobre el RAG

- **Borrado y rectificación** (§36): `scripts/borrar_documento.py` retira un
  documento, reconstruye el índice y comprueba contra la colección que no
  queda ningún fragmento suyo. **1,46 s** en la agencia, **1,23 s** en el
  heredado, cero fragmentos residuales, el resto intacto. Es reconstrucción
  completa, crece con el corpus. Lo que no cubre: las consultas registradas
  que citaron el documento (R-16).
- **Retención del registro**: capítulo 6.2.
- **Transferencias internacionales**: hoy no viaja ningún dato real porque
  los tres inquilinos son sintéticos. En producción exige base jurídica y
  un DPA con el proveedor; es el hueco documental R-18.

### 7.6 Cadena de suministro

`AIBOM.md` se genera desde `uv.lock`, `config.py`, `provider.py` y los
manifiestos, con un test que falla si difiere: 10 paquetes directos y 119
transitivos fijados, cada modelo con su precio o con la marca de que no lo
tiene. Al generarse destapó que el modelo de embeddings está en retirada y
costaba cero (§35). Residual: la versión de Node del puente no está
fijada, y el inventario lo dice.

## 8. Escalabilidad y mantenimiento

### 8.1 Dar de alta un cliente nuevo, cronometrado

La prueba medida de agnosticidad (§43): `gestoria_laboral` en **5 min
42 s**, dos iteraciones, **cero ficheros de código**: un manifiesto, seis
documentos de corpus y un banco de 28 casos. 20 de 28 a la primera (acierto
del enrutador 0,769, cinco fallos y todos a `procedimientos`) y 25 de 28
tras reescribir tres descripciones en treinta y cinco segundos (0,923,
cobertura del riesgo de 0,857 a 1,0); revisado en frío, dos de los tres
rojos eran del banco y no del sistema: **27 de 28** (§45). El control de
acceso y la clasificación por el AI Act vienen gratis con el manifiesto.
Sin banco, `procedimientos` habría llegado a producción con un 77 % de
acierto. Salvedad que la cifra declara: el alta la hizo un asistente de
código con el proyecto en contexto.

Lo que el alta enseña sobre el sistema: el enrutador es el primer cuello
de botella de un cliente nuevo (§1, §43) y se resuelve reescribiendo
descripciones, no código.

### 8.2 Lo que cuesta escalar lo que ya hay

- Los grupos de solapamiento cuestan +40 % por caso del grupo, y el coste
  crece con el tamaño del grupo (§22).
- El borrado RGPD es reconstrucción completa del índice (§36).
- La denegación explícita en el caso parcial (contexto más algo retenido)
  afecta a 14 casos del heredado y sería otro corte de línea base; decidido
  no hacerlo antes de la defensa (§47).

### 8.3 Decisiones pendientes con fecha

| Decisión | Estado | Fecha límite |
|---|---|---|
| Migrar embeddings a `gemini-embedding-2` | Decidido no antes de la defensa: invalida el índice | 14-05-2028 |
| Juez de otra familia repetido tres veces por defecto | Diseñado; falta una segunda clave de Gemini y 0,22 USD | Antes de la memoria final |
| Denegación explícita en el caso parcial | Decidido no hacerlo | Tras la defensa |
| `inj-04` | Residual: arreglarlo es tocar el prompt del enrutador heredado | No se hace |
| Correo como canal | No construido | Fuera |

### 8.4 Mantenimiento frente a proveedores que cambian solos

Tres instancias medidas en cuatro semanas (R-07): `gemini-2.5-flash`
retirado para proyectos nuevos (§29), `claude-sonnet-5` descartando
`temperature` sin avisar (§26), `gemini-embedding-001` en retirada sin
precio publicado (§35). Y un precio del repositorio un 50 % alto (§21). Las
mitigaciones: tabla de precios viva con test, modelos con fecha en el
identificador, conmutación de proveedor verificada, AIBOM.

## 9. Límites y lo que queda fuera

- **El banco es de un turno.** No hay evaluación conversacional multivuelta.
- **Sin anotación humana** del acuerdo con el juez; el juez se evaluó
  contra sí mismo y contra métricas deterministas.
- **La denegación parcial** en el camino documental heredado no avisa al
  modelo (14 casos).
- **`inj-04`** no llega al control con el enrutador por defecto.
- **El envenenamiento del corpus** no está medido como ataque: la
  mitigación es que el corpus es sintético, y desaparece con un cliente
  real.
- **La moderación de contenido** no existe.
- **El coste blando es un suelo** y no hay límite por usuario ni por minuto.
- **Los embeddings no se convierten a dólares.**
- **WhatsApp** no está probado en vivo; **correo** no está construido.
- **Conectores a CRM comerciales**, despliegue íntegramente local y
  omnicanalidad completa quedan fuera (`ALCANCE.md` §7).

## 10. Conclusiones

Lo que se defiende, en tres frases con su número:

1. **El aislamiento es estructural**: una colección por inquilino, y un
   test que abre la colección equivocada falla. Dar de alta un cliente
   cuesta 5 min 42 s y ningún fichero de código.
2. **El control de acceso está antes del modelo y está medido**: cobertura
   del riesgo 1,0 en la agencia, `fuga_literal` 10/10, una fuga real
   encontrada y cerrada en el heredado, y ninguna escritura sin una persona
   que la apruebe.
3. **El evaluador también se evaluó**: 4 de 24 veredictos del juez eran
   falsos y todos en el mismo sentido, y por eso ninguna decisión del
   proyecto cuelga de él. Las decisiones las anclan métricas que no varían.

Y lo que el proyecto aprendió sobre método, que vale más que cualquier
cifra: cinco veces el error estaba en el instrumento y no en el sistema;
tres afirmaciones sobre sesgo fueron falsas antes de que una fuera cierta;
y una hipótesis que sale de los datos no se confirma con los mismos datos.

## 11. Cómo reproducirlo

```bash
git clone https://github.com/JuanArchidona/asistente-multitenant
uv sync --group judge --group app
cp .env.example .env            # claves: sistema, juez, embeddings
uv run pytest                   # 1107 tests, sin llamadas a API
uv run python -m src.ingest_cli # indexa el inquilino activo (TENANT_ID)
uv run python -m evals.runner --etiqueta prueba --sin-juez   # banco sin juez, menos de un minuto
uv run streamlit run app.py
```

Cada cifra de esta memoria tiene su carpeta en `reports/<etiqueta>/` con
`resumen.json`, `informe.md` y las trazas. Las escotillas de línea base
(`ROUTER_TEMPERATURE=defecto`, `JUDGE_PROVIDER=anthropic`,
`GEN_QUIEN_PREGUNTA=0`) reproducen las cifras anteriores a cada corte.

## 12. Documentación técnica y preparación de la defensa

### 12.1 Cómo está documentado el proyecto

La documentación no es un anexo del código: es donde viven las decisiones,
y el código la hace cumplir con tests. Siete ficheros, cada uno con una
función que no se solapa con la de los demás:

| Fichero | Qué es | Quién lo hace cumplir |
|---|---|---|
| `CLAUDE.md` | Fuente única de verdad: qué es el sistema, estado, decisiones cerradas, reglas de trabajo, riesgos abiertos | Si una conversación lo contradice, gana el fichero |
| `docs/ALCANCE.md` | Por qué se reorientó el proyecto, alcance por bloques con líneas de corte decididas de antemano, cortes de línea base fechados con su escotilla | Las escotillas tienen prueba |
| `docs/HALLAZGOS.md` | 49 hallazgos medidos, cada uno con la ejecución que lo respalda, y los que corrigen a otro lo dicen | El registro de riesgos no puede citar un hallazgo que no exista |
| `docs/RIESGOS.md` | 23 riesgos con Rumsfeld, OWASP, ATLAS, AIUC-1, evidencia y estado | `tests/test_riesgos.py`: cada `§` citado existe y las diez casillas del OWASP tienen fila |
| `docs/AIBOM.md` | Inventario de dependencias, modelos y precios | Generado por script; el test falla si difiere del generado |
| `docs/BITACORA.md` | Diario de sesiones: hecho, decidido, pendiente | La sesión siguiente arranca leyéndola |
| `reports/<etiqueta>/` | Evidencia de cada ejecución: `resumen.json`, `informe.md`, trazas | Versionados a propósito: una cifra sin carpeta no es un dato |

Y tres más de operación, cada uno con lo medido dentro: `INCIDENTES.md`
(botón rojo, 14,95 s), `RETENCION.md` (90 días, supresión en décimas de
segundo) y `DESPLIEGUE.md` (usuarios, topes, Render).

### 12.2 El método de trabajo, que también se defiende

Dos reglas de método salieron del propio proyecto y están medidas:

- **Una predicción escrita antes de mirar convierte una cifra en una
  medida** (§21). La corrección del precio del juez se hizo escribiendo tres
  resultados posibles antes de abrir la consola del proveedor; la consola
  marcó uno de los tres.
- **Una hipótesis que sale de los datos no se confirma con los mismos
  datos** (§44). El matiz por origen en la generación era 2,00 veces su
  suelo con 8 tiradas y 1,00 con 24 nuevas.

El proyecto se trabajó desde dos superficies, Claude Code y la app de
Claude, con un puente propio entre ellas (capítulo 6.5). Lo que un agente
podía hacer sobre el repositorio quedó acotado por estructura, y el primer
defecto que se encontró fue precisamente en esa acotación (§19).

### 12.3 La defensa

`docs/GUION_DEMO.md` fija la demostración: doce minutos en seis bloques,
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

## Anexo A. Índice de hallazgos por capítulo

Los 49 hallazgos de `docs/HALLAZGOS.md`, con el capítulo de esta memoria
que los cita. Cada uno nombra la ejecución de `reports/` que lo respalda o
dice que no la tiene.

| Capítulo | Hallazgos |
|---|---|
| 2.1-2.3 Arquitectura y aislamiento | §13, §22, §29 |
| 2.4 Clasificador | §1, §6, §12, §15, §25, §27, §48 |
| 2.5 Rama documental | §10, §14 |
| 2.6 Rama estructurada | §4, §7, §42 |
| 2.7-2.8 Gobernanza y generación | §5, §8, §39, §40, §41, §47 |
| 2.9, 6 Observabilidad y producción | §20, §37, §38 |
| 4 Evaluación y juez | §2, §3, §9, §11, §23, §24, §26, §30, §31, §32, §33 |
| 5 Coste | §16, §17, §18, §21, §28 |
| 7.3 Sesgo | §34, §44 |
| 7.4-7.5 IA responsable, RGPD | §36 |
| 6.4, 7.6 Seguridad, incidentes, cadena de suministro | §19, §35, §46 |
| 8.1 Alta de cliente | §43, §45, §49 |

Hallazgos que corrigen a otro, y que hay que leer juntos: §21 corrige las
cifras en dólares de §17 y §18 (un 50 % altas); §33 matiza §31 y §32 (la
mayoría de tres no generaliza); §41 corrige una condición no escrita de
§8; §47 cierra lo que §22 dejó abierto y cambia su decisión; §22 ejecuta
lo que §12 dejó pendiente; §44 completa §34; §45 revisa §43 sin mover su
cifra.

