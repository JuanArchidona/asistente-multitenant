> **Nota de aplicación (26-09-2026).** Lectura lineal de `MEMORIA.md` hecha por un lector independiente (un agente leyendo de corrido con la cabeza de un tribunal), sobre el borrador 2 tras la segunda revisión de cifras. Se aplicaron las cinco correcciones prioritarias, las once contradicciones de fondo, la caja de definiciones en 1.3, los cuatro párrafos densos, la limpieza de registro y la reordenación (límites, documentación, conclusiones, anexos). No se aplicó mover el capítulo 6 detrás del 4 ni adelantar 1.4 a 1.2, por no mover cosas que la rúbrica puede reordenar de otro modo. Las preguntas del tribunal que la memoria no respondía se respondieron en el sitio donde surgen o se declararon como límite. Los números de línea son los del borrador leído.

# Lectura lineal de `docs/MEMORIA.md` (borrador 2, 26-09-2026)

Lectura única y de corrido, con la cabeza de un miembro de tribunal de máster en IA generativa. No se comentan cifras ni tildes; no se proponen mediciones nuevas. Las líneas son las del fichero a 26-09-2026 (1.241 líneas).

Impresión general antes del detalle: la memoria es honesta y está muy bien anclada, pero se lee como un documento **escrito a capas**. Tiene tres tipos de texto mezclados: argumento (bueno, sobre todo en 2.7, 3.1, 4.3, 5.4, 7.3, 7.4), inventario (tablas de estado que repiten `CLAUDE.md`) y bitácora (fechas, etiquetas de `reports/`, "se descubrió que"). El lector que lee una vez pierde el hilo en cuatro sitios concretos: 2.4, la celda de 2.7, el párrafo de 4.2 y el bloque de WhatsApp de 2.10. Y llega a las conclusiones (cap. 10) para descubrir que aún quedan dos capítulos.

---

## 1. Hilo narrativo

### 1.1 Conceptos usados antes de explicarse

| Línea | Cita corta | Problema | Propuesta |
|---|---|---|---|
| 51, 272-273, 281, 343 | "Cobertura del riesgo **1,0**" | Se usa en el Resumen, en 2.4 y en la tabla de 2.7 antes de la única explicación (356-367). Un tribunal no sabe qué mide un 1,0 hasta la página 8. | Trasladar el párrafo 356-367 a una caja "Cómo leer las cifras de esta memoria" al final de 1.3, junto con la definición de "caso OK" y de las dos familias de métricas (ahora en 4.1, 594-603). Dejar en 2.7 solo la frase del denominador. |
| 449, 453, 621, 623-625 | "Casos OK" | Nunca se define qué hace que un caso sea OK (todas sus métricas en umbral? solo las deterministas?). Es la columna principal de todas las tablas de resultados. | Una frase en la caja anterior. |
| 156, 241, 306, 467, 737 | "(R-18)", "(R-03)", "(R-12)" | Los códigos R-NN se usan desde 1.4 y se explican en 7.1 (873). | En la primera aparición (156): "R-18 en el registro de riesgos del capítulo 7.1". |
| 51, 343, 623-625, 631, 767-769 | `empresa_quien`, `agencia_hitl_v3`, `gestoria_agregacion_v2`, `agencia_quien` | Etiquetas de `reports/` como identificador de la línea base vigente sin decir nunca qué significan. En 4.2 son el encabezado de la tabla de resultados. | En 4.2, columna "Qué es" ("banco heredado tras el segundo corte", etc.) o nota al pie. Fuera de 4.2 y 5.4, sustituir por "línea base vigente" y dejar la etiqueta en el hallazgo. |
| 545 | "la deriva del 13,2 % es semántica" | El 13,2 % no aparece en ningún otro sitio de la memoria. | Borrar la cifra o decir de qué es porcentaje. |
| 457 | "19 min de las 4 h de corte" | "4 h de corte" presupone el presupuesto de `ALCANCE.md`, que el lector no ha visto. | "19 min (el presupuesto asignado en `ALCANCE.md` §4 era de 4 h)". |
| 262, 346, 372 | "temperatura 0 desde el 22-09-2026 (capítulo 4.4)", "desde el 23-09" | El capítulo 2 remite tres veces a los cortes de línea base de 4.4 sin haber dicho qué es un corte. | Una frase en 1.3, regla quinta (130-133), ya casi lo hace: añadir "hubo dos, capítulo 4.4". |

### 1.2 Repeticiones (misma idea, dos o más capítulos)

