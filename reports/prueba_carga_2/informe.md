# Prueba de carga y concurrencia — 2026-09-26

## Pipeline compartido entre hilos — `empresa_servicios` (8 consultas por nivel)

| Concurrencia | Lote (s) | Consultas/min | Pared p50 (s) | Pared p95 (s) | Pared max (s) | Coste (USD) | Errores | Cambios de enrutado | Confidencial denegada |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 23.729 | 20.23 | 3.316 | 3.617 | 3.617 | 0.0155 | 0 | 0 | True |
| 2 | 12.742 | 37.67 | 3.161 | 3.543 | 3.543 | 0.0153 | 0 | 0 | True |
| 4 | 6.806 | 70.53 | 3.215 | 3.714 | 3.714 | 0.0157 | 0 | 0 | True |
| 8 | 4.164 | 115.27 | 3.183 | 4.163 | 4.163 | 0.0147 | 0 | 0 | True |

Coste total del bloque: 0.0612 USD.

## Pipeline compartido entre hilos — `agencia_inmobiliaria` (4 consultas por nivel)

| Concurrencia | Lote (s) | Consultas/min | Pared p50 (s) | Pared p95 (s) | Pared max (s) | Coste (USD) | Errores | Cambios de enrutado | Confidencial denegada |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 17.943 | 13.38 | 4.593 | 4.611 | 4.611 | 0.0283 | 0 | 0 | None |
| 4 | 6.207 | 38.67 | 5.05 | 6.206 | 6.206 | 0.0284 | 0 | 0 | None |

Coste total del bloque: 0.0567 USD.
