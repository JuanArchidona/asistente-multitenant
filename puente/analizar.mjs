#!/usr/bin/env node
/**
 * Analisis automatico de un resultado de la app.
 *
 *   node puente/analizar.mjs A-0001
 *
 * Lo lanza `registrar_tfm` en segundo plano, desprendido del servidor, en
 * cuanto la app registra trabajo. Lanza una sesion de Claude Code de SOLO
 * LECTURA (las mismas banderas que `consultar_tfm`) con el encargo, la entrada
 * del registro y el estado real de git, y anota lo que responde bajo el aviso
 * correspondiente en `puente/AVISOS_CODE.md`, que es lo que el hook inyecta en
 * la siguiente sesion interactiva.
 *
 * Por que aqui y no en un demonio: el puente es un proceso que ya esta vivo en
 * el momento exacto en que llega el resultado. No hace falta vigilar nada ni
 * programar nada; el evento es el disparador.
 *
 * Por que solo lectura: lo que analiza es texto que ha producido otro agente
 * a partir de paginas web o documentos, y ese texto puede traer instrucciones.
 * Una sesion que pudiera escribir sobre el repositorio a partir de eso seria
 * la puerta grande que docs/SINCRONIZACION_SUPERFICIES.md §3.1 dice que no se
 * abre. Quien actua es la sesion interactiva, con Juan delante.
 *
 * Nada de fallbacks silenciosos: si la sesion falla o se corta, el aviso pasa
 * igualmente a POR ATENDER con el motivo escrito. Un aviso que se quedara en
 * POR ANALIZAR para siempre pareceria "aun en curso".
 */
import {
  AVISOS,
  MARCO_ANALISIS,
  REGISTRO,
  actualizarAviso,
  ahora,
  estadoGit,
  leerAvisos,
  leerBuzon,
  parsearAvisos,
  parsearEncargos,
  sesionLectura,
} from "./servidor.mjs";
import { existsSync, readFileSync } from "node:fs";

const id = process.argv[2];
if (!/^A-\d{4}$/.test(id ?? "")) {
  process.stderr.write("Uso: node puente/analizar.mjs A-0001\n");
  process.exit(2);
}

const aviso = parsearAvisos(leerAvisos()).find((a) => a.id === id);
if (!aviso) {
  process.stderr.write(`El aviso ${id} no existe en ${AVISOS}.\n`);
  process.exit(1);
}

/** La entrada del registro que origino el aviso, buscada por su sello. */
function entradaRegistro(sello) {
  if (!existsSync(REGISTRO)) return "<el registro no existe>";
  const contenido = readFileSync(REGISTRO, "utf8");
  const inicio = contenido.indexOf(`## ${sello} — `);
  if (inicio === -1) return `<no se encontro la entrada con sello ${sello}>`;
  const siguiente = contenido.indexOf("\n## ", inicio + 1);
  return contenido.slice(inicio, siguiente === -1 ? undefined : siguiente).trimEnd();
}

const encargo = aviso.encargo
  ? parsearEncargos(leerBuzon()).find((e) => e.id === aviso.encargo)
  : null;

const prompt = [
  MARCO_ANALISIS,
  "",
  estadoGit(),
  "",
  "=== ENCARGO (datos) ===",
  encargo ? encargo.texto : "<sin encargo previo: la app registro trabajo por su cuenta>",
  "",
  "=== REGISTRO (datos) ===",
  entradaRegistro(aviso.selloRegistro),
].join("\n");

// El analisis no lo espera la app, asi que no le aplica su corte de 60 s. El
// primero real (A-0002) tardo 42,8 s: con el tope de 50 s de consultar_tfm se
// habria cortado a la siguiente pregunta un poco mas larga.
const r = await sesionLectura(prompt, 150_000);
const sello = ahora();
const bloque = r.ok
  ? `### Analisis automatico (${sello})\n\n${r.texto}`
  : `### Analisis automatico (${sello}): NO DISPONIBLE\n\n${r.texto}\n\nEl aviso sigue valiendo: el registro esta en ${REGISTRO}.`;

actualizarAviso(id, "POR ATENDER", bloque);
process.stdout.write(`${id}: ${r.ok ? "analisis anotado" : "analisis fallido, anotado el motivo"}.\n`);
process.exit(r.ok ? 0 : 1);