| Idea | Ubicaciones | Propuesta |
|---|---|---|
| El registro de producción: qué campos guarda, qué resume el CLI | 2.9 (389-396) y 6.1 (815-819), casi palabra por palabra | Borrar 2.9 y dejar en 2.1 la línea del flujo. El registro es operación, vive en 6. |
| Cómo se trabajó con el asistente | 1.3 (135-148), 6.5 (854-862), 12.2 (1161-1168) | 1.3 es el sitio. 6.5 se reduce a una frase en 7.2 fila 7 (donde ya se cita §19). 12.2 se fusiona con 4.5. |
| "Una hipótesis que sale de los datos no se confirma con los mismos datos" | 929-930, 1118, 1167-1168 | Se dice en 7.3 y se recoge en Conclusiones. Borrar de 12.2. |
| "Seis veces el error estaba en el instrumento" | 690 (4.5), 884 (7.1, "en tres de ellas"), 1116 (10) | Aceptable en 4.5 y 10; en 7.1 la celda debería remitir "(capítulo 4.5)" en lugar de volver a contarlo. |
| El generador que obedecía la cabecera CONFIDENCIAL (§39/§40) | 346 (fila de tabla 2.7), 373-378 y 383-385 (2.8, dos veces dentro de la misma sección: "ninguna métrica de confidencialidad se movió" en 378 y "ninguna métrica de fuga se movió" en 385), 682 (4.4) | 2.8 se queda con una versión; la fila de 2.7 remite a 2.8; 4.4 solo la escotilla. |
| El `NotFoundError` del disco efímero de Render | 413-418 (2.10) y 561-562 (3.4) | Contarlo una vez, en 3.4 (es un límite de ChromaDB en Render), y en 2.10 dejar "probado en vivo (§51)". |
| El experimento bloqueado del generador con Gemini | 527-540 (3.3), 1031 (8.3), 1071-1074 (9) | 3.3 lo argumenta; 8.3 y 9 lo listan. Quitar de 9 (8.3 ya es la tabla de pendientes) o fusionar 8.3 con 9 (ver §6). |
| La confirmación del tutor del 22-09 | 85-86, 137, 866-867 | Una vez, en 1.2 o 1.3; las otras dos, "(capítulo 1.3)". |
| El alta en 5 min 42 s | 50, 145, 231, 759, 996, 1104 | Es la cifra bandera y se acepta en Resumen, 8.1 y 10. Pero 2.2 (230-232) y 5.4 (759) la repiten con frases distintas: sustituir por "capítulo 8.1". |
| La rama estructurada cita ahora la herramienta y no es estable entre pasadas | 380-382 (2.8) y 630-632 (4.2) | Dejarlo en 4.2, que es donde está la tabla. |
| Los ejes de sesgo y "no se afirma que el sistema no discrimina" | 7.3 (909-930) repite casi entero el bloque de `CLAUDE.md` §8; no es problema para el tribunal, pero se nota el copiado en el ritmo (frases de la bitácora: "se equivocó tres veces antes de acertar") | Mantener el contenido; reescribir el segundo párrafo con la voz de la memoria. |

### 1.3 Secciones que son lista sin argumento

| Línea | Sección | Problema | Propuesta |
|---|---|---|---|
| 1013-1020 | 8.2 "Lo que cuesta escalar lo que ya hay" | Tres viñetas sin relación entre sí; la tercera (denegación parcial) no es de escalabilidad. | Convertir en un párrafo: "Tres cosas crecen con el sistema: el coste del solapamiento con el tamaño del grupo, el tiempo del borrado RGPD con el corpus, y ... ". Mover la denegación parcial a 8.3 o 9, donde ya está. |
| 1043-1097 | 9 "Límites" | Catorce viñetas sin orden: mezcla límites del banco, de la infraestructura, de la interfaz, decisiones tomadas y cosas fuera de alcance. Varias repiten 8.3 uno a uno (`inj-04`, denegación parcial, correo, generador Gemini, WhatsApp). | Agrupar en tres bloques con una frase de cabecera cada uno: "Lo que el banco no mide", "Lo que el despliegue no es todavía", "Lo que queda fuera por decisión". Lo decidido con fecha vive en 8.3 y 9 remite. |
| 547-576 | 3.4 "El resto de la pila" | Cada viñeta está bien por separado, pero no hay una frase de entrada que diga qué tienen en común (todo heredado del patrón del máster, sin alternativa medida). Lo dice la primera viñeta y no las demás. | Frase de apertura: "Cinco piezas heredadas del patrón del máster; ninguna con alternativa medida, y por eso cada una dice qué se mediría si se cambiara." |
| 1022-1032 | 8.3 "Decisiones pendientes con fecha" | El título dice "pendientes"; cinco de las siete filas dicen "Decidido no", "Cerrado", "No se hace", "Fuera". Solo dos están pendientes de verdad. | Renombrar "Decisiones tomadas por no hacer, y las dos que siguen abiertas", o separar las dos pendientes en su propia tabla. |

### 1.4 Dónde se pierde el lector

