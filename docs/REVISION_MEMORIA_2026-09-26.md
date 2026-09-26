> **Nota de aplicación (26-09-2026).** Informe de la segunda lectura hostil
> de `MEMORIA.md`, producida por un revisor independiente (un agente con la
> rúbrica del programa delante y acceso al repositorio) sobre el commit
> `5795882`. Se aplicaron las 7 Altas, 19 de las 20 Medias y las 8 Bajas,
> más las seis correcciones "fuera de la memoria", el mismo día. La Media
> no aplicada es M5 (leer una latencia interna del canal en los logs de
> Render): la memoria dice ahora que la línea existe y no se ha leído. Los
> números de línea son los del commit revisado; la memoria ha cambiado
> desde entonces. Se guarda porque el capítulo 12.2 defiende el método, y
> el método incluye que la memoria se lea con hostilidad antes que el
> tribunal.

# Revisión hostil de `docs/MEMORIA.md` — 2026-09-26

**Objeto:** `docs/MEMORIA.md` (1.144 líneas, commit `5795882` del 25-09-2026), segunda lectura hostil tras la del 24-09. Foco en los capítulos 2.10, 6.3, 6.4, 8.2, 9, 10, 12 y Resumen (cifras nuevas de §51 y §52) y muestreo de 3, 4, 5, 7 y 8.

**Método:** cada cifra se contrastó con el hallazgo citado (`docs/HALLAZGOS.md`, líneas indicadas), con el `resumen.json` de la ejecución (`reports/<etiqueta>/`) y con `CANAL_WHATSAPP.md`, `DESPLIEGUE.md`, `GUION_DEMO.md`, `RIESGOS.md`, `MODULO_4.md`, `AIBOM.md`, `ALCANCE.md`, `BITACORA.md`, `src/config.py`, `src/provider.py`, `tests/`, y el programa del máster (PDF, texto extraído con `pypdf`). Los recuentos (tests, líneas, hallazgos, riesgos, dimensiones del banco, minutos de la demo) se rehicieron con `grep`, `wc`, `pytest` y scripts sobre los ficheros, no de memoria. Cifras comprobadas: 61 en los capítulos objetivo y 47 en el muestreo. Nada del repositorio se ha modificado.

**Resumen ejecutivo:** 7 hallazgos de severidad Alta (cifras que ya no coinciden con su fuente o contradicciones internas), 20 de severidad Media, 8 de severidad Baja. Ninguna de las cifras de §51 y §52 está mal transcrita; los problemas de esos capítulos son de alcance (afirmaciones sin cifra o decisiones posteriores no recogidas). Las Altas más urgentes son tres: el número de hallazgos (50 frente a 52 reales), el inventario del AIBOM (10/119 frente a 12/142 en el fichero generado y protegido por test) y la fila de 8.3 sobre el juez, que describe como pendiente algo que §32 ya cerró el 22-09.

---

## Severidad Alta: cifra incorrecta o contradicción

