# Prueba de carga y concurrencia — 2026-09-26

## Frente HTTP en Render (sin consultas, coste cero)

| Servicio | A la vez | Peticiones | p50 (s) | p95 (s) | max (s) | Errores |
|---|---|---|---|---|---|---|
| asistente-multitenant | 1 | 3 | 0.08 | 0.097 | 0.097 | 0 |
| asistente-multitenant | 5 | 15 | 0.1 | 0.108 | 0.122 | 0 |
| asistente-multitenant | 10 | 30 | 0.117 | 0.14 | 0.178 | 0 |
| asistente-multitenant | 20 | 60 | 0.137 | 0.166 | 0.183 | 0 |
| asistente-whatsapp-n2s9 | 1 | 3 | 0.095 | 0.097 | 0.097 | 0 |
| asistente-whatsapp-n2s9 | 5 | 15 | 0.1 | 0.105 | 0.108 | 0 |
| asistente-whatsapp-n2s9 | 10 | 30 | 0.102 | 0.13 | 0.134 | 0 |
| asistente-whatsapp-n2s9 | 20 | 60 | 0.12 | 0.16 | 0.168 | 0 |

## Pipeline compartido entre hilos — `empresa_servicios` (8 consultas por nivel)

| Concurrencia | Lote (s) | Consultas/min | Pared p50 (s) | Pared p95 (s) | Pared max (s) | Coste (USD) | Errores | Cambios de enrutado | Confidencial denegada |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 25.735 | 18.65 | 3.486 | 3.625 | 3.625 | 0.0150 | 0 | 0 | True |
| 2 | 20.313 | 23.63 | 3.51 | 11.583 | 11.583 | 0.0155 | 0 | 0 | True |
| 4 | 6.746 | 71.15 | 3.114 | 3.846 | 3.846 | 0.0152 | 0 | 0 | True |
| 8 | 13.29 | 36.12 | 3.243 | 13.285 | 13.285 | 0.0149 | 0 | 0 | True |

Coste total del bloque: 0.0605 USD.

## Pipeline compartido entre hilos — `agencia_inmobiliaria` (4 consultas por nivel)

| Concurrencia | Lote (s) | Consultas/min | Pared p50 (s) | Pared p95 (s) | Pared max (s) | Coste (USD) | Errores | Cambios de enrutado | Confidencial denegada |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 20.693 | 11.6 | 5.501 | 5.949 | 5.949 | 0.0319 | 0 | 0 | None |
| 4 | 5.049 | 47.54 | 4.604 | 5.046 | 5.046 | 0.0261 | 0 | 0 | None |

Coste total del bloque: 0.0580 USD.
