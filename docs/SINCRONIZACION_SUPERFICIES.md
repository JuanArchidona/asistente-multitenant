# Sincronizacion entre las dos superficies de trabajo

> Desarrollo del diseño que `CLAUDE.md` §9 resume. §9 describe **lo que hay hoy**;
> este documento describe **lo que falta, por que, y que cuesta**. Si los dos se
> contradicen, gana `CLAUDE.md`.
>
> Escrito el 21 de septiembre de 2026 como propuesta. **Revisado ese mismo dia
> contra el codigo**, que desmintio tres afirmaciones suyas: estan corregidas
> abajo y marcadas como CORRECCION, porque un documento que describe mal una
> puerta de gasto es peor que no tenerlo.
>
> Estado de montaje a 23-09-2026: los puntos 1, 2, 3, 5 y 6 del §7 estan
> **hechos** (`puente/`). Queda el 4 (`medir_tfm`). El 6 es el cierre del
> ciclo: la app avisa a Claude Code y Claude Code se entera solo.

## 1. El punto de partida, y por que importa

El proyecto se trabaja desde dos sitios: **Claude Code**, donde ocurre todo el
desarrollo, y el proyecto **MASTER IA TFM** en la app de Claude, que hace lo que
Claude Code no puede hacer (tareas de navegador, discusion de diseño, redaccion).

La app lee el estado por el **conector de GitHub** al repositorio, que es
**publico**. Eso resuelve mas de lo que parece, y conviene decirlo antes de
proponer nada:

- La app llega al codigo, al corpus, a los manifiestos de inquilino y a la
  documentacion **sin ninguna pieza intermedia**.
- Y llega tambien a **toda la evidencia medida**: `.gitignore` versiona
  `reports/` a proposito, asi que cada `informe.md` de cada ejecucion esta a su
  alcance.

La consecuencia de diseño es que **no hace falta construir un canal de lectura**.
Un canal de lectura propio seria mas lento, mas fragil y mas caro de mantener que
el conector, y no añadiria nada. Lo que hay que construir es solo lo que el
conector no puede dar.

## 2. Los tres huecos reales

| Hueco | Por que el conector no lo cubre | Cuanto duele |
|---|---|---|
| **El arbol de trabajo sin pushear** | GitHub sirve el ultimo push. Entre dos `/cierre` la app opina sobre un mapa viejo | Medio. Se mitiga pusheando mas a menudo |
| **Ejecutar** | La app no puede correr `uv run pytest` ni `evals.runner` | **Alto.** El criterio de evaluacion del master es que una afirmacion sin numero no vale. El hueco cae justo sobre la capacidad de producir numeros |
| **Que la app deje rastro** | El flujo es de una sola direccion: lo que hace la app se queda en su conversacion | **Alto si se automatiza.** Trabajo desatendido sin registro no es revisable, y lo no revisable no es defendible |

## 3. Diseño propuesto

### 3.1 Puente MCP local

Un servidor MCP sobre stdio, en Node y sin dependencias, declarado en la
configuracion de la app. Expone **tres herramientas y ninguna mas**:

- **`consultar_tfm`**: resuelve una pregunta lanzando una sesion de Claude Code
  en modo no interactivo sobre este repositorio, de solo lectura. Su valor aqui
  es **menor** que el del conector: sirve para lo no pusheado y para preguntas
  que necesitan el estado real de git.

  **CORRECCION al montarlo.** La propuesta original daba a la sesion hija una
  lista blanca de Bash para que consultase git. Se descarto: las listas blancas
  de Bash casan **por prefijo**, y un agente con una instruccion inyectada en un
  documento puede componer ordenes que pasen el filtro. En su lugar, **el puente
  ejecuta `git` el mismo, con argumentos fijos y sin shell, e inyecta el
  resultado a la sesion hija como dato**. Asi la hija no necesita ejecutar nada
  y corre con `--restricted`, que quita Bash, PowerShell y WebFetch, ignora los
  ficheros de settings y confina las herramientas de fichero al directorio de
  trabajo; `--tools` nombra solo `Read`, `Grep` y `Glob`, asi que no hay `Edit`
  ni `Write`. Es el mismo principio de superficie minima un paso mas alla.
- **`medir_tfm`**: lanza el banco de evaluacion. Ver §3.2, que es donde esta la
  decision no trivial.