| # | Línea(s) | Texto citado | Qué dice la fuente | Corrección propuesta |
|---|---|---|---|---|
| A1 | 1076, 1118 | "50 hallazgos medidos" / "Los 50 hallazgos de `docs/HALLAZGOS.md`" | `grep -c "^## " docs/HALLAZGOS.md` = **52**. La propia memoria cita §51 (l. 401, 411) y §52 (l. 746, 1002). | "52 hallazgos" en las dos líneas. Añadir §51 al Anexo A (ver M13). `CLAUDE.md` §8 dice "48": actualizar también. |
| A2 | 933-934 | "10 paquetes directos y 119 transitivos fijados" | `docs/AIBOM.md:16`: "**12 paquetes directos y 142 transitivos**", desde el commit `ca3c811` (24-09, LangGraph). El fichero es generado y `tests/test_aibom` falla si difiere: la memoria cita un inventario que ya no existe. | "12 directos y 142 transitivos". Explicar la diferencia con los 14 paquetes del §50 (119 → 142 son 23, no 14: decir qué más entró o cómo cuenta el generador). `RIESGOS.md` R-09 (l. 40) arrastra el mismo 10/119. |
| A3 | 974 (tabla 8.3) | "Juez de otra familia repetido tres veces por defecto \| Diseñado; falta una segunda clave de Gemini y 0,22 USD \| Antes de la memoria final" | Ese estado es el del §24 (`HALLAZGOS.md` l. 1286-1289, mañana del 22-09). §32 (l. 1842-1848) lo **completó el mismo día** con la clave del proyecto `tfm-juez` (6 pasadas, 0,089 USD) y **DECIDIÓ** no automatizar la mayoría de tres porque §33 mide que sobre 10 casos no basta. El juez de otra familia **ya es el defecto** (`src/config.py:232-233`). Contradice la propia memoria 4.3 (l. 607-626) y 4.4 (l. 636). | Sustituir la fila por: "Mayoría de tres del juez por defecto \| Decidido no automatizar (§32, §33): sobre 10 casos tres pasadas no alcanzan; repetir es acto deliberado \| Cerrado el 22-09". `CLAUDE.md` §2 arrastra "Diseñado y no ejecutado: falta una segunda clave de Gemini". |
| A4 | 1099 | "doce minutos en seis bloques" | `docs/GUION_DEMO.md` tiene **ocho bloques con público** (1, 2, 3, 4, 4b, 4c, 5, 6) que suman **15 min** (2+3+3+1+2+1+2+1), más 2 min de preparación. El encabezado del guion ("Doce minutos si se hace entero") quedó desfasado al añadir 4b (HITL) y 4c (WhatsApp). | "quince minutos en ocho bloques, más dos de calentamiento sin público". Corregir también el encabezado del guion. |
| A5 | 489 | "entre 0,0020 y 0,0037 por inquilino en las vigentes (capítulo 5.4)" | El capítulo 5.4 (l. 674, 720-722) da **0,00198 a 0,00406**. 0,0037 es `agencia_quien` (0,141534 USD / 38 = 0,00372), la ejecución **anterior** a `agencia_hitl_v3` (0,162263 / 40 = 0,00406), que es la que la ficha declara vigente. Contradicción interna. | "entre 0,0020 y 0,0041". |
| A6 | 749-750 | "Mantener el banco cuesta entre 0,06 y 0,14 USD por inquilino y pasada sin juez" | `reports/*/resumen.json` `meta.uso_sistema.coste_usd_estimado`: `gestoria_agregacion` 0,061; `empresa_quien` 0,105; `agencia_hitl_v3` **0,162**. 0,14 es `agencia_quien` (0,1415). Mismo error que A5. | "entre 0,06 y 0,16 USD". |
| A7 | 48 (Resumen), 335 (tabla 2.7, fila "Permiso en el `where`"), 1035 (Conclusiones) | "`fuga_literal` **10/10**" citado con §33 como prueba de que "el control de acceso está en la búsqueda, no en el prompt" | §33 (l. 1965-1975) reevalúa las trazas `baseline`/`endurecido` del **10-08-2026**, anteriores a la capa de gobernanza (§8 es del 20-09): compara **dos prompts**, no el permiso en el `where`. Usar la comparación de prompts como evidencia de que el control no está en el prompt es exactamente lo que un tribunal señalará. La cifra 10/10 sí es cierta en la línea base vigente con gobernanza: `reports/empresa_quien/resumen.json` `fuga_literal` n=10, media 1,0 (y `agencia_hitl_v3` 9/9, `gestoria_agregacion_v2` 6/6). | En Resumen, 2.7 y 10 citar `empresa_quien` (§40, §47) como fuente del 10/10, con su n. Dejar §33 donde encaja: 4.3 y 7.2 fila 1 (inyección, comparación de prompts). |

---

## Severidad Media: afirmación sin respaldo o ambigüedad que un tribunal pillaría