- **266-276** (2.4, primera viñeta): en once líneas se cuentan cinco cosas (cuello de botella, seis palabras, tres iteraciones, categoría nueva, no repetibilidad y temperatura). La tercera viñeta (284-288) vuelve sobre la temperatura. El lector no sabe cuál es la "decisión medida" que anuncia el encabezado.
- **343** (2.7, celda "Permiso en el where"): una celda de tabla de unas 90 palabras con cuatro cifras de tres ejecuciones y dos épocas distintas. Es el lugar donde se defiende la decisión central y es ilegible en formato tabla.
- **627-637** (4.2, "Lo que dicen"): una frase de unas 130 palabras con tres puntos y coma, dos paréntesis anidados y dos `ooc-04` que no son el mismo caso. El párrafo más importante del capítulo de evaluación.
- **996-1007** (8.1): quince cifras en un párrafo, con la cronología 20/28 -> 25/28 -> 27/28 -> 28/29 mezclada con aciertos del enrutador, segundos y porcentajes. El Resumen (50) da 25/28 y 27/28; la tabla de 1.4 (164) dice 29 casos; 4.2 (625) dice 28/29. El lector tiene que reconstruir la historia del banco de la gestoría en tres sitios.
- **404-429** (2.10, WhatsApp): la viñeta cuenta la puesta en marcha día a día. Se pierde qué es el canal por el relato de cómo se arregló.

---

## 2. Contradicciones de fondo entre capítulos

| # | Dónde | Qué choca | Propuesta |
|---|---|---|---|
| C1 | 3.3 (503) frente a 4.3 (652-656) | 3.3 justifica el juez de Gemini porque es "el único que admite temperatura 0 de verdad"; 4.3 concluye que "la temperatura no le hace nada" al juez. El argumento de 3.3 queda vacío por el propio capítulo 4. | En 3.3 dejar dos razones (otra familia, 5,5 veces más barato) y quitar la de la temperatura, o decir "admite temperatura 0, aunque el §32 muestra que eso no lo estabiliza". |
| C2 | 4.3 (656), 5.1 (710), 5.4 (800-803) frente a 8.3 (1027) | 4.3: "La única corrección conocida es la mayoría de tres". 5.1 y 5.4 presupuestan "tres pasadas de Gemini" como el coste de mantener el banco, es decir, como práctica. 8.3: "Decidido no automatizarla ... repetir es un acto deliberado". El lector no sabe si la mayoría de tres es el procedimiento del proyecto o una idea descartada. Y 4.2 presenta la línea base vigente "sin juez": si ninguna decisión cuelga del juez y los resultados vigentes no lo usan, la ficha de 5.4 está presupuestando algo que el proyecto no hace. | Una frase en 4.3 que cierre: "El proyecto no la automatiza; cuando se pasa el juez, se pasa tres veces y se lee la mayoría con su razón (8.3)". En 5.4 decir "si se pasa el juez". |
| C3 | 3.1 tabla (470) y 8.4 (1040-1041) frente a 3.3 (538-540) | 3.1 y 8.4 dan la conmutación de proveedor como mitigación de mantenimiento frente a proveedores que cambian; 3.3 concluye que "la conmutación de proveedor no es un plan de contingencia mientras la clave sea gratuita". Las dos cosas se afirman con la misma rotundidad. | En 8.4 matizar: "conmutación verificada (§29) y, desde el §54, condicionada a una clave de pago". En 3.1 fila Mantenimiento, "sin adaptadores, aunque con la salvedad del §54". |
| C4 | 6.1-6.2 (815-828) frente a 2.10 (423-425) y 3.4 (560-562) | El capítulo 6 describe un registro de producción con retención de 90 días, supresión y purga. 2.10 dice que ese registro "quedaba en el disco efímero de Render, sin consola en el plan gratuito" y 3.4 que el disco es efímero. Si el disco se reinicia, la retención de 90 días es una política sobre un fichero que puede no sobrevivir a la noche. La memoria no lo pone en el mismo párrafo nunca. | En 6.1 o 6.2, una frase: "En el despliegue actual el registro vive en el disco efímero del plan gratuito y no sobrevive al reinicio; la política de retención está medida en local y es un requisito del despliegue de pago (capítulo 5.4)". Y listarlo en 9. |
| C5 | Resumen (29-31) frente a 3.4 (555, 573) y 3.3 (527) | Resumen: "cada decisión de diseño tiene una medida detrás". 3.4: `uv` "sin alternativa medida", DeepEval "se descartó por tiempo"; 3.3: "Lo que no se comparó: el generador". | En el Resumen: "cada decisión que se defiende tiene una medida detrás, y las que no la tienen lo dicen". |
| C6 | Resumen (51), 1.2 (95), 2.7 (343), 10 (1108) | 1.2: "el fallo estaba medido (2 fugas)". 2.7: heredado "fugas literales de 2 a 0", agencia "de 1 a 0". Resumen y 10: "una fuga real encontrada y cerrada". No hay contradicción numérica, pero el lector no puede identificar cuál es *la* fuga real: si las dos del heredado, la de la agencia (§5) o la del recorte (§41). | En 2.7, tras la tabla: "La fuga real que se cita en el Resumen es la del §5/§41: ...". Una frase. |
| C7 | 2.7 (343), 4.3 (657-661), 7.2 fila 1 (891) | La misma cifra, `fuga_literal` 8/10 frente a 10/10, sostiene tres afirmaciones distintas: en 2.7 el permiso en el `where`, en 4.3 la comparación de políticas de generación base/endurecida, en 7.2 la defensa contra inyección de instrucciones. Además, la memoria nunca dice cuál de las dos políticas (base o endurecida) es la vigente en producción. | En 4.3 decir cuál es la política por defecto; en 7.2 fila 1 citar los casos `inj-*` y la cobertura del riesgo, no la comparación de políticas; en 2.7 dejar solo la cifra de la línea base vigente. |
| C8 | 1.3 (144-147) frente a 2.10 (421-422) y 8.1 (1001) | 1.3: "las dos cifras de tiempo que la memoria da (5 min 42 s ..., 19 min ...) son tiempo del asistente ... y las dos lo dicen". 2.10 da una tercera ("dieciocho minutos desde el encargo hasta la respuesta verificada") sin la salvedad; 8.1 da "65 s entre las dos pasadas". | O se quita la cifra de 2.10 (sobra) o 1.3 dice "las cifras de tiempo de trabajo". |
| C9 | 1.3 regla tercera (125-127) frente a 3.3 (522-524) | 1.3: la línea base heredada no se toca. 3.3: "la línea de mejora que sale es dar ejemplos a las descripciones", que en el heredado es tocar el prompt del enrutador. 8.3 lo resuelve para `inj-04` ("No se hace"), pero 3.3 lo presenta como línea de mejora sin decir que está vedada en el heredado. | En 3.3: "dar ejemplos a las descripciones en los inquilinos nuevos; en el heredado eso es tocar la línea base (1.3)". |
| C10 | 7.1 tabla (883) frente a 3.3 (538-540) | 7.1 pone "conmutación verificada" como contramedida de conocidos-desconocidos. Misma tensión que C3. | Igual que C3. |
| C11 | 6.3 (835-838) frente a 1.3 regla cuarta (128-129) | 6.3 afirma que el servicio desplegado fue "el mejor banco de pruebas" con un recuento de hallazgos por sesión. Es un juicio de bitácora, no una medida, en una memoria cuya regla es "ninguna cifra sin su ejecución". | Reescribir como hecho: "Cuatro de los hallazgos (§38, §39, §41, §42) salieron de probar el servicio desplegado, no el banco; el §41 es la fuga por tamaño". |

