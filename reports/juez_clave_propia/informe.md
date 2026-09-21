# Informe de evaluación — juez_clave_propia

- Fecha: 2026-09-21T19:59:04+00:00
- Dataset: `evals/datasets/empresa_servicios/golden_consultas.jsonl`
- Duración: 23.7 s
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
| Casos ejecutados | 2 |
| Casos que pasan todas sus métricas | 2 (100%) |
| Fallback silencioso del enrutador | 0 (0%) |
| Latencia media por consulta | 2.827 s |
| Latencia p95 | 2.869 s |
| Llamadas al LLM juez | 16 |
| Coste estimado del juez | 0.0826 USD |
| Cuanto encarece evaluar | - |

## Por métrica

| Métrica | Clave | Casos | Media | % supera umbral |
|---|---|---|---|---|
| Acierto del enrutador | `routing` | 2 | 1.000 | 100% |
| Hit rate (recuperación) | `hit_rate` | 2 | 1.000 | 100% |
| Recall@k | `recall_at_k` | 2 | 1.000 | 100% |
| Precision@k | `precision_at_k` | 2 | 1.000 | 100% |
| MRR | `mrr` | 2 | 1.000 | 100% |
| Dato exigido presente | `contiene` | 2 | 1.000 | 100% |
| Fidelidad al contexto | `faithfulness` | 2 | 1.000 | 100% |
| Relevancia de la respuesta | `answer_relevancy` | 2 | 0.817 | 100% |
| Corrección (G-Eval) | `correctness` | 2 | 0.850 | 100% |

## Por dimensión del banco

| Dimensión | Casos | Casos OK | Métrica crítica |
|---|---|---|---|
| conocimiento | 2 | 2 (100%) | `contiene` = 1.000 (100% pasan) |

## Matriz de confusión del enrutador

Filas: categoría esperada. Columnas: categoría elegida.

| esperada \ obtenida | rrhh |
|---|---|
| **rrhh** | 2 |

## Fallos (0)

Ninguna métrica por debajo de su umbral.

## Detalle por caso

### [OK] `know-rrhh-01` — conocimiento

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
| `faithfulness` | 1.000 | sí | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. All claims made in the actual output are fully supported by the retrieval context, demonstrat |
| `answer_relevancy` | 0.833 | sí | The score is 0.83 because most of the output directly addresses the question about annual vacation days, but it includes one irrelevant statement, a file reference, that doesn't contribute to answerin |
| `correctness` | 0.800 | sí | El dato clave (23 días laborables por año completo) coincide exactamente con el expected output, sin contradicciones numéricas ni de nombres propios. La respuesta añade información adicional (plazo de |
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
| `faithfulness` | 1.000 | sí | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output aligns perfectly with the information provided, great job! |
| `answer_relevancy` | 0.800 | sí | The score is 0.80 because most of the output directly addresses the weekly working hours question, but it includes a source citation that doesn't contribute to answering what the weekly working hours  |
| `correctness` | 0.900 | sí | El actual output transmite el mismo hecho que el expected output: 38,5 horas semanales de lunes a viernes, con jornada intensiva de 7 horas en julio y agosto. No hay contradicciones numéricas, de fech |
| `alcance_riesgo` | - | sí | No aplica: el caso no pone material protegido en juego |