| # | Línea(s) | Texto citado | Qué dice la fuente | Corrección propuesta |
|---|---|---|---|---|
| M1 | 5, 33-34, 141 | "date: 24 de septiembre"; "cinco días de trabajo (del 20 al 24...)"; "ocho sesiones en cinco días" | La memoria incorpora medidas del **25-09** (§51 cierre: token permanente, l. 3487-3495; §52 entero) y una decisión del **26-09** (§51 l. 3486-3491). `BITACORA.md` tiene 8 sesiones del 20 al 24; lo del 25 y 26 no tiene sesión registrada. | O "cinco días de construcción (20-24) y dos de medidas de operación (25-26)", o actualizar a seis días y la fecha del frontispicio. Registrar en la bitácora las sesiones del 25 y 26 antes de citar sus cifras. |
| M2 | 47 | "27 de 28 casos de su banco a la tercera iteración" | §43: 5 min 42 s son **dos** iteraciones y dan 25/28. §45 (l. 2876-2926) no es una iteración del alta sino la **revisión en frío de dos expectativas del banco** (media hora, 0,06 USD), y la propia 8.1 (l. 944-950) lo cuenta así. | "25 de 28 en 5 min 42 s con dos iteraciones; 27 de 28 tras corregir dos expectativas del banco (§45)". |
| M3 | 337 | "5 casos de la gestoría, 28 de 28 (los casos de entonces) en `fuga_literal` (§47)" | `reports/gestoria_denegacion/resumen.json`: `fuga_literal` **n=6**. "28 de 28" copia una frase suelta de §47 (l. 3060) y da un denominador falso, justo lo que el párrafo de l. 357-359 promete no hacer. | "6 de 6 casos con literal prohibido, ninguno filtra; 27 de 28 casos OK en la ejecución". |
| M4 | 998-1002 | "duerme a los quince minutos y reconstruye el índice al despertar. Lo único medido del plan es el despertar: 32 s ... tras un cuarto de hora sin uso" | `reports/arranque_frio/resumen.json` `que_mide`: "Solo el despertar del contenedor: /salud **no construye índices**". La reconstrucción del índice al despertar **no está medida** (DESPLIEGUE.md la afirma para el primer acceso tras despliegue, que es otra cosa). El sondeo fue **cada 20 min** ("20 minutos sin trafico bastan"); "quince" es la política documentada de Render, no lo medido. | "duerme antes de 20 minutos sin tráfico (medido; Render documenta 15)"; "tras 20 minutos sin tráfico"; y "si el disco efímero se reinició, el índice se reconstruye en el primer acceso: no medido, §52 mide solo el despertar". Misma precisión en 5.4 l. 746. |
| M5 | 411-416 | "desde entonces el servidor deja una línea por mensaje ... con huella, inquilino, respuestas y latencia" | Afirmación **sin cifra**: no se cita ninguna latencia interna leída en vivo. §51 cierre (l. 3480-3482) dice "no se leyó". El único número es el ejemplo `latencia=6.53 s` de `CANAL_WHATSAPP.md` (l. 173), cuya procedencia (lectura real o ilustración) no consta. **No comprobable desde el repositorio.** | Citar una lectura real de los Logs de Render con fecha y hora, o escribir "sin lectura todavía". Si el 6,53 s es real, decirlo y datarlo en §51 o en un §53. |
| M6 | 1021-1022 | "falta el aislamiento con dos números" | §51 cierre (l. 3486-3491): "**no se medirá antes de la defensa** (decidido el 26-09-2026)", con su razón. La memoria lo deja como pendiente. | "el aislamiento con dos números reales no se mide antes de la defensa (decidido el 26-09, §51): es el mismo mecanismo que la credencial web y lo fijan las pruebas simuladas". Añadirlo a la tabla 8.3. |
| M7 | 785-787 | "cinco salieron de probar fuera del banco, y tres de ellos (§39, §41, §42) en el servicio desplegado" | §38 (l. 2340-2395) también salió del servicio desplegado (E-0005: fallo de login en Render). Son **cuatro**: §38, §39, §41, §42. | "cuatro de ellos (§38, §39, §41, §42)". |
| M8 | 190-193, 1053 | "unas 5.200 líneas ... 1.117 tests que corren en 11 segundos (contados el 24-09)" ; "# 1117 tests" | `wc -l` sobre `src/`, `mcp_servers/` y `app.py` en el commit `add840a` (cierre del 24-09) = **5.427**; hoy 5.455. Tests: `CLAUDE.md:37` y `BITACORA.md:9` dicen **1.118** al cierre del 24-09; hoy `pytest -q` ejecuta **1.114** sin el grupo `langgraph` (contado en los puntos de progreso; el módulo se salta) y §50 dice que ese grupo añade 10, así que al menos 1.124. Los "11 segundos" no los pude verificar: un plugin de pytest suprime la línea de resumen. | "unas 5.400 líneas"; recontar los tests con `uv sync --group langgraph` en el cierre y escribir cifra y fecha en las dos líneas. |
| M9 | 398-399 | "25 pruebas con mensajes simulados (`tests/test_canal_whatsapp.py`)" | `grep -c "def test_"` = **29** hoy (26 en `add840a`; 25 fue la cifra del 23-09, sesión 7). | "29 pruebas" o fechar: "25 el 23-09, 29 tras el registro por mensaje del 25-09". |
| M10 | 774-775, 1083 | "Medidas en décimas de segundo sobre un registro de 10.000 líneas (§37)"; "supresión en décimas de segundo" | §37 (l. 2325-2327): **0,048 s** y **0,040 s**. Son centésimas. | "menos de 0,05 s". `CLAUDE.md` repite "décimas". |
| M11 | 741 | "Entre 12 y 15 tokens por consulta (§37)" | §37 (l. 2302): **14,1 tokens de media** sobre 91 consultas. No da rango. | "unos 14 tokens de media (91 consultas del golden set)". |
| M12 | 685-686, 843 | "una fuga a pleno ritmo, medida en 12,5 USD por hora (§17)" | §17 (l. 476-571) **no contiene** la cifra ni la palabra "hora". Solo aparece en §16 (l. 473) atribuida a §17, sin derivación escrita. Además §21 corrigió un 50 % a la baja todo lo derivado del precio de `claude-sonnet-5`; si 12,5 salió de 0,0417 USD/caso, la cifra corregida rondaría 8,3. **No comprobable.** | Escribir la derivación (casos por hora × coste por caso al precio corregido) en §16 o §21 y citar esa línea, o retirar la cifra y decir "el crédito se agota en el orden de una hora". |
| M13 | 1122-1136 (Anexo A) | Índice de hallazgos por capítulo | Mapa real (grep de `§N` por encabezado): **§51 no aparece** (citado en 2.10 y 9). **§20** aparece en "2.9, 6" y **no se cita en ningún capítulo** (2.7 l. 356 y 2.9 usan su contenido sin nombrarlo). §22 y §29 están en "2.1-2.3" y se citan en 2.4/5.4/8.2 y 3.1/3.3/8.4. §7 en "2.6" pero está en 3.2. §9 y §11 en "4" pero están en 2.7. §10 y §14 en "2.5" pero están en 2.3. §42 en "2.6" pero está en 2.7, 2.8, 4.2, 6.3 y 7.2. §46 se cita también en 1.3, 2.9 y 6.1. | Regenerar el índice desde el grep (tabla al final de este informe) o cambiar el criterio a "capítulo principal" y decirlo. Citar §20 en 2.9 (las tres señales) o quitarlo del índice. Encabezado a 52. |
| M14 | 130, 169, 254, 387, 457 | "(§4.4 de esta memoria)", "(§8.1)", "(§4.4)", "(§6.2)", "(§8.4)" | En toda la memoria `§N` es un hallazgo de `HALLAZGOS.md`. "§8.1" colisiona con el hallazgo §8 y "§6.2" con el §6; l. 636-637 y 663 usan "§5.c/§5.d" para `ALCANCE.md`. Tres significados para un mismo signo. | Reservar `§` a los hallazgos; escribir "capítulo 8.1" (como ya se hace en l. 227, 283, 536) y "`ALCANCE.md` §5.c" siempre con el fichero delante. |
| M15 | 395-398 | WhatsApp: "aprobación humana por texto" listada como característica sin salvedad | `CANAL_WHATSAPP.md` l. 164-166: "Sin medir todavía: la latencia interna, el aislamiento con dos números y **la aprobación por texto en vivo**". Solo está probada con mensajes simulados. | "aprobación humana por texto (probada con mensajes simulados, no en vivo)". |
| M16 | 399-400 | "5,1 s una consulta contra el sistema real (bitácora, sesión 7; sin carpeta en `reports/`)" | `BITACORA.md:165` lo confirma. Es **una** muestra sin traza guardada, y la memoria exige "ninguna cifra sin su ejecución" (l. 125). | Declarar N=1 en el texto ("una sola consulta simulada, 5,1 s, sin traza") o sustituirla por la lectura de los logs de Render cuando exista (M5). |
| M17 | 745-748 | "Un plan de pago lo elimina y es un coste fijo independiente del volumen que se suma aparte" | Afirmación **sin número** en la ficha de coste, contra la regla de l. 110-111. No se cita el precio del plan ni se dice que no se consultó. | Poner la cifra del plan de pago de Render que elimina la suspensión (con fecha de consulta) o escribir "precio no consultado". |
| M18 | 231-239 | Colección de Chroma por inquilino: justificada solo por riesgo | Sin coste ni límite: no se dice qué cuesta una colección (tokens de ingesta ya medidos: 2.724, 3.027 y 2.912 en §37/§43; tamaño en disco no medido) ni cuántas colecciones abiertas soporta un proceso. La rúbrica pide escalabilidad y mantenimiento además de riesgo. | Una frase con lo medido (tokens por ingesta) y lo no medido (N colecciones, tamaño), remitiendo a 9 "no hay prueba de carga". |
| M19 | 526-536 (3.4) | Pila: `uv`, Pydantic, ChromaDB, Streamlit, Render, DeepEval, Node "sin dependencias" | Lista sin "por qué" en ninguno de los cinco criterios; solo DeepEval lleva un hallazgo. Es el capítulo "Selección y justificación ... herramientas" del programa. | Una razón por línea: heredado de la 3.1 (10/10) y coste cero; alternativa descartada; qué se mediría si se cambiara. |
| M20 | 546-548 (tabla 4.1) | "Las ocho de la 3.3 más cobertura del riesgo" / agencia "Las mismas más rama estructurada, solapamiento y escritura" | `golden_consultas.jsonl`: heredado **8 dimensiones** (verificado), agencia **9** (añade `accion`), gestoría 8. "Cobertura del riesgo" es una métrica, no una dimensión; "rama estructurada" y "solapamiento" no son dimensiones del banco. | "Ocho dimensiones; la agencia añade `accion` (dos casos, §42). Métricas nuevas: cobertura del riesgo, `accion_sin_aprobar`, verificación de citas". |

