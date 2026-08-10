# Entrega Módulo 3.3 — Evaluación de agentes

Banco de pruebas del **asistente RAG con enrutador** construido en las entregas
2.1, 2.3 y 3.1: casos con tarea y respuesta esperada, métricas por capa,
ejecución real sobre el MVP y expansión sintética validada del banco.

- MVP evaluado (entrega 3.1, calificada 10/10): https://github.com/JuanArchidona/master_ia_entrega_3.1
- Agente productor de actas (2.1): https://github.com/JuanArchidona/master_ia_entrega_2.1
- Asistente RAG con enrutador (2.3): https://github.com/JuanArchidona/master_ia_entrega_2.3

## Por qué esta entrega existe

La corrección de la 3.1 señaló tres huecos: no había **tests automatizados que
puntuaran cambios** de modelo, embedder o chunking; no había **observabilidad**;
y no había **control de costes**. El primero es el que desbloquea a los otros dos
— sin forma de medir, cualquier iteración es a ojo — y es exactamente lo que
pide el enunciado del módulo 3.3. Este repo lo implementa.

El plan estaba escrito en
[`docs/PROXIMOS_PASOS.md`](https://github.com/JuanArchidona/master_ia_entrega_3.1/blob/master/docs/PROXIMOS_PASOS.md)
de la 3.1; aquí se ejecuta.

## Qué contiene

```
corpus/                     # el corpus del RAG, ampliado con material de confidencialidad
src/                        # sistema bajo prueba (vendorizado de la 3.1, parametrizado)
evals/
  schema.py                 # esquema de un caso: tarea, respuesta esperada, criterio
  datasets/
    golden_consultas.jsonl        # 52 casos curados a mano, 8 dimensiones
    golden_transcripcion.jsonl    # 5 casos del agente transcriptor (flujo 2.1)
    sinteticos_consultas.jsonl    # casos generados y validados automáticamente
  metrics/
    deterministas.py        # enrutado, recuperación, literales (sin coste, sin varianza)
    juez.py                 # DeepEval: faithfulness, relevancia, G-Eval, PII leakage
  runner.py                 # ejecuta el banco y escribe los informes
  sweep.py                  # barrido de configuraciones sobre recuperación
  generar_sinteticos.py     # generación + doble validación de casos nuevos
  transcripcion.py          # evaluación determinista del agente 2.1
reports/                    # resultados de las ejecuciones (evidencia de la entrega)
tests/                      # 322 pruebas sin llamadas a API (puerta de CI)
docs/VALORACION_MVP.md      # lectura de los resultados y qué hacer con ellos
```

## Los cuatro niveles del enunciado

| Nivel | Qué pedía | Dónde está |
|---|---|---|
| Mínimo | Banco de pruebas | `evals/datasets/golden_consultas.jsonl` — 52 casos en 8 dimensiones, con respuesta esperada y criterio |
| Medio | Selección de métricas objetivo | `evals/schema.py` (`METRICAS_POR_DIMENSION`) y `evals/metrics/` — 13 métricas en 4 capas, con umbral justificado por métrica |
| Pro | Ejecución y valoración del MVP | `reports/` y [`docs/VALORACION_MVP.md`](docs/VALORACION_MVP.md) |
| Peter Steinberger | Pruebas sintéticas expandiendo las iniciales | `evals/generar_sinteticos.py` → 57 casos aceptados de 110 candidatos; el banco pasa de 52 a 109 |

## Resultados en una tabla

Sobre el MVP tal cual salió de la 3.1, sin modificarlo:

| | Resultado |
|---|---|
| Casos que pasan todas sus métricas | 45/52 con métricas deterministas, 35/52 añadiendo el juez |
| Recuperación | hit_rate 1,000 · recall@k 1,000 · MRR 0,982 · precision@k 0,708 |
| Dato exigido presente | 35/35 |
| **Fugas de datos personales** | **2** (salario individual y datos de salud) |
| Coste y latencia | 0,0021 USD por consulta · 3,8 s de media · 5,3 s p95 |
| Mejor configuración del barrido | `headings` + `top_k=2`: precisión 0,674 → 0,919 sin perder recall |
| Efecto de subir dimensiones del embedder | Ninguno (1536 y 3072 idénticos a 768) |
| Prompt endurecido | Las 2 fugas desaparecen; coste: relevancia 0,880 → 0,778 |
| Agente transcriptor (flujo 2.1) | 4/5 · fecha exacta 5/5 · ninguna fuga · inyección ignorada |

La lectura completa, con las causas y qué hacer con cada hallazgo, está en
[`docs/VALORACION_MVP.md`](docs/VALORACION_MVP.md).

## Diseño del banco

### Cuatro capas, porque fallan por motivos distintos

| Capa | Métricas | Coste por caso |
|---|---|---|
| Enrutado | acierto, matriz de confusión, **tasa de fallback silencioso** | 1 llamada al modelo ligero |
| Recuperación | hit_rate, recall@k, precision@k, MRR | 1 embedding |
| Generación | faithfulness, answer relevancy, corrección (G-Eval), abstención, confidencialidad, PII leakage | juez LLM |
| Transcripción (2.1) | F1 por campo sobre decisiones, tareas y asistentes; fecha exacta; ausencia de fugas | 1 llamada |

Separarlas es lo que permite diagnosticar: si la fidelidad baja, se mira antes
la recuperación para saber si el problema es que el generador inventa o que le
llegó basura.

### Ocho dimensiones, no solo preguntas fáciles

`conocimiento`, `frontera` (suena a una categoría pero es de otra), `agregacion`
(requiere combinar documentos), `fuera_de_alcance` (verosímil pero ausente del
corpus), `confidencialidad`, `inyeccion`, `robustez` (erratas y jerga) y
`fuera_de_dominio`.

Un banco de solo preguntas contestables premia al sistema que siempre contesta
algo, que es justo el que alucina. **Diecisiete de los 52 casos exigen abstenerse
o denegar**; son los que detectan alucinación y fugas.

### Métricas deterministas primero

Todo lo que se puede medir sin juez se mide sin juez: no cuesta, no tiene
varianza entre ejecuciones y se puede lanzar sobre el set sintético completo y
en cada barrido. El juez LLM se reserva para lo que de verdad exige criterio.

### El juez nunca es el modelo evaluado

Genera `claude-haiku-4-5`, juzga `claude-sonnet-5`, y `Config` rechaza la
configuración si coinciden. Lo ideal sería cambiar también de familia (el juez
es conmutable a Gemini con `JUDGE_PROVIDER=gemini`), pero la cuota gratuita de
Gemini permite 20 generaciones al día, insuficiente. Queda como limitación
declarada del informe, y por eso el veredicto se ancla en las deterministas.

## Ejecución

Requisitos: [uv](https://docs.astral.sh/uv/) y Python >= 3.11.

```bash
cp .env.example .env        # rellenar ANTHROPIC_API_KEY y GEMINI_API_KEY
uv sync --group judge
```

```bash
# Banco completo sobre el MVP tal cual (línea base)
uv run python -m evals.runner --etiqueta baseline

# Solo métricas deterministas: gratis, segundos, sin juez
uv run python -m evals.runner --etiqueta rapido --sin-juez

# Una variante del sistema, sin tocar el .env
uv run python -m evals.runner --etiqueta endurecido --gen-policy hardened

# Reevaluar una ejecución anterior sin volver a llamar al sistema
uv run python -m evals.runner --etiqueta rejuicio --desde-trazas reports/baseline/trazas.jsonl

# Barrido de configuraciones (solo embeddings: sin generación ni juez)
uv run python -m evals.sweep

# Expandir el banco con casos sintéticos validados
uv run python -m evals.generar_sinteticos

# Agente transcriptor (flujo 2.1)
uv run python -m evals.runner --suite transcripcion --etiqueta transcripcion
```

Cada ejecución escribe en `reports/<etiqueta>/`: `trazas.jsonl` (lo que hizo el
sistema), `resultados.json` (métrica a métrica), `resumen.json` (agregados) e
`informe.md` (lectura humana).

Las ejecuciones que acompañan a esta entrega:

| Carpeta | Qué contiene |
|---|---|
| `reports/baseline/` | El MVP de la 3.1 con todas las métricas |
| `reports/baseline_repeticion/` | Segunda pasada del juez sobre las mismas trazas: mide su variabilidad |
| `reports/baseline_determinista/` | Las mismas trazas solo con métricas deterministas |
| `reports/endurecido/` | La variante `GEN_POLICY=hardened`, para comparar |
| `reports/sintetico/` | Los 57 casos generados automáticamente |
| `reports/transcripcion/` | El agente transcriptor (flujo 2.1) |
| `reports/sweep/` | Las 11 configuraciones de chunking, `top_k` y dimensiones |

## Dos decisiones de método que abaratan el banco

**El barrido no genera respuestas.** Comparar configuraciones de chunking o
embedder es un problema de recuperación: si mejoran los fragmentos que llegan al
generador, la respuesta solo puede mejorar. Medir la generación en cada
combinación multiplicaría el coste por veinte para ver el mismo efecto con más
ruido. Once configuraciones cuestan unos pocos céntimos de embeddings.

**El barrido se salta el enrutador.** Cada consulta se busca directamente en la
fuente que el golden set declara correcta. No es un atajo: un error de enrutado
contaminaría por igual a todas las configuraciones y solo añadiría varianza. El
acierto del enrutador se mide aparte, en el banco principal.

## Cambios en el sistema bajo prueba

Vendorizado de la 3.1 con lo mínimo para poder evaluarlo:

- **Parámetros de calidad en `Config`**: `CHUNK_STRATEGY`, `CHUNK_SIZE`,
  `CHUNK_OVERLAP`, `EMBED_DIMS`, `TOP_K`, `DISTANCE_THRESHOLD`, `GEN_POLICY`.
  En la 3.1 estaban hardcodeados, y lo que está hardcodeado no se puede barrer.
- **Chunking por encabezados** como alternativa al de caracteres.
- **`Enrutamiento.fallback`**: el fallo de parseo se marca en vez de disfrazarse
  de clasificación `otro`.
- **Contabilidad de tokens en `provider.py`**: la 3.1 descartaba el bloque
  `usage`. Es la base del control de costes que pedía la corrección.
- **`SYSTEM_GEN_HARDENED`**: variante del prompt con reglas de confidencialidad
  y de resistencia a inyección, para poder **puntuar el cambio de prompt** en vez
  de decidirlo a ojo. La línea base sigue siendo el prompt literal de la 3.1.

## Alcance y evolución natural

**En alcance**: banco curado y sintético, métricas por capa, ejecución real,
barrido de configuraciones, evaluación del transcriptor, CI y valoración escrita.

**Fuera de alcance (roadmap)**:

- Observabilidad en producción (Langfuse/Opik sobre `get_chat()`) — el bloque B
  del roadmap de la 3.1, que este banco no sustituye: mide en laboratorio, no en
  producción.
- Evaluación conversacional multiturno; el banco es de un turno.
- Juez de familia distinta a la del generador, cuando la cuota lo permita.
- Anotación humana de una muestra para medir el acuerdo con el juez LLM: sin
  eso, la calidad del juez es una suposición razonable, no un dato.
