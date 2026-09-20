> Versión: 1.0 · Actualizado: 2026-09-20 · Idioma: ES

# Alcance del TFM — decisiones cerradas

Documento de reorientación del TFM, acordado el 2026-09-20. Sustituye al roadmap
de la sección 9 del `CLAUDE.md`, que estaba escrito en junio dando por hecho un
arranque desde cero.

El cambio de fondo: el TFM **no se construye desde este repositorio vacío**, sino
sobre el sistema acumulado en las entregas 2.1, 2.3, 3.1 y 3.3, que ya cubre
cuatro de los seis pasos del flujo objetivo y trae consigo un banco de evaluación
de 109 casos.

## 1. Por qué se reorienta

El Módulo 5 se define en el programa como *"Capstone Project: diseño y defensa de
un sistema GenAI"*, con este criterio: **"el objetivo del proyecto no está
únicamente en que el sistema funcione, sino en justificar cada decisión técnica
en términos de calidad, coste, escalabilidad, riesgo y mantenimiento"**.

Eso no premia construir mucho, premia poder justificar con números. Y justificar
con números es exactamente lo que produce el banco de la 3.3. Partir de cero
habría significado gastar el mes en reconstruir lo que ya está medido.

### Punto de partida heredado

| Paso del flujo objetivo | Estado al 2026-09-20 |
|---|---|
| Trigger | Interfaz Streamlit desplegada (3.1) |
| Clasificador | Hecho y medido: acierto, matriz de confusión, fallback |
| Recuperación documental | Hecha y optimizada: barrido de 11 configuraciones |
| Recuperación estructurada | **No existe** |
| Generación | Hecha, anclada al contexto y con cita de fuente |
| Guardrails | Parcial: el fallo está medido (2 fugas), no corregido |
| Output | Un solo canal |

Dos de los cinco requisitos no funcionales del documento de concepto ya están
medidos y cumplidos: latencia (3,8 s de media, 5,3 s p95, frente al objetivo de
3-8 s) y coste (0,0021 USD por consulta, frente al objetivo de "céntimos"). Los
que faltan son PII y human-in-the-loop.

## 2. Decisiones cerradas

| Decisión | Resolución |
|---|---|
| Punto de partida | Fork del repo de la 3.3, en repositorio nuevo y **público** |
| Orquestación | **Python vanilla**, más un capítulo de justificación con prototipo mínimo en LangGraph para comparar |
| Posicionamiento | Asistente interno de conocimiento y datos para **servicios profesionales**, no "cualquier sector" |
| Tenants | **A** (empresa de servicios, heredado) y **C** (agencia inmobiliaria, completo) |
| Rama estructurada | Servidores **MCP**, no function calling suelto |
| Gobernanza | PII, filtrado por permisos en la recuperación, HITL y trazabilidad |
| Observabilidad | Trazas y coste acumulado en producción |
| Canales | Correo real, más WhatsApp contra la Cloud API en entorno de pruebas |
| Modelo del clasificador | Modelo pequeño local o afinado, **comparado con medidas** contra Haiku |
| Despliegue | Render, con autenticación y tope de gasto |
| Módulo 4 | Su análisis se produce **dentro del TFM**; la entrega del 4.x se extrae de aquí |

### Decisiones descartadas y por qué

- **Tenant B (asesoría).** Se valoró un tercer tenant de asesoría fiscal y
  laboral, apoyado en una sesión real con un prospecto. Descartado para
  concentrar el esfuerzo en dos tenants bien construidos. La sesión se conserva
  como **investigación de usuario anonimizada** en la definición del problema,
  sin construirle tenant.
- **Slack como canal.** El segmento objetivo no lo usa. Sustituido por correo y
  WhatsApp.
- **Multi-tenancy genérica sin tenants concretos.** Un corpus deliberadamente
  vago no demuestra agnosticidad, la esconde.

## 3. Los dos tenants

**Tenant A — empresa de servicios (heredado, sin cambios).** Corpus actual de
RRHH, desarrollo, marca y actas. Su función no es narrativa: es mantener vivos
los 109 casos del banco como **suite de regresión**, para que cualquier pieza
nueva se pueda comprobar contra una línea base medida. Incluye el anexo
confidencial y el acta con inyección de prompt, que son el material de ataque de
la capa de gobernanza.

**Tenant C — agencia de compraventa y alquiler (nuevo, completo).** Elegido por
ser el más alejado estructuralmente del tenant A: aquí los datos son mercado y
operaciones, no políticas internas. Corpus propio, golden set propio y las dos
ramas de recuperación funcionando.

Su rama estructurada consume **dos servidores MCP**:

1. **Interno**: cartera, leads, visitas y ofertas, sobre datos sintéticos.
2. **Externo real**: los [servicios web libres del
   Catastro](https://www.catastro.hacienda.gob.es/ws/Webservices_Libres.pdf),
   oficiales, gratuitos y sin clave, envueltos en un servidor MCP propio.

El valor del segundo es que enfrenta el contrato de herramientas a un sistema
externo real, con sus timeouts, sus huecos de datos y sus fallos.

### Sobre idealista

Verificado el 2026-09-20, en dos pasos.

**Existe un servidor MCP oficial**, `https://mcp-app.idealista.com/claude/v1/mcp`,
publicado por idealista S.A.U. y sin inicio de sesión obligatorio. **Pero está
cerrado a clientes externos**: el handshake `initialize` devuelve 403 de
Cloudflare, con y sin User-Agent identificativo. No se intentó sortear el bloqueo.

No es una barrera mal configurada, es política declarada. Su [documentación
oficial](https://idealista.github.io/mcp-app-docs/claude/) lo dice sin
ambigüedad:

> It is only available through the official idealista connector approved for
> Claude, and it does not support manual configuration from other MCP clients.

Expone cuatro herramientas: `search_properties`, `property_detail`, `get_howto` y
`guide_idealista_assistant`. Los servidores MCP de idealista que hay en el
ecosistema abierto son **scrapers** de terceros, incompatibles con las
condiciones de uso.

Plan resultante:

1. El código del TFM **no llama a idealista**. La fuente externa real en
   ejecución es el Catastro.
2. El conector de idealista se usa **solo durante el desarrollo**, desde Claude,
   para generar la cartera sintética del tenant C con forma y precios realistas.
3. Solicitado el acceso a la [API
   oficial](https://developers.idealista.com/access-request) el 2026-09-20, sin
   número de referencia ni plazo comprometido. Si llega a tiempo, se integra como
   tercera fuente.
4. Enviada consulta a soporte por credenciales de desarrollo del MCP. El canal es
   el formulario genérico de `idealista.com/info/contacto`, sin correo publicado.
   Dada la documentación citada arriba, la respuesta esperable es negativa.

### Dos hallazgos que se llevan a la memoria

- **La PII no entra solo por el corpus.** La respuesta del conector incluye
  `contactInfo.phone1.phoneNumber` y descripciones en texto libre. La
  anonimización tiene que envolver **las dos ramas de recuperación**, no solo la
  documental. Decisión de arquitectura justificada con una prueba.
- **Depender de un MCP de terceros es un riesgo de negocio, no técnico.** Su
  disponibilidad la decide el proveedor. El 403 es la evidencia, y sostiene el
  argumento de mantenimiento que pide el capstone.

## 4. Alcance por prioridad, con líneas de corte

Las horas semanales disponibles no están fijadas. El alcance se ordena por
prioridad y **la línea de corte se decide ahora**, no en octubre con prisa.

### Bloque 1 — Núcleo (no se corta)

1. Fork del repo de la 3.3 y reorganización a estructura multi-tenant.
2. `tenant_id` en el estado, aislamiento en el índice y en la recuperación.
3. Autenticación y tope de gasto en el despliegue.
4. Rama estructurada: servidor MCP interno del tenant C y nodo de recuperación.
5. Corpus y golden set del tenant C.
6. El banco de 109 casos del tenant A pasando en verde tras cada cambio.

### Bloque 2 — Lo que distingue al TFM

7. Capa de gobernanza: anonimización de PII antes de salir al LLM, filtrado por
   permisos en la recuperación, HITL y registro de quién preguntó qué.
8. Análisis de riesgos y encaje con el EU AI Act (absorbe el Módulo 4).
9. Servidor MCP del Catastro como fuente externa real.
10. Observabilidad en producción y coste acumulado por tenant.
11. Canal de correo, de extremo a extremo.

### Bloque 3 — Lo que se cae primero si falta tiempo

12. Clasificador con modelo pequeño local o afinado, con comparativa medida.
13. Canal de WhatsApp en entorno de pruebas.
14. Prototipo en LangGraph para la comparativa de orquestación (si se cae, la
    comparativa se sostiene igual, argumentada sin prototipo).

### Bloque 4 — Cierre (no se corta)

15. Alta cronometrada de un tenant nuevo: horas invertidas y líneas tocadas en el
    núcleo. Es la prueba medida de agnosticidad.
16. Memoria técnica y preparación de la defensa.

**Regla de corte**: si hay que elegir, se sacrifica siempre alcance del bloque 3
antes que profundidad de la documentación del bloque 4. El capstone puntúa la
justificación, no el número de funcionalidades.

## 5. Activos comerciales que produce el TFM

Acordados como entregables propios, no como subproducto:

1. **Cifra de coste de alta de un cliente nuevo** — horas y elementos a tocar,
   medidos en el punto 15. Convierte una propuesta en una conversación con
   números.
2. **Demo pública multi-tenant navegable** — la aplicación desplegada con los dos
   tenants, para enseñar en una primera llamada sin montar nada.
3. **Ficha de coste por consulta y por cliente** — desglose mensual según
   volumen, apoyado en la contabilidad de tokens ya existente.
4. **Artículos técnicos** sobre los hallazgos medibles, sin datos de cliente.

Restricción: nada de lo publicable puede contener datos identificables de
prospectos reales.

## 6. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| No se dispone del enunciado oficial ni de la rúbrica del TFM | **Abierto** — lo citado procede del programa del máster, no de instrucciones de evaluación |
| Reutilizar entregas propias calificadas | **Abierto** — es lo esperable en un capstone que pide integrar los módulos, pero no está verificado en ninguna normativa |
| Clave de API de Anthropic revocada | **Resuelto** el 2026-09-20 — dos claves nuevas, sistema y juez, validadas |
| Sin tope de gasto en la cuenta de Anthropic | **Abierto** — las claves viven en el workspace por defecto, sin límite mensual. Cerrar antes de exponer el despliegue |
| Enunciado del Módulo 4 sin publicar | **Abierto** — solo hay presentación del módulo; el encaje con el TFM se confirma al publicarse |
| Aprobación de la API de idealista | Mitigado — el Catastro cubre la función sin depender de aprobación |
| Verificación de negocio de WhatsApp | Mitigado — entorno de pruebas con números de test, y bloque 3 |

## 7. Lo que queda fuera del TFM

- Conectores reales a CRM comerciales (HubSpot, Salesforce, Zendesk).
- Omnicanalidad completa: se implementan dos canales, no tres.
- Despliegue íntegramente local con modelos open source, más allá del
  clasificador.
- Evaluación conversacional multivuelta: el banco sigue siendo de un turno.
- Anotación humana para medir el acuerdo con el juez LLM.