---

## Severidad Baja: estilo, redacción, erratas

| # | Línea(s) | Texto citado | Observación | Corrección propuesta |
|---|---|---|---|---|
| B1 | 3, 9 | "borrador 1" / "Estado: borrador 1, abierto el 24-09-2026" | Ya ha pasado dos lecturas hostiles y absorbe hechos del 25 y 26. | "borrador 2, revisado el 26-09-2026". |
| B2 | 36-37 | "la observabilidad, el despliegue con autenticación, ... la interfaz web autenticada y un canal de WhatsApp" | "despliegue con autenticación" e "interfaz web autenticada" son lo mismo dicho dos veces. | Dejar uno. |
| B3 | 848 | "Sobre-dependencia" | Los prefijos van soldados: "sobredependencia" (`MODULO_4.md:58` escribe "Sobre-dependencia"; unificar). | "Sobredependencia". |
| B4 | 990 | "multivuelta" | Correcto pero raro; el resto del texto dice "de un turno" (l. 446, 461). | "multiturno" o "de varios turnos". |
| B5 | 676-677 | "La primera cifra de la 3.3 tenía el precio de `claude-sonnet-5` un 50 % alto" | Frase confusa: no era "la cifra de la 3.3" sino la tabla `PRECIOS` heredada de ella (§21). | "El repositorio heredado de la 3.3 tenía el precio de `claude-sonnet-5` un 50 % alto". |
| B6 | 588, 1002 | Líneas de 130+ caracteres | El resto del fichero está envuelto a ~76 columnas; estas dos no. | Reenvolver. |
| B7 | 94 | "109 casos, 13 métricas en 4 capas" | Herencia de la 3.3, sin § ni ejecución en este repositorio. **No comprobable aquí** (no lo cité). | Añadir "(entrega 3.3, `evals/` heredado)". |
| B8 | 61, 1101 (GUION) | "Ruíz" | Ortográficamente es "Ruiz" (sin tilde), pero es el literal del corpus y del golden set (`auth-rrhh-01`). | No tocar en la memoria; anotar en el corpus que la grafía es deliberada. |

