---
title: "Asistente interno multi-tenant de conocimiento y datos para empresas de servicios profesionales"
subtitle: "Memoria técnica del Trabajo Fin de Máster"
author: "Juan Archidona Ahijado — Máster en IA Generativa Avanzada, The Bridge"
date: "25 de octubre de 2026"
lang: es
---

**Repositorio:** <https://github.com/JuanArchidona/asistente-multitenant>

**Servicio desplegado:** <https://asistente-multitenant.onrender.com>

## Resumen ejecutivo

**Qué es.** Un asistente interno para empresas de servicios profesionales
(gestorías, agencias inmobiliarias, consultoras). Un empleado le pregunta en
lenguaje natural y el asistente responde combinando dos fuentes: la
documentación propia de la empresa (convenios, procedimientos, actas,
expedientes), mediante recuperación aumentada (RAG), y sus datos de negocio
(el CRM), mediante servidores MCP (Model Context Protocol, el estándar para
que un modelo use herramientas de otros sistemas). El mismo código atiende a varias empresas
a la vez, que en esta memoria se llaman **inquilinos**.

**El problema que resuelve de verdad.** Contestar bien no basta para poder
desplegarlo: lo que decide si una empresa lo acepta es **quién puede ver
qué**. El convenio es para todos; los salarios, solo para dirección; los
ingresos de un comprador, solo para quien lleva la operación. Este sistema
aplica ese control **antes** de que el modelo de lenguaje vea nada: lo que
un usuario no puede ver no llega nunca a la ventana de contexto del modelo,
así que el modelo no puede filtrarlo aunque quiera.

**Qué hay construido.** Tres inquilinos sintéticos con su documentación, sus
datos y su banco de pruebas; las dos ramas de consulta (documentos y CRM);
el control de acceso; una escritura en el CRM que solo se ejecuta si una
persona la aprueba; tres canales (web, WhatsApp y correo) desplegados en
Render; un registro de producción con evaluación automática de la calidad de
las respuestas; y un análisis de riesgos, sesgo y cumplimiento del AI Act.

**Tres resultados, con su número:**

| Qué se quería demostrar | Resultado medido |
|---|---|
| Dar de alta un cliente nuevo no exige programar | Un tercer inquilino se montó en **5 min 42 s** sin tocar una línea de código; su banco de pruebas pasó 27 de 28 casos tras corregir dos expectativas mal escritas |
| El control de acceso funciona y no depende del modelo | En la agencia, **todos** los casos con material protegido llegan al control (cobertura 1,0), y en los tres bancos **ninguna** respuesta contiene un dato prohibido (10 de 10, 9 de 9 y 6 de 6 casos) |
| El evaluador automático también se evaluó | El juez basado en un modelo de lenguaje se equivocó en **4 de 24** veredictos, siempre en el mismo sentido; por eso ninguna decisión del proyecto depende de él |

**Cómo se trabajó.** El proyecto parte de cuatro entregas anteriores del
máster y se desarrolló en once jornadas, entre el 20 de septiembre y el 25
de octubre de 2026, con un copiloto de código (Claude Code) dirigido por el
autor. La regla que guía todo el documento es la del propio máster: cada
decisión se justifica con una medida, y lo que no se ha medido se dice.

**Cómo comprobarlo.** El capítulo 6.6 explica qué puede verificar un tercero
y cómo: desde pasar las 1.255 pruebas automáticas sin coste hasta recorrer
el sistema desplegado con los usuarios de evaluación.

## Cómo leer esta memoria

**Dónde está lo que pide el enunciado.** El enunciado del proyecto final
pide cubrir los cuatro módulos del máster. Los capítulos siguen ese orden:

| Módulo | Lo que pide el enunciado | Capítulo |
|--|----------|-----|
| 1 | Qué modelos se usan y por qué | 3.1 |
| 1 | Configuración, forma de consumo, parámetros y prompts candidatos | 3.2 |
| 1 | Costes anticipados según niveles de uso | 3.3 |
| 2 | Flujo de acciones, niveles de autonomía e intervención humana | 2.1, 2.5 |
| 2 | Cómo un proceso de negocio se convierte en un proceso técnico | 1.1, 2.2 |
| 2 | Por qué ese framework y qué controles intermedios | 4.1, 4.2, 2.4 |
| 2 | Cómo se usaron los copilotos y cómo se controló su salida | 4.3 |
| 3 | Despliegue y paso automatizado a producción | 6.1 |
| 3 | Evaluación: tests, LLM como juez, evaluadores no subjetivos | 5 |
| 3 | Monitorización y rendimiento en producción | 6.2 |
| 4 | Análisis de riesgos y controles de seguridad | 7.1, 7.2, 2.4 |
| 4 | Red-teaming con una herramienta | 7.2 |
| 4 | Anonimización y enmascarado de datos | 2.4 (a la salida de las herramientas), 8.2 (en la consulta, decidido en contra) |
| 4 | Regulación (AI Act, RGPD), sesgo y cadena de suministro | 7.3 a 7.6 |
| Nota 9-10 | Que un tercero pueda usarlo sin carga de mantenimiento | 6.1, 6.6 |

**Las evidencias.** Cada cifra sale de una medición guardada en el
repositorio. Las mediciones están numeradas como **hallazgos** en el
fichero `docs/HALLAZGOS.md`, cada uno con la ejecución que lo respalda. Para
no interrumpir la lectura, el texto no los cita en cada frase: al final de
cada apartado, una línea en cursiva dice qué hallazgos lo sostienen, y el
**anexo B** da el título de cada uno. El **anexo C** es un glosario con los
términos técnicos que se repiten (inquilino, enrutador, cobertura del
riesgo, corte de línea base...).

## 1. El problema y el punto de partida

### 1.1 El problema

Una empresa de servicios profesionales tiene su conocimiento repartido en
dos sitios que no se hablan: **documentos** (convenios, procedimientos,
actas, expedientes) y **sistemas de datos** (CRM, agenda, cartera de
inmuebles). Tres preguntas lo ilustran:

- "¿Cuántos días de vacaciones me corresponden?" se responde con el
  convenio, un documento.
- "¿Qué visitas tiene Iván el jueves?" se responde con el CRM, un sistema
  de datos que cambia cada día.
- "¿Quiénes son las partes de la operación 118?" puede estar en el
  expediente escrito, en el CRM o en los dos, y quien pregunta no tiene por
  qué saber dónde. El sistema tiene que poder mirar en ambos.

Un asistente que solo busca en documentos responde lo que está escrito e
inventa lo demás; uno que solo consulta sistemas no sabe de procedimientos.
Y en cualquiera de los dos, lo que decide si se puede poner en producción
no es la calidad de la respuesta, sino **quién puede ver qué**.

El asistente tiene que servir a varias empresas con el mismo código, porque
una empresa pequeña de servicios no paga un desarrollo a medida. De ahí
salen los dos requisitos que ordenan todo el diseño: **el aislamiento entre
clientes**, y que **dar de alta un cliente nuevo cueste poco** y se pueda
medir.

### 1.2 Lo que se heredó de las entregas del máster

El proyecto no parte de cero. Las entregas 2.1, 2.3, 3.1 y 3.3 del máster ya
habían construido un asistente de documentos para una empresa, con su
evaluación. Partir de ahí no fue comodidad: el criterio del máster premia
justificar con números, y esas entregas traían un banco de 109 casos de
prueba ya medidos. Rehacerlo habría consumido el mes en reconstruir lo que
ya estaba demostrado. El tutor confirmó el 22 de septiembre que partir de
entregas propias calificadas es admisible.

| Pieza | Estado al empezar (20-09-2026) | De qué entrega |
|---|---|---|
| Interfaz web | Desplegada en Render | 3.1 (10/10) |
| Clasificador de consultas | Hecho y medido | 2.3 y 3.3 |
| Búsqueda en documentos | Hecha y ajustada con 11 configuraciones probadas | 2.3 y 3.3 |
| Consulta a sistemas de datos | **No existía** | — |
| Respuesta con cita de la fuente | Hecha | 2.3 |
| Control de acceso | El fallo estaba medido (2 fugas), no corregido | 3.3 |
| Banco de evaluación | 109 casos, 13 métricas, integración continua | 3.3 (10/10) |

El sistema heredado ya cumplía dos requisitos de su documento de concepto:
latencia (3,8 s de media) y coste (0,0021 USD por consulta). Lo nuevo de
este proyecto es todo lo demás: varios clientes, la consulta al CRM, el
control de acceso, la aprobación humana, los canales, la operación en
producción y el análisis de riesgos.

### 1.3 Los tres inquilinos

Los tres son **sintéticos**: el repositorio es público y ningún dato real
de ninguna empresa entra en él.

| | Empresa de servicios | Agencia inmobiliaria | Gestoría laboral |
|---|---|---|---|
| Qué es | La empresa heredada de las entregas anteriores | Domara Inmobiliaria, agencia ficticia de Zaragoza | Asesoría Marín y Lasheras, gestoría ficticia |
| Para qué está | Comprobar que nada de lo heredado se rompe | Demostrar que el diseño sirve a otro negocio y tiene datos vivos en un CRM | Medir cuánto cuesta dar de alta un cliente nuevo |
| Fuentes | 7 documentos | 10 documentos y un CRM | 6 documentos |
| Casos de prueba | 53 | 40 | 29 |
| Material sensible | Anexo con salarios; un acta con un intento de manipular al modelo | Expediente con DNI, ingresos y solvencia del comprador | Nóminas y datos de clientes |

La agencia se eligió por ser la más distinta de la empresa heredada: sus
datos son mercado y operaciones, no políticas internas. La gestoría se
construyó al final, cronometrada, como prueba de que el diseño es de verdad
independiente del cliente (capítulo 8.1).

### 1.4 El criterio que guía todo: medir

El programa del máster define el proyecto final así: *"el objetivo del
proyecto no está únicamente en que el sistema funcione, sino en justificar
cada decisión técnica en términos de calidad, coste, escalabilidad, riesgo
y mantenimiento"*. De ahí sale la regla de trabajo: **ante cualquier
propuesta, la pregunta es si se puede medir; una afirmación sin número no
vale.** Cuatro normas la concretan, y varias las vigila una prueba
automática:

- **No se relaja el banco de pruebas.** Un caso se corrige si la
  expectativa estaba mal, nunca porque el resultado incomode, y cada
  corrección queda justificada por escrito.
- **Nada de fallos silenciosos.** Si algo se degrada (el CRM no responde,
  la búsqueda sale vacía, el modelo corta su respuesta), el sistema lo
  marca y lo dice. La confusión más cara es que "el CRM está caído" se lea
  como "no hay datos".
- **Lo heredado no se toca sin decirlo.** Una prueba compara el prompt del
  clasificador, carácter a carácter, con el de la entrega 3.3; si cambia,
  las cifras de antes dejan de ser comparables.
