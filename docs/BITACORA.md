# Bitácora — Entrega 3.3 (Evaluación de agentes)

## 2026-08-10 — Sesión única: banco de pruebas completo

**Punto de partida.** Análisis del repo de la 3.1 (calificada 10/10) y de su
`docs/PROXIMOS_PASOS.md`. La corrección del profesor pedía tests automatizados
que puntúen cambios de modelo, embedder y chunking; el bloque A de ese roadmap
es, literalmente, el enunciado de la 3.3. Se decide ejecutarlo.

**Decisiones tomadas al arrancar** (consultadas con Juan):

1. Stack híbrido: DeepEval para el juez LLM, harness propio para las
   deterministas.
2. Ampliar el corpus con material confidencial ficticio y una inyección de
   prompt, para que las métricas de PII midan algo real.
3. Alcance completo: golden set + sintéticos + barrido de configuraciones.

**Trabajo hecho.**

- Vendorizado del sistema bajo prueba (`src/` + `corpus/`) y parametrización de
  todo lo que la 3.1 tenía hardcodeado: chunking, dimensiones del embedder,
  `top_k`, umbral de distancia y política del prompt del generador.
- Chunker por encabezados como alternativa al de caracteres.
- Contabilidad de tokens en `provider.py` (la 3.1 descartaba `usage`).
- Golden set curado: 52 consultas en 8 dimensiones + 5 casos de transcripción.
- Métricas en cuatro capas; umbral justificado por métrica.
- Runner con fases separadas (ejecución / evaluación) y `--desde-trazas` para
  reevaluar sin volver a llamar al sistema.
- Barrido de 11 configuraciones y generador de sintéticos con doble validación.
- 322 pruebas sin llamadas a API y workflow de CI.

**Incidencias y cómo se resolvieron.**

- *Clave de Anthropic caducada* (401). Se avisó a Juan, que la renovó. Mientras
  tanto se avanzó todo lo que solo necesitaba embeddings (barrido) y lo que no
  necesitaba API (tests, esquema, métricas deterministas).
- *Cuota de Gemini*: 100 embeddings/minuto y **20 generaciones al día** en el
  plan gratuito. Se resolvió por diseño, no con esperas: los embeddings de
  consulta se calculan en lote (una llamada por dimensionalidad en vez de una
  por consulta) y el juez se movió a Anthropic con un modelo de tier distinto al
  evaluado. Queda conmutable a Gemini vía `JUDGE_PROVIDER`.
- *Bug real destapado por el barrido*: al cortarse por cuota, `construir_indice`
  dejaba la colección creada y vacía, y la ejecución siguiente la daba por
  buena — el barrido reportó 0 aciertos para dos configuraciones que en realidad
  nunca se indexaron. Arreglado calculando los embeddings antes de tocar la
  colección, y `indice_existe` ahora comprueba que tenga contenido.

**Hallazgo que se decidió NO incorporar al banco.** Cuatro de los cinco fallos
de enrutado son peticiones de datos personales que el enrutador clasificó como
`otro`, evitando así la recuperación y la fuga. Se valoró admitir `otro` como
categoría válida en esos casos y se descartó: relajar la etiqueta después de ver
los resultados es sobreajustar el banco (slide 15 del material del módulo). Se
narra como hallazgo en la valoración, señalando que es una barrera accidental y
frágil, no un diseño.

**Estado al cerrar.** Entrega presentada en el campus el 2026-08-10 a las 15:20
con el PDF adjunto ("Enviado para calificar"). Repo en `master` con CI en verde.
Gasto de API de la jornada: unos 6 USD.

**Para la próxima sesión.** Nada pendiente en esta entrega. Si se retoma el tema,
lo siguiente por orden de valor: observabilidad en producción (bloque B del
roadmap de la 3.1), evaluación multivuelta, y anotar a mano una muestra para
medir el acuerdo entre el juez LLM y criterio humano — hoy la calidad del juez
es una suposición razonable, no un dato.

## 2026-08-10 (tarde) — Corrección: 10,00 / 10,00

Corregida por Iraitz Montalbán a las 16:41, poco más de una hora después de
presentarla. Valoró la profundidad del ejercicio y, en concreto, **haber
evaluado también al juez y su estabilidad**: "los LLMs como juez tampoco son
perfectos y sufren de los mismos problemas que los agentes como tal".

Dos líneas de mejora, archivadas en `docs/PROXIMOS_PASOS.md` sin implementarlas
aquí (mismo criterio que con la 3.1: el repo está entregado y calificado, el
valor está en aplicarlo hacia delante):

1. **Un token de API para el agente y otro para el juez**, para separar en
   facturación lo que cuesta el sistema de lo que cuesta evaluarlo y poder
   estimar el incremento de coste ante nuevos despliegues. Es un hueco real: el
   acumulador de `provider.py` solo ve los tokens del sistema bajo prueba; el
   gasto del juez lo lleva DeepEval por dentro y no se captura.
2. **Revisión desde el punto de vista de la seguridad.** El banco trata
   confidencialidad e inyección como dimensiones de calidad, no como una
   revisión de seguridad: quedan fuera la superficie expuesta, la custodia de
   secretos, el corpus como vector de inyección y el control de acceso al
   contenido (hoy la única barrera entre un empleado y los salarios es el
   prompt, no un filtro por permisos en la recuperación).
