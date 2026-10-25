# Prompt para el segundo análisis de legibilidad de la memoria (encargo E-0026)

Pegar el texto de abajo, tal cual, en Gemini y en ChatGPT, en conversaciones
nuevas, con el PDF nuevo adjunto (`docs/entrega/TFM_Juan_Archidona.pdf`, 32
páginas, commit 3d1ba91). Mismo texto en los dos. Las tres notas son las
mismas que en el primer análisis (E-0025), para poder compararlas.

---

Te adjunto la memoria técnica de mi Trabajo Fin de Máster (Máster en IA
Generativa Avanzada). Necesito un análisis de su legibilidad y su
complejidad, no de su contenido técnico.

**Contexto.** El proyecto es un asistente interno para empresas de
servicios profesionales: responde consultas con la documentación de cada
cliente (RAG) y con sus datos de negocio (servidores MCP), sirve a varios
clientes con el mismo código y aplica el control de acceso antes de que el
modelo vea nada. El documento es lo único que se entrega, junto con el
repositorio de código como evidencia; no hay defensa oral.

**Quién lo lee y cómo se evalúa.** Lo corrige un tutor del máster,
probablemente con ayuda de un agente que recorre una lista de criterios
módulo a módulo. El enunciado pide que el documento explique, con sus
razones: qué modelos se usan y por qué, cómo se configuran y cuánto cuestan
(módulo 1); el flujo, la autonomía y la intervención humana, el framework y
el uso de copilotos (módulo 2); el despliegue, la evaluación con tests y
LLM como juez, y la monitorización en producción (módulo 3); y los
controles de seguridad, el análisis de riesgos y el red-teaming (módulo 4).
La nota máxima exige además que un tercero pueda usar el sistema sin carga
de mantenimiento. El tutor dijo que no se puntúa lo bonito, sino que estén
las decisiones y su porqué.

**Es una segunda versión.** Un primer análisis de la versión anterior (37
páginas) señaló estos problemas: se leía como un registro de ingeniería y
no como un documento explicativo; párrafos sobrecargados de cifras, con la
cifra antes que su explicación; cientos de referencias a hallazgos ("§22")
y rutas de fichero dentro de la prosa; ausencia de índice; temas repartidos
en varios sitios; y un orden de capítulos que no seguía el enunciado. Esta
versión se reescribió para corregirlo. No des por hecho que lo consiguió:
juzga el documento tal como está.

**Lo que te pido:**

1. **Diagnóstico general**: legibilidad (densidad, longitud de frases,
   jerga, siglas sin explicar), estructura (si se sigue el hilo de capítulo
   a capítulo) y adecuación al lector descrito arriba. Una valoración de 1 a
   10 en cada una, con su porqué.
2. **Los problemas de la versión anterior, uno por uno**: para cada uno de
   los listados arriba, si sigue, mejoró o desapareció, con un ejemplo
   literal del texto (cita la frase y la página o el capítulo).
3. **Los cinco problemas que más dificultan ahora la lectura**, cada uno
   con ejemplos literales.
4. **Lo que falta o sobra** para el lector descrito: algo que el enunciado
   pide y no se encuentra con facilidad, o algo que no aporta y alarga.
5. **Tres pasajes reescritos** como ejemplo: elige tres párrafos todavía
   difíciles, cítalos y reescríbelos más claros, sin inventar datos ni
   cambiar cifras.
6. **Lo que no hay que tocar.**

No reescribas el documento entero. Sé concreto y crítico; prefiero saber
qué falla a que me digas que está bien.
