# CLAUDE.md — Asistente multi-tenant (TFM)

> Fuente única de verdad del proyecto. Si algo de una conversación contradice
> este documento o `docs/ALCANCE.md`, gana el documento.
>
> Este repositorio **parte de la entrega 3.3 del máster** y conserva su historia
> de commits. Los ficheros del banco de evaluación, el corpus del inquilino
> heredado y buena parte de `src/` vienen de allí. Lo anterior a
> `docs: add TFM scope and closed decisions` es la 3.3, no este proyecto.

## 1. Qué es

**Asistente interno multi-tenant de conocimiento y datos para empresas de
servicios profesionales.** Responde consultas combinando dos fuentes:

- **Documental**: RAG sobre el corpus propio de cada cliente.
- **Estructurada**: datos de negocio consultados por **MCP**.

```
entrada → clasificador → recuperación (documental | estructurada)
        → generación anclada → gobernanza → salida
```

Es el Trabajo Fin de Máster de Juan Archidona Ahijado (Máster en IA Generativa
Avanzada, The Bridge). Se defiende en **octubre de 2026**.

El criterio con el que se evalúa, del programa del máster: *"el objetivo del
proyecto no está únicamente en que el sistema funcione, sino en justificar cada
decisión técnica en términos de calidad, coste, escalabilidad, riesgo y
mantenimiento"*. **Ante cualquier propuesta, la pregunta es si se puede medir.
Una afirmación sin número no vale.**

## 2. Estado (2026-09-20)

Funciona de extremo a extremo con dos inquilinos, las dos ramas de recuperación
y control de acceso estructural. **596 tests en verde**, `ruff` limpio.

| Pieza | Estado |
|---|---|
| Inquilino como concepto de primera clase | Hecho |
| Aislamiento entre inquilinos (colección propia) | Hecho y probado |
| Rama documental (RAG heredado) | Hecho |
| Rama estructurada (MCP) | Hecho |
| Control de acceso en las dos ramas | Hecho y medido |
| Bancos de evaluación por inquilino | Hecho (53 + 38 casos) |
| Cobertura del riesgo en el banco | Hecha y medida (A 0,636 / C 0,778) |
| Observabilidad y coste en producción | Pendiente |
| Canales (correo, WhatsApp) | Pendiente |
| Human-in-the-loop | Pendiente |
| Despliegue con autenticación y tope de gasto | Pendiente |
| Clasificador con modelo pequeño o afinado | Pendiente (bloque 3) |
| Alta cronometrada de un inquilino nuevo | Pendiente (bloque 4) |

El alcance completo, ordenado por prioridad y **con las líneas de corte ya
decididas**, está en `docs/ALCANCE.md` §4. La regla: se sacrifica alcance antes
que profundidad de la documentación.

## 3. Los dos inquilinos

| | `empresa_servicios` | `agencia_inmobiliaria` |
|---|---|---|
| Qué es | Empresa de servicios heredada de las entregas 2.3/3.1/3.3 | Domara Inmobiliaria, agencia ficticia de Zaragoza |
| Para qué está | Sostener el banco heredado como **suite de regresión** | Demostrar agnosticidad y la rama estructurada |
| Categorías | rrhh, desarrollo, actas, marca | cartera (estructurada), expedientes, procesos, normativa, comercial, actas |
| Corpus | 7 documentos | 10 documentos |
| Banco | 53 casos | 38 casos |
| MCP | No | `mcp_servers/agencia_crm.py` |

Ambos son **sintéticos**. Ningún dato real de ninguna empresa entra aquí: el
repositorio es público.

## 4. Decisiones cerradas, y por qué

- **Colección de Chroma por inquilino**, no un índice filtrado por metadato. El
  aislamiento tiene que ser estructural: un filtro mal construido en una sola
  ruta de consulta devuelve documentos de otro cliente sin que nada lo señale.
- **Servidores MCP**, no herramientas cableadas. Un `tools=[...]` dentro del
  agente ata el sistema a la API de un cliente; un servidor lo convierte en
  contrato.
- **Control de acceso antes del modelo.** El permiso va **dentro del `where`**
  de la búsqueda y la redacción se aplica al salir de la herramienta. Un prompt
  que dice "no reveles el DNI" deja el DNI en la ventana de contexto.
- **Python vanilla**, con un capítulo de justificación comparándolo con
  LangGraph. El capstone puntúa la justificación, no la herramienta.
- **Todo lo que distingue a un inquilino es declarativo**: categorías, fuentes,
  servidores MCP y política de acceso viven en `tenants/<id>.json`. Si dar de
  alta un cliente exige editar un `.py`, la costura está mal puesta — y eso se
  mide cronometrando el alta al final del proyecto.

