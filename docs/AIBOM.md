# AIBOM: inventario de lo que compone el sistema

> **Generado** por `scripts/generar_aibom.py` a partir de `uv.lock`,
> `pyproject.toml`, `.python-version`, `src/config.py`, `src/provider.py`,
> `tenants/*.json`, `corpus/` y `datos/`. No se edita a mano:
> `tests/test_aibom.py` lo regenera y falla si difiere. La version
> legible por maquina, con la forma de CycloneDX 1.6, es `docs/aibom.json`.
>
> Cierra el riesgo R-09 de `RIESGOS.md` (cadena de suministro, OWASP LLM 5):
> sin inventario no se puede saber si un incidente de una dependencia o de
> un modelo afecta al proyecto.

## Entorno de ejecucion

- Python `3.11` (`.python-version`); el lock exige `>=3.11`.
- `uv.lock` revision 3: 12 paquetes directos y 142 transitivos, todos con version y origen fijados.
- Node para el puente MCP: **sin fijar en el repositorio**. Lo pone el equipo
  que ejecuta la app. Es el unico componente ejecutable cuya version no
  esta escrita, y por eso se dice aqui.

## Paquetes declarados

| Paquete | Version | Grupo | Origen |
|---|---|---|---|
| `anthropic` | 0.121.0 | runtime | https://pypi.org/simple |
| `chromadb` | 1.5.9 | runtime | https://pypi.org/simple |
| `deepeval` | 4.1.7 | judge | https://pypi.org/simple |
| `google-genai` | 2.17.0 | runtime | https://pypi.org/simple |
| `langgraph` | 1.2.12 | langgraph | https://pypi.org/simple |
| `mcp` | 2.2.0 | runtime | https://pypi.org/simple |
| `pydantic` | 2.13.4 | runtime | https://pypi.org/simple |
| `pypdf` | 6.15.0 | runtime | https://pypi.org/simple |
| `pytest` | 9.1.1 | dev | https://pypi.org/simple |
| `python-dotenv` | 1.2.2 | runtime | https://pypi.org/simple |
| `ruff` | 0.16.2 | dev | https://pypi.org/simple |
| `streamlit` | 1.64.0 | app | https://pypi.org/simple |

Los 142 transitivos estan en `docs/aibom.json`, con version y origen.

## Modelos

Los valores por defecto de `src/config.py`; una variable de entorno los
cambia, y entonces el inventario vigente es el de ese despliegue, no este.

| Modelo | Proveedor | Roles (variable de entorno) | Precio USD por millon de tokens (entrada, salida) |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | Anthropic | ANTHROPIC_MODEL_GENERATOR, ANTHROPIC_MODEL_ROUTER | 1.00 / 5.00 |
| `claude-sonnet-5` | Anthropic | BUILDER_MODEL | 2.00 / 10.00 |
| `gemini-3.6-flash` | Google | GEMINI_MODEL, JUDGE_MODEL | 0.75 / 3.75 |
| `gemini-embedding-001` | Google | GEMINI_EMBED_MODEL | **sin precio en la tabla** |

## Servicios externos

Cada llamada a un modelo es una transferencia de datos a este servicio
(RIESGOS.md R-18).

| Servicio | Endpoint |
|---|---|
| Anthropic | `https://api.anthropic.com` |
| Google | `https://generativelanguage.googleapis.com` |

## Servidores MCP

| Servidor | Orden de arranque | Runtime |
|---|---|---|
| `agencia_inmobiliaria/crm` | `python -m mcp_servers.agencia_crm` | python (fijado por .python-version y uv.lock) |
| `puente/servidor.mjs` | `node puente/servidor.mjs` | node, SIN FIJAR en el repositorio (sin package.json ni .nvmrc); sin dependencias |

## Datos

| Conjunto | Documentos | Origen |
|---|---|---|
| `corpus/agencia_inmobiliaria` | 10 | sintetico, escrito para el proyecto; ningun dato real |
| `corpus/empresa_servicios` | 7 | sintetico, escrito para el proyecto; ningun dato real |
| `corpus/gestoria_laboral` | 6 | sintetico, escrito para el proyecto; ningun dato real |
| `datos/agencia_inmobiliaria/crm.json` | 1 | sintetico, generado con semilla fija por scripts/generar_crm_agencia.py |

## Como se mantiene

```bash
uv run python scripts/generar_aibom.py             # regenera
uv run python scripts/generar_aibom.py --comprobar # sale con 1 si esta viejo
```

Cuando cambia `uv.lock`, un modelo por defecto o un manifiesto, la suite
falla hasta que se regenera. Es la unica forma de que un inventario diga la
verdad seis meses despues de escribirse.
