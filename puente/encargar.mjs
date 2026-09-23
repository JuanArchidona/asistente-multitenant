#!/usr/bin/env node
/**
 * Deja un encargo en el buzon que lee la app.
 *
 *   node puente/encargar.mjs \
 *     --titular "..." --pide "..." --para "..." \
 *     --terminado "..." --donde "..." [--modo desatendido|supervisado] [--abrir]
 *
 *   node puente/encargar.mjs --listar
 *   node puente/encargar.mjs --enlace E-0003
 *
 * Por que un CLI y no una herramienta MCP: **el sentido del buzon es que la app
 * no se de encargos a si misma.** Quien los escribe es Claude Code, que tiene
 * sistema de ficheros y no necesita el protocolo; la app solo los lee por
 * `encargos_tfm`. Si escribir fuera una herramienta MCP, un modelo al que se le
 * cuele una instruccion en un documento podria fabricarse la orden de trabajo
 * que luego dice haber cumplido.
 *
 * El formato y la fecha los compone `servidor.mjs`, de donde este fichero
 * importa: dos sitios escribiendo el mismo formato es un sitio donde el formato
 * se desincroniza.
 *
 * ## El modo, y por que lo decide quien encarga
 *
 * `desatendido`: se puede hacer sin navegador, sin sesion en ningun sitio y sin
 * nadie delante (buscar en la web, leer el repositorio por el conector o el
 * puente, redactar, comparar). Una tarea programada de la app lo atiende sola.
 *
 * `supervisado`: necesita el navegador con sesion (campus, formularios) o una
 * decision de Juan. Lo atiende un chat con Juan delante, y para eso esta
 * `--abrir`: abre la app en el proyecto con el encargo ya escrito en la caja.
 * **La app no auto-envia** —esta documentado y es deliberado—, asi que queda
 * una pulsacion humana. No es friccion: es el punto donde alguien mira.
 *
 * ## El enlace profundo
 *
 * `claude://claude.ai/project/<uuid>?q=<texto>` abre el proyecto con el texto
 * en la caja. El uuid del proyecto vive en `puente/proyecto.local.json`, que
 * no se versiona: no es secreto, pero es de Juan y el repositorio es publico.
 */
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { anadirEncargo, encargosTfm, leerBuzon, parsearEncargos } from "./servidor.mjs";

const AQUI = dirname(fileURLToPath(import.meta.url));
const PROYECTO = join(AQUI, "proyecto.local.json");

const CAMPOS = ["titular", "pide", "para", "terminado", "donde", "modo"];
const OBLIGATORIOS = ["titular", "pide", "para", "terminado", "donde"];

const AYUDA = `Uso:
  node puente/encargar.mjs --titular T --pide P --para Q --terminado C --donde D [--modo M] [--abrir]
  node puente/encargar.mjs --listar
  node puente/encargar.mjs --enlace E-0003

Campos:
  --titular     Una linea que resuma el encargo.
  --pide        Que se pide exactamente.
  --para        Para que sirve, que decision desbloquea.
  --terminado   Criterio que decide si esta hecho. No es una sugerencia.
  --donde       Donde debe quedar el resultado.
  --modo        'desatendido' (sin navegador ni nadie delante: lo puede hacer
                una tarea programada) o 'supervisado' (necesita a Juan en el
                chat). Por defecto, supervisado.
  --abrir       Abre la app de Claude en el proyecto con el encargo escrito en
                la caja. Falta pulsar enviar: la app no auto-envia.
  --enlace ID   Imprime el enlace profundo de un encargo ya existente.
`;

function parsear(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) throw new Error(`Argumento inesperado: ${a}`);
    const clave = a.slice(2);
    if (["listar", "help", "abrir"].includes(clave)) {
      args[clave] = true;
      continue;
    }
    if (!CAMPOS.includes(clave) && clave !== "enlace") {
      throw new Error(`Opcion desconocida: --${clave}`);
    }
    const valor = argv[i + 1];
    if (valor === undefined || valor.startsWith("--")) {
      throw new Error(`--${clave} necesita un valor.`);
    }
    args[clave] = valor;
    i += 1;
  }
  return args;
}