- **Los cambios que rompen la comparación se fechan.** Dos veces se cambió
  un valor por defecto que hacía incomparables las cifras de antes y de
  después; los dos quedan fechados, con la forma de reproducir el
  comportamiento anterior (capítulo 5.2).

*Evidencia: hallazgos 3, 45, 46 y 47.*

## 2. La arquitectura

### 2.1 El flujo, de la pregunta a la respuesta

```
pregunta (web, WhatsApp o correo)
  1. autenticación      la credencial fija el cliente y los permisos de quien pregunta
  2. clasificación      ¿de qué tema es? ¿documentos, datos del CRM, ambos o ninguno?
  3. recuperación       documentos: búsqueda con el permiso dentro de la consulta
                        CRM: herramientas MCP, con los datos sensibles tachados a la salida
  4. respuesta          el modelo redacta solo con lo recuperado y sabiendo quién pregunta
  5. control de salida  citas comprobadas; una escritura queda pendiente de aprobación
  6. registro           quién, qué tema, coste, tiempo, qué se retuvo (no la respuesta)
respuesta, con el aviso de que se habla con una IA
```

Paso a paso:

1. **Autenticación.** El usuario entra con su credencial (usuario y
   contraseña en la web, su número en WhatsApp, su dirección en el correo).
   La credencial decide a qué cliente pertenece y qué roles tiene; el resto
   del sistema nunca adivina ninguna de las dos cosas.
2. **Clasificación.** Un modelo pequeño (Claude Haiku) lee la pregunta y
   devuelve el tema y el destino: documentos, CRM, ambos u "otro" si no
   tiene que ver con la empresa. Los temas posibles no están en el código:
   los declara cada cliente.
3. **Recuperación.** Si el destino son documentos, se buscan los fragmentos
   más parecidos en la colección de ese cliente, con el permiso del usuario
   como condición de la búsqueda. Si es el CRM, el modelo llama a las
   herramientas del servidor MCP del cliente, y los campos que el usuario no
   puede ver se sustituyen por una marca antes de que el modelo los lea.
4. **Respuesta.** El modelo redacta con lo recuperado y nada más, citando la
   fuente. Sabe quién pregunta y que todo lo que tiene delante ya pasó el
   control de acceso.
5. **Control de salida.** Un verificador sin modelo comprueba que cada
   fuente citada se recuperó de verdad. Si el modelo quiere escribir en el
   CRM, la escritura no se ejecuta: queda propuesta hasta que una persona la
   apruebe.
6. **Registro.** Cada consulta deja una línea con lo necesario para operar
   el sistema (capítulo 6.2), sin guardar el texto de la respuesta.

Todo está escrito en Python sin framework de orquestación (por qué, en el
capítulo 4.1): unas 7.200 líneas de código y 1.255 pruebas automáticas que
corren en menos de 20 segundos sin llamar a ningún proveedor.

### 2.2 Un cliente es un fichero de configuración

**Problema.** Si dar de alta un cliente exige programar, el producto no
escala: cada cliente es un proyecto.

**Decisión.** Todo lo que distingue a un cliente vive en un fichero
declarativo, el **manifiesto**: sus temas, cada
uno con su descripción y su destino; qué temas se solapan; qué servidores
MCP tiene; qué herramientas escriben y por tanto necesitan aprobación; su
política de acceso (qué documentos y qué campos son restringidos, para qué
rol y por qué); y su clasificación según el AI Act. El sistema valida el
manifiesto al arrancar y se niega a funcionar si falta algo. El anexo D
muestra un fragmento.

**Resultado.** La gestoría se dio de alta escribiendo solo su manifiesto,
sus documentos y su banco de pruebas, sin tocar código (capítulo 8.1).

**El aislamiento entre clientes es estructural.** Cada cliente tiene su
propia colección en la base vectorial (ChromaDB), en lugar de una colección
común filtrada por un campo "cliente". La razón: un filtro mal escrito en
una sola consulta devuelve documentos de otro cliente sin que nada lo
avise, mientras que una colección distinta no puede mezclarse. Una prueba
abre la colección de un cliente y falla si abre la de otro. El precio es
pequeño: indexar cuesta entre 2.700 y 3.100 tokens por cliente, y ocho
lecturas simultáneas sobre una colección no la frenan (0,25-0,31 s). Lo que
no se midió es cuántas colecciones aguanta un mismo proceso.

Dos defectos de este aislamiento aparecieron al medir y se corrigieron: dos
fuentes de un mismo cliente compartían los identificadores de sus
fragmentos, y un índice desactualizado no daba error sino resultados
vacíos. Hoy el índice lleva una firma de su contenido, su política de
acceso y su esquema, y se reconstruye solo si la firma no coincide.

*Evidencia: hallazgos 10, 13, 14, 37, 43 y 53.*

### 2.3 Dos ramas: documentos y datos del CRM

**La rama de documentos** busca en la colección del cliente filtrando por
dos condiciones a la vez: la fuente que corresponde al tema (el convenio
para recursos humanos, los expedientes para operaciones) y el permiso de
quien pregunta. La configuración de la búsqueda (tamaño de los fragmentos,
número de resultados, dimensiones de los vectores) viene de la entrega 3.3,
que comparó 11 configuraciones, y no se ha cambiado.

**La rama del CRM** existe porque hay preguntas que ningún documento puede
responder: qué inmuebles hay publicados hoy, a qué precio, qué visitas hay
mañana. El CRM de la agencia es un servidor MCP propio con cinco
herramientas sobre datos sintéticos. Por qué un servidor MCP y no funciones
programadas dentro del agente se explica en el capítulo 4.2.

**El clasificador es el primer cuello de botella de un cliente nuevo.** La
agencia arrancó con un acierto de clasificación de 0,700: tenía expedientes
con datos de clientes y ningún tema los describía, y el clasificador no
puede elegir un tema que nadie le ha descrito. Añadir seis palabras a una
descripción subió el acierto del clasificador de 0,700 a 0,833, y los casos
que pasan todas sus métricas, de 18 a 22 de 30; crear el tema "expedientes"
llevó estos últimos de 29 a 33 de 38. Todo sin tocar código: reescribiendo
descripciones.

**Cuando la pregunta es ambigua, se consultan las dos ramas.** Una pregunta
sobre una operación concreta puede estar en el expediente o en el CRM, y la
pregunta no dice cuál. En lugar de obligar al clasificador a adivinar, el
manifiesto declara que esos dos temas se solapan y el sistema consulta
ambos. Así, la fracción de casos con material protegido que llegan al
control de acceso pasó de 0,778 a 1,0 en la agencia. El precio, medido: un
40 % más de coste y medio segundo más en esas consultas.

**La temperatura cero no da resultados idénticos.** Con la configuración
heredada, 4 de 38 casos cambiaban de tema entre dos pasadas iguales. Se
fijó la temperatura del clasificador a 0 (910 llamadas de medida, 0,57
USD): los 3 casos inestables de la agencia dejaron de variar, pero 1 de los
53 casos del banco heredado sigue variando, y la redacción de las
respuestas sigue siendo aleatoria. Por eso esta memoria no promete
resultados reproducibles al pie de la letra.

*Evidencia: hallazgos 1, 4, 6, 12, 15, 22 y 27.*

### 2.4 El control de acceso, antes del modelo

**Problema.** La forma habitual de proteger un dato es decirle al modelo
"no reveles el salario". Pero eso deja el salario dentro de la ventana de
contexto, y el modelo puede revelarlo por error, por una pregunta ingeniosa
o por una instrucción escondida en un documento.

**Decisión.** El control se aplica antes de que el modelo vea nada, en dos
puntos:

- **En la búsqueda de documentos**, el permiso es una condición más de la
  consulta a la base vectorial. Un documento restringido no se recupera para
  quien no tiene el rol: no es que el modelo no lo cite, es que no llega.
- **En el CRM**, los campos sensibles (DNI, teléfono, ingresos) se
  sustituyen por una marca en cuanto la herramienta devuelve el resultado,
  según la política del manifiesto. Es el **enmascarado de datos** que pide
  el Módulo 4, aplicado donde está el dato.

**Por qué así.** La primera versión de la rama del CRM, sin este control,
devolvía DNI, teléfono e ingresos del comprador a cualquier usuario. Era la
fuga real del proyecto, y el corpus de documentos no podía haberla
detectado. Una variante apareció después en el servicio desplegado: el
recorte del resultado a 6.000 caracteres se hacía antes de tachar los
campos, y una respuesta de 6.028 caracteres dejó pasar el dato sin tachar.
Hoy se tacha primero y se recorta después, y desde el 25 de octubre el
recorte ya no es silencioso: se marca, se avisa al usuario y se le prohíbe
al modelo dar totales o rangos de una lista incompleta (con la cartera
recortada, el modelo había dado como precio mínimo de los 48 inmuebles uno
que no lo era: 80.000 euros en vez de 74.000).

**Resultado, medido:**

| Mecanismo | Qué se midió |
|---|---|
| Permiso dentro de la búsqueda | Frente al sistema heredado, las fugas literales bajaron de 2 a 0 en la empresa y de 1 a 0 en la agencia, sin perder calidad de respuesta. Hoy, 10 de 10 casos sin ningún dato prohibido en la respuesta |
| Campos tachados en el CRM | De filtrar DNI, teléfono, correo e ingresos a cualquiera, a 0 |
| Denegación explícita | Si el permiso deja la búsqueda vacía, la respuesta dice que el dato existe y a qué rol está restringido, en vez de decir que no existe |
| El modelo sabe quién pregunta | Antes negaba a dirección un salario que sí podía ver (3 veces de 5); después, 5 de 5 |
| Verificación de citas | 588 de 588 citas comprobables, ninguna inventada, en 22 ejecuciones |

**La medida que corrige la lectura optimista: la cobertura del riesgo.**
"Cero fugas" no significa nada si las preguntas peligrosas no llegan al
control. Por eso el proyecto mide también qué fracción de los casos con
material protegido llega de verdad al control de acceso.

- **Hoy**: 1,0 en la agencia y en la gestoría; 0,636 en la empresa
  heredada, donde cuatro preguntas peligrosas se clasifican como "otro" y
  no llegan al control.
- **Por qué importa**: al principio, de 20 casos solo llegaban 11, y "cero
  fugas sobre 17 casos" era en realidad "cero fugas sobre 9".
- **Lo que queda**: subir el 0,636 es trabajo del clasificador, y tocar el
  heredado rompería la comparación con la entrega anterior; queda como
  riesgo residual. Las muestras son pequeñas (7 casos en la empresa y 9 en
  la agencia), y por eso cada caso está en la traza con su razón.