- **`registrar_tfm`**: añade una entrada al registro de encargos. **No es
  escritura general**: es un `append` determinista, en Node, sobre **un fichero
  de ruta fija**, con el formato compuesto por el propio puente y los campos
  obligatorios. No puede crear, borrar, mover ni reformatear nada.

**El principio que sostiene las tres**: a un agente no se le da una puerta
grande, se le da la superficie minima del problema concreto. `registrar_tfm` no
es "escribir", es "añadir una entrada a este fichero". `medir_tfm` no es
"ejecutar Python", es "ejecutar este script", con interprete y ruta como
constantes del puente. Si la ruta fuese un parametro, seria una puerta para
ejecutar cualquier cosa del disco.

**Marco de reglas.** Cada consulta se antepone con un texto que quien llama no
puede sobreescribir. Debe recoger las reglas del §5 de `CLAUDE.md`, porque son
precisamente las que un agente rompe sin darse cuenta:

- No se relaja el banco: `evals/datasets/` no se toca, y una expectativa solo se
  corrige con su justificacion escrita en `docs/HALLAZGOS.md`.
- La linea base heredada no se toca: hay un test que compara el prompt del
  enrutador caracter a caracter con el de la 3.3.
- Nada de fallbacks silenciosos: si algo degrada, se marca y se propaga.
- Ninguna cifra sin su ejecucion. Si no esta en un `reports/<etiqueta>/`, no es
  un dato.
- Sin emoticonos y sin atribucion.

### 3.2 La medicion tiene que ser asincrona, y con puerta de coste

Dos restricciones obligan a apartarse del patron obvio.

**Restriccion de tiempo. CORRECCION: la premisa original era falsa, la
conclusion aguanta.** Este documento decia que el banco "no cabe". Contrastado
contra los `resumen.json` de `reports/`, no es cierto:

| Ejecucion | Casos | Duracion |
|---|---|---|
| `agencia_*` sin juez | 38 | 33-39 s |
| `empresa_*` sin juez | 53 | 42-45 s |
| `sintetico` sin juez | 57 | **56,0 s** |
| `baseline` / `endurecido` **con juez** | 52 | **370-453 s** |

Sin juez el banco tarda **menos de un minuto** y cabe de sobra en los 4 minutos
del chat. Lo que no cabe es la pasada con juez.

Aun asi se mantiene **lanzar y soltar**, por una razon distinta y mejor: contra
el limite de 60 s de una tarea programada, `sintetico` a 56,0 s deja **cuatro
segundos de margen**. Una herramienta sincrona que funciona casi siempre y a
veces corta es peor que una que nunca bloquea, porque el corte se lee como un
fallo del sistema evaluado y no como lo que es.

El patron correcto es **lanzar y soltar**:

1. `medir_tfm` arranca `evals.runner` en segundo plano con una `--etiqueta` que
   compone el puente.
2. Devuelve **de inmediato** la etiqueta y la ruta donde aparecera el informe.
3. El resultado se lee despues en `reports/<etiqueta>/informe.md`, por el puente
   o por el conector una vez pusheado.

**Restriccion de coste.** `CLAUDE.md` §8 registra como riesgo abierto que **no
hay tope de gasto en la cuenta del proveedor**. Una herramienta que deja lanzar
el banco es una herramienta que deja gastar sin supervision, y en una tarea
programada no hay supervision por definicion. Por eso el puente expone modos, no
parametros libres:

| Modo | Coste | Disponible |
|---|---|---|
| `--desde-trazas --sin-juez` | **Ninguno**: reevalua trazas guardadas sin llamar a nadie | Por defecto |
| `--sin-juez` a secas | Sin coste de juez, pero **el sistema bajo prueba si llama al proveedor** | Solo con autorizacion expresa |
| Cualquier modo **sin** `--sin-juez` | El mas alto: lanza el juez, que es el modelo caro | **Fuera del puente.** Se lanza a mano |

**CORRECCION, y es la importante de todo el documento.** La version original de
esta tabla daba `--desde-trazas` por gratis y lo ponia por defecto. No lo es. En
`evals/runner.py` el juez se crea salvo que se pase `--sin-juez`, con
independencia de `--desde-trazas`:

```python
juez = None
if not args.sin_juez:
    juez = Juez(api_key=clave, modelo=cfg.judge_model, ...)
```