---

## 3. Lo que un tribunal preguntaría al terminar cada capítulo

**Capítulo 1.**
1. ¿Cuánto del código es nuevo? 2.1 da 5.400 líneas y 1.121 tests en total; la memoria nunca separa lo heredado de lo construido en los cinco días (líneas, módulos, tests). Es la primera pregunta de un tribunal que sabe que se parte de una entrega calificada.
2. ¿Quién asigna los roles y cómo se administran en un cliente real? 1.1 plantea "quién puede ver qué" como el problema central y la memoria solo dice (6.3) que hay seis usuarios en un JSON.
3. ¿De dónde salen los objetivos no funcionales (3-8 s, "céntimos") que se dan por cumplidos en 1.2?

**Capítulo 2.**
1. ¿Qué responde el sistema cuando el clasificador devuelve `otro`? Se cita cinco veces como destino y nunca se dice qué ve el usuario.
2. ¿Qué pasa cuando el servidor MCP está caído? La regla "nada de fallbacks silenciosos" se enuncia en 1.3; el comportamiento concreto de la rama estructurada ante fallo no se describe ni se mide (el simulacro de 6.4 mide otro fallo).
3. Cuando el destino es "ambos" (solapamiento), ¿cómo se fusionan los dos contextos en una respuesta y cómo se cita cada uno? 2.4 da el precio; ninguna sección da el mecanismo.

**Capítulo 3.**
1. ¿Por qué ChromaDB? 3.4 dice lo que se mediría si se cambiara, no por qué se eligió más allá de la herencia; el mismo párrafo reconoce que el índice en disco efímero costó dos consultas reales.
2. ¿Por qué Haiku como generador y no un modelo mayor? La memoria lo reconoce en 527-540 como no comparado; el tribunal lo preguntará igual y conviene tener la respuesta de coste (5.4) enlazada desde aquí.
3. ¿La comparación con LangGraph vale si el sistema no usa nada de lo que LangGraph aporta? 3.1 lo reconoce (473-477); un tribunal preguntará por qué entonces se eligió LangGraph como comparador y no, por ejemplo, un framework de RAG.

**Capítulo 4.**
1. ¿Cuáles son los 9 casos que fallan en la agencia y los 5 del heredado? 4.2 nombra uno (`ooc-04`); los demás no aparecen en ningún sitio. Un tribunal quiere saber si son fallos de enrutado, de generación o de banco.
2. ¿Hay un umbral de aceptación? 48/53 y 31/40 se presentan sin decir qué cifra habría sido inaceptable.
3. ¿Contra qué se validó el juez si no hay anotación humana? 9 lo declara como límite; 4.3 debería anticiparlo con una frase.

