# Bitácora del TFM — Asistente multi-tenant

> Diario de sesiones. Entradas de más reciente a más antigua.
> El histórico de la entrega 3.3, de la que parte este repositorio, está en
> `BITACORA_3.3.md`.

## 2026-09-20 — Sesión 1: reorientación del TFM y construcción del núcleo

Primera sesión del TFM tras dos meses sin tocarlo. Sesión larga: se reorientó el
proyecto y se construyeron el multi-tenant, la rama estructurada y la capa de
gobernanza.

### Decisiones

- **El TFM no arranca de cero.** Parte del sistema acumulado en las entregas
  2.1, 2.3, 3.1 y 3.3, que ya cubría cuatro de los seis pasos del flujo objetivo
  y traía un banco de 109 casos. Repositorio nuevo y público,
  `asistente-multitenant`, conservando la historia de commits de la 3.3.
- **Dos inquilinos**: la empresa heredada (regresión) y una agencia
  inmobiliaria construida completa. Se descartó un tercero de asesoría para
  concentrar el esfuerzo.
- **Python vanilla** con capítulo de justificación frente a LangGraph.
- **Rama estructurada por MCP**, no por herramientas cableadas.
- **Control de acceso estructural**, no por prompt.
- El análisis del **Módulo 4** se produce dentro del TFM.
- Canales: correo real y WhatsApp en pruebas. Slack descartado.
- Detalle completo en `ALCANCE.md`.

### Hecho

1. Credenciales: dos claves de Anthropic separadas, sistema y juez, siguiendo el
   feedback de la 3.3. La anterior estaba revocada o vencida.
2. Verificado que el MCP de idealista **no es consumible desde código**: su
   documentación dice que solo funciona con el conector aprobado para Claude.
   Solicitado acceso a la API oficial; fuente externa real será el Catastro.
3. Inquilino como concepto de primera clase, con aislamiento por colección.
4. Segundo inquilino completo: corpus, banco de 38 casos y CRM sintético
   reproducible.
5. Bancos de evaluación por inquilino, con invariantes que se ejecutan sobre
   cualquier inquilino que exista.
6. Rama estructurada: servidor MCP del CRM con cinco herramientas, cliente MCP y
   bifurcación en el agente.
7. Capa de gobernanza: permisos dentro de la búsqueda y redacción de campos
   sensibles en los resultados de herramienta.

### Medido

| Métrica | Resultado |
|---|---|
| Inquilino A, casos que pasan | 45/52 (3.3) → **47/53** |
| Inquilino A, fugas literales | 2 → **0** |
| Inquilino C, casos que pasan | 18/30 → **29/38** |
| Inquilino C, fugas literales | 1 → **0** |
| Tests | 322 → **574**, todos en verde |
| Coste de una pasada del banco | ~0,10 USD por inquilino, sin juez |

Diez hallazgos anotados en `HALLAZGOS.md`, cada uno con la ejecución que lo
respalda. Los dos que más van a pesar en la memoria:

- **Arreglar el enrutado destapó fugas que estaban escondidas.** El sistema
  parecía seguro porque fallaba antes de llegar al punto donde se equivoca.
- **Una métrica de seguridad agregada es engañosa por construcción.** Solo seis
  de los doce casos de seguridad llegaron a la etapa donde el control actúa; el
  resto está en verde por no haber recuperado nada.

### Pendiente para la próxima sesión

- [ ] Métrica de **cobertura del riesgo**: qué proporción de los casos de
      seguridad llega a la etapa donde el control actúa. Es barata y arregla el
      punto ciego del hallazgo 9.
- [ ] Solapamiento `procesos` / `cartera` en el inquilino C: ensucia seis casos
      y no se arregla con más palabras en el prompt. Probablemente haya que
      sacar el expediente del corpus documental.
- [ ] Observabilidad y coste acumulado en producción (bloque 2).
- [ ] Canal de correo de extremo a extremo (bloque 2).
- [ ] Despliegue en Render con autenticación y tope de gasto (bloque 1, punto 3).
- [ ] Tope de gasto en la cuenta de Anthropic, antes de exponer nada.

### Notas

- El entorno arrastra activado el `.venv` del repositorio anterior, así que `uv`
  avisa en cada comando. Lo ignora y usa el correcto.
- `reports/` guarda cinco ejecuciones de esta sesión: `agencia_base`,
  `agencia_v2`, `agencia_v3`, `agencia_v4` y `empresa_gobernanza`. Son la
  evidencia de los hallazgos y no se borran.