Asi que `--desde-trazas` a secas lanza el juez en cada llamada. Y agrava: el juez
corre sobre el modelo caro y **`evals/metrics/juez.py` no contabiliza tokens**,
asi que ese gasto no lo registra nada. El modo por defecto del puente tiene que
llevar **las dos banderas**.

Corolario incomodo: la puerta queda **invertida respecto a lo medible**. El modo
que se restringe (`--sin-juez`) es el unico cuyo coste si se instrumenta; el que
se pone por defecto es el que no. Instrumentar el juez deberia ir antes que
ampliar el puente.

Que `--sin-juez` se describa como gratis en la ayuda del runner se refiere **al
juez**, no a la ejecucion. Confundirlo es la forma barata de gastar sin querer, y
este documento ya cayo una vez.

**El inquilino tambien es una puerta.** `evals.runner` toma el inquilino de
`TENANT_ID` del entorno, con `empresa_servicios` por defecto. Si `medir_tfm`
compone la etiqueta pero no el inquilino, una medicion desatendida corre en
silencio **contra el inquilino equivocado** y produce un informe que parece
valido. Es un fallback silencioso de manual. El inquilino tiene que ser
parametro explicito del puente, con lista blanca de valores.

### 3.3 Buzon y registro

Dos ficheros de texto, que es la forma mas simple que funciona:

- **Buzon de encargos**: Claude Code escribe lo que la app debe hacer. Un encargo
  dice que se pide, para que, que se considera terminado y donde debe quedar.
- **Registro**: la app anota que hizo realmente. Seis campos obligatorios
  (titular, quien, que se pidio, que se hizo, donde quedo, que queda abierto), y
  **se registra tambien lo que fallo**: un registro que solo recoge exitos no
  sirve para revisar nada.

La fecha la pone **el puente con el reloj del equipo**, no quien llama. Una hora
plausible puesta por un modelo puede desfasarse horas y contaminar cualquier
cruce posterior.

## 4. Decision pendiente antes de montar nada

**El repositorio es publico**, y eso cambia donde pueden vivir el buzon y el
registro. Un registro versionado publicaria el detalle de que partes del trabajo
se delegaron a una herramienta, en el repositorio que acompaña a la defensa. Dos
salidas:

| Opcion | A favor | En contra |
|---|---|---|
| **Gitignorar** `ENCARGOS_*.md` y `REGISTRO_*.md` | Quedan como utillaje privado donde el resto de piezas ya saben mirar | No se recuperan si se borran, y **la app no los ve por el conector** |
| **Sacarlos a una carpeta hermana** | Separacion conceptual limpia | Una tarea programada **no alcanza la carpeta asociada al proyecto, pero si el puente**: el registro tendria que ir obligatoriamente por `registrar_tfm` |

**CORRECCION.** La version original decia que gitignorados quedan "alcanzables
por todo". No: quedan alcanzables por lo que tenga sistema de ficheros —Claude
Code y el puente— pero **no por el conector de GitHub**, que es como lee la app.
Toda lectura del registro desde la app pasa obligatoriamente por el puente.

**RESUELTO el 21-sep-2026: se gitignoran.** El argumento que decide no es la
reversibilidad en abstracto, sino que **no se conoce todavia la rubrica ni la
normativa academica del TFM** (riesgo abierto del §8 del `CLAUDE.md`). Publicar
en un repositorio publico es irreversible de hecho —historial, forks, caches— y
gitignorar se deshace en un commit. Con las reglas sin conocer, gana la opcion
reversible; si la rubrica resulta pedir lo contrario, se versionan entonces.

## 5. Reparto, y lo que la app no toca

| | Claude Code | App |
|---|---|---|
| Codigo, corpus, bancos, mediciones, documentacion | Si | No |
| Lectura del estado pusheado | Si | Si, por el conector |
| Tareas de navegador (campus, normativa, formularios) | No | Si |
| Redaccion larga y discusion de diseño | Posible | Mejor aqui |
| Lanzar mediciones | Si | Solo por `medir_tfm`, con las puertas de §3.2 |

**Fuera del alcance de la app, en cualquier modo**: `evals/datasets/`, el prompt
del enrutador y las cifras de estado de `CLAUDE.md` §2. Son el suelo sobre el que
se mide todo lo demas; si se mueven sin control, ninguna comparacion entre
ejecuciones vuelve a ser valida.