**Capítulo 5.**
1. ¿Cuánto costó el proyecto entero? Se dan créditos (12,87 y 12,66 USD) y un 22 % invisible, pero nunca el gasto total de desarrollo y evaluación.
2. ¿Cuántas consultas al mes hace un inquilino real? La ficha de 5.4 usa 500/2.000/10.000 sin justificar el orden de magnitud.
3. ¿Qué costaría la misma consulta con el generador alternativo? La tabla de 3.3 dice que Gemini dobla su precio en 2027 pero no hay ninguna cifra comparada.

**Capítulo 6.**
1. ¿Alguien lee el registro? Hay CLI, no hay alertas ni umbrales; el tope blando se comprueba al consultar, no se avisa.
2. ¿El registro sobrevive a un reinicio de Render? (Ver C4.)
3. ¿Cómo se da de alta o de baja un usuario en producción sin redesplegar, si viven en una variable de entorno?

**Capítulo 7.**
1. ¿Cuántos ataques de inyección hay en el banco y de qué tipo? Se citan `inj-04` y "los `inj-*`" sin decir cuántos son ni qué prueban; 7.2 fila 1 apoya la inyección en una cifra que es de otra cosa (C7).
2. ¿Qué significa "por construcción" en cuatro filas de 7.2 (2, 3, 5, 7)? Para un tribunal es sinónimo de "no medido"; la fila 3 lo admite, las otras no.
3. En un servicio multi-tenant, ¿quién es responsable y quién encargado del tratamiento? 7.5 lista lo que exigiría producción sin situar al operador del asistente en ese esquema.

**Capítulo 8.**
1. ¿Qué pasa cuando un inquilino cambia su manifiesto en producción (nueva categoría, política más estricta)? Reindexar, invalidar la línea base, migrar el registro. La memoria mide el alta, no el cambio.
2. ¿Quién escribe el banco de 28 casos de un cliente nuevo? 8.1 lo cuenta como parte de los 5 min 42 s hechos por el asistente; en un cliente real es trabajo del cliente o del integrador.
3. ¿Cuántos inquilinos aguanta un proceso? Declarado como no medido en 2.3; el tribunal preguntará por una estimación.

**Capítulo 9.**
1. ¿Cuál es el orden de prioridad para pasar de demostración a piloto con un cliente real? Los límites están listados, no ordenados.

**Capítulos 10-12.**
1. ¿Cuál es la aportación original del TFM frente a la 3.3, en una frase? Las conclusiones dan tres cifras, y dos de ellas (control de acceso, evaluar al evaluador) son continuaciones directas del feedback de la 3.3.
2. ¿Qué haría distinto? Ninguna sección lo dice; 4.5 y 12.2 lo rozan.

---

## 4. Densidad