## 5. Reglas de trabajo

- **No se relaja el banco.** Se corrige un caso cuando la expectativa era
  incorrecta, nunca cuando el resultado incomoda. Cada corrección se justifica
  por escrito en `docs/HALLAZGOS.md`.
- **Nada de fallbacks silenciosos.** Si algo degrada —parseo fallido,
  recuperación vacía, servidor caído— se marca y se propaga. La confusión más
  cara es que "el CRM está caído" se lea como "no tengo esa información".
- **La línea base heredada no se toca.** Hay un test que compara el prompt del
  enrutador carácter a carácter con el de la 3.3; si cambia, las métricas de los
  109 casos dejan de ser comparables.
- **Sin emoticonos** en código, documentos, commits ni interfaz.
- **Sin atribución a Claude** en commits ni entregables.
- Commits en inglés, conventional commits. Documentación en español.
- Ningún dato personal real, en ningún sitio.

## 6. Estructura

```
corpus/<tenant>/<fuente>/*.md      Documentos de cada inquilino
datos/<tenant>/crm.json            Datos de negocio sintéticos (generados)
tenants/<tenant>.json              Manifiesto: categorías, MCP, política
mcp_servers/                       Servidores MCP por inquilino
scripts/                           Generadores reproducibles (semilla fija)
src/
  tenant.py       Inquilino: categorías, destinos, servidores, política
  gobernanza.py   Control de acceso: permisos y redacción
  mcp_cliente.py  Cliente MCP (hilo con bucle propio)
  agent.py        Orquestación y bifurcación de ramas
  router.py       Enrutador (prompt construido desde el manifiesto)
  retriever.py    Recuperación filtrada por fuente y por permiso
  provider.py     Abstracción de proveedor, con tool-calling
evals/            Banco: datasets por inquilino, métricas, runner, barrido
reports/          Evidencia de cada ejecución
docs/
  ALCANCE.md      Decisiones cerradas y alcance por bloques
  HALLAZGOS.md    Hallazgos medidos, con la ejecución que los respalda
```

## 7. Comandos

```bash
uv sync --group judge
uv run pytest                                      # 596 tests, sin llamadas a API
uv run ruff check src evals tests mcp_servers scripts

uv run python -m src.ingest_cli                    # indexa el inquilino activo
TENANT_ID=agencia_inmobiliaria uv run python -m src.ingest_cli

uv run python -m evals.runner --etiqueta X --sin-juez   # banco sin coste de juez
uv run python scripts/generar_crm_agencia.py            # regenera el CRM sintético
```

`TENANT_ID` selecciona el inquilino; por defecto, `empresa_servicios`.

**Al cambiar el corpus, la política de acceso o el esquema de metadatos hay que
reindexar.** La firma del índice cubre las tres cosas —el corpus desde §14, que
es cuando costó una ejecución entera descubrir que faltaba—, pero conviene
saberlo: un índice obsoleto no da error, devuelve vacío (`docs/HALLAZGOS.md` §10
y §14).

## 8. Riesgos abiertos

- No se dispone del enunciado oficial ni de la rúbrica del TFM.
- Reutilizar entregas propias calificadas no está verificado en ninguna
  normativa.
- Sin tope de gasto en la cuenta de Anthropic; cerrar antes de exponer el
  despliegue.
- **Cobertura del riesgo: 0,636 en A y 0,778 en C.** Resuelto lo que se podía
  resolver enrutando (§12). Lo que queda son casos que no llegan al control por
  fallo de enrutado, y subirlos es trabajo de enrutador, no de gobernanza.
- **`expedientes` y `cartera` se solapan y no se arregla escribiendo mejor.** Los
  datos de las partes de una operación viven a la vez en el expediente
  documental y en el CRM, así que la ambigüedad está en el modelo de datos y no
  en la pregunta. Medido dos veces (§6, §12). La salida es que una consulta
  ambigua **consulte las dos ramas** en vez de elegir: decisión de arquitectura
  pendiente, afecta a dos casos.
- **El enrutador no repite: 11 % de los casos cambia de categoría entre pasadas
  idénticas** (§15). Ningún acierto global del enrutador se puede reportar de una
  sola pasada. Los casos de seguridad sí son estables, así que la cobertura se
  puede leer; el acierto global no.

## 9. Mantenimiento

Al cerrar un avance relevante: actualizar la sección 2, anotar el hallazgo
medido en `docs/HALLAZGOS.md` citando su ejecución, y commitear junto al código.
