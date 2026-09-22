#!/usr/bin/env node
/**
 * Deja un encargo en el buzon que lee la app.
 *
 *   node puente/encargar.mjs \
 *     --titular "..." --pide "..." --para "..." \
 *     --terminado "..." --donde "..."
 *
 *   node puente/encargar.mjs --listar
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
 */
import { anadirEncargo, encargosTfm } from "./servidor.mjs";

const CAMPOS = ["titular", "pide", "para", "terminado", "donde"];

const AYUDA = `Uso:
  node puente/encargar.mjs --titular T --pide P --para Q --terminado C --donde D
  node puente/encargar.mjs --listar

Campos:
  --titular     Una linea que resuma el encargo.
  --pide        Que se pide exactamente.
  --para        Para que sirve, que decision desbloquea.
  --terminado   Criterio que decide si esta hecho. No es una sugerencia.
  --donde       Donde debe quedar el resultado.
`;

function parsear(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) throw new Error(`Argumento inesperado: ${a}`);
    const clave = a.slice(2);
    if (clave === "listar" || clave === "help") {
      args[clave] = true;
      continue;
    }
    if (!CAMPOS.includes(clave)) throw new Error(`Opcion desconocida: --${clave}`);
    const valor = argv[i + 1];
    if (valor === undefined || valor.startsWith("--")) {
      throw new Error(`--${clave} necesita un valor.`);
    }
    args[clave] = valor;
    i += 1;
  }
  return args;
}

try {
  const args = parsear(process.argv.slice(2));

  if (args.help || (!args.listar && Object.keys(args).length === 0)) {
    process.stdout.write(AYUDA);
    process.exit(0);
  }

  if (args.listar) {
    process.stdout.write(`${encargosTfm().texto}\n`);
    process.exit(0);
  }

  const faltan = CAMPOS.filter((c) => !args[c]);
  if (faltan.length) {
    // Todos obligatorios: un encargo sin criterio de terminado o sin sitio
    // donde dejar el resultado se cumple a medias y nadie puede decir que no.
    throw new Error(`Faltan campos obligatorios: ${faltan.join(", ")}`);
  }

  const { id, sello } = anadirEncargo(args);
  process.stdout.write(`Encargo ${id} anotado con fecha ${sello}.\n`);
} catch (e) {
  process.stderr.write(`Error: ${e.message}\n\n${AYUDA}`);
  process.exit(1);
}