| Línea | Cita (inicio) | Problema | Propuesta |
|---|---|---|---|
| 33-44 | "El proyecto parte de las entregas 2.1, 2.3 ..." | Un párrafo con tres cosas: origen, cronología con paréntesis de bitácora, lista de siete piezas construidas, y quién lo hizo. La frase 35-40 tiene unas 60 palabras. | Tres frases: origen; qué se construyó (lista de siete, sin fechas); quién (remitir a 1.3). |
| 152-156 | "Los tres son sintéticos ... Eso mitiga hoy el riesgo de transferencia ..." | El inciso sobre RGPD y R-18 interrumpe la presentación de los inquilinos antes de la tabla. | Dejar "Los tres son sintéticos: ningún dato real entra en un repositorio público." y llevar el resto a 7.5, donde ya está (970-979). |
| 266-276 | "El enrutador es el primer cuello de botella ..." | Viñeta de unas 130 palabras y cinco hallazgos. La frase 273-276 ("Y el enrutador tampoco repite ...") cambia de tema dentro de la viñeta. | Partir en dos viñetas: "el prompt no puede devolver lo que no describe" (§1, §6, §12) y mover la no repetibilidad a la tercera viñeta, que ya trata la temperatura. |
| 320-331 | "Y filtra todo, y el corpus no podía haberlo detectado (§5) ..." | Frase 326-328 con dos puntos, un inciso de 6.028 caracteres y una causa; la moraleja ("un control que depende del tamaño ...") llega al final de la viñeta. | Separar el §5 (redacción al salir) del §41 (redacción antes del recorte) en dos viñetas. |
| 343 | Celda "Permiso en el `where`" | Unas 90 palabras, cuatro cifras, dos épocas, un paréntesis con nombre de caso. | Convertir la tabla de 2.7 en subsecciones cortas o dejar en la celda solo la cifra vigente y remitir a 4.2 y 4.3. |
| 356-367 | "La medida "cobertura del riesgo" merece explicación ..." | Bien escrito, pero en 2.7 hace tres cosas: define la métrica, corrige el "cero fugas sobre 17", y declara los tamaños de muestra. | Ver §1.1: la definición sube a 1.3; en 2.7 quedan la corrección y la muestra. |
| 373-378 y 383-385 | "Antes no lo sabía y obedecía ..." / "En las diez consultas del §39 ..." | Dos párrafos que dicen lo mismo con cifras distintas (3 de 5; 70 %). | Un solo párrafo. |
| 404-429 | Viñeta de WhatsApp | Unas 250 palabras, ocho fechas u horas relativas, cuatro sucesos. | Reducir a: qué es el canal (número como credencial, artículo 50, aprobación por texto, firma del webhook, teléfono fuera del registro), cómo está probado (29 pruebas simuladas; en vivo con un número y dos preguntas, §51) y el límite (latencia interna solo simulada). Cinco líneas. La historia va a `CANAL_WHATSAPP.md`. |
| 449, 453 | Celdas de la tabla de 3.1 | Paréntesis explicativos dentro de celdas ("el que cambia es el generador muestreando: mismas 106 llamadas ..."). | Nota bajo la tabla. |
| 487-496 | "Tres decisiones de ingeniería de la rama ..." | Una frase de unas 85 palabras con tres puntos y coma, seguida de un salto a idealista sin transición. | Tres frases cortas y un párrafo aparte para el MCP de terceros. |
| 527-540 | "Lo que no se comparó: el generador ..." | Cuenta el intento, la causa, la cifra, la conclusión y la consecuencia para la justificación en un solo párrafo. | Párrafo 1: no se comparó y por qué (herencia). Párrafo 2: el intento y la consecuencia ("la conmutación no es contingencia"). |
| 627-637 | "Lo que dicen: el heredado no se ha degradado ..." | Una frase de unas 130 palabras. | Tres párrafos, uno por inquilino, tres frases cada uno. |
| 715-724 | "Hay tres cifras de coste por consulta ..." | Tres cosas: desambiguar las tres cifras, el error del 50 % en la tabla de precios, y `modelos_sin_precio`. | Las dos últimas van a 8.4 (proveedores que cambian), que ya cita §21. |
| 728-734 | Viñeta "Tope duro" | Cuatro cifras y una inversión del riesgo en una viñeta. Frase 730-732 con inciso de cuatro números. | "Tope duro: prepago sin recarga. Una fuga a pleno ritmo lo agotaría en 55 minutos (§53). El riesgo que queda es el contrario: quedarse sin crédito en la defensa." |
| 835-838 | "de los nueve hallazgos de la sesión del 23-09 por la mañana ..." | Recuento de bitácora dentro de una frase de despliegue. | Ver C11. |
| 902-907 | "De los nueve guardarraíles ... y la categoría `otro` hace de filtro de fuera de ámbito." | La última cláusula no engancha con la frase: el paréntesis de justificación se cierra y la frase sigue con otro sujeto. | "Falta la moderación de contenido. El hueco está justificado: en un asistente interno el vector es la consulta, la inyección lo cubre en parte y la categoría `otro` filtra lo que está fuera de ámbito." |
| 983-990 | "12 paquetes directos y 142 transitivos fijados ... (eran 10 y 119 al generarse el 23-09; ...)" | Paréntesis de historia de recuentos dentro de la frase principal. | Quitar el paréntesis; el AIBOM tiene su propia historia. |
| 996-1007 | Párrafo del alta | Quince cifras, cronología de cuatro estados del banco, y la salvedad al final. | Cronología en una tabla de cuatro filas (primera pasada, segunda, revisión en frío, tras §49) y un párrafo de tres frases con la lectura. |
| 999-1003 | "20 de 28 a la primera (acierto ... a `procedimientos`) y 25 de 28 tras reescribir tres descripciones: 65 s entre las dos pasadas, banco incluido (0,923, ...); revisado en frío, ..." | Una frase de unas 70 palabras con dos paréntesis y dos puntos y coma. | Ver fila anterior. |
| 1053-1070 | Viñeta de la prueba de carga | Unas 200 palabras; mezcla lo que se midió (que no es un límite) con lo que no. | Lo medido va a un 6.6 "Carga y arranque en frío" (o a 8.2); en 9 queda solo la frase "Sin medir: consultas reales concurrentes contra Render, techo de hilos, CPU del plan gratuito, reconstrucción del índice tras reinicio". |

---

## 5. Registro

### 5.1 Bitácora en lugar de memoria

