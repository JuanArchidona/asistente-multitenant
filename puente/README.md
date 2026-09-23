# Puente MCP con el proyecto MASTER IA TFM

Servidor MCP local sobre stdio, en Node y sin dependencias. Da a la app de
Claude lo que el conector de GitHub no puede dar: **el arbol de trabajo sin
pushear**, **un sitio donde dejar rastro**, y desde el 23-09-2026 **un ciclo
completo**: Claude Code encarga, la app ejecuta y registra, el puente avisa a
Claude Code y le adelanta un analisis, y la siguiente sesion de Claude Code lo
recibe sin que nadie tenga que acordarse de mirar.

El diseno y su justificacion estan en `docs/SINCRONIZACION_SUPERFICIES.md`. Esto
es la puesta en marcha y lo medido.

## El ciclo

```
Claude Code                    puente                         app de Claude
-----------                    ------                         -------------
encargar.mjs  ── escribe ──>  ENCARGOS_APP.md  <── lee ──    encargos_tfm
   --abrir    ── enlace claude:// con el encargo en la caja ──>  (chat; Juan pulsa enviar)
                                                              o tarea programada
                                                                 (desatendido)
                              REGISTRO_APP.md  <── escribe ── registrar_tfm
                              AVISOS_CODE.md   <── crea ────── (el puente, al registrar)
                              analizar.mjs     ── sesion de solo lectura, 10-30 s
hook UserPromptSubmit <── inyecta los avisos POR ATENDER en cada prompt
avisos.mjs --atendido ── cierra el aviso
```

**La cadena termina en Claude Code.** Un aviso nunca genera un encargo nuevo
por si solo: la sesion de analisis no puede escribir (corre con `--restricted`
y sin `Write`), y a la sesion interactiva se le dice en la propia inyeccion que
si la accion es volver a encargar, se lo proponga a Juan. Dos agentes que
reaccionan el uno al otro sin nadie en medio amplifican un error en vez de
cazarlo.

## Que expone, y que no

| Herramienta | Que hace |
|---|---|
| `encargos_tfm` | Devuelve los encargos pendientes **literales**, sin lanzar ninguna sesion. Con `solo_desatendidos: true` devuelve solo los que se pueden hacer sin navegador ni nadie delante, y dice cuantos supervisados quedan fuera. |
| `consultar_tfm` | Responde una pregunta sobre el repositorio leyendo el arbol real, incluido lo no pusheado. **Solo lectura.** |
| `registrar_tfm` | Anade una entrada al registro de trabajo. `append` determinista sobre un fichero de ruta fija. Con `encargo` marca ese encargo como atendido. **Siempre** deja un aviso a Claude Code y lanza su analisis en segundo plano. |

No expone nada mas. Quien llama controla **el texto de una pregunta, un
booleano y siete campos de texto**; binario, directorio, banderas, lista de
herramientas y rutas de los cuatro ficheros son constantes de `servidor.mjs`.

## Los tres ficheros, y quien escribe cada uno

| Fichero | Lo escribe | Lo lee | Versionado |
|---|---|---|---|
| `ENCARGOS_APP.md` | Claude Code (`encargar.mjs`); el puente lo marca al registrar | la app (`encargos_tfm`) | No |
| `REGISTRO_APP.md` | el puente (`registrar_tfm`) | Claude Code, `analizar.mjs` | No |
| `AVISOS_CODE.md` | el puente al registrar; `analizar.mjs`; Claude Code al atender | el hook de Claude Code | No |

## Encargar: el buzon, el modo y el enlace

```bash
node puente/encargar.mjs --titular T --pide P --para Q --terminado C --donde D \
                         [--modo desatendido|supervisado] [--abrir]
node puente/encargar.mjs --listar
node puente/encargar.mjs --enlace E-0003 [--abrir]
```

Los cinco campos son obligatorios. Un encargo sin criterio de terminado o sin
sitio donde dejar el resultado se cumple a medias y nadie puede decir que no.

**El modo lo decide quien encarga**, porque es quien sabe si hace falta
navegador o sesion:

| Modo | Que puede necesitar | Quien lo atiende |
|---|---|---|
| `desatendido` | Busqueda web, conector de GitHub, `consultar_tfm`, redaccion | La **tarea programada** del proyecto, sola; o un chat |
| `supervisado` (por defecto) | Navegador con sesion (campus, formularios), una decision de Juan | Un **chat con Juan delante** |

`--abrir` abre la app de Claude con la orden de atender el encargo ya escrita
en la caja, por el enlace profundo `claude://cowork/new?q=...`. **La app no
auto-envia**: esta documentado como decision deliberada y no como carencia,
asi que queda una pulsacion humana. No es friccion: es el punto donde alguien
mira.

**El enlace no abre el proyecto, y esta medido dos veces** (21-09 en un puente
equivalente de este equipo, 23-09 aqui): `claude://claude.ai/project/<uuid>?q=`
abre el proyecto e ignora `q`, la caja llega vacia. `q` solo funciona con las
rutas `/new`, y `folder` no convive con `q`. Por eso la conversacion se abre
**fuera del proyecto** y el texto lleva un preambulo que suple sus
instrucciones en lo esencial. El puente esta igualmente, porque se declara a
nivel de aplicacion y no de proyecto.

Ademas, cada vez que la app registra algo, el puente lanza **un aviso en el
escritorio de Windows** para Juan (una notificacion normal del sistema). Es
solo para la persona; Claude Code se entera por el hook.

**No hay herramienta MCP para escribir en el buzon, y es deliberado.** A la app
la puede dirigir un modelo al que se le cuele una instruccion en un documento o
en una pagina web; si escribir fuera una herramienta, ese modelo podria
fabricarse la orden de trabajo que luego dice haber cumplido. Quien ejecuta los
encargos no puede darse encargos a si mismo.

Por el mismo motivo, **marcar un encargo como atendido lo hace el puente y no
quien dice haberlo hecho**: solo ocurre cuando `registrar_tfm` cita el
identificador. Los tres casos se distinguen en vez de colapsarse:

| Caso | Que pasa |
|---|---|
| El identificador no existe | **Falla y no registra nada.** Registrarlo dejaria una entrada que dice atender algo que nadie pidio, y el encargo real seguiria pendiente. |
| El encargo ya estaba atendido | Se registra, y la respuesta avisa de que es una segunda entrada sobre el mismo. |
| Sin campo `encargo` | Se registra como trabajo sin encargo previo, y el registro lo dice. |

## La tarea programada de la app (modo desatendido)

Se crea una vez, en el proyecto MASTER IA TFM, en **Programado**. Con la
frecuencia que se quiera (cada hora esta bien: el encargo espera a la
siguiente pasada, y eso es latencia, no fallo). El texto:

> Llama a encargos_tfm con solo_desatendidos = true. Si no devuelve ningun
> encargo, termina aqui: no hagas nada mas y no registres nada. Si devuelve
> encargos, atiende cada uno tal cual esta escrito, usando solo el conector de
> GitHub, consultar_tfm y la busqueda web; no uses el navegador. Cuando
> termines cada uno, o si no puedes terminarlo, llama a registrar_tfm citando
> su identificador en el campo encargo, contando tambien lo que fallo y por
> que. No inventes encargos, no atiendas encargos supervisados y no pidas
> confirmacion: si algo no se puede hacer sin una persona, registralo asi.

Dos limites medidos en un puente equivalente de este equipo el 21 y 22 de
septiembre, que condicionan que encargos se declaran desatendidos:

- Una tarea programada **alcanza el puente MCP local pero no el navegador ni
  la carpeta del proyecto**. Todo lo que necesite sesion en una web es
  supervisado.
- **Corta a unos 60 s.** `encargos_tfm` y `registrar_tfm` vuelven al instante
  y el analisis corre fuera del proceso de la app, asi que lo que tiene que
  caber es el trabajo. Un encargo desatendido es **una busqueda y un
  resultado escrito**, no una investigacion.

En ese puente equivalente el ciclo desatendido **no funciono nunca**: 15
pasadas, cero encargos, 8 caidas por el limite de 60 s solo al leer el buzon,
porque leerlo lanzaba una sesion de Claude Code entera. Aqui `encargos_tfm` es
literal y no lanza nada, y por eso merece volver a medirlo. **Hasta que una
tarea programada registre un encargo real, el modo desatendido es una
hipotesis, no una capacidad.**

