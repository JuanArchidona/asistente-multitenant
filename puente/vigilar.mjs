#!/usr/bin/env node
/**
 * Vigilante del puente: despierta a Claude Code cuando la app registra algo,
 * sin esperar al siguiente prompt de Juan.
 *
 *   node puente/vigilar.mjs                 # sondea cada 20 s, no termina nunca
 *   node puente/vigilar.mjs --intervalo 10  # otro periodo, en segundos
 *
 * Lo ejecuta la herramienta Monitor de Claude Code, que la skill `/arranque`
 * arma al empezar la sesion: cada linea que este proceso escribe en stdout
 * llega a la sesion como un evento. Aqui solo se escribe una linea por aviso
 * nuevo (POR ATENDER o POR ANALIZAR), asi que el resto del tiempo el proceso
 * calla. El hook `avisos.mjs --hook` sigue existiendo y cubre el caso en que
 * la sesion no tenga vigilante (o este haya caducado): los dos caminos llevan
 * al mismo sitio, atender el aviso y marcarlo con `avisos.mjs --atendido`.
 *
 * Estado: `puente/.vigilados`, la lista de identificadores ya anunciados. No se
 * versiona y sobrevive a cada rearme. Al arrancar se anuncia en el acto todo
 * aviso pendiente que no este en esa lista. Antes se daban por vistos sin
 * anunciar, confiando en el hook, y el 10-10-2026 A-0017 cayo en el hueco:
 * llego mientras el monitor caducaba, el rearme lo marco como visto y solo lo
 * trajo el hook, que depende de que haya un prompt. Un aviso repetido es
 * ruido; uno perdido es el fallback silencioso que el proyecto prohibe.
 *
 * Regla que este fichero no puede romper: un aviso NO genera un encargo nuevo
 * a la app por si solo. Este proceso solo lee y anuncia.
 */
import { execFileSync } from "node:child_process";
import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const AVISOS = join(AQUI, "avisos.mjs");
const VISTOS = join(AQUI, ".vigilados");
const PENDIENTE = /\b(POR ATENDER|POR ANALIZAR)\b/;

function leerVistos() {
  if (!existsSync(VISTOS)) return new Set();
  return new Set(readFileSync(VISTOS, "utf8").split(/\r?\n/).filter(Boolean));
}

function pendientes() {
  let salida = "";
  try {
    salida = execFileSync(process.execPath, [AVISOS, "--listar"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    // Un fallo puntual al listar no para el vigilante; el siguiente sondeo lo intenta otra vez.
    return [];
  }
  return salida
    .split(/\r?\n/)
    .filter((l) => PENDIENTE.test(l))
    .map((l) => ({ id: l.trim().split(/\s+/)[0], linea: l.trim() }))
    .filter((a) => /^A-\d{4}$/.test(a.id));
}

function parsear(argv) {
  let intervalo = 20;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--intervalo") {
      intervalo = Number(argv[i + 1]);
      i += 1;
    } else if (argv[i] === "--help") {
      process.stdout.write("Uso: node puente/vigilar.mjs [--intervalo SEGUNDOS]\n");
      process.exit(0);
    } else {
      throw new Error(`Argumento inesperado: ${argv[i]}`);
    }
  }
  if (!Number.isFinite(intervalo) || intervalo < 5) throw new Error("--intervalo: minimo 5 segundos");
  return { intervalo };
}

const { intervalo } = parsear(process.argv.slice(2));
const vistos = leerVistos();

function sondear() {
  for (const a of pendientes()) {
    if (vistos.has(a.id)) continue;
    vistos.add(a.id);
    appendFileSync(VISTOS, `${a.id}\n`);
    process.stdout.write(`NUEVO AVISO DEL PUENTE: ${a.linea}\n`);
  }
}

// El primer sondeo va al arrancar: cubre lo que llego entre la caducidad del
// monitor anterior y este rearme.
sondear();
setInterval(sondear, intervalo * 1000);