Tildes: no encontré ninguna palabra con tilde faltante en el cuerpo de la memoria (grep de los 30 casos más frecuentes; las coincidencias eran claves JSON o "solo/esta" correctas). Los encabezados sin tilde están en `HALLAZGOS.md` §21-§34, no en la memoria.

---

## Fuera de la memoria pero afecta a lo que cita

Documentos que la memoria referencia y que están desfasados; quien lea la memoria y siga el enlace verá la contradicción.

| Fichero | Línea | Qué está mal | Fuente |
|---|---|---|---|
| `docs/GUION_DEMO.md` | 3 | "Doce minutos si se hace entero" | Suma real 15 min en 8 bloques (A4) |
| `docs/GUION_DEMO.md` | 144 | "sobre la agencia: 38 casos en menos de un minuto" | El banco de la agencia tiene 40 casos desde §42 |
| `docs/CANAL_WHATSAPP.md` | 3-6 | "probado con mensajes simulados; la prueba en vivo está pendiente de la cuenta de pruebas de Meta" | Probado en vivo el 24-09 (§51); el propio documento lo dice más abajo |
| `docs/RIESGOS.md` | 40 (R-09) | "10 paquetes directos y 119 transitivos" | `AIBOM.md:16` dice 12 y 142 (A2) |
| `CLAUDE.md` | §2 tabla, §8 | "Juez de otra familia ... Diseñado y no ejecutado: falta una segunda clave de Gemini"; "48 hallazgos" | §32 lo ejecutó el 22-09; hay 52 hallazgos (A1, A3) |
| `docs/DESPLIEGUE.md` | 102-103 | "El servicio se deja suspendido fuera de las pruebas y de la defensa" | `CLAUDE.md` §2: "Vivo a propósito desde el 23-09"; §52 lo mide vivo |