| Línea | Cita | Propuesta |
|---|---|---|
| 9-17 | Bloque de estado del borrador | Se quita al entregar; anotarlo para no olvidarlo. |
| 36-37, 144 | "(del 20 al 24 de septiembre de 2026, ocho sesiones registradas en la bitácora)"; "La bitácora registra ocho sesiones en cinco días" | Una sola vez, en 1.3, y sin "registradas en la bitácora": "cinco días de construcción y dos de medidas de operación". |
| 194-196 | "(los dos números, contados el 26-09-2026 con `wc -l` y `pytest` ...; no están en ningún hallazgo)" | Nota al pie o borrar; en el texto, "unas 5.400 líneas y 1.121 tests". |
| 346, 372, 391, 419, 503, 1027, 1092 | "desde el 23-09", "El 25-09", "desde el 22-09", "por decisión del 26-09" | En el cuerpo de la memoria las fechas solo tienen sentido en 4.4 (cortes) y 8.3 (decisiones). En el resto, "desde el segundo corte de línea base" o nada. |
| 505, 669, 724, 988 | "hasta el §29", "Desde el §24", "hasta el §28", "Al generarse destapó" | Un hallazgo no es un momento. "hasta que se verificó (§29)", "desde que se midió (§24)". |
| 404-429 | Toda la viñeta de WhatsApp | Ver §4. Frases como "La línea existe y todavía no se ha leído ningún valor en Render" son estado de trabajo, no memoria. |
| 421-422 | "dieciocho minutos desde el encargo hasta la respuesta verificada" | Borrar: es tiempo del puente con la app, no del sistema. |
| 531 | "Se intentó el 26-09" | "Se intentó". |
| 729-730 | "12,87 USD de crédito en Anthropic el 21-09 (§16) y 12,66 el 23-09" | Una sola cifra con "a fecha de la última medida (§16)". |
| 796-798 | "(precio consultado el 26-09-2026 en fuentes secundarias, porque la página de precios de Render no se pudo leer sin JavaScript)" | Nota al pie: "precio de fuentes secundarias a 26-09-2026". La razón técnica sobra. |
| 835-838 | "de los nueve hallazgos de la sesión del 23-09 por la mañana (§35 a §43)" | Ver C11. |
| 957-959 | "Las citas literales las trajo la app de Claude leyendo EUR-Lex y se contrastaron ..." | "Las citas literales se tomaron de EUR-Lex y se contrastaron ...". Quién las trajo es 1.3. |
| 985-987 | "(eran 10 y 119 al generarse el 23-09; el grupo de la interfaz añadió 12 ese mismo día y el de LangGraph 14 el 24-09, §50)" | Borrar. |
| 1193-1194 | "regenerado el 26-09-2026 desde las citas `§N` del texto" | Aceptable en un anexo; quitar la fecha. |
| 153, 793, 970 | "mitiga hoy", "corre hoy", "hoy no viaja" | "en el estado actual" o "en el despliegue actual". |

### 5.2 Etiquetas de `reports/` en medio de frases

51 (`empresa_quien` en el Resumen), 343 (`empresa_quien`, `auth-rrhh-01`), 345 (`gestoria_denegacion`), 628 y 636 (`ooc-04` dos veces, y no es el mismo caso), 631 (`agencia_quien`). En el Resumen y en el capítulo 2 bastaría la cifra con "(línea base vigente, §40)". Las etiquetas son útiles en las tablas de 4.2 y 5.4 y en el anexo; fuera de ahí son ruido para el tribunal.

### 5.3 El "yo", el autor y el asistente

El párrafo de 1.3 (135-148) fija el reparto: el asistente escribe, el autor decide. El resto de la memoria usa "se" impersonal y "el autor" (42, 140, 835, 858, 897, 1006), lo que es coherente. Tres desvíos:

- 957-959: "la app de Claude" aparece como actor que investiga normativa. Es el único sitio donde el asistente hace algo distinto de escribir código y documentos bajo dirección; o se dice en 1.3 ("y la investigación normativa del capítulo 7.4") o se despersonaliza aquí.
- 854-862 (6.5): el capítulo habla de "la sesión hija de solo lectura" y del "puente", jerga del utillaje del autor que un tribunal no conoce. Si se mantiene, una frase que diga qué es el puente antes de decir qué falló.
- 1006-1007 y 457: la salvedad "lo hizo un asistente de código con el proyecto en contexto" se repite en cada cifra de tiempo, como manda 1.3, y está bien. Pero en 421-422 (WhatsApp) falta (C8).

---

## 6. Estructura

### 6.1 Correspondencia con las cinco características del capstone

| Característica del programa | Capítulos actuales | Observación |
|---|---|---|
| Definición del problema y contexto | 1 | Correcto. 1.4 (inquilinos) podría ir antes de 1.2 (herencia), porque el lector entiende mejor "lo heredado" cuando ya sabe que `empresa_servicios` es un inquilino. |
| Arquitectura | 2 | Correcto, con 2.9 sobrando (es operación) y 2.10 sobredimensionado. |
| Selección y justificación (calidad, coste, escalabilidad, riesgo, mantenimiento) | 3, 5, 7, 8 | El capítulo 3 abre "por criterios" solo en 3.1 (tabla 464-471). Los otros cuatro criterios tienen capítulo propio (5 coste, 7 riesgo, 8 escalabilidad y mantenimiento) sin que nadie lo diga. |
| Evaluación y control | 4, 6 | 4 es evaluación; 6 es control operativo. Están separados por el capítulo de coste. |
| Documentación y defensa | 12 (y 11) | Llega después de las conclusiones. |