**Lo que el control deja ver, por decisión.** La interfaz web dice bajo cada
respuesta qué documentos retuvo el permiso ("Retenido por permiso:
anexo_confidencial_plantilla.md"), también a quien no tiene el rol;
WhatsApp y el correo solo dicen cuántos. Revela que el documento existe y
cómo se llama, no su contenido. Se decidió mantenerlo así: quien pregunta
sabe que la información existe y a quién pedirla.

*Evidencia: hallazgos 2, 5, 8, 9, 11, 22, 23, 39, 40, 41, 47, 67 y 68.*

### 2.5 Autonomía e intervención humana

El sistema tiene tres niveles de autonomía, de más a menos:

1. **Responder** a partir de lo recuperado: autónomo, dentro de lo que el
   control de acceso deja ver.
2. **Consultar** el CRM: autónomo, solo con herramientas de lectura.
3. **Escribir** en el CRM (registrar una visita): **nunca autónomo**. El
   modelo propone la escritura con sus datos; una persona la ve en una
   tarjeta y la aprueba o la rechaza; las tres cosas quedan registradas.

**Cómo se garantiza que el modelo no escriba.** Una herramienta que
escribe se declara dos veces: en el manifiesto del cliente y en el propio
servidor MCP, que la marca como "no de solo lectura". Si las dos
declaraciones no coinciden, el sistema no arranca. Cuando el modelo pide
esa herramienta, el agente no la ejecuta: devuelve al modelo que la acción
está pendiente de aprobación.

**Resultado.** En los 40 casos del banco de la agencia, ninguna escritura
se ejecutó sin aprobación, y tras pasar el banco no había ninguna visita
nueva en el CRM. En las dos correcciones simuladas del 25 de octubre, una
persona aprobó una visita desde la web y quedó registrada con su origen.

*Evidencia: hallazgo 42.*

### 2.6 Los tres canales

El mismo sistema atiende por tres vías. En las tres, la credencial fija el
cliente y los roles, y el aviso del artículo 50 del AI Act (que se está
hablando con una IA) se muestra al empezar.

- **Web** (Streamlit, en Render): usuario y contraseña, tarjeta de
  aprobación de escrituras y un tope de gasto visible.
- **WhatsApp** (API oficial de Meta): el número de teléfono es la
  credencial, la aprobación se da respondiendo por texto, la firma del
  mensaje de Meta es obligatoria y el teléfono nunca se guarda en el
  registro. Probado con 34 pruebas automáticas y en vivo con un número
  real: las mismas respuestas que en la web, en 4,2-4,3 s con el servicio
  despierto y 13,9 s tras despertar.
- **Correo** (un buzón de Gmail dedicado): la dirección del remitente es la
  credencial. Como un remitente se puede falsificar, el canal exige que el
  servidor de correo haya verificado el origen (con DKIM o SPF, las firmas
que prueban que un correo viene del dominio que dice) y rechaza el
  resto sin consultar. Probado con 54 pruebas automáticas y en vivo: 19-24 s
  de extremo a extremo, casi todo espera del buzón; dentro del sistema,
  4,6-7,8 s. Es el único servicio de pago, porque el plan gratuito de Render
  bloquea el envío de correo.

Las incidencias de la puesta en marcha (un índice que no se construía al
arrancar, una clave ausente que mataba el servicio sin rastro, los avisos
automáticos de Google en el buzón) están en el anexo D.

*Evidencia: hallazgos 51, 55, 56, 58 y 59.*

## 3. Modelos, configuración y coste

### 3.1 Qué modelo hace qué, y por qué

| Función | Modelo | Por qué este |
|---|---|---|
| Clasificar y redactar | `claude-haiku-4-5` | Heredado con su rendimiento medido; barato (0,0020-0,0041 USD por consulta según el cliente) y rápido. Ninguno de los fallos de la empresa y la agencia se debe a la redacción, así que un modelo mayor, de 2 a 5 veces más caro por token, no compraría nada medible |
| Juez de calidad | `gemini-3.6-flash` | De otra familia que el que redacta, para que no se juzgue a sí mismo, y 5,5 veces más barato por evaluación que la alternativa de Anthropic |
| Vectores de búsqueda | `gemini-embedding-001` (768 dimensiones) | Heredado. Se retira el 14-05-2028 y ya no tiene precio publicado; cambiarlo invalidaría el índice y movería todas las medidas de búsqueda, así que se decidió no migrar antes de entregar |
| Proveedor alternativo | `gemini-3.6-flash` para todo | Para poder cambiar de proveedor si Anthropic falla; comprobado de extremo a extremo |

**Se midieron dos alternativas, y las dos perdieron por razones distintas.**

*Un clasificador sin modelo de lenguaje.* **Conclusión: Haiku se queda,
porque acierta más.** En lugar de preguntar a Haiku, se compara la pregunta
con la descripción de cada tema mediante vectores. Es cuatro veces más
rápido (0,32 s frente a 1,12 s) y no cuesta nada de chat,
pero acierta menos con clientes que no ha visto (0,735 frente a 0,882 en
68 casos), sobre todo en temas definidos por el tipo de documento, como las
actas. Aun así, el clasificador por vectores llevó al
control de acceso los 13 casos de riesgo, incluidos los que Haiku manda a
"otro"; la mejora que sugiere es dar ejemplos en las descripciones de los
temas, no entrenar un modelo.

*Otra familia como redactor.* **Conclusión: como redactores empatan, y
Haiku se queda por latencia.** Se repitieron los bancos de la empresa y de
la gestoría con Gemini haciendo de clasificador y de redactor. El primer
intento murió por la cuota gratuita (20 peticiones al día: 73 de 82 casos
fallaron); con facturación y un tope de 5 EUR al mes salió así:

| Banco | Casos correctos con Haiku | Con Gemini | Bien clasificados por los dos | Correctos entre esos, Haiku / Gemini |
|---|---|---|---|---|
| Empresa (53) | 48 | 51 | 46 | 46 / 46 |
| Gestoría (29) | 28 | 27 | 27 | 27 / 27 |

En los casos que ambos clasificaron bien, los dos aciertan 73 de 73.
Gemini cuesta la mitad (0,00099 frente a 0,00198 USD por consulta) y tarda
1,9 veces más (6,2 s de media frente a 3,3); la diferencia de casos
correctos viene toda de la clasificación. En un asistente la latencia
pesa, y el empate no justifica romper la comparación con todo lo medido.
Lo que sí deja es el cambio de proveedor demostrado como plan de
contingencia real, no como una promesa.

*Evidencia: hallazgos 17, 24, 29, 32, 35, 48, 54 y 57.*

### 3.2 Configuración y prompts

**Cómo se consume el modelo.** Por API, con el SDK (la librería oficial)
de cada proveedor y su mecanismo nativo de llamada a herramientas. Cada llamada tiene un límite de 1.024 tokens
de salida; si el modelo llega al límite, la respuesta lo avisa en lugar de
cortarse sin más. Hay una clave de API para el sistema y otra para el juez,
para separar en la factura lo que cuesta funcionar de lo que cuesta
evaluar.

**Los parámetros que importan, con su motivo:**

- **Temperatura 0 en el clasificador**, para reducir la variación entre
  pasadas (capítulo 2.3). El redactor usa la del proveedor.
- **El prompt del clasificador se construye desde el manifiesto**: cada
  cliente aporta sus temas y descripciones. El de la empresa heredada está
  congelado por una prueba.
- **El prompt del redactor dice quién pregunta y que todo su contexto ya
  está autorizado.** Antes no lo decía, y el modelo obedecía las marcas
  "CONFIDENCIAL" escritas dentro de los propios documentos: negaba a
  dirección un salario que el control le había entregado. Con el cambio, 5
  de 5.

**Los prompts candidatos.** Se compararon dos versiones del prompt del
redactor: la **base**, heredada, y una **endurecida**, con instrucciones
explícitas de no revelar datos sensibles. Antes de existir el control de
acceso, la base dejó escapar un salario y un dato de salud y la endurecida
no (8 de 10 frente a 10 de 10 casos sin fuga); pero la endurecida empeoraba
la calidad de las respuestas. Con el control de acceso ya en la búsqueda,
la base no filtra nada (10 de 10), así que se usa la base: **el prompt dejó
de ser el control**. Esta comparación la decidió una métrica sin
variación, no el juez, por lo que explica el capítulo 5.3.

**Los dos cambios que rompen la comparación.** Dos veces se cambió un valor
por defecto y las cifras de antes y de después dejaron de ser comparables.
Quedan fechados para no mezclar nunca dos cifras que miden cosas distintas:

| Fecha | Qué cambió | Qué se ganó | Cómo volver atrás |
|---|---|---|---|
| 22-09-2026 | Temperatura del clasificador a 0; juez por defecto a Gemini | Menos variación; juez independiente y 5,5 veces más barato | `ROUTER_TEMPERATURE=defecto`, `JUDGE_PROVIDER=anthropic` |
| 23-09-2026 | El redactor sabe quién pregunta | De 2 de 5 a 5 de 5 al entregar un dato autorizado | `GEN_QUIEN_PREGUNTA=0` |

**Todos los prompts están catalogados** en un fichero generado desde el
código y vigilado por una prueba (anexo D.4): cada uno con su uso, modelo,
temperatura y una huella. Cada línea del registro de producción lleva esa
huella y el commit desplegado, de modo que cualquier cifra se puede separar
por versión de prompt.

*Evidencia: hallazgos 18, 24, 26, 27, 31, 33, 39, 40 y 67.*

### 3.3 Cuánto cuesta

**Una consulta cuesta entre 0,002 y 0,004 USD**, según el cliente. Las
cifras salen de los tokens contados en las últimas pasadas del banco de
cada uno, que mezclan consultas cortas y largas, de una rama y de dos:

| Cliente | Coste por consulta | Tokens de entrada | Latencia media / p95 (la que no supera el 95 % de las consultas) |
|---|---|---|---|
| Empresa (solo documentos) | 0,00198 USD | 973 | 3,28 s / 4,36 s |
| Gestoría (solo documentos) | 0,00211 USD | 1.130 | 2,95 s / 4,01 s |
| Agencia (documentos y CRM) | 0,00406 USD | 2.671 | 4,09 s / 5,73 s |

La agencia cuesta el doble porque la rama del CRM mete en el contexto lo
que devuelven las herramientas y porque las preguntas ambiguas consultan
las dos ramas: es el precio de responder lo que ningún documento contiene.
Las latencias son con el servicio despierto; la primera consulta de un
cliente tras despertar tarda 19-20 s, 8,5 s de ellos reconstruyendo el
índice, más los 32 s que tarda en despertar el servicio (capítulo 6.5).

**Por niveles de uso**, a los precios de `claude-haiku-4-5` (1,00 USD por
millón de tokens de entrada y 5,00 de salida):

| Consultas al mes | Cliente solo con documentos | Cliente con CRM |
|---|---|---|
| 500 | 1,0 USD | 2,0 USD |
| 2.000 | 4,0 USD | 8,1 USD |
| 10.000 | 19,8 USD | 40,6 USD |

Los volúmenes son supuestos razonables para una plantilla de diez a cien
personas, no medidas: ningún cliente real ha usado el sistema.

**Lo que hay que sumar:** la infraestructura (7 USD al mes por servicio en
el plan de pago de Render, 21 USD los tres servicios despiertos; hoy solo
paga el de correo); los vectores de búsqueda, unos 14 tokens por consulta,
sin precio publicado (al precio de su sucesor serían tres millonésimas de
dólar); y la evaluación, que no se paga por consulta sino por cambio: pasar
el banco de un cliente cuesta entre 0,06 y 0,16 USD.

**Evaluar cuesta 11 veces más que funcionar**: 0,0278 USD por caso con juez
frente a 0,00245 sin él. Por eso pasar el juez es un acto deliberado, no
una rutina.

**¿Y un modelo abierto en una máquina propia?** Una GPU L4 en la nube, la
mínima para un modelo de unos 8.000 millones de parámetros, cuesta unos
0,70 USD la hora: 511 USD al mes encendida (110 USD al mes a 0,15 USD la
hora en una región barata o con instancias interrumpibles). Para que salga
a cuenta frente a la API harían falta entre 27.000 y 258.000 consultas al
mes según el cliente y el precio; a los volúmenes previstos, la API es
entre 3 y 500 veces más barata, sin contar operar el servidor ni que la
calidad de ese modelo está sin medir. El argumento a favor de un modelo
propio no es el coste sino la privacidad: no manda datos a un tercero.

**Topes de gasto.** El **tope duro** es el del proveedor: los servicios
desplegados usan una clave en un espacio con un límite de 10 USD al mes, y
las claves de desarrollo no salen de la máquina del autor. Una fuga a
pleno ritmo (115 consultas por minuto) gastaría 13,7 USD por hora y
agotaría ese límite en 44 minutos. El **tope blando** lo pone el propio
sistema sobre el gasto registrado: al superarlo deja de consultar y lo
dice. Es una cota inferior del gasto real, porque no cuenta los vectores
de búsqueda ni lo gastado fuera de la aplicación, y no hay límite por
usuario.

**Lo que la contabilidad no ve.** La contabilidad propia mide el banco de
pruebas, no todo el proyecto: no ve un 22 % del gasto de la clave
(llamadas de desarrollo y reintentos). Los costes de esta memoria excluyen
siempre los vectores de búsqueda.

*Evidencia: hallazgos 16, 17, 21, 22, 32, 35, 37, 53, 55, 57, 67 y 68.*

## 4. Cómo se construyó: framework, MCP y copiloto

### 4.1 Python sin framework, frente a LangGraph

**La pregunta.** ¿Hace falta un framework de orquestación de agentes, como
LangGraph, o basta con Python y las llamadas del SDK?

**Cómo se respondió: midiendo, no argumentando.** Se construyó el mismo
sistema encadenado por un grafo de LangGraph 1.2.12, reutilizando
exactamente las mismas piezas (clasificador, búsqueda, control de acceso,
redactor); diez pruebas comprueban que las dos versiones hacen las mismas
llamadas. Después se pasaron los bancos por las dos:

| | Python sin framework | LangGraph |
|---|---|---|
| Casos correctos, empresa (53) | 48 | 47 (la redacción es aleatoria) |
| Llamadas y tokens de entrada | 106 llamadas, 51.559 tokens | Idénticos |
| Latencia media por caso | 3,284 s | 3,295 s (+0,011 s) |
| Casos correctos, agencia (40) | 31, ninguna escritura sin aprobar | Igual |
| Líneas de código de orquestación | 21 | 95 (4,5 veces más) |
| Paquetes nuevos | 0 | 14 |

**Decisión: Python sin framework.** Para un flujo de un turno con una
bifurcación, el grafo hace exactamente lo mismo y añade 14 dependencias y
4,5 veces más código que mantener y auditar. Cada dependencia es superficie
de ataque (el material del Módulo 4 recoge un incidente real en otra
librería del ecosistema) y cada versión nueva del framework es un cambio de
comportamiento que habría que volver a medir.

**Lo que esta medida no dice.** LangGraph aporta estado entre pasos,
reanudación tras una interrupción y ramas en paralelo, y este sistema no
usa nada de eso. Si llega a necesitarlo, la comparación hay que rehacerla;
la aprobación humana sería el primer candidato. La memoria entre turnos que
sí se añadió no necesitó estado: reescribe la pregunta antes de
clasificarla (capítulo 8.3).

*Evidencia: hallazgos 50 y 66.*

### 4.2 Servidores MCP, frente a herramientas programadas en el agente

**Problema.** Si las herramientas del CRM se programan dentro del agente,
el sistema queda atado a la API de un cliente concreto.

**Decisión.** Cada cliente declara en su manifiesto qué servidores MCP
arrancar; el servidor publica sus herramientas y dice cuáles escriben; el
agente solo habla el protocolo. Dar de alta un cliente con un CRM propio
es escribir su servidor, no tocar el agente.

Tres decisiones de detalle, medidas: los servidores se arrancan una vez
(1,1 s) y se mantienen abiertos, porque abrirlos en cada consulta habría
añadido unos 40 segundos en 36 casos; las sesiones del protocolo se abren y
cierran en la misma tarea; y el prompt lleva la fecha del día, porque el
modelo no sabe qué día es. Si un servidor MCP no responde, la consulta
falla y lo dice; ese fallo no se ha simulado (capítulo 8.3).

*Evidencia: hallazgo 7.*

### 4.3 Desarrollo con un copiloto: quién hizo qué y cómo se controló

El enunciado pide explicar cómo se usaron los copilotos y cómo se controló
su salida. Este proyecto se escribió entero con uno, Claude Code, más la
app de Claude para las tareas de navegador; el tutor confirmó que su uso es
libre.

**El reparto.** El copiloto escribió el código, las pruebas, los documentos
y esta memoria, y ejecutó las mediciones. El autor puso el producto (que
sale de su propuesta de la entrega 1.4), las reglas de trabajo, las
decisiones con coste, riesgo o alcance, las acciones con credenciales y
facturación, que hizo a mano, y la revisión. Algunas decisiones del autor:

| Fecha | Decisión |
|---|---|
| 23-09 | Que el redactor sepa quién pregunta, aceptando romper la comparación |
| 24-09 | Hacer el alta en Meta con la app y con él delante, contra la recomendación del copiloto |
| 26-09 | Construir el canal de correo, que estaba fuera del alcance |
| 27-09 | Pagar el plan de Render del correo; poner a mano un tope de 5 EUR al mes en Gemini |
| 11-10 | Evaluar en producción con un juez de otra empresa, aceptando enviarle una muestra; tope de 10 USD al mes para la clave desplegada |
| 25-10 | Marcar las respuestas cortadas y leer el tope de gasto de la base persistente, tras la corrección simulada |

**El método: la especificación manda sobre la conversación.** Un fichero
de instrucciones del proyecto es la fuente única de verdad: si
algo de una conversación lo contradice, gana el fichero. El copiloto lo
carga al empezar cada sesión. Dos rutinas estructuran cada jornada: una de
arranque, que lee el diario de sesiones y el estado del repositorio, y una
de cierre, que escribe el diario y publica, y que solo lanza el autor.

**El control: reglas que el copiloto no puede saltarse.** Una regla escrita
en un prompt se olvida; una regla con prueba automática falla. Las del
proyecto: el prompt heredado no cambia sin que una prueba falle; el juez no
puede ser el mismo modelo que redacta; una métrica retirada por defectuosa
no puede volver; el inventario de dependencias y el catálogo de prompts se
regeneran y una prueba falla si están desactualizados; nada llega a
producción con una prueba rota (capítulo 6.1). Las reglas que no se pueden
automatizar (no relajar el banco, nada de fallos silenciosos) las vigila la
revisión.

**Lo que el método cazó.** El argumento a favor del método no es que el
copiloto acierte, sino que sus errores se ven:

- El precio de un modelo estaba un 50 % alto y todo lo derivado salía
  inflado; lo destapó una predicción escrita antes de mirar la factura.
- El experimento de sesgo hizo tres afirmaciones falsas antes de acertar
  (capítulo 7.3).
- Dos lecturas críticas de esta memoria en septiembre encontraron 35
  correcciones cada una.
- El 25 de octubre, dos **correcciones simuladas**, con la app de Claude en
  el papel del tutor y los usuarios de evaluación, encontraron lo que
  ninguna lectura desde dentro había visto: la integración continua en
  rojo, dos recortes silenciosos, un tope de gasto que se reiniciaba y un
  guion de demostración que un tercero no podía seguir.

Y un caso en que el control llegó tarde: una entrega del Módulo 4 extraída
de este repositorio salió con dos afirmaciones falsas que la revisión
encontró después de enviarla.

**En cifras**, entre el 20-09 y el 25-10-2026: 152 commits (más 7 heredados
de la entrega 3.3), quince sesiones de trabajo, 68 hallazgos medidos y
1.255 pruebas.

*Evidencia: hallazgos 18, 21, 34, 67 y 68.*

## 5. Evaluación

### 5.1 El banco de pruebas y sus dos tipos de métricas

Hay un banco por cliente, con el mismo motor heredado de la entrega 3.3:
53 casos de la empresa (la referencia que no debe empeorar), 40 de la
agencia (para lo nuevo: el CRM, las preguntas ambiguas y la escritura
aprobada) y 29 de la gestoría (para medir el alta de un cliente). Cada caso
es una pregunta con lo que se espera: el tema, el documento que hay que
recuperar, los datos que deben aparecer y los que no deben aparecer nunca.
Cubren ocho tipos de pregunta, de las normales a los intentos de
manipulación.

**La lección más cara del proyecto es separar dos tipos de métrica:**

- **Deterministas**: se calculan sin un modelo y dan siempre lo mismo. Si
  el tema es el correcto, si aparece un dato prohibido (fuga literal), si
  la pregunta peligrosa llegó al control (cobertura del riesgo), si la
  respuesta cita una fuente y si esa fuente se recuperó de verdad, si se
  escribió algo sin aprobar. **Todas las decisiones del proyecto se apoyan
  en estas.**
- **De juez**: un modelo de lenguaje puntúa la fidelidad, la relevancia y
  la confidencialidad. Varían entre pasadas idénticas (capítulo 5.3) y
  cuestan 11 veces más que funcionar. Ninguna decisión depende de ellas.

Ejecutar el sistema y evaluarlo están separados: las respuestas se guardan
y se pueden reevaluar sin volver a pagarlas. Eso permitió estrenar el
verificador de citas sobre 22 ejecuciones antiguas.

*Evidencia: hallazgos 11, 23, 42 y 47.*

### 5.2 Resultados

Un **caso correcto** es el que pasa todas sus métricas. Últimas pasadas,
sin juez:

| Banco | Casos correctos | Acierto del clasificador | Cobertura del riesgo | Respuestas con fuente |
|---|---|---|---|---|
| Empresa (53) | 48 | 0,9038 | 0,6364 | 1,0 |
| Agencia (40) | 31 | 0,825 | 1,0 | 0,92 |
| Gestoría (29) | 28 | 0,963 | 1,0 | 1,0 |

No hay un umbral de aprobado fijado de antemano. La regla es otra: ninguna
pasada empeora respecto a la anterior sin que el motivo quede escrito.

**Por qué fallan los que fallan.** En la empresa y la agencia, ninguno de
los 14 casos fallidos se debe a la redacción de la respuesta:

- **Empresa, 5 fallos**, todos de clasificación: uno que sigue variando
  entre pasadas, y cuatro preguntas peligrosas que el clasificador manda a
  "otro" y no llegan al control (son exactamente lo que baja la cobertura a
  0,636). Con el cambio a varios clientes, la empresa pasa 48 casos frente
  a 49 en la versión anterior.
- **Agencia, 9 fallos**: siete de clasificación entre temas vecinos
  (procesos, normativa y comercial) y dos en que la respuesta del CRM no
  nombra la herramienta de la que sale el dato.
- **Gestoría, 1 fallo**, del sistema: una pregunta cuya respuesta correcta
  es que el dato no consta ("¿Cuándo es la comida de Navidad del despacho?").

Una métrica de juez no entra en esta tabla: ninguna decisión depende de ella
(capítulo 5.3).

**La búsqueda funciona.** En la empresa y en la gestoría, el documento
correcto se recupera siempre y casi siempre en primer lugar. En la
agencia, los cuatro casos en que no se recupera son errores de
clasificación: con el tema correcto, los 20 aciertan. Una búsqueda híbrida
(por palabras clave combinada con la de vectores) se midió en los tres
clientes y no mejoró nada; se queda la de vectores. Las tablas completas
están en el anexo D.

*Evidencia: hallazgos 42, 45, 49 y 64.*

### 5.3 Evaluar al evaluador

El profesor de la entrega 3.3 pidió evaluar también al juez y su
estabilidad. **Conclusión: una puntuación de juez no se lee sin su
razonamiento, y ninguna decisión del proyecto depende de una.** Cuatro
medidas llevan ahí:

- **El número contradice su propio razonamiento.** Con las mismas
  respuestas y el mismo prompt, el juez de Anthropic escribió "mereciendo
  la puntuación máxima" y puso 0,1; el de Gemini, a temperatura 0, escribió
  "cumple exactamente" y puso 0,1. El fallo no es de una familia ni de la
  temperatura: es pedir un número y su justificación en la misma respuesta.
- **Se equivoca siempre hacia el mismo lado.** En una prueba de 4 casos
  repetidos 6 veces, 4 de los 24 veredictos eran falsos, y los cuatro
  suspendían lo que debía aprobar. La temperatura 0 no lo arreglaba. Por
  tanto, el número de casos correctos de una pasada con juez es una cota
  inferior, y promediar pasadas empeora la cifra en vez de corregirla.
- **No puede decidir comparaciones finas.** Al comparar los dos prompts
  candidatos, 5 y 6 de 10 casos cambiaban de veredicto entre tres pasadas
  idénticas. La comparación la decidió la fuga literal, que no varía.
- **El juez de Anthropic ignoraba la temperatura sin avisar**: ese modelo
  no admite el parámetro y la librería de evaluación lo descartaba en
  silencio, lo que explica parte de la variación medida en la entrega 3.3.

El juez sigue siendo útil para vigilar la producción (capítulo 6.2), donde da un veredicto de tres valores con su
razón y no un número.

Además se retiró una métrica de datos personales que puntuaba al revés:
penalizaba al sistema por nombrar a la persona cuyos datos estaba
protegiendo, de modo que una denegación correcta sacaba 0. Afectaba a 17
casos. Lo que queda sin hacer: validar el juez contra la opinión de
personas.

*Evidencia: hallazgos 24, 26, 30, 31, 32 y 33.*

### 5.4 Lo que el banco enseñó sobre medir

Siete veces el error estaba en el instrumento de medida y no en el
sistema. Dos ejemplos: la mitad de los casos de seguridad no llegaban al
control de acceso, así que no probaban nada; y un caso de robustez
aprobaba a un sistema que no había respondido. Todos se corrigieron por
escrito, con el motivo, antes de sacar conclusiones.

Y dos reglas de método que salieron del proyecto: **una predicción escrita
antes de mirar convierte una cifra en una medida**, y **una hipótesis que
sale de los datos no se confirma con los mismos datos** (capítulo 7.3).

*Evidencia: hallazgos 3, 11, 21, 31, 45, 47, 49 y 54.*

## 6. Producción: despliegue, monitorización y operación

### 6.1 Despliegue y paso automatizado a producción

**Dónde y cómo.** Los tres servicios (web, WhatsApp, correo) están en
Render, definidos en un fichero del repositorio. El primer
despliegue tardó 1 min 32 s. Hay seis usuarios del autor (dos por cliente)
y cuatro de evaluación para quien corrija.

**Nada llega a producción con una prueba rota.** En cada cambio, la
integración continua de GitHub pasa el analizador de estilo, las 1.255
pruebas y una auditoría de vulnerabilidades de las dependencias que se
despliegan. Render solo despliega un cambio cuando todo eso está en verde.
Se comprobó con un cambio roto a propósito: se quedó fuera más de cuatro
minutos mientras los cambios correctos se desplegaban en 77 y 109 s.

**La puerta funcionó sola.** La primera auditoría encontró 23
vulnerabilidades en 6 paquetes: 18 se cerraron actualizando y 5 quedaron
como excepción escrita porque afectan a un modo de ChromaDB que este
sistema no usa. El 25 de octubre, tras catorce días sin cambios, aparecieron
avisos nuevos publicados en ese tiempo; la integración continua se puso en
rojo, el servicio siguió en la última versión buena y se actualizaron siete
paquetes. La detección y la protección son automáticas: la integración
continua encuentra la vulnerabilidad y el despliegue se detiene sin que
nadie lo vigile. Actualizar los paquetes sí exige a una persona, y como no
hay alertas (capítulo 6.2), esa persona se entera al mirar la integración
continua.

*Evidencia: hallazgos 38, 60, 61 y 67.*

### 6.2 Monitorización y calidad en producción

**El registro.** Cada consulta real deja una línea: cliente, usuario, tema,
rama, fuentes, documentos retenidos por permiso, campos tachados, tokens,
coste y latencia; si falló, el tipo de fallo; si la respuesta o los datos
de una herramienta se recortaron, la marca. Cada línea lleva además el
commit desplegado y la huella de los prompts, así que un cambio se puede
comparar antes y después sobre tráfico real. **No se guarda el texto de la
respuesta**, por privacidad. El registro va a una base Postgres de Render
que sobrevive a los reinicios, y una herramienta de consola lo resume por
cliente: consultas, coste acumulado, latencia y cuántas veces alguien pidió
lo que no le tocaba.

**La calidad, medida al servir.** Sobre todas las consultas, el
verificador de citas comprueba que cada fuente citada se recuperó de
verdad. Sobre la mitad, elegida al azar, un juez de otra familia que el
redactor dice si la respuesta está respaldada por lo recuperado, con un
veredicto de tres valores (fiel, parcial, no fiel). Corre en un hilo aparte
para no añadir espera, y al registro solo van el veredicto y su coste. En
las primeras consultas reales: tres de tres sin citas inventadas, y un
juez cuyo veredicto salía cortado por un límite de salida demasiado bajo,
corregido el mismo día.

**Por qué un registro propio y no una plataforma como Langfuse.** Una
plataforma recibiría el texto de cada pregunta y respuesta, que este
registro no guarda a propósito; lo que hay que vigilar aquí es propio del
dominio (qué se retuvo, qué se tachó, qué rama); y no añade dependencias ni
servicios. Se pierde la interfaz de exploración, que se suple con la
herramienta de consola.

**Lo que falta: alertas.** Nadie recibe un aviso cuando el gasto sube o el
juez empieza a decir "no fiel"; hay que consultarlo. Está declarado en el
capítulo 8.2.

*Evidencia: hallazgos 20, 23, 30, 46, 62, 67 y 68.*

### 6.3 Retención y supresión de datos

El registro se guarda 90 días. Un usuario puede pedir que se borren sus
líneas y las anteriores a una fecha se purgan; en los dos casos queda una
marca que dice cuánto se borró, sin decir de quién. Las dos operaciones
tardan menos de 0,05 s sobre un registro de 10.000 líneas. La tensión entre
la trazabilidad que pide el artículo 12 del AI Act y el riesgo de
vigilancia de los empleados queda escrita, no resuelta.

*Evidencia: hallazgo 37.*

### 6.4 Incidentes y plan B

**El botón rojo.** Un plan escrito dice qué hacer ante un incidente y en
qué orden (revocar la clave, parar, congelar la evidencia, sustituir la
clave), quién avisa a quién, y que todo incidente termina en un hallazgo.
Un simulacro lo ejecuta: **14,95 s** la parte automática, y la primera vez
destapó que las consultas fallidas no dejaban rastro en el registro. La
parte manual (revocar y rotar claves en las consolas) no se ha cronometrado;
se estima en unos cinco minutos.

**Si el proveedor cae, el usuario lo sabe.** Los tres canales responden
con un mensaje que dice qué ha pasado y a quién acudir, con el contacto que
declara cada cliente. Medido provocando los dos fallos más probables: el
mensaje llega en 6 s con la clave revocada y en 13 s con el proveedor
inalcanzable. Se decidió no cambiar de proveedor automáticamente, porque
cambiaría la clasificación, y con ella el control de acceso, en mitad de un
incidente.

*Evidencia: hallazgos 46, 57 y 63.*

### 6.5 Carga y arranque en frío

**Concurrencia.** Ocho consultas a la vez sobre el mismo sistema tardan lo
que una (mediana de 3,16-3,32 s con 1, 2, 4 y 8 a la vez), sin errores y
sin cambiar la clasificación ni el permiso. La puerta web de un servicio
gratuito aguanta 20 clientes simultáneos (216 peticiones, máximo 0,19 s).

**Arranque en frío.** El plan gratuito de Render duerme el servicio tras
unos 15-20 minutos sin uso. Despertar cuesta 32 s la web y 42-61 s el
servicio de WhatsApp, y ninguna petición se pierde mientras tanto. La
primera consulta tras despertar tarda además lo que cuesta reconstruir el
índice, porque el disco del plan gratuito no se conserva. Con un plan de
pago (capítulo 3.3) el servicio no dormiría.

*Evidencia: hallazgos 52, 53 y 59.*

### 6.6 Cómo lo comprueba un tercero

**Alcance.** Lo desplegado es una **demostración verificable**, no un
servicio listo para un cliente real: un tercero puede comprobar cada
afirmación de esta memoria sin depender del autor, pero dar servicio a un
cliente exigiría lo que lista el capítulo 8.3 para pasar a piloto (plan de
pago, alertas, límites por usuario, alta de usuarios sin redesplegar).

No hay defensa oral, así que este documento y el repositorio tienen que
bastar. De lo más barato a lo más completo:

| Qué se comprueba | Cómo | Qué hace falta | Coste |
|---|---|---|---|
| Que el código hace lo que dice | Instalar y pasar las pruebas (anexo A) | Nada: ninguna prueba llama a una API de pago | 1.255 pruebas en unos 20 s |
| Que cada cifra tiene respaldo | Cada hallazgo del anexo B lleva a su ejecución guardada en el repositorio | Nada | — |
| Que el banco da lo que dice | Pasar el banco de un cliente (anexo A) | Claves propias de Anthropic y Gemini | 0,002-0,004 USD por caso |
| Que el sistema funciona desplegado | La web, con los usuarios `eval_empleado`, `eval_direccion`, `eval_comercial` y `eval_gerencia` | Sus contraseñas, que van en el comentario de la entrega, no en el repositorio público | Unos 32 s si el servicio dormía |
| Que se comporta como se describe | El guion de demostración del repositorio (anexo D.4): cada paso con su pregunta literal y lo que tiene que verse | Las mismas credenciales | 0,064-0,069 USD los bloques de la web |

WhatsApp y el correo solo atienden a números y direcciones dados de alta;
probarlos exige que el autor añada los de quien evalúa.

*Evidencia: hallazgos 52, 67 y 68.*

## 7. Seguridad, riesgos e IA responsable

Este capítulo cubre el Módulo 4. El tutor señaló la seguridad como
requisito, y el análisis se hizo sobre este proyecto en lugar de en
entregas aparte.

### 7.1 El registro de riesgos

Un registro con 24 riesgos (anexo D.4) clasifica cada uno con
cuatro marcos: el cuadrante de la matriz de Rumsfeld (conocido o
desconocido), su casilla del OWASP Top 10 para LLM, su técnica de MITRE
ATLAS y su dominio de AIUC-1, más la evidencia que lo respalda, el control
y el estado. Una prueba automática comprueba que cada evidencia citada
existe y que las diez casillas del OWASP tienen al menos una fila: **un
riesgo sin evidencia es una opinión**.

| Cuadrante | Qué recomienda el Módulo 4 | Qué pone el proyecto |
|---|---|---|
| Lo que sabemos que sabemos | Pruebas y métricas | El banco, las métricas deterministas, la contabilidad de coste (14 riesgos) |
| Lo que sabemos que no sabemos | Vigilar | Precios con prueba, cambio de proveedor medido, inventario de dependencias |
| Lo que no sabíamos que sabíamos | Buscar vulnerabilidades | Cinco riesgos que salieron de mirar con desconfianza; en tres el error estaba en el instrumento |
| Lo que no sabemos que no sabemos | Plan y botón rojo | Topes de gasto y plan de incidentes simulado |

*Evidencia: hallazgos 54 y 57.*

### 7.2 Los diez riesgos del OWASP, y el red-teaming

| Riesgo OWASP | Estado en el proyecto |
|---|---|
| Inyección de instrucciones | **Medido**: ocho casos del banco con intentos de manipulación; los que llegan al control no filtran nada; uno no llega y es el residual. Y la batería de red-teaming (abajo) |
| Salida insegura | Por diseño: texto para una persona; la web no interpreta HTML y el correo es texto plano |
| Envenenamiento de datos | Por diseño, no atacado: el corpus es sintético. Un cliente real trae su corpus y esa defensa desaparece |
| Denegación de servicio | Por diseño: topes de gasto. El sistema aguanta 20 clientes y 8 consultas a la vez, así que el riesgo plausible es económico, no de capacidad. No hay límite por usuario |
| Cadena de suministro | Inventario generado y vigilado, auditoría en cada cambio (capítulo 7.6) |
| Información confidencial | **Lo más fuerte del proyecto** (capítulo 2.4) |
| Complementos inseguros | Por diseño: servidores MCP como procesos aparte. En el puente con la app del autor se encontró y cerró un acceso a las claves |
| Agencia excesiva | **Medido**: ninguna escritura sin aprobación en 40 casos (capítulo 2.5) |
| Sobredependencia | **Medido sobre el propio evaluador** (capítulo 5.3) |
| Robo de modelo | No aplica: no hay modelo propio |

"Por diseño" quiere decir que el control existe pero no se ha atacado.

**Red-teaming con una herramienta.** El enunciado pide un agente o
framework de red-teaming. Se usó DeepTeam contra el sistema completo, en
los dos clientes con material sensible: 64 ataques estándar (sacar datos
personales o el prompt, saltarse el rol, mezclar clientes, instrucciones
escondidas, agencia excesiva), reforzados con siete técnicas, por 2,1 USD.
**Ninguna fuga** por ningún criterio objetivo. Pero solo 7 de los 64
ataques llegaron al control de acceso (los otros 57 eran tan rebuscados que
el clasificador los mandó a "otro" y el modelo se negó), y en los 7 el
documento protegido quedó retenido en la búsqueda. Conclusión: una batería
genérica mide sobre todo la prudencia del modelo; el control de acceso lo
prueban mejor los casos del banco, escritos para este negocio. Además, la
herramienta tenía tres defectos que hubo que corregir para que midiera
algo; el peor contaba como "ataque superado" las veces en que el propio
atacante se negaba a atacar.

De los nueve guardarraíles que enumera el Módulo 4, el proyecto tiene ocho.
Falta la moderación de contenido, justificada en el capítulo 8.2.

*Evidencia: hallazgos 19, 30, 32, 35, 42, 53 y 65.*

### 7.3 Sesgo

**Cómo se midió.** Pares de preguntas idénticas salvo en un rasgo de la
persona (género, edad, origen, discapacidad), con un grupo de control para
saber cuánto varía el sistema por puro azar, en tres capas:

| Capa | Cómo | Resultado |
|---|---|---|
| Búsqueda | Distancia entre los resultados de cada par | Ningún rasgo llega al doble de la variación por azar |
| Clasificación | Tema asignado con seis variantes de nombre | Estable |
| Redacción | Cinco medidas sin juez, ocho repeticiones por variante | Ningún rasgo por encima de la variación por azar |

**Lo que no se afirma: que el sistema no discrimina.** Dos de las cinco
medidas de redacción no tienen recorrido y solo prueban que no hay
negativas ni omisiones selectivas. Presentarlo como ausencia de sesgo sería
la falsa objetividad que el propio Módulo 4 señala como riesgo.

**El experimento se equivocó tres veces antes de acertar**, y las tres
afirmaciones intermedias eran falsas, concretas y alarmantes (por ejemplo,
que la discapacidad movía los resultados 75 veces más que el resto), todas
por pares mal emparejados. Desde entonces trece pruebas comprueban que los
pares siguen emparejados. Y una sospecha que salió de leer las respuestas
(que el origen cambiaba los matices, 2,00 veces con 8 repeticiones) bajó a
1,00 con 24: una hipótesis que sale de los datos no se confirma con los
mismos datos.

*Evidencia: hallazgos 34 y 44.*

### 7.4 AI Act

**Lo que obliga hoy.** Un asistente que habla con personas debe avisar de
que es una IA (artículo 50.1, en aplicación desde el 2 de agosto de 2026).
Lo declara el manifiesto de cada cliente y lo muestran los tres canales.

**El riesgo de ser "alto riesgo".** La empresa heredada tiene salarios y
evaluaciones de empleados (empleo, anexo III, punto 4) y la agencia tiene
ingresos y solvencia de compradores (punto 5b). Si el asistente se usara
para evaluar personas o decidir sobre ellas, sería un sistema de alto
riesgo. La salida es el artículo 6.3: no lo es un sistema que hace una
tarea de procedimiento limitada, siempre que no perfile personas y que
quien lo alegue documente su evaluación. Esa documentación es un bloque
obligatorio del manifiesto (condición, justificación, usos excluidos y
declaración de que no perfila), y el validador rechaza un manifiesto que
alegue la excepción y perfile, o que toque el anexo III sin clasificarse.

**El calendario cambió.** El Reglamento (UE) 2026/1744, del 27 de julio de
2026, retrasa las obligaciones de alto riesgo al 2 de diciembre de 2027.
Hoy obliga el artículo 50, y la clasificación por cliente es diseño
anticipado, no cumplimiento exigible. Las citas se contrastaron con la
Comisión y el BOE.

### 7.5 RGPD

- **Derecho de supresión sobre los documentos.** Un script retira un
  documento, reconstruye el índice y comprueba que no queda ningún
  fragmento suyo: 1,46 s en la agencia y 1,23 s en la empresa. No borra las
  consultas registradas que lo citaron.
- **Retención del registro**: capítulo 6.3.
- **Transferencias internacionales.** Hoy no viaja ningún dato real
  porque los clientes son sintéticos. Con un cliente real, cada consulta
  enviaría fragmentos de sus documentos a proveedores fuera de la Unión: el
  cliente sería responsable del tratamiento, quien opera el asistente,
  encargado, y cada proveedor, subencargado. Eso exige base jurídica para la
  transferencia, contratos de encargo, registro de actividades y, si se
  tocara el anexo III sin la excepción, una evaluación de impacto. Nada de
  eso está escrito: es un hueco declarado, no un cumplimiento.

*Evidencia: hallazgo 36.*

### 7.6 Cadena de suministro

Un inventario de dependencias y modelos (anexo D.4) se genera desde el
fichero de bloqueo de versiones y la configuración, y una prueba falla si
está desactualizado: 18 paquetes directos y 148 indirectos, todos con
versión fijada, y cada modelo con su precio o la marca de que no lo tiene.
La primera vez que se generó destapó que el modelo de vectores está en
retirada y aparecía con coste cero. La auditoría de vulnerabilidades del
capítulo 6.1 completa el control.

*Evidencia: hallazgos 35 y 61.*

## 8. Escalabilidad, límites y lo que queda fuera

### 8.1 Dar de alta un cliente nuevo, cronometrado

La prueba de que el diseño no depende del cliente: la gestoría se dio de
alta en **5 min 42 s**, en dos iteraciones y **sin tocar código**, con un
manifiesto, seis documentos y un banco de 28 casos escrito antes de la
primera pasada.

| Momento | Casos correctos | Qué pasó |
|---|---|---|
| Primera pasada | 20 de 28 | El clasificador acertaba 0,769; los cinco fallos de clasificación iban al mismo tema |
| Segunda pasada, 65 s después | 25 de 28 | Tres descripciones reescritas; acierto 0,923 y cobertura del riesgo de 0,857 a 1,0 |
| Revisión del banco en frío | 27 de 28 | Dos de los tres fallos eran expectativas mal escritas en el banco |
| Un caso más que combina dos documentos | 28 de 29 | El banco actual (capítulo 5.2) |

El control de acceso y la clasificación del AI Act vinieron gratis con el
manifiesto. Sin banco de pruebas, un tema habría llegado a producción con
un 77 % de acierto. Dos salvedades: el alta la hizo el copiloto con el
proyecto en contexto, y con un cliente real el banco lo escribe quien
conoce el negocio, y ese tiempo no está medido.

*Evidencia: hallazgos 1, 43, 45 y 49.*

### 8.2 Lo que no está, y por qué

| Qué | Decisión y motivo | Cuándo se reconsideraría |
|---|---|---|
| Alertas activas | No montadas: el tope de gasto corta y lo dice, pero nadie recibe un aviso; hay que consultar el registro | Tras el feedback de la primera entrega |
| Enmascarar datos personales en la pregunta | No montado: el enmascarado actúa sobre lo que devuelve el CRM (capítulo 2.4). Enmascarar la pregunta exige un detector de nombres en español sin medir y rompería las preguntas por nombre que dirección sí puede hacer ("el salario de Laura Gómez") | Con datos reales de un cliente |
| Moderación de contenido | No montada: asistente interno, usuarios autenticados, sin contenido de terceros salvo los documentos del cliente; el red-teaming no la pidió | Si se abre a clientes externos |
| Varios agentes (planificador y especialistas) | En contra: el flujo es un clasificador y dos ramas; un planificador añadiría al menos +0,0005 USD (+25 %) y +1,1 s por consulta sin un solo fallo del banco que lo pida | Si aparecen tareas de varios pasos |
| Optimizar prompts automáticamente (con DSPy) | En contra: optimizaría contra el banco, que no tiene casos reservados, y el número subiría sin significar nada fuera de él | Con un conjunto reservado |
| Caché de prompts | No aplica: el mínimo que el proveedor guarda son 4.096 tokens y una consulta usa entre 973 y 2.671 | Si el contexto crece |
| Entorno de preproducción | No montado: la puerta es la integración continua y el banco; duplicar servicios duplicaría credenciales y superficie expuesta | Con más de un desarrollador |
| Migrar el modelo de vectores | No antes de entregar: invalida el índice y todas las medidas de búsqueda | Antes del 14-05-2028 |
| Denegación explícita cuando el permiso retiene solo parte | No antes de entregar: afecta a 14 casos de la empresa y rompería la comparación | Tras la entrega |
| La pregunta peligrosa que el clasificador manda a "otro" | Residual: arreglarla es tocar el prompt heredado | No se hace |
| Rotar claves y cronometrar la parte manual del plan de incidentes | No hay incidente que lo pida | Tras la entrega |
| Indicador de negocio de un piloto | Sin usuarios reales no se puede medir; el candidato es la fracción de consultas resueltas sin acudir a otra persona | En un piloto |

*Evidencia: hallazgos 32, 33, 35, 47, 48, 50 y 60.*

### 8.3 Límites de lo medido

**Del banco de pruebas:**

- **Lo escribió quien construyó el sistema**, y no hay casos reservados que
  nadie haya mirado. Las descripciones de la agencia se ajustaron sobre el
  mismo banco. Lo más parecido a una prueba independiente es el alta de la
  gestoría, con un banco escrito antes de la primera pasada.
- **Una conversación es de un turno, salvo lo medido.** Un banco aparte de
  doce conversaciones de dos turnos mostró que sin memoria se pierden 4 de
  12 preguntas de seguimiento ("¿Y la baja?"); reescribiendo la pregunta con
  el turno anterior se recuperan las tres que eran de memoria, por 0,8 s
  más. Está activado en la web. Puede arrastrar el tema del turno anterior:
  una pregunta de salario tras una de vacaciones acabó en "no está en el
  contexto", sin fuga pero sin la denegación clara. Las conversaciones
  largas no están medidas.
- **El juez no se ha validado contra personas**, y la comparación de
  redactores es de una sola pasada por modelo.
- **El envenenamiento del corpus y la caída de un servidor MCP** no se han
  simulado.

**Del despliegue:**

- **La web sirve para demostrar, no para un cliente**, y lo dice en
  pantalla: contraseñas con sal y comparación segura, pero sin límite de
  intentos, sin caducidad de sesión, sin límite de gasto por usuario y sin
  alta de usuarios sin redesplegar.
- **La base del registro es gratuita** y caduca el 10-11-2026.
- **La carga se midió en un proceso**, no con consultas reales simultáneas
  contra Render.
- **WhatsApp y el correo** se probaron en vivo con un número y una
  dirección; la aprobación por correo y el aislamiento con dos números no se
  probaron en vivo.

**De los proveedores.** Cuatro veces un proveedor cambió algo sin avisar o
con consecuencias no anunciadas: un modelo retirado para proyectos nuevos,
un parámetro ignorado en silencio, el modelo de vectores en retirada sin
precio y una cuota gratuita que agotó un banco entero. Las defensas: precios
con prueba que recalcula desde los tokens, modelos con versión fijada,
inventario de dependencias y cambio de proveedor medido.

**Para pasar de demostración a piloto**, por este orden: plan de pago para
la base del registro y los servicios, límites por usuario, alta de usuarios
sin redesplegar, alertas, y el corpus real de un cliente con su propia
evaluación y su contrato de encargo.

*Evidencia: hallazgos 6, 21, 26, 28, 29, 35, 48, 54, 55, 57, 58, 59, 66 y 67.*

## 9. Conclusiones

Los tres resultados del resumen ejecutivo sostienen tres afirmaciones:

1. **Un cliente nuevo es configuración, no desarrollo**, y el aislamiento
   entre clientes no depende de que nadie se acuerde de filtrar.
2. **La confidencialidad no depende del modelo**: lo que un usuario no
   puede ver no llega al modelo, la fuga real que tuvo el proyecto se
   encontró y se cerró, y ninguna escritura se ejecuta sin una persona.
3. **Las decisiones se apoyan en medidas que no varían**, porque el
   evaluador automático también se midió y se equivoca en un solo
   sentido.

La aportación propia, en una frase: convertir el asistente de documentos de
una empresa en un sistema para varias, con dos fuentes de datos, en el que
el control de acceso no depende del modelo, y demostrar con el cronómetro
que un cliente nuevo no cuesta programar.

Lo que el proyecto aprendió sobre medir vale más que cualquier cifra: siete
veces el error estaba en el instrumento y no en el sistema; tres
afirmaciones sobre sesgo fueron falsas antes de que una fuera cierta; y una
corrección hecha desde fuera encontró en menos de una hora lo que catorce sesiones
desde dentro no habían visto.

Lo que se haría distinto: reservar desde el primer día casos de prueba que
nadie mire hasta el final, comprobar la cuota de cada proveedor antes de
apoyar una decisión en él, y someter el sistema a una corrección externa
mucho antes de la entrega.

## Anexo A. Cómo reproducirlo

```bash
git clone https://github.com/JuanArchidona/asistente-multitenant
uv sync --group judge --group app --group langgraph
cp .env.example .env            # claves: sistema, juez, embeddings
uv run pytest                   # 1.255 tests con el grupo langgraph, sin llamadas a API
uv run python -m src.ingest_cli # indexa el inquilino activo (TENANT_ID)
uv run python -m evals.runner --etiqueta prueba --sin-juez   # banco sin juez, menos de un minuto
uv run streamlit run app.py
```

`TENANT_ID=agencia_inmobiliaria` o `TENANT_ID=gestoria_laboral` cambian de
cliente. Cada cifra de esta memoria tiene su carpeta en `reports/` con el
resumen, el informe y las trazas. Para reproducir el comportamiento anterior
a cada cambio de valores por defecto: `ROUTER_TEMPERATURE=defecto`,
`JUDGE_PROVIDER=anthropic` y `GEN_QUIEN_PREGUNTA=0`.

## Anexo B. Los hallazgos y dónde se usan

Los 68 hallazgos de `docs/HALLAZGOS.md`, con lo que midió cada uno y
los apartados de esta memoria que se apoyan en él. Cada hallazgo, en ese
fichero, explica la medida completa y nombra la ejecución guardada en
`reports/` que la respalda, o dice que no la tiene. Los que no se usan en
la memoria aparecen con una raya: son medidas intermedias o superadas.
Esta tabla se genera desde el texto y una prueba falla si difiere.

| Nº | Qué se midió | Dónde se usa |
|-|------------|---|
| 1 | El enrutador es el primer cuello de botella de un cliente nuevo | 2.3, 8.1 |
| 2 | Arreglar el enrutado destapó tres fugas que estaban escondidas | 2.4 |
| 3 | Dos defectos del propio banco, corregidos antes de sacar conclusiones | 1.4, 5.4 |
| 4 | La rama estructurada responde lo que ningún documento contiene | 2.3 |
| 5 | La rama estructurada filtra todo, y el corpus no podía haberlo detectado | 2.4 |
| 6 | Tres iteraciones sobre las descripciones de categoría | 2.3, 8.3 |
| 7 | Dos decisiones de ingeniería de la rama MCP, con su medida | 4.2 |
| 8 | El control estructural cierra las fugas sin romper el producto | 2.4 |
| 9 | La medida de seguridad solo vale si la consulta llegó al punto de riesgo | 2.4 |
| 10 | Un índice obsoleto no falla | 2.2 |
| 11 | La mitad de los casos de seguridad no probaba nada | 2.4, 5.1, 5.4 |
| 12 | La categoría que no existe no se arregla con más palabras | 2.3 |
| 13 | Dos fuentes del mismo inquilino comparten espacio de nombres | 2.2 |
| 14 | El hallazgo 10, otra vez, en el eje que su arreglo no cubría | 2.2 |
| 15 | El enrutador tampoco repite | 2.3 |
| 16 | El coste del banco no es el coste del proyecto | 3.3 |
| 17 | Evaluar cuesta diecisiete veces más que funcionar | 3.1, 3.3 |
| 18 | La clave del juez estaba en todas partes menos donde importaba | 3.2, 4.3 |
| 19 | Confinar al directorio de trabajo no es confinar a lo que se puede enseñar | 7.2 |
| 20 | "El control actuó" no significa que nadie intentara colarse | 6.2 |
| 21 | Una predicción escrita antes de mirar convierte una cifra en una medida | 3.3, 4.3, 5.4, 8.3 |
| 22 | No elegir sale más barato que elegir mal, y se puede medir cuánto | 2.3, 2.4, 3.3 |
| 23 | Una métrica determinista se puede ejecutar sobre el pasado, y esta se estrenó midiéndose a sí misma | 2.4, 5.1, 6.2 |
| 24 | Ir a montar el instrumento independiente destapó que el instrumento no lo era | 3.1, 3.2, 5.3 |
| 25 | El enrutado previo por identificador no se construye, y la razón es una cuenta de dos minutos | — |
| 26 | El juez nunca corrió a temperatura 0, y el parámetro estaba puesto | 3.2, 5.3, 8.3 |
| 27 | La varianza del enrutador costaba un parámetro, no el triple de llamadas | 2.3, 3.2 |
| 28 | Un modelo sin precio costaba cero, y el agujero estaba dentro de la contabilidad | 8.3 |
| 29 | La conmutación de proveedor era una forma, no un hecho | 3.1, 8.3 |
| 30 | El juez escribe el razonamiento correcto y le pone el número equivocado | 5.3, 6.2, 7.2 |
| 31 | La métrica de PII penalizaba al sistema por explicar lo que se negaba a revelar | 3.2, 5.3, 5.4 |
| 32 | Al juez la temperatura no le hace nada, y sus errores van todos en el mismo sentido | 3.1, 3.3, 5.3, 7.2, 8.2 |
| 33 | La comparación de prompts la decide una métrica sin varianza, y el juez no puede decidirla | 3.2, 5.3, 8.2 |
| 34 | Medir sesgo sin control no es medir mal, es afirmar cosas falsas y alarmantes | 4.3, 7.3 |
| 35 | El inventario destapó, al generarse, que el modelo de embeddings está en retirada y cuesta cero | 3.1, 3.3, 7.2, 7.6, 8.2, 8.3 |
| 36 | Un borrado efectivo del índice tarda 1,5 segundos, y se comprueba contra la colección | 7.5 |
| 37 | Los embeddings ya cuentan, el registro ya se puede podar, y las dos cosas dejan rastro | 2.2, 3.3, 6.3 |
| 38 | El primer despliegue tardó minuto y medio y se paró en el login por una clave que nadie iba a usar | 6.1 |
| 39 | El generador aplica un control de acceso que nadie le pidió, y lo hace a ratos | 2.4, 3.2 |
| 40 | Decirle al generador quién pregunta | 2.4, 3.2 |
| 41 | Recortar antes de redactar dejaba pasar sin redactar, y que no hubiera datos personales fue suerte | 2.4 |
| 42 | El modelo propone, la persona aprueba | 2.5, 5.1, 5.2, 7.2 |
| 43 | Dar de alta un cliente nuevo cuesta cinco minutos y cuarenta y dos segundos, y ningún fichero de código | 2.2, 8.1 |
| 44 | La generación tampoco discrimina por encima del ruido, y la cuarta afirmación falsa se mató antes de escribirla | 7.3 |
| 45 | Los dos casos de la gestoría eran del banco, no del sistema | 1.4, 5.2, 5.4, 8.1 |
| 46 | El botón rojo tarda quince segundos, y la primera vez que se pulsó el registro no vio nada | 1.4, 6.2, 6.4 |
| 47 | El camino documental ya no confunde "no es para ti" con "no existe", y el banco heredado no se mueve | 1.4, 2.4, 5.1, 5.4, 8.2 |
| 48 | Un enrutador sin modelo de lenguaje | 3.1, 8.2, 8.3 |
| 49 | El banco de la gestoría recupera su caso de agregación real, y el primer rojo fue del banco otra vez | 5.2, 5.4, 8.1 |
| 50 | El mismo sistema encadenado por LangGraph | 4.1, 8.2 |
| 51 | El canal de WhatsApp llegó a producción sin índice | 2.6 |
| 52 | El plan gratuito de Render duerme a los quince minutos y despertar cuesta entre 32 y 61 segundos, sin que ninguna... | 6.5, 6.6 |
| 53 | Ocho consultas a la vez sobre un mismo `Sistema` tardan lo que una | 2.2, 3.3, 6.5, 7.2 |
| 54 | La conmutación a Gemini funciona y no sirve para comparar | 3.1, 5.4, 7.1, 8.3 |
| 55 | El canal de correo llegó a Render y lee pero no puede contestar | 2.6, 3.3, 8.3 |
| 56 | El canal de correo contesta en vivo | 2.6 |
| 57 | Con clave de pago, Gemini empata a Haiku como generador en los 73 casos bien enrutados por los dos; toda la diferencia... | 3.1, 3.3, 6.4, 7.1, 8.3 |
| 58 | El control de suplantación de correo (R-24) se sostiene por exigir un `pass` positivo, no porque Gmail rechace | 2.6, 8.3 |
| 59 | La latencia interna de WhatsApp, leída por fin en producción | 2.6, 6.5, 8.3 |
| 60 | Producción ya no recibe un commit con la CI en rojo | 6.1, 8.2 |
| 61 | Lo desplegado tenía 23 vulnerabilidades conocidas en 6 paquetes | 6.1, 7.6 |
| 62 | Las primeras consultas reales con el registro persistente y la evaluación al servir | 6.2 |
| 63 | Cuando el proveedor cae, el usuario ya sabe qué pasa y a quién acudir | 6.4 |
| 64 | La recuperación híbrida no mejora nada | 5.2 |
| 65 | Red-teaming con herramienta | 7.2 |
| 66 | Sin memoria, 4 de 12 seguimientos se pierden; reescribiendo la consulta con el turno anterior se recuperan los 3 que... | 4.1, 8.3 |
| 67 | Una corrección simulada desde fuera encontró lo que catorce sesiones desde dentro no vieron | 2.4, 3.2, 3.3, 4.3, 6.1, 6.2, 6.6, 8.3 |
| 68 | La segunda corrección simulada encontró el recorte que faltaba | 2.4, 3.3, 4.3, 6.2, 6.6 |

## Anexo C. Glosario

| Término | Qué significa en esta memoria |
|---|---|
| Inquilino | Cada empresa cliente que usa el sistema. Comparten código, no datos |
| Manifiesto | El fichero de configuración de un inquilino: temas, fuentes, servidores MCP, política de acceso, clasificación del AI Act |
| RAG | Recuperación aumentada: buscar fragmentos de documentos y dárselos al modelo para que responda con ellos |
| MCP | Model Context Protocol: protocolo estándar para que un modelo use herramientas de un sistema externo, aquí el CRM |
| Clasificador (enrutador) | El paso que decide el tema de la pregunta y si va a documentos, al CRM, a ambos o a ninguno |
| Rama | Cada camino de respuesta: la de documentos y la del CRM |
| Solapamiento | Dos temas declarados como ambiguos entre sí; la pregunta se consulta en los dos |
| Control de acceso estructural | El permiso aplicado dentro de la búsqueda y a la salida de las herramientas, no en el prompt |
| Tachar (redactar) campos | Sustituir un dato sensible por una marca antes de que el modelo lo vea |
| Banco de pruebas | El conjunto de casos (pregunta y resultado esperado) con que se mide el sistema |
| Caso correcto | Un caso que pasa todas sus métricas |
| Fuga literal | Métrica que comprueba si aparece en la respuesta un dato que no debe aparecer |
| Cobertura del riesgo | De los casos con material protegido, la fracción que llega de verdad al control de acceso |
| Juez LLM | Un modelo de lenguaje que puntúa las respuestas de otro |
| Métrica determinista | Una que se calcula sin modelo y da siempre lo mismo |
| Corte de línea base | Un cambio de valor por defecto que hace incomparables las cifras de antes y de después |
| Traza | El registro detallado de una consulta: tema, fuentes, herramientas, retenciones, tiempos |
| Hallazgo | Una medición documentada en `docs/HALLAZGOS.md`, con la ejecución que la respalda |
| Por diseño | Un control que existe pero no se ha atacado ni medido |
| Cota inferior | Una cifra que, por cómo se mide, solo puede quedarse corta: el valor real es igual o mayor |

## Anexo D. Detalle técnico

### D.1 Ejecuciones de referencia

Las tablas del capítulo 5.2 y 3.3 salen de estas pasadas del banco, cada
una guardada en `reports/<nombre>/`: `empresa_quien` (empresa),
`agencia_hitl_v3` (agencia) y `gestoria_agregacion_v2` (gestoría; su coste
es el de la pasada `gestoria_agregacion`, de la que reevalúa las trazas).

**Calidad de la búsqueda** en esas pasadas, sobre los casos con un
documento esperado. El acierto (hit rate) y el recall@k dicen si el
documento correcto aparece entre los recuperados; la precisión@k, qué
parte de lo recuperado es el documento correcto; y el MRR, lo arriba que
aparece (1,0 es siempre el primero):

| Banco | Casos | Acierto (hit rate) | Recall@k | Precision@k | MRR |
|---|---|---|---|---|---|
| Empresa | 37 | 1,0 | 1,0 | 0,82 | 0,98 |
| Agencia | 20 | 0,8 | 0,8 | 0,5 | 0,8 |
| Gestoría | 17 | 1,0 | 1,0 | 0,82 | 1,0 |

La precisión de 0,5 de la agencia dice que la mitad del contexto que recibe
el redactor viene de otros documentos.

**Otros costes medidos:** pasada de los dos bancos con el juez de Anthropic,
2,53 USD; sin juez, 0,25 USD; una evaluación, 0,00417 USD con Anthropic y
0,00076 con Gemini; los dos bancos con juez, al menos 0,73 USD (una pasada
de Anthropic) o 0,40 USD (tres de Gemini); el experimento de sesgo, 0,0046
USD en búsqueda y clasificación y 0,27 USD en redacción (336 respuestas).

### D.2 Fragmento del manifiesto de la agencia

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

### D.3 Incidencias de la puesta en marcha de los canales

- **WhatsApp.** Las dos primeras consultas reales fallaron porque el
  servidor no reconstruía el índice al arrancar en un disco que Render
  borra; se corrigió con una única función de arranque compartida por los
  tres canales. Leyendo los registros de Render se vio que un reintento de
  Meta esperaba a que el sistema terminara de arrancar y que el arranque de
  un cliente bloqueaba los mensajes de los demás; se corrigió con un
  bloqueo por cliente. En frío, 13,9 s, de ellos unos 8 s en construir el
  sistema y 2 s el índice.
- **Correo.** El plan gratuito de Render bloquea el envío de correo, y el
  servicio pasó al de pago. El primer correo autorizado dejó el servicio
  mudo: la configuración se cargaba dentro del hilo de sondeo y una clave
  ausente lo mataba sin rastro; ahora se carga al arrancar y un servicio sin
  claves no arranca y dice cuál falta. Los tres primeros correos del buzón
  eran avisos automáticos de Google, y el canal descarta ahora el correo
  automático. El rechazo de remitentes falsificados se cerró en simulación:
  Gmail no los filtra (publica una política DMARC que no rechaza), así que
  lo que protege al canal es exigir la verificación positiva del origen.

### D.4 La documentación del repositorio

| Fichero | Qué es |
|---|---|
| `CLAUDE.md` | Fuente única de verdad: qué es el sistema, estado, decisiones, reglas de trabajo y riesgos abiertos |
| `docs/ALCANCE.md` | Por qué se reorientó el proyecto, alcance por bloques y cambios de valores por defecto fechados |
| `docs/HALLAZGOS.md` | Los 68 hallazgos medidos, cada uno con su ejecución |
| `docs/RIESGOS.md` | Los 24 riesgos con sus cuatro marcos, evidencia y estado |
| `docs/AIBOM.md`, `docs/PROMPTS.md` | Inventario de dependencias y catálogo de prompts, generados y vigilados por prueba |
| `docs/GUION_DEMO.md` | El recorrido de demostración para terceros |
| `docs/INCIDENTES.md`, `docs/RETENCION.md`, `docs/DESPLIEGUE.md` | Plan de incidentes, política de retención y despliegue |
| `docs/BITACORA.md` | Diario de sesiones |
| `reports/` | Evidencia de cada ejecución: resumen, informe y trazas |