---

## Lo que está bien y no hay que tocar

Comprobado contra la fuente; coincide. Quien aplique el informe puede dejarlo tal cual.

**Capítulos objetivo (2.10, 6.3, 6.4, 8.2, 9, 10, 12, Resumen)**

- 2.10 l. 401-407: `NotFoundError` en las dos primeras consultas reales, causa (índice no construido en disco efímero, `app.py` y banco con copia propia), corrección con `asegurar_indice` única, redespliegue a las 12:03, vacaciones igual que la web, salario denegado sin fuga, "menos de un minuto cada una" con precisión de minuto: coincide con §51 (l. 3392-3480) y `CANAL_WHATSAPP.md` l. 159-166.
- 2.10 l. 408-411: token de usuario del sistema el 25-09, caducidad *Nunca* en el depurador, mismas dos preguntas respondidas, **dieciocho minutos** (07:15 a 07:33): coincide con §51 cierre (l. 3491-3495) y `CANAL_WHATSAPP.md` l. 113-120.
- 2.10 l. 400: "5,1 s" está en `BITACORA.md:165`, sesión 7, tal como se cita.
- 6.3 l. 781: "1 min 32 s (§38)" coincide con §38 l. 2352 y `DESPLIEGUE.md` l. 87. "Se paró en el login por exigir la clave del juez" coincide con §38.
- 6.3 l. 785: "nueve hallazgos de la sesión del 23-09 por la mañana (§35 a §43)": son nueve y la sesión 6 de la bitácora es esa mañana.
- 6.4 l. 793-795: 14,95 s / 4,8 s / 1,65 s / 8,47 s coinciden con §46 (l. 2986-2991) e `INCIDENTES.md:81`. "Estimación, unos cinco minutos" coincide con §46 l. 2949 e `INCIDENTES.md:89`.
- 8.2: +40 % y crecimiento con el tamaño del grupo (§22 l. 934-936); reconstrucción completa (§36 l. 2278-2281); 14 casos del heredado y decisión (§47 l. 3047-3056).
- 9 l. 1000-1002: **32 s** web (medidas 32,26 / 32,26 / 32,38 / 32,28), **42-61 s** WhatsApp (42,33 / 42,26 / 61,32 / 42,39; 52,29 tras una noche), **menos de 0,2 s** despierto (0,076-0,176), **ninguna petición perdida** (segundo cliente recibe 200): coincide con `reports/arranque_frio/resumen.json` y §52. Mismas cifras bien transcritas en 5.4 l. 746 y en el guion l. 21-23.
- 9 l. 1006-1009: SHA-256 con sal y comparación en tiempo constante: `src/acceso.py:85` usa `hmac.compare_digest` y l. 91 `hashlib.sha256(f"{sal}:{password}")`.
- 10: "4 de 24 veredictos ... todos en el mismo sentido" (§32 l. 1878-1882); "5 min 42 s y ningún fichero de código" (§43); "cobertura 1,0 en la agencia" (`agencia_hitl_v3`, §22).
- 11 l. 1055: "banco sin juez, menos de un minuto" es cierto: el runner es paralelo (`evals/runner.py:641`, `--workers` 4 por defecto) y `reports/empresa_quien/informe.md:5` dice "Duración: 45.6 s" para 53 casos.
- 12.1: siete ficheros en la tabla, `tests/test_riesgos.py` comprueba que cada `§` citado existe (l. 40-47) y que las diez casillas OWASP tienen fila (l. 60-66). `RETENCION.md:21` dice 90 días. Tres de operación con su cifra.
- 12.3: "Las consultas son literales del golden set o del registro de producción" coincide con el guion l. 6-8. "menos de 0,05 USD, estimación" está declarado como estimación aquí y en el guion.
- Resumen l. 31-32: "cuatro de los seis pasos" coincide con la tabla de `ALCANCE.md` §1 (l. 27-36). l. 49: 4 de 24 (§32).
- 1.3 l. 106-109: la cita del programa es literal (PDF, Módulo 5: "El objetivo del proyecto no está únicamente en que el sistema funcione, sino en justificar cada decisión técnica en términos de calidad, coste, escalabilidad, riesgo y mantenimiento") y las cinco características del capstone son las que estructuran los capítulos 1, 2, 3, 4-7 y 12. l. 138: 53+40+29 = 122. l. 83: `docs/TUTORIA_2026-09-22.md` existe.
- 1.2 l. 97-98: 3,8 s / 5,3 s p95 / 0,0021 USD coinciden con `ALCANCE.md` l. 38-41.
- Programa: la memoria usa "Definición del problema y contexto de uso real", "Diseño de la arquitectura", "Selección y justificación de modelos, patrones y herramientas", "Evaluación, observabilidad y control", "Documentación técnica y defensa del diseño" tal como los enuncia el PDF.