## El canal de vuelta: avisos, analisis y hook

Al registrar, el puente crea un aviso `A-000N` en `AVISOS_CODE.md` y lanza
`analizar.mjs` **desprendido**: una sesion de Claude Code de solo lectura con
el encargo, la entrada del registro y el estado real de git, que responde en
cuatro secciones fijas (cumple el criterio, que contrastar, a que afecta,
accion propuesta) y las anota bajo el aviso. Si la sesion falla o se corta, el
aviso pasa igualmente a POR ATENDER con el motivo escrito: un aviso que se
quedara en POR ANALIZAR para siempre pareceria "aun en curso".

Estados, y quien los cambia:

| Estado | Lo pone |
|---|---|
| `POR ANALIZAR` | el puente, al registrar |
| `POR ATENDER` | `analizar.mjs`, con el analisis o con su fallo |
| `ATENDIDO <fecha>` | Claude Code, con `avisos.mjs --atendido` |

**El hook** es lo que cierra el ciclo sin que nadie tenga que acordarse.
`.claude/settings.json` ejecuta `node puente/avisos.mjs --hook` en cada
`UserPromptSubmit`; lo que escribe entra en el contexto de la sesion. Si no hay
avisos pendientes no escribe nada. Se corta a 8.000 caracteres avisando, porque
Claude Code corta a 10.000 sin avisar.

```bash
node puente/avisos.mjs --listar
node puente/avisos.mjs --atendido A-0001 --nota "que se hizo con el"
node puente/avisos.mjs --esperar E-0003 --segundos 900   # sale con 0 cuando vuelve
```

`--esperar` es para una sesion viva que acaba de encargar y quiere enterarse
en cuanto vuelva: lanzarlo con `Bash` en segundo plano da **una** notificacion
al terminar. No usar `Monitor` para esto: caduca a los 30 minutos y avisa al
caducar, y en el puente equivalente ese ruido llevo a apagarlo justo cuando
habia un encargo en vuelo.

**Lo que la sesion hija NO puede leer.** `--restricted` confina las herramientas
de fichero al directorio de trabajo, y el directorio de trabajo **es** el
repositorio, donde vive el `.env` con las claves de API. Por eso hay ademas una
lista de denegacion explicita (`DENEGADAS` en `servidor.mjs`) sobre `.env` y
`.git/config`, para `Read` y para `Grep`. Ver `docs/HALLAZGOS.md` §19. Vale
igual para `consultar_tfm` y para el analisis: comparten banderas.

`medir_tfm` sigue sin existir: es el punto 4 del §7 de
`docs/SINCRONIZACION_SUPERFICIES.md`.

## Como declararlo en la app

En la configuracion de servidores MCP del proyecto MASTER IA TFM:

```json
{
  "mcpServers": {
    "claude-code-tfm": {
      "command": "C:\\Program Files\\nodejs\\node.exe",
      "args": [
        "C:\\Users\\<usuario>\\Desktop\\Master\\TFM\\asistente-multitenant\\puente\\servidor.mjs"
      ],
      "env": { "CLAUDE_BIN": "C:\\Users\\<usuario>\\.local\\bin\\claude.exe" }
    }
  }
}
```

**Conviene anadir siempre el binario explicito**, no solo si falla. El proceso
que lanza la app puede heredar un `PATH` distinto al de una terminal, y el
sintoma seria un puente que arranca bien y falla en la primera consulta. Se
aceptan `CLAUDE_BIN` (la convencion de los otros puentes de este equipo) y
`PUENTE_CLAUDE_BIN`. El analisis en segundo plano hereda el mismo binario.

## Como comprobar que funciona

Desde la app, con una pregunta cuya respuesta ya se conozca **y que el conector
no pueda responder**:

> Usa consultar_tfm y dime que ficheros hay sin commitear ahora mismo.

Para el buzon, que vea un encargo que el conector no puede ver:

> Usa encargos_tfm y dime que encargos tengo pendientes.

Y el ciclo entero desde la linea de ordenes, sin la app, hablando JSON-RPC con
el servidor.

