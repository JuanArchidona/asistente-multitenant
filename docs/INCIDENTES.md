# Plan de respuesta a incidentes

> Una página, para el cuadrante que no tenía nada: los desconocidos-
> desconocidos de la matriz de Rumsfeld (`RIESGOS.md` R-23). El Módulo 4.4 pide
> para ese cuadrante un botón rojo y un plan de mitigación y comunicación. El
> botón rojo existía de hecho (el tope de prepago); el plan no estaba escrito.
> Escrito el 23-09-2026 para el sistema tal como está: dos inquilinos
> sintéticos, sin despliegue público, con un operador (Juan). Cuando haya
> despliegue y clientes, cada "quién" de abajo cambia de nombre, no de sitio.

## 1. Qué es un incidente aquí

Cualquiera de estas cinco cosas, y cualquier otra que se le parezca:

| # | Incidente | Cómo se detecta hoy | Riesgo de `RIESGOS.md` |
|---|---|---|---|
| I-1 | Un usuario recibe datos que su permiso no cubre, del mismo o de otro inquilino | Un caso `conf-*` o `inj-*` del banco que pasa a fallar; una consulta de producción con `denegados` vacío donde no debería; un aviso de una persona | R-02, R-03 |
| I-2 | Una clave de API queda expuesta (commit, log, respuesta de un agente, pantalla) | `git log -p` sobre `.env`; el consumo de la clave en la consola del proveedor sube sin ejecuciones conocidas; el puente devuelve contenido de `.env`; **desde el 23-09**, una clave revocada aparece como `consultas_fallidas` con tipo `AuthenticationError` en `observabilidad_cli` (§46) | R-04 |
| I-3 | Gasto anómalo | La consola del proveedor marca más de lo que suma `reports/` y el registro de producción; el crédito baja sin pasadas conocidas | R-08 |
| I-4 | El proveedor cambia de comportamiento o retira un modelo | Un test de precios o de conmutación falla; un 404 de modelo; una métrica del banco se mueve sin cambio en el repositorio; **desde el 23-09**, las consultas que revientan quedan en el registro con su tipo de error (`_fallo`), en vez de no dejar rastro (§46) | R-07 |
| I-5 | El sistema responde algo inaceptable (sesgado, inventado, fuera de ámbito) y alguien lo ve | Un aviso de una persona; el verificador de citas con una cita no resoluble; un caso de sesgo por encima del suelo | R-05, R-13, R-21 |

Lo que no está en esta tabla se trata como I-5 hasta que se sepa más.

## 2. El botón rojo, en orden

Se para primero y se investiga después. Cada paso es una orden, no una
intención:

1. **Cortar el gasto.** En la consola de Anthropic y en la de Google, revocar
   la clave afectada (o todas si no se sabe cuál). El prepago con recarga
   automática desactivada ya limita la pérdida máxima al crédito que quede;
   revocar la lleva a cero. **No activar nunca la recarga automática para
   "poder seguir trabajando" durante un incidente.**
2. **Parar el sistema.** Hoy no hay despliegue: basta con no lanzar
   `src.main` ni `evals.runner`. Cuando lo haya, el servicio se detiene antes
   de mirar nada.
3. **Congelar la evidencia.** No borrar ni reindexar. `uv run python
   scripts/simulacro_incidente.py` hace la copia de `reports/` y del
   registro de producción con manifiesto SHA-256 en `data/incidentes/`
   (1,65 s, §46); si el puente estaba en juego, copiar además
   `puente/REGISTRO_APP.md` a mano.
4. **Rotar las claves** y actualizar `.env`. Si la clave estuvo en un commit,
   además reescribir el historial no basta: la clave está comprometida desde
   el momento del push y se revoca igualmente.

## 3. Quién avisa a quién

| Situación | Quién | A quién | Cuándo |
|---|---|---|---|
| Cualquier incidente | Juan (operador) | Iraitz Montalbán (tutor), si afecta a lo que se defiende | Antes de 24 horas |
| I-1 con datos de una persona real | Juan | La persona afectada y, si procede, la AEPD (artículo 33 del RGPD: 72 horas) | Hoy no aplica: no hay datos reales. Se deja escrito para el día que los haya |
| I-2 | Juan | Nadie más: es su cuenta. Se registra | En el momento |
| I-4 | Juan | Nadie: es una decisión de línea base. Se registra en `HALLAZGOS.md` y `ALCANCE.md` §5.c si cambia la comparabilidad | En la sesión en que se detecta |

No hay más nombres porque no hay más personas. El plan dice dónde iría cada
uno, y eso es lo que un plan tiene que decir.

## 4. Qué se registra, y dónde

Todo incidente termina con una entrada en `docs/HALLAZGOS.md`, con el mismo
formato que los demás hallazgos: qué pasó, cómo se detectó, qué se midió, qué
se cambió. Si cambia el estado del proyecto, además en `CLAUDE.md` §2 o §8. Un
incidente que no acaba en un hallazgo no ha terminado.

Ya hay tres precedentes tratados así antes de que este plan existiera, y son la
prueba de que el formato funciona:

- **§19**: el puente leía el `.env` entero. Detectado probando, cerrado con la
  lista de denegación, medido antes y después.
- **§21 y §28**: un precio inflado un 50 % y un modelo que costaba cero.
  Detectados comparando la consola del proveedor con la contabilidad propia,
  cerrados con un test que recalcula desde tokens.
- **§29**: `gemini-2.5-flash` retirado para proyectos nuevos. Detectado al
  conmutar de proveedor, cerrado cambiando el modelo por defecto y dejando el
  camino verificado.

## 5. Lo que este plan no cubre, y lo dice

- ~~**No hay simulacro.**~~ **Hecho el 23-09-2026** (§46, `reports/simulacro_incidente`):
  clave revocada simulada, evidencia congelada y vuelta en **14,95 s** en total.
  La primera pulsación destapó que una consulta fallida no dejaba rastro en el
  registro; corregido. **Sigue sin simularse la mitad manual**: revocar y rotar
  la clave en las consolas y en Render, que exige navegador y la cuenta de Juan.
- **No hay canal para que un usuario avise.** Con dos inquilinos sintéticos no
  hay usuarios; con un despliegue, hace falta un correo o un formulario, y ese
  correo es un requisito del artículo 50 tanto como el aviso de IA.
- ~~**No hay retención definida**~~ Definida el 23-09 en `RETENCION.md` (R-16, §37).
