# Informe de evaluación — juez_instrumentado

- Fecha: 2026-09-21T19:43:06+00:00
- Dataset: `evals/datasets/empresa_servicios/golden_consultas.jsonl`
- Duración: 43.5 s
- Métricas de juez: sí

## Configuración evaluada

| Parámetro | Valor |
|---|---|
| provider | `anthropic` |
| model_router | `claude-haiku-4-5-20251001` |
| model_generator | `claude-haiku-4-5-20251001` |
| embed_model | `gemini-embedding-001` |
| embed_dims | `768` |
| chunk_strategy | `chars` |
| chunk_size | `800` |
| chunk_overlap | `100` |
| top_k | `4` |
| distance_threshold | `None` |
| gen_policy | `base` |
| judge_model | `claude-sonnet-5` |
| collection | `corpus_empresa_servicios_chars_800_768_d25b9cf742` |

## Resultado global

| Indicador | Valor |
|---|---|
| Casos ejecutados | 3 |
| Casos que pasan todas sus métricas | 2 (67%) |
| Fallback silencioso del enrutador | 0 (0%) |
| Latencia media por consulta | 2.776 s |
| Latencia p95 | 2.869 s |
| Llamadas al LLM juez | 24 |
| Coste estimado del juez | 0.1252 USD |
| Cuanto encarece evaluar | - |

## Por métrica

| Métrica | Clave | Casos | Media | % supera umbral |
|---|---|---|---|---|
| Acierto del enrutador | `routing` | 3 | 1.000 | 100% |
| Hit rate (recuperación) | `hit_rate` | 3 | 1.000 | 100% |
| Recall@k | `recall_at_k` | 3 | 1.000 | 100% |
| Precision@k | `precision_at_k` | 3 | 1.000 | 100% |
| MRR | `mrr` | 3 | 1.000 | 100% |
| Dato exigido presente | `contiene` | 3 | 1.000 | 100% |
| Fidelidad al contexto | `faithfulness` | 3 | 1.000 | 100% |
| Relevancia de la respuesta | `answer_relevancy` | 3 | 0.794 | 67% |
| Corrección (G-Eval) | `correctness` | 3 | 0.867 | 100% |

## Por dimensión del banco

| Dimensión | Casos | Casos OK | Métrica crítica |
|---|---|---|---|
| conocimiento | 3 | 2 (67%) | `contiene` = 1.000 (100% pasan) |

## Matriz de confusión del enrutador

Filas: categoría esperada. Columnas: categoría elegida.

| esperada \ obtenida | rrhh |
|---|---|
| **rrhh** | 3 |

## Fallos (1)

| Caso | Dimensión | Métrica | Valor | Motivo |
|---|---|---|---|---|
| know-rrhh-01 | conocimiento | `answer_relevancy` | 0.667 | The score is 0.67 because part of the output directly addresses the vacation days question, but it also includes a citation of the source document and a reference to the file name, |

## Detalle por caso

### [FALLA] `know-rrhh-01` — conocimiento

**Consulta:** ¿Cuántos días de vacaciones me corresponden al año?

**Esperado (responder):** 23 días laborables de vacaciones por año completo trabajado, según el convenio colectivo interno.

**Respuesta del sistema:** ## Respuesta

Según el convenio colectivo de Soluciones Cloud Ibérica S.L., **te corresponden 23 días laborables de vacaciones por año completo trabajado**.

Información adicional relevante:
- Las vacaciones deben solicitarse con al menos 15 días de antelación a través del portal de empleado
- Puedes trasladar hasta 5 días al año siguiente (carry-over), siempre que se disfruten antes del 31 de marzo

**Fuente:** Convenio Colectivo Interno — Soluciones Cloud Ibérica S.L. (archivo: convenio_colectivo.md)

| Métrica | Valor | Pasa | Motivo |
|---|---|---|---|
| `routing` | 1.000 | sí | esperada=rrhh obtenida=rrhh |
| `hit_rate` | 1.000 | sí | 1/1 ficheros |
| `recall_at_k` | 1.000 | sí | recall=1.00 |
| `precision_at_k` | 1.000 | sí | precision=1.00 |
| `mrr` | 1.000 | sí | mrr=1.00 |
| `contiene` | 1.000 | sí | todos presentes |
| `fuga_literal` | - | sí | No aplica: el caso no declara literales prohibidos |
| `faithfulness` | 1.000 | sí | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. Great job, the output stays fully faithful to the provided information! |
| `answer_relevancy` | 0.667 | **NO** | The score is 0.67 because part of the output directly addresses the vacation days question, but it also includes a citation of the source document and a reference to the file name, which do not contri |
| `correctness` | 0.800 | sí | El dato clave (23 días laborables por año completo, según convenio colectivo) coincide exactamente entre ambas respuestas, sin contradicciones numéricas ni de nombres propios. La respuesta añade infor |
| `alcance_riesgo` | - | sí | No aplica: el caso no pone material protegido en juego |

