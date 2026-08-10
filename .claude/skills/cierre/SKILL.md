---
name: cierre
description: Cierra la jornada de trabajo de la entrega — escribe la bitácora, actualiza el CLAUDE.md de la entrega (y el estado en Master/CLAUDE.md si la entrega se completa) y hace commit + push. Usar al terminar cada sesión.
---

# Cierre de jornada (entrega del máster)

Ejecuta el cierre de forma **totalmente autónoma** (Juan ya autorizó commit + push
automáticos y la edición directa de los CLAUDE.md). Solo detente si el push falla o
si detectas algo destructivo o anómalo.

## 1. Recapitular la sesión

Revisa la conversación de hoy y el repo (`git status`, `git diff`, `git log` desde el
último cierre) y extrae: **Hecho**, **Decisiones** (con su porqué en una línea),
**Pendiente** (incluye lo heredado sin resolver) y **Notas**.

## 2. Actualizar CLAUDE.md

- Actualiza el `CLAUDE.md` de esta entrega: estado, decisiones tomadas, roadmap.
- Si la entrega queda **completada y entregada**, actualiza también la sección
  "Estado de las entregas" de `Master/CLAUDE.md` (dos niveles arriba).

## 3. Escribir la entrada de bitácora

Añade una entrada nueva en `docs/BITACORA.md` **inmediatamente después de la cabecera**
(entradas de más reciente a más antigua). Crea el archivo si no existe:

```
## AAAA-MM-DD — Sesión N: <título breve>

**Hecho:**
- ...

**Decisiones:**
- ...

**Pendiente para la próxima sesión:**
- [ ] ...

**Notas:**
- ...
```

Omite subsecciones vacías, excepto **Hecho** y **Pendiente**.

## 4. Commit y push

- `git add` de los archivos de la sesión (código, `docs/BITACORA.md`, `CLAUDE.md`).
  No añadas ignorados ni temporales.
- Conventional commits en inglés (`feat:`, `docs:`, …); commits separados por área si aplica.
- `git push` si hay remoto configurado. Si falla, deja el commit local e informa del
  error exacto y cómo resolverlo. Si aún no hay remoto, indícalo en el resumen.

## 5. Resumen de cierre

Escribe el resumen como **markdown enriquecido directamente en la respuesta** — nunca
dentro de un bloque de código (los ``` matan el renderizado). Estructura:

> ## Cierre AAAA-MM-DD — Sesión N
>
> **<resumen de la jornada en 1-2 líneas>**
>
> ### Hecho
> - <logros de la sesión, con **negrita** en los hitos>
>
> ### Commits y push
> - `<hash>` <mensaje> · Push: <OK / fallo + motivo / sin remoto>
>
> ### Próxima sesión
> - **<primera tarea pendiente>** <y contexto mínimo para retomarla>

Reglas de estilo: PROHIBIDO usar emojis (en cualquier texto, documento o código),
negrita para hitos y tareas, rutas/comandos/hashes con `backticks`.
