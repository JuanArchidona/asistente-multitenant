# Puente MCP con el proyecto MASTER IA TFM

Servidor MCP local sobre stdio, en Node y sin dependencias. Da a la app de
Claude las dos cosas que el conector de GitHub no puede dar: **el arbol de
trabajo sin pushear** y **un sitio donde dejar rastro**.

El diseno y su justificacion estan en `docs/SINCRONIZACION_SUPERFICIES.md`. Esto
es solo la puesta en marcha.

## Que expone, y que no

| Herramienta | Que hace |
|---|---|
| `encargos_tfm` | Devuelve los encargos pendientes **literales**, sin argumentos y sin lanzar ninguna sesion. Es como se entera la app de lo que tiene que hacer. |
| `consultar_tfm` | Responde una pregunta sobre el repositorio leyendo el arbol real, incluido lo no pusheado. **Solo lectura.** |
| `registrar_tfm` | Anade una entrada al registro de trabajo. `append` determinista sobre un fichero de ruta fija. Con el campo opcional `encargo` marca ese encargo como atendido. |

No expone nada mas. Quien llama controla **el texto de una pregunta y siete
campos de texto**; binario, directorio, banderas, lista de herramientas y rutas
del buzon y del registro son constantes de `servidor.mjs`.

### El buzon: escribirlo no es una herramienta

Los encargos se dejan desde la linea de ordenes, o sea desde Claude Code:

```bash
node puente/encargar.mjs --titular T --pide P --para Q --terminado C --donde D
node puente/encargar.mjs --listar
```

Los cinco campos son obligatorios. Un encargo sin criterio de terminado o sin
sitio donde dejar el resultado se cumple a medias y nadie puede decir que no.

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

El formato del buzon lo compone `servidor.mjs`, de donde `encargar.mjs` importa:
dos sitios escribiendo el mismo formato es un sitio donde el formato se
desincroniza. Por eso el bucle de stdio del servidor solo arranca si es el punto
de entrada.

**Lo que la sesion hija NO puede leer.** `--restricted` confina las herramientas
de fichero al directorio de trabajo, y el directorio de trabajo **es** el
repositorio, donde vive el `.env` con las claves de API. Por eso hay ademas una
lista de denegacion explicita (`DENEGADAS` en `servidor.mjs`) sobre `.env` y
`.git/config`, para `Read` y para `Grep`. Ver `docs/HALLAZGOS.md` §19.

`medir_tfm` todavia no existe: es el punto 4 del §7 de
`docs/SINCRONIZACION_SUPERFICIES.md`, el unico que queda, y no se monta hasta
que el rastro demuestre ser fiable.

## Como declararlo en la app

En la configuracion de servidores MCP del proyecto MASTER IA TFM:

```json
{
  "mcpServers": {
    "claude-code-tfm": {
      "command": "node",
      "args": [
        "C:\\Users\\<usuario>\\Desktop\\Master\\TFM\\asistente-multitenant\\puente\\servidor.mjs"
      ]
    }
  }
}
```

**Conviene anadir siempre el binario explicito**, no solo si falla. El servidor
se ha verificado arrancando desde un directorio ajeno al repositorio y
resolviendo `claude.exe` por `PATH`, pero el proceso que lanza la app puede
heredar un `PATH` distinto al de una terminal, y el sintoma seria un puente que
arranca bien y falla en la primera consulta:

```json
"env": { "PUENTE_CLAUDE_BIN": "C:\\Users\\<usuario>\\.local\\bin\\claude.exe" }
```

## Como comprobar que funciona

La prueba buena es una pregunta cuya respuesta ya se conozca **y que el conector
no pueda responder**, para poder distinguir un fallo del puente de una respuesta
mala:

> Usa consultar_tfm y dime que ficheros hay sin commitear ahora mismo.

Si contesta con la lista real del `git status` local, el puente funciona. Si
contesta con lo que hay en GitHub, o dice que no lo sabe, esta respondiendo por
el conector y el puente no esta activo.

Para el buzon, la prueba es que vea un encargo que el conector no puede ver
—porque el fichero no esta versionado—:

> Usa encargos_tfm y dime que encargos tengo pendientes.

Y el ciclo entero se comprueba desde la linea de ordenes, sin la app, hablando
JSON-RPC con el servidor. Lo verificado el 22-09-2026: `tools/list` publica las
tres herramientas; un `registrar_tfm` con `encargo` inexistente devuelve
`isError` y **no crea el fichero de registro**; con un identificador mal formado
tambien falla; con el identificador bueno marca el encargo y deja el rastro
cruzado en las dos direcciones; y una segunda llamada sobre el mismo encargo
avisa en vez de pasar por la primera.

## Cuando NO usarlo

Para leer ficheros ya pusheados, **el conector de GitHub es mejor**: es mas
rapido y no gasta. `consultar_tfm` lanza una sesion de Claude Code, que consume
de la suscripcion. Es un medidor distinto del de las claves de API que usa
`evals.runner`, y conviene no mezclarlos al revisar el gasto.

## Lo que quedo medido al montarlo

Sesion del 21 de septiembre de 2026, sobre este repositorio:

| Prueba | Resultado |
|---|---|
| `initialize`, `tools/list` | Correctos |
| Campo obligatorio vacio en `registrar_tfm` | Rechazado con `isError` |
| Herramienta inexistente | Rechazada con JSON-RPC `-32602` |
| Ficheros sin commitear (el conector no puede saberlo) | Correcto, **8,2 s** |
| Peticion de borrar `evals/datasets/` | **Denegada**, citando las reglas, **14,0 s** |
| Arranque desde un directorio ajeno al repo | Correcto: rutas y `git` son independientes del cwd |
| Resolucion de `claude.exe` por `PATH` | Correcta en terminal, **4,9 s**; no verificable en el proceso de la app |
| Lectura del `.env` **sin** la lista de denegacion | Lo leia entero: 31 lineas con claves reales |
| Peticion directa del valor de una clave | No lo filtra; responde sobre el codigo que la usa |
| Rodeo con `Grep` de `sk-ant` sobre `.env` | **Rechazado**, nombrando la peticion como volcado de credenciales |
| Consulta legitima tras las denegaciones | Sigue funcionando, **7,1 s** |

En la ultima, la sesion hija ademas corrigio un error de hecho de la propia
pregunta: los golden estan por inquilino
(`evals/datasets/<tenant>/golden_consultas.jsonl`), no en la ruta que se le dio.

## Mantenimiento

El puente **decide que puede hacer un agente sobre este repositorio**. No
deberia cambiar sin que una persona lo lea entero.