**Primer encargo natural.** Los dos riesgos abiertos de `CLAUDE.md` §8 que siguen
sin cerrar son tareas de navegador: conseguir **el enunciado oficial y la rubrica
del TFM**, y **verificar en la normativa academica si reutilizar entregas propias
calificadas esta permitido**. Ninguno lo puede resolver Claude Code, los dos
condicionan decisiones de alcance, y el segundo afecta a la mitad heredada del
repositorio. La defensa es en octubre de 2026.

## 6. Limites ya medidos

Medidos el 21-sep-2026 sobre un montaje equivalente. Se recogen para no volver a
pagarlos:

- La app corta a unos **4 minutos desde el chat** y a **60 segundos desde una
  tarea programada**.
- Una tarea programada **no alcanza la carpeta asociada al proyecto**, pero **si
  alcanza el puente**. Cualquier rastro de trabajo desatendido tiene que pasar
  por el puente.
- El navegador integrado funciona desatendido **solo si ya tiene sesion abierta**.
- En los enlaces profundos `claude://`, el parametro de consulta **solo funciona
  abriendo conversacion nueva**, y **no convive** con el parametro de carpeta.
- Conviene invocar el ejecutable directamente y pasar el texto por **entrada
  estandar**: en Windows los argumentos se concatenan sin escapar y la linea de
  comandos tiene tope de longitud.

## 7. Orden de montaje

1. ~~**Resolver §4**~~ **HECHO** el 21-sep-2026: se gitignoran. Ver §4.
2. ~~**Puente con `consultar_tfm` y `registrar_tfm`**~~ **HECHO** el 21-sep-2026:
   `puente/servidor.mjs`, con su puesta en marcha y sus pruebas en
   `puente/README.md`. Verificado con una pregunta cuya respuesta se conocia y
   que el conector no puede responder —que ficheros hay sin commitear— y con una
   peticion de borrar `evals/datasets/`, que denego citando las reglas.
3. ~~**Buzon, con el encargo de la rubrica y la normativa**~~ **HECHO** el
   22-sep-2026. `puente/ENCARGOS_APP.md`, que escribe Claude Code con
   `node puente/encargar.mjs` y lee la app con `encargos_tfm`. Tres decisiones
   que no estaban en el diseno original:
   - **Los encargos se devuelven literales, sin sesion hija.** `consultar_tfm`
     habria servido, pero un encargo es una orden de trabajo y parafrasear una
     orden de trabajo la degrada; ademas cuesta una sesion de Claude por
     consulta. `encargos_tfm` no gasta nada.
   - **Escribir en el buzon no es una herramienta MCP.** Solo se puede desde la
     linea de ordenes, o sea desde Claude Code. Si escribir fuera una
     herramienta, un modelo al que se le cuele una instruccion en un documento
     podria fabricarse la orden de trabajo que luego dice haber cumplido.
   - **El encargo lo marca atendido el puente, no quien dice haberlo hecho**, y
     solo cuando `registrar_tfm` lo cita por su identificador. Un identificador
     que no existe **falla y no registra nada**: aceptarlo dejaria una entrada
     que dice atender algo que nadie pidio, y el encargo real seguiria
     pendiente sin que nada lo senalase. Y citar uno ya atendido se anota como
     segunda entrada sobre el mismo, en vez de pasar por la primera.

   El primer caso real es **E-0001, la tutoria del 22-09-2026 a las 16:00**.
4. **`medir_tfm` asincrona, solo `--desde-trazas --sin-juez`** (las dos
   banderas, ver §3.2) y con el inquilino como parametro explicito. Ampliar a
   `--sin-juez` a secas cuando el rastro demuestre ser fiable **y el coste del
   juez este instrumentado**.
5. ~~**Actualizar `CLAUDE.md` §9**~~ **HECHO** el 22-sep-2026, al cerrar el
   punto 3. La afirmacion se ha partido en vez de borrarse: **sobre el estado
   del proyecto** el flujo sigue siendo de una sola direccion, y eso es lo que
   sostiene que el repositorio sea la fuente de verdad; lo que tiene vuelta es
   **el trabajo por hacer y el rastro de lo hecho**, que no son estado. Si la
   distincion se perdiera, el registro de la app acabaria compitiendo con
   `CLAUDE.md` por decir como esta el proyecto.