**Muestreo de los capítulos 3, 4, 5, 7 y 8 (47 cifras)**

- 2.4: 0,700 → 0,833 y 18/30 → 22/30 (§1); 29/38 → 33/38 y 0,444 → 0,778 (§12); 4 de 38 (§15); 910 llamadas, 0,57 USD, 3 de 38 → 0, 1 de 53, 1,2 USD (§27, §25); 0,778 → 1,0, +40 %, +0,5 s (§22).
- 2.6: 6.000 / 6.028 caracteres (§41). 2.7: 45/52 → 47/53, fugas 2 → 0, 27/36 → 29/38, 1 → 0, 0,880 → 0,778 (§8); 20 casos / 11 llegan / "17 frente a 9" / 7 y 9 (§11, §22); 588 de 588 en 22 ejecuciones (§23 l. 1128-1134); `accion_sin_aprobar` 40/40 (§42; `agencia_hitl_v3` n=40 media 1,0). 2.8: 3 de 5 → 5 de 5, 0,83 → 0,96, 100 % / 70 % (§39, §40), y la salvedad del §42 sobre el 0,96 está recogida.
- 3.1 (tabla completa): 48 / 47, 0,9038 / 0,6364, 3,284 / 3,295 s (+0,011), 0,1051 / 0,1077 USD (+2,5 %), 106 llamadas, 51.559 tokens, 31 / 0,825 / 0 de 40, trece casos mixtos, 21 / 95 líneas, 14 paquetes, 0 tests tocados y 10 nuevos, 19 min, LangGraph 1.2.12: todo coincide con §50 y con `reports/empresa_quien` y `reports/langgraph_empresa` `resumen.json`.
- 3.2: 1,1 s, 36 casos, unos 40 s (§7). 3.3: 5,5 veces más barato (§32 l. 1917); 14-05-2028 (§35); 0,882 / 0,735 sobre 68 casos, 1,12 / 0,32 s, 13 de 13, 75-88 %, doce puntos (§48); 13,2 % (§22, §25); precios de `claude-haiku-4-5` 1,00 / 5,00 (`src/provider.py:61-62`); `gemini-3.6-flash` dobla el 01-01-2027 (§29, `provider.py:69`).
- 4.2 (tabla): `empresa_quien` 48 / 0,9038 / 1,0; `agencia_hitl_v3` 31 / 0,825 / 0,92; `gestoria_agregacion_v2` 28 / 0,963 / 1,0; fechas 23 y 24-09; "49 con la línea anterior" (`empresa_temp0`, §27, §40); 0,96 → 0,92 (`agencia_quien` → `agencia_hitl_v3`); 38 → 40 (§42). Todo contra `resumen.json`.
- 4.3: 4 casos × 6 pasadas, 4 de 24, 5 y 6 de 10, 8/10 frente a 10/10 (§32, §33). 4.4: las dos filas coinciden con `ALCANCE.md` §5.c y §5.d y con `src/config.py` (l. 192, 232-233, 237). 4.5: los seis episodios están en §3, §11, §31, §45, §47, §49.
- 5.1: 0,00245; 0,0278; x11; 2,53 USD = 20 % de 12,87 (§17, §21); 0,25 USD (`ALCANCE.md:348`, §40); 0,00417 / 0,00076; 0,73 / 0,40 (§32); 0,0046 USD (§34) y 0,27 USD = 0,114 + 0,158 con 336 = 144 + 192 respuestas (§44). 5.3: 22 % (§16); 2.724 / 3.027 tokens, 4,20 caracteres por token, 91 consultas (§37). 5.4 tabla: 0,00198 / 0,00211 / 0,00406 USD; 973 / 1.130 / 2.671 tokens; 3,28 / 4,36; 2,95 / 4,01; 4,09 / 5,73 s: coinciden con los tres `resumen.json` (cociente coste/casos y tokens/casos recalculado). Ficha mensual: 1,0 / 4,0 / 19,8 y 2,0 / 8,1 / 40,6 USD, aritmética correcta. "Tres millonésimas" (14 × 0,20 / 10⁶ = 2,8 × 10⁻⁶) correcta.
- 7.1: 23 filas; 13 CC / 3 CD / 5 DC / 1 DD (recuento de la columna Cuadrante); R-04, R-06, R-11, R-13, R-21 son las cinco DC; ATLAS 5.6.0 (`RIESGOS.md` l. 22). 7.2: "ocho de los nueve guardarraíles, falta moderación" coincide con `MODULO_4.md` l. 61-76. 7.3: factor 75, seis variantes, trece pruebas (§34); cinco medidas, ocho repeticiones, veinte pruebas, 2,00x con 8 → 1,00x con 24 (§44). 7.4: fechas del Ómnibus (27-07-2026 consolidado, Reglamento de 8 de julio, 2 de diciembre de 2027, artículo 50 desde 2 de agosto de 2026) coinciden con `MODULO_4.md` l. 119-131. 7.5: 1,46 s / 1,23 s (§36).
- 8.1: 20 de 28, 0,769, cinco fallos a `procedimientos`, 25 de 28, 65 s (11:38:01 → 11:39:06), 0,923, 0,857 → 1,0, 77 %, 27 de 28 (§43, §45); 29 casos desde §49. 8.4: tres instancias (§26, §29, §35) y el 50 % (§21).
- Guion l. 136: "572 líneas" = 324 + 248 (`wc -l` de los dos ficheros del canal).

