# Prompt para el análisis de legibilidad de la memoria (encargo E-0025)

Pegar el texto de abajo, tal cual, en Gemini y en ChatGPT, con el PDF
adjunto (`docs/entrega/TFM_Juan_Archidona.pdf`). Mismo texto en los dos para
que los análisis se puedan comparar.

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

**Lo que me preocupa a mí, como autor, al releerlo:**

1. Es extenso (37 páginas) y difícil de leer de corrido.
2. Puede resultar inconexo: salta entre temas y no siempre se ve el hilo.
3. Hace referencias constantes a hallazgos ("§22", "§47") y a apartados de
   otros documentos que el lector no puede recordar ni consultar sin salir
   del texto.
4. No tiene índice.
5. Le falta ser explicativo: da muchas cifras y poca explicación de qué
   significan y por qué importan.

**Lo que te pido:**

1. **Diagnóstico general**: legibilidad (densidad, longitud de frases,
   jerga, siglas sin explicar), estructura (si se sigue el hilo de capítulo
   a capítulo) y adecuación al lector descrito arriba. Una valoración de 1 a
   10 en cada una, con su porqué.
2. **Los cinco problemas que más dificultan la lectura**, cada uno con
   ejemplos literales del texto (cita la frase y la página o el capítulo).
3. **Las referencias**: cuántas veces aproximadamente aparece "§" y otras
   referencias cruzadas, si estorban, y qué harías con ellas (quitarlas del
   cuerpo, notas al pie, un anexo, explicarlas en línea...).
4. **Estructura propuesta**: un índice de cómo reorganizarías el documento,
   qué recortarías o moverías a anexos, y qué longitud te parece razonable
   para el cuerpo principal sin perder lo que el enunciado pide.
5. **Tres pasajes reescritos** como ejemplo del estilo que propones: elige
   tres párrafos especialmente difíciles, cítalos y reescríbelos más claros
   y explicativos, sin inventar datos ni cambiar cifras.
6. **Lo que no hay que tocar**: lo que está bien y conviene conservar.

No reescribas el documento entero. Sé concreto y crítico; prefiero saber
qué falla a que me digas que está bien.