function proyecto() {
  if (!existsSync(PROYECTO)) {
    throw new Error(
      `Falta ${PROYECTO} con {"uuid": "..."} del proyecto de la app. ` +
        "Se lee de la URL del proyecto (claude.ai/cowork/project/<uuid>)."
    );
  }
  const datos = JSON.parse(readFileSync(PROYECTO, "utf8"));
  if (!/^[0-9a-f-]{36}$/.test(datos.uuid ?? "")) {
    throw new Error(`El uuid de ${PROYECTO} no tiene forma de uuid.`);
  }
  return datos;
}

/**
 * El texto que aparece en la caja. Corto y literal: la app lee el encargo
 * entero por `encargos_tfm`, asi que aqui solo hace falta la orden de ir a por
 * el. Si el texto del encargo viajara en el enlace, habria dos copias.
 */
function textoParaLaCaja(id) {
  return (
    `Usa encargos_tfm y atiende el encargo ${id} tal cual esta escrito. ` +
    `Cuando termines, o si no puedes terminarlo, registra el resultado con ` +
    `registrar_tfm citando "${id}" en el campo encargo.`
  );
}

function enlace(id) {
  const { uuid } = proyecto();
  return `claude://claude.ai/project/${uuid}?q=${encodeURIComponent(textoParaLaCaja(id))}`;
}

/** Abre el enlace con el manejador del sistema, sin shell y sin escapar nada. */
function abrir(url) {
  const orden =
    process.platform === "win32"
      ? ["rundll32", ["url.dll,FileProtocolHandler", url]]
      : process.platform === "darwin"
        ? ["open", [url]]
        : ["xdg-open", [url]];
  const hijo = spawn(orden[0], orden[1], { detached: true, stdio: "ignore", shell: false });
  hijo.unref();
}

try {
  const args = parsear(process.argv.slice(2));

  if (args.help || Object.keys(args).length === 0) {
    process.stdout.write(AYUDA);
    process.exit(0);
  }

  if (args.listar) {
    process.stdout.write(`${encargosTfm().texto}\n`);
    process.exit(0);
  }

  if (args.enlace) {
    const existe = parsearEncargos(leerBuzon()).some((e) => e.id === args.enlace);
    if (!existe) throw new Error(`El encargo ${args.enlace} no esta en el buzon.`);
    const url = enlace(args.enlace);
    if (args.abrir) abrir(url);
    process.stdout.write(`${args.abrir ? "Abierta la app con el encargo en la caja. Falta pulsar enviar.\n" : ""}${url}\n`);
    process.exit(0);
  }

  const faltan = OBLIGATORIOS.filter((c) => !args[c]);
  if (faltan.length) {
    // Todos obligatorios: un encargo sin criterio de terminado o sin sitio
    // donde dejar el resultado se cumple a medias y nadie puede decir que no.
    throw new Error(`Faltan campos obligatorios: ${faltan.join(", ")}`);
  }

  const { id, sello, modo } = anadirEncargo(args);
  process.stdout.write(`Encargo ${id} (${modo}) anotado con fecha ${sello}.\n`);

  if (modo === "desatendido") {
    process.stdout.write(
      "Lo atendera la tarea programada del proyecto en su siguiente pasada, o un chat que llame a encargos_tfm.\n"
    );
  }
  if (args.abrir) {
    const url = enlace(id);
    abrir(url);
    process.stdout.write(
      `Abierta la app en el proyecto con el encargo en la caja. Falta pulsar enviar.\n` +
        `Si la app no se abre o la caja llega vacia, el enlace es:\n${url}\n`
    );
  } else if (modo === "supervisado") {
    process.stdout.write(
      `Necesita a Juan en el chat. Para abrirle la app con el encargo en la caja: node puente/encargar.mjs --enlace ${id}\n`
    );
  }
} catch (e) {
  process.stderr.write(`Error: ${e.message}\n\n${AYUDA}`);
  process.exit(1);
}