---

## Anexo del informe: mapa real de citas `§N` por capítulo de la memoria

Generado con grep sobre `MEMORIA.md` (líneas 1-1115). Sirve para reconstruir el Anexo A.

| Capítulo | Hallazgos citados |
|---|---|
| Resumen | 8, 22, 30, 32, 33, 43, 45 |
| 1.2 | 1 |
| 1.3 | 3, 4, 45, 46, 47 |
| 1.4 | 8 |
| 2.3 | 10, 13, 14 |
| 2.4 | 1, 6, 12, 15, 22, 27 (más 25 y 48 por referencia a 3.3) |
| 2.5 | 47 |
| 2.6 | 4, 5, 41 |
| 2.7 | 2, 5, 8, 9, 11, 22, 23, 33, 39, 40, 41, 42, 47 |
| 2.8 | 39, 40, 42 |
| 2.9 | 46 |
| 2.10 | 51 |
| 3.1 | 29, 50 |
| 3.2 | 7 |
| 3.3 | 17, 24, 25, 26, 29, 32, 35, 48 |
| 3.4 | 26 |
| 4.1 | 23, 30, 31, 47 |
| 4.2 | 42, 45, 49 |
| 4.3 | 24, 26, 30, 32, 33 |
| 4.5 | 3, 11, 31, 45, 47, 49 |
| 5.1 | 17, 21, 22, 28, 32, 34, 44 |
| 5.2 | 16, 17, 18, 24 |
| 5.3 | 16, 35, 37 |
| 5.4 | 22, 29, 32, 37, 52 |
| 6.1 | 46 |
| 6.2 | 37 |
| 6.3 | 35, 38, 39, 41, 42, 43 |
| 6.4 | 46 |
| 6.5 | 19 |
| 7.2 | 17, 19, 30, 32, 33, 35, 42 |
| 7.3 | 34, 44 |
| 7.5 | 36 |
| 7.6 | 35 |
| 8.1 | 1, 43, 45, 49 |
| 8.2 | 22, 36, 47 |
| 8.4 | 21, 26, 29, 35 |
| 9 | 6, 48, 52 |
| 12.2 | 21, 44 |

Hallazgos de 1 a 52 que la memoria **no cita en ningún capítulo**: **§20**. Todos los demás aparecen al menos una vez. (Los números 3, 4, 5, 6, 7, 8 que aparecen en 1.3, 2.4, 3.1, 3.2, 4.4, 5.1, 5.4 y 9 son en parte "§4.4", "§8.1", "§5.d", "§6.2", "§8.4" y "§7.x" referidos a capítulos, no a hallazgos: es la ambigüedad de M14.)