## Lo que quedo medido

**21-09-2026**, al montarlo:

| Prueba | Resultado |
|---|---|
| `initialize`, `tools/list` | Correctos |
| Campo obligatorio vacio en `registrar_tfm` | Rechazado con `isError` |
| Herramienta inexistente | Rechazada con JSON-RPC `-32602` |
| Ficheros sin commitear (el conector no puede saberlo) | Correcto, **8,2 s** |
| Peticion de borrar `evals/datasets/` | **Denegada**, citando las reglas, **14,0 s** |
| Arranque desde un directorio ajeno al repo | Correcto: rutas y `git` son independientes del cwd |
| Lectura del `.env` **sin** la lista de denegacion | Lo leia entero: 31 lineas con claves reales |
| Rodeo con `Grep` de `sk-ant` sobre `.env` | **Rechazado**, nombrando la peticion como volcado de credenciales |

**22-09-2026**, el buzon: un `registrar_tfm` con `encargo` inexistente devuelve
`isError` y **no crea el fichero de registro**; con el identificador bueno marca
el encargo y deja el rastro cruzado; una segunda llamada sobre el mismo avisa.

**23-09-2026**, el ciclo completo, simulando a la app por JSON-RPC:

| Prueba | Resultado |
|---|---|
| `encargos_tfm` con `solo_desatendidos` | Devuelve solo E-0002 y dice que hay 1 supervisado fuera |
| `registrar_tfm` citando E-0002 | Marca el encargo, crea A-0001 y arranca el analisis; vuelve al instante |
| Analisis automatico | Anotado en **29 s**; detecto por si mismo que quien registro no era la app |
| `--esperar E-0002` | Sale con 0 al pasar a POR ATENDER |
| Hook en una sesion sin cabeza (`claude -p`) | **Inyectado**: la sesion respondio `HOOK OK: A-0001 [POR ATENDER]` |
| Hook con `$CLAUDE_PROJECT_DIR` en la ruta | **Fallaba**: en este equipo el hook corre bajo PowerShell y la variable se expande a vacio. Ruta relativa al proyecto, que vale en los tres interpretes |
| Hook sin avisos pendientes | No escribe nada, sale con 0 |
| Modo invalido en `encargar.mjs` | Rechazado |

**23-09-2026, primer encargo real desde el enlace (E-0001):** el enlace
`cowork/new` abrio la conversacion con la orden en la caja y la app la
ejecuto al pulsar enviar. Leyo el encargo por `encargos_tfm`, pero
`consultar_tfm` **supero los 60 s que la app tolera** por llamada, y fuera del
proyecto la app **no tiene el conector de GitHub**, asi que no pudo leer
`docs/TUTORIA_2026-09-22.md`; pidio los datos a Juan en vez de inventarlos
(correcto) y no registro. La misma pregunta desde Claude Code tardo **13,9 s**.
Consecuencias aplicadas: el tope del puente baja de 150 a **50 s**, para que
sea el puente quien devuelva el error y no el cliente; y cada sesion de
lectura deja una linea con su duracion en `puente/puente.log`, porque sin eso
la proxima desviacion solo se puede suponer. El encargo se cerro desde Claude
Code con un registro que dice exactamente eso.

Lo que **no** esta medido a 23-09-2026: que una tarea programada registre un
encargo desatendido. Y no es necesario para el ciclo: solo lo seria si se
quisiera que la app trabajase sin Juan, y los encargos que mas valen (campus,
formularios) necesitan a Juan de todos modos.

## Cuando NO usarlo

Para leer ficheros ya pusheados, **el conector de GitHub es mejor**: es mas
rapido y no gasta. `consultar_tfm` y el analisis automatico lanzan una sesion
de Claude Code cada uno, que consume de la suscripcion. Es un medidor distinto
del de las claves de API que usa `evals.runner`, y conviene no mezclarlos al
revisar el gasto.

## Mantenimiento

El puente **decide que puede hacer un agente sobre este repositorio**. No
deberia cambiar sin que una persona lo lea entero. Lo mismo vale para el hook
de `.claude/settings.json`: lo que inyecta lo lee cada sesion.