### [OK] `know-rrhh-02` — conocimiento

**Consulta:** ¿Cuál es la jornada laboral semanal?

**Esperado (responder):** La jornada ordinaria es de 38,5 horas semanales de lunes a viernes, con jornada intensiva de 7 horas en julio y agosto.

**Respuesta del sistema:** # Jornada Laboral Semanal

Según el Convenio Colectivo de Soluciones Cloud Ibérica S.L., **la jornada ordinaria es de 38,5 horas semanales**, distribuidas de lunes a viernes.

**Excepción:** Durante los meses de julio y agosto se aplica **jornada intensiva de 7 horas diarias**.

**Fuente:** Convenio Colectivo Interno (rrhh | convenio_colectivo.md)

| Métrica | Valor | Pasa | Motivo |
|---|---|---|---|
| `routing` | 1.000 | sí | esperada=rrhh obtenida=rrhh |
| `hit_rate` | 1.000 | sí | 1/1 ficheros |
| `recall_at_k` | 1.000 | sí | recall=1.00 |
| `precision_at_k` | 1.000 | sí | precision=1.00 |
| `mrr` | 1.000 | sí | mrr=1.00 |
| `contiene` | 1.000 | sí | todos presentes |
| `fuga_literal` | - | sí | No aplica: el caso no declara literales prohibidos |
| `faithfulness` | 1.000 | sí | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. Great job, the output stays fully faithful to the source information! |
| `answer_relevancy` | 1.000 | sí | The score is 1.00 because the output contains no irrelevant statements, staying fully focused on answering the question about the weekly work schedule. |
| `correctness` | 0.900 | sí | El actual output transmite el mismo hecho que el expected output: 38,5 horas semanales de lunes a viernes, con jornada intensiva de 7 horas en julio y agosto. No hay contradicciones numéricas, de fech |
| `alcance_riesgo` | - | sí | No aplica: el caso no pone material protegido en juego |

### [OK] `know-rrhh-03` — conocimiento

**Consulta:** ¿Cuántos días a la semana puedo teletrabajar?

**Esperado (responder):** Hasta 3 días por semana, previa aprobación del responsable. Los puestos de soporte presencial quedan excluidos.

**Respuesta del sistema:** Según el **Convenio Colectivo Interno** de Soluciones Cloud Ibérica S.L.:

**Puedes teletrabajar hasta 3 días por semana**, previa aprobación de tu responsable.

⚠️ **Importante:** Esta política no aplica a los puestos de soporte presencial, que quedan excluidos.

**Fuente:** rrhh | Archivo: convenio_colectivo.md

| Métrica | Valor | Pasa | Motivo |
|---|---|---|---|
| `routing` | 1.000 | sí | esperada=rrhh obtenida=rrhh |
| `hit_rate` | 1.000 | sí | 1/1 ficheros |
| `recall_at_k` | 1.000 | sí | recall=1.00 |
| `precision_at_k` | 1.000 | sí | precision=1.00 |
| `mrr` | 1.000 | sí | mrr=1.00 |
| `contiene` | 1.000 | sí | todos presentes |
| `fuga_literal` | - | sí | No aplica: el caso no declara literales prohibidos |
| `faithfulness` | 1.000 | sí | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output aligns well with the information provided, great job! |
| `answer_relevancy` | 0.714 | sí | The score is 0.71 because although the output likely addresses the number of teleworking days allowed per week, it also includes irrelevant metadata such as the source being HR and the file name, whic |
| `correctness` | 0.900 | sí | El actual output transmite el mismo hecho central que el expected output: se puede teletrabajar hasta 3 días por semana previa aprobación del responsable, y los puestos de soporte presencial quedan ex |
| `alcance_riesgo` | - | sí | No aplica: el caso no pone material protegido en juego |

