# Asistente interno multi-tenant de conocimiento y datos

[![CI](https://github.com/JuanArchidona/asistente-multitenant/actions/workflows/ci.yml/badge.svg)](https://github.com/JuanArchidona/asistente-multitenant/actions/workflows/ci.yml)

Trabajo Fin de Máster de Juan Archidona Ahijado (Máster en IA Generativa
Avanzada, The Bridge).

Un asistente para empresas de servicios profesionales que responde
consultas combinando dos fuentes: la documentación propia de cada cliente,
por RAG, y sus datos de negocio, por servidores MCP. El mismo código sirve a
varios clientes (inquilinos) sin tocar un fichero de Python, porque todo lo
que distingue a uno vive en un manifiesto declarativo. El control de acceso
se aplica **antes** de que el modelo vea nada, la única escritura la aprueba
una persona, y cada decisión tiene una medida detrás.

| | |
|---|---|
| Memoria técnica | [`docs/MEMORIA.md`](docs/MEMORIA.md) (el PDF entregado se genera de aquí) |
| Servicio desplegado | <https://asistente-multitenant.onrender.com> |
| Usuarios de evaluación | `eval_empleado`, `eval_direccion` (empresa de servicios), `eval_comercial`, `eval_gerencia` (agencia); las contraseñas van en el comentario de la entrega, no aquí |
| Recorrido guiado | [`docs/GUION_DEMO.md`](docs/GUION_DEMO.md) |
| Hallazgos medidos | [`docs/HALLAZGOS.md`](docs/HALLAZGOS.md), cada uno con la ejecución que lo respalda en `reports/` |

## Tres cifras

| Afirmación | Cifra | Hallazgo |
|---|---|---|
| Dar de alta un cliente nuevo no exige código | 5 min 42 s, cero ficheros `.py`, 27 de 28 casos de su banco | §43, §45 |
| El control de acceso está en la búsqueda, no en el prompt | Cobertura del riesgo 1,0 en la agencia; `fuga_literal` 10 de 10 | §22, §40 |
| El evaluador también se evaluó | 4 de 24 veredictos del juez LLM eran falsos, los cuatro en el mismo sentido | §30, §32 |

## El flujo

```
entrada (web, WhatsApp, correo)
  → autenticación: la credencial fija el inquilino y los roles
  → clasificador: categoría y destino (documental | estructurado | ambos | otro)
  → recuperación: colección propia del inquilino con el permiso en el where,
                  o herramientas MCP con redacción de campos al salir
  → generación anclada, que sabe quién pregunta
  → gobernanza: verificación de citas, escrituras pendientes de aprobación
  → registro de producción (sin guardar la respuesta) y juez sobre una muestra
```

Python sin framework de orquestación; la comparación con LangGraph está
construida y medida (memoria, capítulo 3.1).

## Ejecutarlo

Requiere Python 3.11+ y [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/JuanArchidona/asistente-multitenant
cd asistente-multitenant
uv sync --group judge --group app --group langgraph
uv run pytest                         # 1.251 pruebas, ninguna llama a una API de pago

cp .env.example .env                  # claves propias: Anthropic, Gemini (sistema, juez, embeddings)
uv run python -m src.ingest_cli       # indexa el inquilino activo (TENANT_ID, por defecto empresa_servicios)
uv run python -m src.main "¿Cuántos días de vacaciones me corresponden?"
uv run python -m evals.runner --etiqueta prueba --sin-juez   # banco sin juez, menos de un minuto
uv run streamlit run app.py           # interfaz; usuarios de ejemplo en usuarios.example.json
```

`TENANT_ID=agencia_inmobiliaria` o `TENANT_ID=gestoria_laboral` cambian de
inquilino. El resto de comandos (sesgo, carga, red-teaming, observabilidad,
supresión RGPD) está en el anexo A de la memoria y en `CLAUDE.md` §7.

## Dónde está cada cosa

```
tenants/<id>.json         Manifiesto de cada inquilino: categorías, MCP, política de acceso, AI Act
corpus/<id>/              Documentos sintéticos de cada inquilino
mcp_servers/              Servidor MCP del CRM de la agencia
src/                      El sistema: enrutador, recuperación, gobernanza, agente, canales, registro
evals/                    Banco de evaluación por inquilino, métricas y experimentos
reports/<etiqueta>/       Evidencia de cada ejecución: resumen, informe y trazas
docs/                     Memoria, hallazgos, riesgos, AIBOM, prompts, despliegue, incidentes
app.py, render.yaml       Interfaz web y blueprint de Render
```

Los tres inquilinos son **sintéticos**: ningún dato real de ninguna empresa
entra en este repositorio, que es público.

## Calidad y despliegue

- **CI** en cada push: `ruff`, las pruebas y una auditoría de vulnerabilidades
  de lo que se despliega (`pip-audit`).
- **Render solo despliega un commit con la CI en verde**
  (`autoDeployTrigger: checksPass` en los tres servicios, vigilado por test).
- **En producción**, verificación determinista de citas sobre todas las
  consultas y un juez de otra familia que el generador sobre la mitad, sin
  guardar la respuesta.

## Origen

El repositorio parte de la entrega 3.3 del máster y conserva su historia de
commits: lo anterior a `docs: add TFM scope and closed decisions` es esa
entrega. Su README está en [`docs/README_3.3.md`](docs/README_3.3.md) y su
bitácora en [`docs/BITACORA_3.3.md`](docs/BITACORA_3.3.md).
