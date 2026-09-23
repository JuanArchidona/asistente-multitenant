# Borrado cronometrado: `anexo_confidencial_plantilla.md` (empresa_servicios)

Fecha: 2026-09-23T09:27:08+02:00. Estrategia `chars`, embeddings `gemini-embedding-001` a 768 dimensiones.

| Medida | Valor |
|---|---|
| Fragmentos del fichero en el indice, antes | 3 |
| Fragmentos del fichero en el indice, despues | 0 |
| Fragmentos totales, antes / despues | 15 / 12 |
| Borrado efectivo (cero fragmentos y el resto intacto) | **EFECTIVO** |
| Tiempo hasta borrado efectivo | **1.23 s** |
| Tiempo de restauracion (camino de rectificacion) | **1.12 s** |
| Fragmentos tras restaurar / antes | 3 / 3 |
| Caracteres embebidos por pasada | 8444 |

El borrado es una reconstruccion completa del indice del inquilino, asi que
cuesta lo que cuesta reindexar su corpus entero, y ese coste crece con el
corpus. Un borrado incremental (eliminar por metadato `archivo` sin
reindexar) seria O(1) y esta fuera del sprint; lo que se defiende aqui es
que el camino existe, es verificable contra la coleccion y esta medido.

No cubre el registro de observabilidad: las consultas que citaron el
documento siguen registradas (RIESGOS.md R-16).