### 6.2 Qué movería

1. **Terminar con las conclusiones.** Orden propuesto: 1, 2, 3, 4, 5, 6, 7, 8, 9 (límites), 10 (documentación y defensa, hoy 12), 11 (conclusiones, hoy 10), Anexo A (cómo reproducirlo, hoy 11), Anexo B (índice de hallazgos). Las conclusiones a mitad del documento restan fuerza a las tres frases con número, que son lo mejor de la memoria.
2. **Un párrafo de entrada al capítulo 3** que diga: "Los cinco criterios del capstone se reparten así: la calidad se mide en el capítulo 4, el coste en el 5, el riesgo en el 7, la escalabilidad y el mantenimiento en el 8; este capítulo justifica las elecciones de patrón y de modelo y remite a cada uno." Con eso los capítulos 5-8 dejan de parecer añadidos.
3. **Fusionar 2.9 en 6.1**, y mover 6 (operación) a continuación de 4 (evaluación) si se quiere respetar "evaluación y control" como bloque. Alternativa menor: dejar 6 donde está y renombrarlo "Control en producción".
4. **Fusionar 8.3 y 9** en una sola tabla "Lo que no está, y por qué": columnas "Qué", "Decisión o límite", "Cuándo". Hoy el lector encuentra `inj-04`, la denegación parcial, el correo, el generador Gemini y WhatsApp en los dos sitios.
5. **Reunir el método en un solo sitio.** 1.3 (reglas y quién hizo qué), 4.5 (el banco descubrió sus defectos) y 12.2 (dos reglas de método) son el mismo capítulo troceado. 6.5 se reduce a una frase donde ya se cita el §19. Propuesta: 1.3 se queda con las reglas y el reparto de autoría; 4.5 absorbe 12.2 y se titula "Lo que el banco enseñó sobre el método".
6. **Renombrar 2.7** ("Gobernanza: el control va antes del modelo") a "Control de acceso antes del modelo", porque el capítulo 7 se llama "Gobernanza, seguridad e IA responsable" y el lector cree que va a leer lo mismo dos veces.
7. **Añadir la caja "Cómo leer las cifras"** al final de 1.3: qué es un caso OK, qué es la cobertura del riesgo y su denominador, qué son las dos familias de métricas, qué es R-NN, qué es §N, qué es una etiqueta de `reports/` y qué es un corte de línea base. Siete definiciones de una línea. Hoy están en 2.7, 4.1, 7.1, 4.4 y el anexo.
8. **Mover lo medido de la prueba de carga y del arranque en frío** (1053-1070) desde 9 a un 6.6, porque un resultado positivo (ocho en vuelo tardan lo que una) no es un límite; en 9 quedan las cuatro cosas sin medir.

---

## Las cinco correcciones que más mejorarían la lectura

1. **Reescribir la viñeta de WhatsApp (404-429) en cinco líneas** y, con el mismo criterio, quitar del cuerpo todas las fechas que no sean de 4.4 y 8.3 y todos los "desde el §N". Es lo que más delata que la memoria se escribió a trozos.
2. **Caja "Cómo leer las cifras" al final de 1.3** con cobertura del riesgo, caso OK, dos familias de métricas, R-NN, §N, etiquetas de `reports/` y cortes de línea base. Resuelve de golpe las siete presuposiciones del §1.1 y permite adelgazar 2.7, 4.1 y 7.1.
3. **Cerrar por escrito las tres contradicciones de fondo**: la mayoría de tres del juez (práctica o descartada; C2), la conmutación de proveedor (mitigación o no contingencia; C3, C10) y el registro de producción en disco efímero frente a la retención de 90 días (C4). Las tres las encontrará un tribunal que lea con atención el capítulo 4 y el 6, y ninguna exige medir nada.
4. **Terminar con las conclusiones** (orden 1-9, documentación y defensa, conclusiones, anexos), fusionar 2.9 en 6.1 y 8.3 con 9, y reunir el método en 1.3 y 4.5.
5. **Partir los cuatro párrafos monstruo**: la celda 343, la frase 627-637, el párrafo 996-1007 (con su tabla de cronología del banco de la gestoría) y la viñeta 266-276. Son los cuatro sitios donde se defiende lo más importante (control de acceso, resultados vigentes, alta de cliente, enrutador) y los cuatro donde el lector se rinde.

## Valoración

La memoria se defiende sola en la evidencia y no en la lectura: un tribunal que la lea una vez creerá cada cifra, pero saldrá con tres preguntas que el texto ya sabe responder y no responde en el mismo sitio (qué es un caso OK, si el juez se pasa tres veces o no, y qué pasa con el registro cuando Render se reinicia), y habrá dejado de leer con atención en el párrafo de 4.2 y en el bloque de WhatsApp.
