---
name: arranque
description: Arranca una sesión de trabajo de la entrega cargando todo el contexto — bitácora, tareas pendientes, estado del repo, entorno y enunciado. Usar al inicio de cada jornada.
---

# Arranque de sesión de trabajo (entrega del máster)

Ejecuta estos pasos en orden y termina con un **resumen de arranque** único y un plan
propuesto. No pidas confirmación entre pasos.

## 1. Contexto de la entrega

- Lee el `CLAUDE.md` de esta carpeta (estado, decisiones, roadmap).
- Comprueba si existe el enunciado en `docs/enunciado/`. Si no existe, la primera
  tarea del plan será pedírselo a Juan.

## 2. Bitácora y tareas pendientes

- Lee `docs/BITACORA.md` si existe (2-3 entradas más recientes; orden de más reciente
  a más antigua). Extrae lo hecho, decisiones y **tareas pendientes** (checkboxes sin marcar).
- Si no hay bitácora, usa el roadmap del `CLAUDE.md` como fuente de tareas.

## 3. Estado del repositorio y entorno

- `git status` y `git log --oneline -10` (si aún no hay repo, anótalo: el scaffold está pendiente).
- Si hay `pyproject.toml`: `uv sync` y, si existe script de verificación de conexión,
  ejecútalo. Si falla algo (dependencias, `.env`, claves), repórtalo con el error
  concreto y el arreglo **antes** del plan.

## 4. Vigilante del puente (siempre, desde el 27-09-2026)

Juan quiere que la sesión reaccione a lo que registra la app de Claude **sin
esperar a su siguiente prompt**. Para eso se arma un monitor al arrancar:

- Si la herramienta `Monitor` no está cargada, cárgala con
  `ToolSearch` (`select:Monitor`).
- Llama a `Monitor` con `command: node puente/vigilar.mjs`,
  `description: avisos nuevos del puente con la app de Claude` y
  `timeout_ms: 1800000` (el máximo). El script sondea `avisos.mjs --listar`
  cada 20 s y escribe una línea por aviso nuevo; los que ya estén pendientes
  al arrancar no los anuncia, porque el hook los inyecta en el primer prompt.
- **Rearma el monitor en cada notificación de expiración**, durante toda la
  sesión, con la misma llamada. Si expira sin eventos, es lo normal.
- Cuando llegue un evento: lee el aviso y el registro en
  `puente/REGISTRO_APP.md`, contrasta lo que diga contra el repositorio,
  actúa (hallazgo, corrección, documentación) y márcalo con
  `node puente/avisos.mjs --atendido A-NNNN --nota "..."`. Un aviso **nunca**
  genera un encargo nuevo a la app por sí solo: si la acción es volver a
  encargar, propónselo a Juan.
- Di en el resumen de arranque que el vigilante está armado.

## 5. Resumen de arranque

Escribe el resumen como **markdown enriquecido directamente en la respuesta** — nunca
dentro de un bloque de código (los ``` matan el renderizado). Usa encabezados,
negritas y listas, con esta estructura:

> ## Sesión AAAA-MM-DD
>
> **<Fase/estado de la entrega> · Último hito: <1 línea> · Repo: <estado>**
>
> ### Pendientes heredados
> - **<tarea>**: <detalle breve> *(de bitácora o roadmap)*
>
> ### Avisos
> - <problemas de entorno, trabajo sin commitear, fechas límite, bloqueos — con
>   **negrita** en lo crítico. Si no hay avisos, omite la sección.>
>
> ### Vigilante
> - Armado sobre `puente/vigilar.mjs`; se rearma cada 30 minutos.
>
> ### Foco sugerido
> 1. **<tarea 1>**: <por qué es lo prioritario>
> 2. **<tarea 2>**: <...>
>
> ¿Con cuál arrancamos, o traes otro foco?

Reglas de estilo: PROHIBIDO usar emojis (en cualquier texto, documento o código),
negrita para lo accionable/crítico, rutas y comandos con `backticks`, y cierra
siempre con la pregunta a Juan en una línea propia.