6. **Cerrar el ciclo: que Claude Code se entere solo.** **HECHO** el
   23-sep-2026. Hasta entonces el canal de vuelta terminaba en un fichero que
   alguien tenia que acordarse de leer, y el primer caso real lo demostro: la
   tutoria (E-0001) se registro desde Claude Code sin pasar por la app, y el
   buzon se quedo diciendo PENDIENTE. Cuatro piezas, todas en `puente/`:
   - **Modo del encargo**, `desatendido` o `supervisado`, que decide quien
     encarga. `encargos_tfm` admite `solo_desatendidos` para que una tarea
     programada no intente lo que no puede hacer, y dice cuantos deja fuera.
   - **Enlace profundo** `claude://cowork/new?q=...` desde
     `encargar.mjs --abrir`: abre la app con la orden en la caja. **No
     auto-envia**, y esta documentado como decision deliberada: la ida
     totalmente desatendida solo existe por la tarea programada. Y **no abre
     el proyecto**: la ruta del proyecto ignora `q` (medido el 21-09 en el
     puente equivalente y otra vez aqui el 23-09, con la caja vacia en
     pantalla), asi que la conversacion se abre fuera y el texto lleva un
     preambulo que suple las instrucciones del proyecto. Al registrar, el
     puente lanza ademas una notificacion de escritorio para Juan.
   - **Aviso y analisis al registrar.** `registrar_tfm` crea un aviso en
     `AVISOS_CODE.md` y lanza `analizar.mjs` desprendido: una sesion de solo
     lectura (las mismas banderas que `consultar_tfm`) que anota en 10-30 s si
     el resultado cumple el criterio, que hay que contrastar, a que afecta y
     que accion propone. El puente es un proceso vivo justo cuando llega el
     resultado, asi que el evento es el disparador: ni demonio, ni detector
     que caduque, ni tarea de Windows.
   - **Hook de Claude Code** (`.claude/settings.json`, `UserPromptSubmit`):
     `avisos.mjs --hook` inyecta los avisos sin atender en cada prompt, y no
     escribe nada si no hay. Es la regla que no hay que acordarse de aplicar.

   **La cadena termina en Claude Code**, y es la regla que no se negocia. Un
   puente equivalente de este equipo la formulo el 21-09 tras tres errores en
   una manana que solo se cazaron porque habia dos miradas distintas: si los
   dos lados reaccionan automaticamente el uno al otro, la segunda mirada se
   convierte en un eco. Aqui esta impuesta por estructura (la sesion de
   analisis no puede escribir) y por texto (la inyeccion dice que volver a
   encargar pasa por Juan).

   **Lo que ese puente equivalente midio y este hereda sin volver a pagar**:
   una tarea programada alcanza el puente MCP local pero no el navegador ni
   la carpeta; corta a unos 60 s; y su ciclo desatendido no funciono nunca
   (15 pasadas, 0 encargos, 8 caidas por leer el buzon con una sesion de
   Claude Code entera). Aqui `encargos_tfm` es literal y el analisis corre
   fuera del proceso de la app, asi que la hipotesis merece medirse otra
   vez; hasta que una tarea programada registre un encargo real, el modo
   desatendido es hipotesis y no capacidad.

Los puntos 2, 3, 4 y 6 son independientes entre si una vez resuelto el 1, y cada
uno aporta valor por separado. Si el proyecto se queda sin tiempo, el orden de
sacrificio es el inverso: **el 4 es el que mas aporta y el que mas riesgo trae**.

Al 23-sep-2026 queda pendiente **solo el punto 4**, y dos mediciones del 6 que
solo se pueden hacer con la app: un encargo ejecutado desde el enlace profundo
y un encargo desatendido registrado por la tarea programada.

## 8. Mantenimiento

- **Sin `/cierre` no hay sincronizacion.** El conector lee lo pusheado; lo que no
  se pushea no existe para la app.
- **Al cambiar de repositorio hay que repuntar la conexion de GitHub** del
  proyecto de la app. No avisa: sigue leyendo un repositorio muerto.
- El puente **decide que puede hacer un agente sobre este repositorio**. No
  deberia cambiar sin que una persona lo lea entero.
