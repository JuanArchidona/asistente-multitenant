# Despliegue mínimo con autenticación

> La interfaz desplegada (`app.py`) y lo que la rodea: usuarios, tope de
> gasto, Render. Cierra el punto 3 del bloque 1 de `ALCANCE.md` ("autenticación
> y tope de gasto en el despliegue") en su versión mínima, la que sirve para
> una demostración en vivo o grabada. Escrito el 23-09-2026.

## Qué es y qué no

Es la interfaz de la entrega 3.1 (Streamlit en Render) adaptada al sistema
multi-tenant: entrada con usuario y contraseña, un inquilino por credencial,
roles que viajan al control de acceso, aviso del artículo 50, traza de cada
respuesta, registro de producción y tope de gasto blando.

No es: carga de documentos desde la interfaz (la 3.1 la tenía; aquí el corpus
es versionado y el alta de documentos es ingesta), gestión de usuarios desde
la interfaz, ni un sistema de identidad. Con usuarios reales, el fichero de
usuarios se sustituye por un proveedor de identidad (OIDC) y esta capa
desaparece; lo que queda es la idea, que el inquilino y los roles vienen de la
identidad y no de la interfaz.

## En local

```bash
uv sync --group app
cp usuarios.example.json usuarios.local.json   # y cambiar la sal y los hashes
uv run python -m src.acceso hash --sal MI_SAL --password MI_CONTRASENA
uv run streamlit run app.py
```

Sin `usuarios.local.json` arranca con las credenciales de ejemplo (contraseña
`cambiar` para los cuatro usuarios) **y lo dice en pantalla**. Los cuatro
usuarios de ejemplo cubren las cuatro combinaciones que interesan en una
demostración:

| Usuario | Inquilino | Roles | Para enseñar |
|---|---|---|---|
| `empleado` | empresa de servicios | ninguno | El anexo confidencial se retiene por permiso |
| `direccion` | empresa de servicios | `rrhh_direccion` | El mismo anexo, visible |
| `comercial` | agencia | ninguno | Expediente retenido; DNI, teléfono e ingresos redactados en el CRM |
| `gerencia` | agencia | `direccion` | Todo visible, y la rama estructurada por MCP |

## En Render

`render.yaml` es el blueprint. New > Blueprint > este repositorio; Render pide
las tres variables sin valor: las dos claves de API y `APP_USUARIOS_JSON`, que
es el contenido de `usuarios.local.json` en una línea. El arranque lo escribe
a disco si no existe.

Tres decisiones heredadas de la 3.1 y una nueva:

- **Plan gratuito.** El servicio se duerme sin tráfico (primer arranque lento)
  y el disco es efímero: el índice se reconstruye desde el corpus versionado
  la primera vez que un usuario de cada inquilino entra. Cuesta una pasada de
  embeddings por inquilino, unos 3.000 tokens (§37).
- **`uv sync --frozen`**: el entorno es exactamente el de `uv.lock`, el mismo
  que inventaría `AIBOM.md`.
- **Las claves nunca están en el repositorio** (`sync: false`).
- **Nueva: `TOPE_GASTO_USD`**, 2 USD por defecto. Ver abajo.

Lo que **no** está resuelto y hay que saber antes de dar la URL a nadie: el
servicio es público en internet. La autenticación es la única puerta, y es
una puerta de demostración. No se deja levantado más tiempo del que dure la
defensa, igual que se hizo con la 3.1.

## Los dos topes de gasto

| Tope | Dónde | Qué limita | Qué no ve |
|---|---|---|---|
| **Duro** | Prepago sin recarga automática en Anthropic y Google | La pérdida máxima real: el crédito que quede | Nada: cuando se acaba, se acaba |
| **Blando** | `TOPE_GASTO_USD` en la interfaz, sobre el registro de producción | Que la interfaz siga respondiendo cuando lo registrado supera el tope | Los embeddings (§37), lo gastado fuera de la interfaz (§16), un modelo sin precio (§28) |

El blando existe para que la demostración no pueda vaciar el crédito por un
descuido, y es un suelo por construcción. Si los dos se cruzan en el sentido
malo (el registro dice 1 USD y el crédito está a cero), manda el duro y la
interfaz mostrará el error del proveedor: no se disimula.

## Lo que se mide

- **Coste por consulta y acumulado por inquilino**, en la barra lateral, del
  registro de producción (`src/observabilidad.py`).
- **Latencia p95 por inquilino**, del mismo registro.
- **El control de acceso, en la respuesta**: qué se retuvo por permiso y qué
  campos se redactaron, con el mismo usuario que entró. Es la demostración
  de que el permiso va dentro de la búsqueda: entrar como `empleado` y como
  `direccion` con la misma pregunta.

## Lo medido en el primer despliegue (23-09-2026, HALLAZGOS.md §38)

| Medida | Valor |
|---|---|
| Primer despliegue desde el blueprint, hasta "Deploy live" | **1 min 32 s** |
| Primera carga de la página tras el despliegue | unos 30 s |
| Log de arranque | sin errores; `uv` construye el paquete y Streamlit arranca |
| Pantalla inicial | el formulario, con el aviso de credenciales de ejemplo |
| Login como `empleado` | **Fallo**: la configuración exigía `GEMINI_API_KEY_JUEZ` a un proceso que nunca evalúa. Corregido con `load_config(con_juez=False)` en la interfaz |
| Redespliegue del arreglo (automático desde `master`) | 2 min 06 s y 1 min 21 s los dos siguientes |
| Consulta de vacaciones como `empleado` | Respuesta correcta citando el convenio; traza 3,9 s, reloj de pared 15-23 s con el arranque en frío; anexo retenido por permiso y avisado |
| Salario como `direccion` frente a `empleado` | El permiso funciona en recuperación (a `direccion` le llega el anexo, a `empleado` no). El generador se negó a dar el salario a `direccion` citando la cabecera del anexo: ver §39 y el guion, que usa otra pregunta |
| Barra de gasto | Va una consulta por detrás (se pinta antes de procesar la consulta). 0,0018 USD la primera consulta, 0,0046 USD tras dos |

La URL pública es `https://asistente-multitenant.onrender.com`. El servicio
se deja suspendido fuera de las pruebas y de la defensa.

## Riesgos que abre, y dónde están registrados

- R-08 (coste): el tope blando reduce el residual "sin límite de peticiones",
  pero no lo cierra: no hay límite por usuario ni por minuto.
- R-18 (transferencias): con el servicio público, cada consulta viaja al
  proveedor desde Frankfurt; los datos siguen siendo sintéticos.
- R-20 (salida): la respuesta sigue siendo texto para una persona; ningún
  canal la reenvía.
