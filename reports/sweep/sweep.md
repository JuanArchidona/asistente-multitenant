# Barrido de configuraciones — recuperación

- Casos evaluados: 43 (los del golden set que declaran fichero esperado)
- Embeddings de consulta calculados: 3 (el resto se reutilizaron de la caché)
- Sin generación ni juez LLM: el coste del barrido es solo de embeddings.
- La recuperación se hace sobre la fuente correcta conocida, sin pasar por el
  enrutador, para que un error de enrutado no contamine la comparación.

| Configuración | Fragmentos | hit_rate | recall@k | precision@k | MRR | Δ recall | Δ precision | Dist. media |
|---|---|---|---|---|---|---|---|---|
| baseline (3.1) | 15 | 1.000 | 1.000 | 0.674 | 0.985 | - | - | 0.353 |
| chars-400 | 28 | 1.000 | 1.000 | 0.830 | 0.961 | = | +0.155 | 0.339 |
| chars-1200 | 9 | 1.000 | 1.000 | 0.659 | 0.973 | = | -0.015 | 0.369 |
| headings-800 | 38 | 1.000 | 1.000 | 0.806 | 1.000 | = | +0.132 | 0.346 |
| headings-1200 | 36 | 1.000 | 1.000 | 0.806 | 1.000 | = | +0.132 | 0.349 |
| headings-400 | 43 | 1.000 | 1.000 | 0.826 | 1.000 | = | +0.151 | 0.344 |
| top_k=2 | 15 | 0.977 | 0.965 | 0.930 | 0.977 | -0.035 | +0.256 | 0.332 |
| top_k=6 | 15 | 1.000 | 1.000 | 0.659 | 0.985 | = | -0.015 | 0.366 |
| headings + top_k=2 | 38 | 1.000 | 1.000 | 0.919 | 1.000 | = | +0.244 | 0.317 |
| dims=1536 | 15 | 1.000 | 1.000 | 0.674 | 0.985 | = | = | 0.360 |
| dims=3072 | 15 | 1.000 | 1.000 | 0.674 | 0.985 | = | = | 0.329 |
