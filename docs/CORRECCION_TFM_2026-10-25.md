# Corrección del TFM — primera entrega, 25 de octubre de 2026

> Registro de la calificación de la primera entrega (intento 1 de 3, PDF del
> commit `5468fcc`) y de lo que se hizo con ella. Lo contrastado contra el
> repositorio va con su fuente; lo que dice el corrector, resumido y sin
> rellenar huecos.

## La calificación

- **93,00 / 100**, calificado el domingo 25-10-2026 a las 20:30 por Iraitz
  Montalbán, siete horas después de la entrega (13:19).
- Comentario en el campus: el trabajo está "blindado", las decisiones están
  fundamentadas con números (evaluaciones, red-teaming, costes, latencias) y
  la elección de Python sin framework frente a LangGraph es "la mejor opción
  con los requisitos que manejas".
- Informe adjunto en PDF (cuatro páginas), con el desglose por módulo que
  sigue. Es el mecanismo que el tutor anunció el 6-10: un agente que recorre
  la memoria módulo a módulo (`docs/MODULO_5.md`, "Cómo se evalúa").

| Módulo | Peso | Nota |
|---|---|---|
| 1. Modelos y consumo | 25 % | 9,8 |
| 2. Arquitectura y flujos | 25 % | 9,7 |
| 3. Despliegue y evaluación | 21 % | 9,5 |
| 4. Seguridad y riesgos | 25 % | 9,9 |
| **Nota final ponderada** | | **9,3** (el texto dice 9,35) |

## Los pesos suman 96 %

9,8 × 0,25 + 9,7 × 0,25 + 9,5 × 0,21 + 9,9 × 0,25 = **9,345**, que es el 93
del campus. Con los cuatro módulos al 25 % sale **9,725**, y casi lo mismo
normalizando sobre el 96 % (9,73). El enunciado no fija pesos
(`docs/MODULO_5.md`), y los otros tres módulos pesan igual, así que el 21 %
parece una errata del informe. De los 6,55 puntos que faltan hasta 100, 4
vienen del peso que no se reparte y 2,55 de las notas de los módulos.

**Juan lo señaló al corrector el 26-10** con un mensaje breve, planteado como
duda y aceptando el peso si es intencionado. Pendiente de respuesta.

## Las áreas de mejora ya estaban declaradas

Las cinco son filas de la tabla "Lo que no está, y por qué" de la memoria
(`docs/MEMORIA.md`, capítulo 8.2), con el mismo ejemplo en el caso del
enmascarado:

| Mejora del informe | Dónde estaba | Cuándo se reconsideraba |
|---|---|---|
| Alertas activas de gasto y calidad | 8.2, "Alertas activas" | Tras el feedback de la primera entrega |
| Enmascarar datos personales en la pregunta ("el salario de Laura Gómez") | 8.2, "Enmascarar datos personales en la pregunta" | Con datos reales de un cliente |
| Moderación de contenido para clientes externos | 8.2, "Moderación de contenido" | Si se abre a clientes externos |
| Entorno de preproducción | 8.2, "Entorno de preproducción" | Con más de un desarrollador |
| Migrar el modelo de vectores antes del 14-05-2028 | 8.2, "Migrar el modelo de vectores" | Antes del 14-05-2028 |

El informe las presenta como "oportunidades reales de escalar el sistema hacia
producción con clientes reales, no defectos del proyecto actual". Ninguna es
un hallazgo nuevo.

## Una lectura del informe que la memoria no sostiene

El informe dice que el juez automático "fue evaluado y mide consistentemente".
La memoria dice lo contrario: entre tres pasadas idénticas cambian de
veredicto 5 y 6 casos de 10, temperatura 0 no lo estabiliza, y por eso la
comparación base/endurecido la decide una métrica determinista (hallazgos 30,
32 y 33). Es una lectura a favor y no se discute; se anota porque confirma
que el corrector resume, y que una frase de la memoria puede salir del
informe con el sentido cambiado.

## Decisión

**No se reentrega** (Juan, 26-10). Construir las mejoras antes del 31-10
subiría como mucho unas décimas con un corrector que puede variar entre
pasadas, y las cinco ya tienen su motivo y su momento escritos. Lo único que
vale puntos es el peso del módulo 3, y eso se resuelve con el mensaje, no con
otra entrega.
