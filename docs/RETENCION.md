# Retención y supresión del registro de producción

> Política del registro de observabilidad (`data/observabilidad/<tenant>/trazas.jsonl`),
> que guarda **quién preguntó qué**. Es a la vez la trazabilidad que pide el
> artículo 12 del AI Act y un dato personal de quien pregunta, así que tiene
> que tener una política de retención y un camino de supresión. Riesgo R-16 de
> `RIESGOS.md`. Escrita el 23-09-2026.

## Qué se guarda y por qué

| Campo | Se guarda | Por qué |
|---|---|---|
| Consulta | Sí, en claro | Sin ella no se puede responder "quién preguntó qué", que es un requisito de la capa de gobernanza |
| Usuario | Sí, su identificador | Es el sujeto del control de acceso; sin él no se puede saber si alguien pidió lo que no le toca |
| Respuesta | **No**: longitud y hash | Es el texto con más probabilidad de arrastrar datos del corpus. `OBS_GUARDAR_RESPUESTA=1` la activa y quien lo hace asume lo que implica |
| Contexto recuperado | No | Son fragmentos del corpus, que ya están en el índice |
| Categoría, fuentes, señales de control, latencias, coste | Sí | Es lo que responde a las preguntas de explotación |
| Versión (commit y huella de los prompts) | Sí | Partir cualquier cifra por versión (`docs/PROMPTS.md`), desde el 11-10-2026 |
| Calidad de la respuesta | Sí, solo números: citas, citas inventadas, si cita alguna fuente, y el veredicto del juez cuando la consulta cae en la muestra | Saber cómo va en producción sin guardar la respuesta: se evalúa al servir, en memoria (`src/evaluacion_produccion.py`) |
| Razonamiento del juez | **No** | Podría repetir datos de la respuesta. Se pide un veredicto de tres valores y no un número para que no haga falta leerlo con su razón |

**Una transferencia nueva desde el 11-10-2026.** Con `EVAL_PRODUCCION_FRACCION`
mayor que cero, la consulta, el contexto recuperado y la respuesta de la
fracción muestreada se envían al juez (Gemini, con su clave y proyecto
propios) para que dé su veredicto. Google no los conserva más allá de lo que
digan sus condiciones de la API de pago; aquí no se guarda nada de lo enviado.
Decidido por el autor y registrado en R-18 de `RIESGOS.md`.

## Cuánto tiempo

**90 días por defecto.** Es el plazo que cubre un ciclo de facturación
trimestral y una revisión de seguridad, y es más corto que el año que suele
citarse para registros de auditoría porque aquí el registro contiene la
consulta en claro. No hay borrado automático: la purga se ejecuta a mano, y
eso es un hueco declarado (una tarea programada la cerraría, cuando haya
despliegue).

```bash
uv run python -m src.observabilidad_cli --tenant <id> --purgar-dias 90
```

## Supresión a petición (RGPD, artículo 17)

Una persona puede pedir que se borren sus consultas. El camino existe, está
cronometrado y deja rastro de sí mismo:

```bash
uv run python -m src.observabilidad_cli --tenant <id> --borrar-usuario <usuario>
```

Quita todas las líneas de ese usuario y deja **una lápida**: una línea que dice
cuándo, cuántas líneas se quitaron y el hash del usuario, no el usuario. La
auditoría sigue sabiendo que hubo un borrado sin conservar a quién.

## Lo que la lápida resuelve, y lo que no

El módulo dice que "un registro que se puede reescribir no es evidencia", y la
supresión reescribe. La contradicción es real y se resuelve así: la reescritura
**solo quita líneas, nunca cambia ninguna, y siempre añade una lápida**. El
resumen de explotación muestra cuántos borrados hubo y cuántas consultas se
quitaron; un registro podado se distingue de uno entero. Lo que no resuelve:
que quien tenga acceso de escritura al fichero pueda editarlo sin dejar lápida.
Eso es control de acceso al sistema de ficheros, no de este módulo.

Las **líneas ilegibles** (un proceso muerto a media escritura) se conservan:
no se sabe de quién son, y borrarlas sería borrar sin saber qué.

## Lo que sigue fuera

- Las **consultas ya enviadas al proveedor** del modelo. El proveedor tiene
  su propia retención, y eso es la transferencia internacional de R-18.
- El **índice** no guarda consultas; los documentos se borran por otro camino
  (`scripts/borrar_documento.py`, HALLAZGOS.md §36).
- El **registro del puente** con la app (`puente/REGISTRO_APP.md`) es
  utillaje de desarrollo, no de producción, y no entra aquí.
