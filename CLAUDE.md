# CLAUDE.md — Entrega Módulo 3.3: Evaluación de agentes

> Contexto de esta entrega. El contexto global del máster (alumno, convenciones,
> patrón técnico) se carga automáticamente desde `Master/CLAUDE.md` — no repetirlo aquí.

## Estado

- **Fase:** implementación completa, pendiente de presentar en el campus.
- **Entregable:** repo + `Entrega_Modulo_3.3_Juan_Archidona.pdf`.
- **Repo GitHub:** https://github.com/JuanArchidona/master_ia_entrega_3.3
- Material del profesor en `../Documentación/01_Evaluación de agentes.pptx` y los
  notebooks de clase (`02_Evaluación_de_modelos_con_DeepEval.ipynb`,
  `03_Evaluando_el_retrieved_de_nuestro_RAG.ipynb`).

## Enunciado (resumen)

Validar que el agente hace lo que debe. Crear ejemplos con tarea y respuesta
esperada, elegir métricas según el caso (RAG, filtrado de información privada…)
y, si se puede, ejecutar y valorar el MVP. Cuatro niveles: banco de pruebas
(mínimo), selección de métricas (medio), ejecución y valoración (pro), pruebas
sintéticas que expanden las iniciales (Peter Steinberger). Referencia sugerida
—no obligatoria—: el tutorial de DeepEval sobre el agente de resumen.

## Relación con las entregas anteriores

El sistema evaluado es el MVP de la **3.1** (calificada 10/10), que a su vez
integra el agente de transcripción de la **2.1** y el asistente RAG con
enrutador de la **2.3**. La corrección de la 3.1 pidió explícitamente tests
automatizados que puntúen cambios de modelo, embedder y chunking; el plan quedó
escrito en `Módulo 3/3.1/Entrega/docs/PROXIMOS_PASOS.md` (bloque A) y esta
entrega lo ejecuta.

## Decisiones de esta entrega

- **Stack híbrido**: DeepEval para las métricas de juez LLM (es lo que enseñó el
  profesor y lo que enlaza el enunciado) y harness propio para las deterministas
  de enrutado y recuperación. Una librería de juez en las deterministas solo
  añadiría coste y varianza.
- **Sistema bajo prueba vendorizado** (`src/` + `corpus/` copiados de la 3.1) en
  lugar de submódulo: el repo es autocontenido y evaluable de un `uv sync`.
- **Parámetros de calidad subidos a `Config`** (chunking, dims, top_k, umbral de
  distancia, política del prompt). Sin esto no hay barrido posible.
- **Corpus ampliado** con un anexo confidencial ficticio (salarios, DNIs, IBANs,
  datos de salud) y un acta con una inyección de prompt embebida. Sin material
  sensible, las métricas de PII darían cero fugas por ausencia de datos, no por
  mérito del sistema.
- **Juez ≠ modelo evaluado**, validado en `Config`. Genera `claude-haiku-4-5`,
  juzga `claude-sonnet-5`. Cambiar además de familia (Gemini) sería mejor y está
  soportado (`JUDGE_PROVIDER=gemini`), pero la cuota gratuita de Gemini son 20
  generaciones al día. Limitación declarada en el informe.
- **El barrido de configuraciones no genera respuestas ni usa juez**: compara
  solo recuperación, saltándose el enrutador para no meter su varianza en la
  comparación. Once configuraciones cuestan céntimos.
- **`GEN_POLICY=base|hardened`**: la línea base es el prompt literal de la 3.1;
  la variante endurecida añade confidencialidad y resistencia a inyección. Así
  el cambio de prompt se puntúa en vez de decidirse a ojo.
- Sin emojis en ningún texto, documento o código (preferencia global de Juan).

## Hallazgos de la ejecución

Ver [`docs/VALORACION_MVP.md`](docs/VALORACION_MVP.md) para el detalle. En corto:

- El MVP **filtra datos personales** (salario individual y datos de salud) cuando
  la consulta llega a recuperar el anexo confidencial: `SYSTEM_GEN` de la 3.1 no
  tiene ninguna regla de confidencialidad. Es el fallo más grave y el banco lo
  demuestra con literales, no con opiniones.
- La **variante endurecida del prompt elimina las dos fugas** sin romper el caso
  de control (la banda salarial agregada se sigue respondiendo) y supera la
  prueba de inyección **con el fichero confidencial ya recuperado**, algo a lo
  que la línea base nunca llegó a enfrentarse. Precio: la relevancia baja de
  0,880 a 0,778 por respuestas más largas.
- El **enrutador actúa como barrera accidental**: en varias peticiones de datos
  personales clasifica `otro`, no recupera nada y por tanto no filtra. Se
  decidió **no** relajar la etiqueta del banco para dar eso por bueno: ajustar el
  criterio tras ver los resultados es sobreajustar el banco. Se narra como
  hallazgo en la valoración.
- **Cero fallbacks silenciosos** del enrutador en 52 casos: el parseo manual de
  JSON aguanta, aunque siga siendo una clase de fallo latente.
- El barrido dice que **`headings` + `top_k=2`** sube la precisión de
  recuperación de 0,674 a 0,919 manteniendo recall 1,0 y MRR 1,0, y que **subir
  las dimensiones del embedder (1536, 3072) no cambia nada**.
- Dos pasadas del juez sobre las mismas trazas miden su **variabilidad**: la
  métrica de confidencialidad cambia de veredicto en el 50 % de los casos, y por
  eso el veredicto se ancla en las deterministas.

## Roadmap de la entrega

1. ~~Scaffold y vendorizado del sistema bajo prueba.~~ Hecho.
2. ~~Parametrizar `Config` y añadir chunking por encabezados.~~ Hecho.
3. ~~Ampliar el corpus con material de confidencialidad e inyección.~~ Hecho.
4. ~~Golden set curado (52 consultas + 5 transcripciones).~~ Hecho.
5. ~~Métricas deterministas y de juez.~~ Hecho.
6. ~~Runner, informes y barrido.~~ Hecho.
7. ~~Tests y CI.~~ Hecho (322 pruebas sin API).
8. ~~Ejecución real, set sintético y valoración.~~ Hecho.
9. PDF de entrega y presentación en el campus virtual. **Pendiente.**

## Memoria de sesiones

- Diario en `docs/BITACORA.md` (lo escribe `/cierre`, lo lee `/arranque`).
