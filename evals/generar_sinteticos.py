"""Generación de casos sintéticos que expanden el banco curado.

    uv run python -m evals.generar_sinteticos --por-fragmento 2 --variantes 2

Un golden set escrito a mano tiene un techo evidente: 52 casos son los 52 que a
una persona se le ocurrieron un martes. Generar casos con un LLM levanta ese
techo, pero introduce el riesgo que hace inútiles a la mayoría de los bancos
sintéticos: si el generador se inventa la pregunta *y* la respuesta esperada,
el banco mide la coincidencia entre dos modelos, no la verdad.

De ahí que aquí lo importante no sea generar sino **filtrar**. Todo candidato
pasa dos puertas antes de entrar al dataset:

1. **Validación programática**, que no opina: la categoría existe, el fichero
   existe en el corpus y —la comprobación que de verdad importa— el literal
   exigido en `debe_contener` aparece **textualmente en el documento fuente**.
   Si el dato que se va a exigir no está en el corpus, la pregunta se la ha
   inventado el generador y se descarta sin más discusión.
2. **Crítica de un segundo modelo**, que sí opina, sobre lo que ningún regex
   puede juzgar: si la pregunta se responde solo con ese fragmento, si suena a
   pregunta real de un empleado y si la respuesta esperada es correcta.

Y una decisión de método: **el banco no lo escribe el modelo al que evalúa**.
Construye y critica `claude-sonnet-5` (`BUILDER_MODEL`); responde
`claude-haiku-4-5`. Si el mismo modelo escribiera las preguntas y las
respondiera, el banco premiaría su forma de decir las cosas en vez de que las
diga bien. La independencia ideal sería además de familia (Gemini construyendo
un banco para Claude), pero la cuota gratuita de Gemini —20 generaciones al
día— no da para generar y criticar más de cien candidatos.

Se generan tres familias:

- `conocimiento`, a partir de fragmentos del corpus (pregunta -> fragmento).
- `robustez`, reescribiendo casos curados como los escribiría alguien con prisa,
  conservando la respuesta esperada del caso original.
- `fuera_de_alcance`, preguntas verosímiles cuya respuesta NO está en el corpus,
  que son los casos que detectan alucinación y los más tediosos de escribir a
  mano.
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from src.config import Config, load_config
from src.ingest import trocear
from src.provider import AnthropicChat, GeminiChat

from .dataset import RAIZ_DATASETS, cargar_consultas, escribir_jsonl
from .metrics.deterministas import normalizar
from .schema import CasoConsulta, Dimension
from .transcripcion import similitud_tokens

FUENTES_VALIDAS = ("rrhh", "desarrollo", "actas", "marca")
UMBRAL_DUPLICADO = 0.85
# Generacion y critica van en lotes JSON: con el techo del sistema evaluado (1024)
# el array se trunca y el lote entero se pierde al parsearlo.
MAX_TOKENS_LOTE = 8000

SYSTEM_GENERADOR = """Eres un ingeniero de calidad que construye un banco de pruebas para un
asistente documental interno de empresa. Generas casos de prueba realistas, no ejercicios de
comprensión lectora: las preguntas deben sonar a lo que escribiría un empleado.

Responde SIEMPRE con un array JSON válido, sin texto adicional ni markdown."""

SYSTEM_CRITICO = """Eres un revisor severo de casos de prueba. Tu trabajo es RECHAZAR los casos
defectuosos, no aprobarlos. Ante la duda, rechaza.

Responde SOLO con un objeto JSON: {"valido": true|false, "motivo": "<breve>"}"""


@dataclass
class Candidato:
    consulta: str
    respuesta_esperada: str
    debe_contener: list[str]
    categoria: str
    archivo: str
    dimension: str
    semilla: str


def _json_array(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("["):]
    ini, fin = raw.find("["), raw.rfind("]")
    if ini == -1 or fin == -1:
        return []
    try:
        datos = json.loads(raw[ini:fin + 1])
    except json.JSONDecodeError:
        return []
    return [d for d in datos if isinstance(d, dict)]


def _json_objeto(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
    ini, fin = raw.find("{"), raw.rfind("}")
    if ini == -1 or fin == -1:
        return {}
    try:
        return json.loads(raw[ini:fin + 1])
    except json.JSONDecodeError:
        return {}


# --- Fragmentos del corpus ---------------------------------------------------

def fragmentos_corpus(cfg: Config) -> list[tuple[str, str, str]]:
    """(fuente, archivo, texto) troceando por estructura.

    Se trocea por encabezados y no por caracteres porque cada fragmento va a ser
    el contexto del que nace una pregunta: un corte a mitad de frase produciría
    preguntas sobre información amputada.
    """
    from dataclasses import replace

    cfg_headings = replace(cfg, chunk_strategy="headings")
    salidas = []
    for fuente_dir in sorted(Path(cfg.corpus_path).iterdir()):
        if not fuente_dir.is_dir() or fuente_dir.name not in FUENTES_VALIDAS:
            continue
        for archivo in sorted(fuente_dir.glob("*.md")):
            texto = archivo.read_text(encoding="utf-8")
            for chunk in trocear(texto, cfg_headings):
                if len(chunk.strip()) < 120:  # encabezados sueltos sin contenido
                    continue
                salidas.append((fuente_dir.name, archivo.name, chunk))
    return salidas


# --- Generación --------------------------------------------------------------

def generar_desde_fragmentos(chat, modelo: str, lote: list[tuple[str, str, str]],
                             n: int) -> list[Candidato]:
    """Genera casos para varios fragmentos en una sola llamada.

    Agrupar no es una optimización cosmética: el plan gratuito de Gemini admite
    cinco generaciones por minuto, así que una llamada por fragmento convertiría
    la generación en una espera de media hora. El precio de agrupar es que el
    modelo tiene que decir a qué fragmento corresponde cada caso, y de eso se
    encarga el campo `fragmento` — si no cuadra, el caso se descarta.
    """
    bloques = "\n\n".join(
        f"### FRAGMENTO {i}\n(fuente: {fuente} | documento: {archivo})\n{texto}"
        for i, (fuente, archivo, texto) in enumerate(lote)
    )
    user = f"""{bloques}

Genera {n} casos de prueba POR CADA fragmento, cuya respuesta esté ÍNTEGRAMENTE en ese
fragmento concreto.

Reglas estrictas:
- La pregunta la escribe un empleado, en español, sin citar el documento ni decir
  "según el fragmento".
- "respuesta_esperada": una o dos frases con el dato correcto.
- "debe_contener": UN literal corto (un número, un nombre propio, un código) que
  aparezca TEXTUALMENTE en ese fragmento y sin el cual la respuesta sería incorrecta.
  Si no hay ningún literal así, devuelve la lista vacía.
- No generes preguntas de sí/no ni preguntas cuya respuesta sea todo el fragmento.
- "fragmento" debe ser el número del fragmento del que sale el caso.

Formato: [{{"fragmento": 0, "consulta": "...", "respuesta_esperada": "...",
"debe_contener": ["..."]}}]"""

    salidas = []
    for i, d in enumerate(_json_array(chat.completar(SYSTEM_GENERADOR, user, modelo, max_tokens=MAX_TOKENS_LOTE))):
        if not d.get("consulta") or not d.get("respuesta_esperada"):
            continue
        try:
            idx = int(d.get("fragmento", -1))
        except (TypeError, ValueError):
            continue
        if not 0 <= idx < len(lote):
            continue
        fuente, archivo, _ = lote[idx]
        literales = d.get("debe_contener") or []
        if isinstance(literales, str):
            literales = [literales]
        salidas.append(
            Candidato(
                consulta=str(d["consulta"]).strip(),
                respuesta_esperada=str(d["respuesta_esperada"]).strip(),
                debe_contener=[str(x) for x in literales][:1],
                categoria=fuente,
                archivo=archivo,
                dimension=Dimension.conocimiento.value,
                semilla=f"{archivo}#{idx}.{i}",
            )
        )
    return salidas


def generar_variantes(chat, modelo: str, semillas: list[CasoConsulta], n: int) -> list[Candidato]:
    """Reformula varios casos curados a la vez, conservando su respuesta esperada.

    Estas variantes son gratis en términos de ground truth: como la pregunta es
    la misma con otras palabras, la respuesta correcta ya está validada a mano.
    Lo que miden es si el sistema aguanta la forma real de escribir de la gente,
    no la forma en que se redactó el golden set.
    """
    bloques = "\n".join(f"{i}. {s.consulta}" for i, s in enumerate(semillas))
    user = f"""Estas son preguntas que hacen los empleados a un asistente interno:

{bloques}

Genera {n} reformulaciones de CADA UNA, tal y como se escriben en un chat interno: sin
tildes, con abreviaturas, con erratas, en minúsculas, o planteadas como una petición
("necesito saber...") en vez de como pregunta.

Reglas: la respuesta correcta debe seguir siendo exactamente la misma, y no puedes
introducir ningún dato nuevo ni cambiar el tema.

Formato: [{{"original": 0, "consulta": "..."}}]"""

    salidas = []
    for i, d in enumerate(_json_array(chat.completar(SYSTEM_GENERADOR, user, modelo, max_tokens=MAX_TOKENS_LOTE))):
        consulta = str(d.get("consulta", "")).strip()
        try:
            idx = int(d.get("original", -1))
        except (TypeError, ValueError):
            continue
        if not consulta or not 0 <= idx < len(semillas):
            continue
        semilla = semillas[idx]
        salidas.append(
            Candidato(
                consulta=consulta,
                respuesta_esperada=semilla.respuesta_esperada,
                debe_contener=list(semilla.debe_contener),
                categoria=semilla.categoria_esperada,
                archivo=semilla.archivos_esperados[0] if semilla.archivos_esperados else "",
                dimension=Dimension.robustez.value,
                semilla=f"{semilla.id}#{i}",
            )
        )
    return salidas


def generar_fuera_de_alcance(chat, modelo: str, fuente: str, indice: str, n: int) -> list[Candidato]:
    user = f"""El asistente interno tiene una única fuente documental de la categoría "{fuente}",
cuyo contenido completo es este índice de secciones:

{indice}

Genera {n} preguntas que un empleado haría de forma natural a la categoría "{fuente}" y cuya
respuesta NO esté en ese contenido, pero que resulten completamente verosímiles: el tipo de
cosa que uno esperaría encontrar ahí y no está.

Reglas: no inventes que el documento dice algo; la pregunta debe ser legítima y quedarse sin
respuesta. Evita preguntas absurdas o de otro dominio.

Formato: [{{"consulta": "...", "por_que_no_esta": "..."}}]"""

    salidas = []
    for i, d in enumerate(_json_array(chat.completar(SYSTEM_GENERADOR, user, modelo, max_tokens=MAX_TOKENS_LOTE))):
        consulta = str(d.get("consulta", "")).strip()
        if not consulta:
            continue
        salidas.append(
            Candidato(
                consulta=consulta,
                respuesta_esperada=(
                    "La documentación interna disponible no contiene esa información; "
                    "el asistente debe reconocerlo y no inventar una respuesta."
                ),
                debe_contener=[],
                categoria=fuente,
                archivo="",
                dimension=Dimension.fuera_de_alcance.value,
                semilla=f"ooc-{fuente}#{i}",
            )
        )
    return salidas


# --- Validación --------------------------------------------------------------

def validar_programatico(
    cand: Candidato, textos_corpus: dict[str, str], consultas_existentes: list[str]
) -> tuple[bool, str]:
    if len(cand.consulta) < 12:
        return False, "consulta demasiado corta"
    if len(cand.consulta) > 300:
        return False, "consulta demasiado larga"
    if cand.categoria not in FUENTES_VALIDAS:
        return False, f"categoría inexistente: {cand.categoria}"

    if cand.dimension != Dimension.fuera_de_alcance.value:
        if cand.archivo not in textos_corpus:
            return False, f"el fichero {cand.archivo!r} no está en el corpus"
        documento = normalizar(textos_corpus[cand.archivo])
        for literal in cand.debe_contener:
            if normalizar(literal) not in documento:
                return False, f"el literal {literal!r} no aparece en el documento fuente"

    for existente in consultas_existentes:
        if similitud_tokens(cand.consulta, existente) >= UMBRAL_DUPLICADO:
            return False, f"duplicado de un caso ya presente: {existente!r}"

    return True, ""


def validar_juez_lote(
    chat, modelo: str, items: list[tuple[Candidato, str]]
) -> list[tuple[bool, str]]:
    """Somete un lote de candidatos a la crítica del segundo modelo.

    Un candidato sin veredicto se rechaza. Es deliberado: en un banco de pruebas
    el coste de colar un caso malo (mide mal para siempre) es mayor que el de
    descartar uno bueno (siempre se puede generar otro).
    """
    bloques = []
    for i, (cand, contexto) in enumerate(items):
        if cand.dimension == Dimension.fuera_de_alcance.value:
            bloques.append(
                f"""### CASO {i} — tipo: pregunta SIN respuesta en la documentación
Contenido completo de la fuente "{cand.categoria}":
{contexto}

Pregunta propuesta: {cand.consulta}

Rechaza si la pregunta SÍ puede responderse, aunque sea parcialmente, con ese contenido.
Rechaza también si es absurda, si no encaja en la categoría o si no es algo que un empleado
preguntaría de verdad."""
            )
        else:
            bloques.append(
                f"""### CASO {i} — tipo: pregunta CON respuesta en el fragmento
Fragmento del documento "{cand.archivo}":
{contexto}

Pregunta propuesta: {cand.consulta}
Respuesta esperada: {cand.respuesta_esperada}
Literal exigido: {cand.debe_contener}

Rechaza si: la respuesta esperada no se deduce del fragmento o lo contradice; la pregunta no
puede responderse solo con este fragmento; la pregunta es artificial, cita el documento o es
trivial; o el literal exigido no es imprescindible para que la respuesta sea correcta."""
            )

    user = (
        "\n\n".join(bloques)
        + "\n\nEmite un veredicto por cada caso.\n"
        'Formato: [{"caso": 0, "valido": true|false, "motivo": "<breve>"}]'
    )

    veredictos = {}
    for d in _json_array(chat.completar(SYSTEM_CRITICO, user, modelo, max_tokens=MAX_TOKENS_LOTE)):
        try:
            veredictos[int(d.get("caso", -1))] = (
                bool(d.get("valido")),
                str(d.get("motivo", ""))[:200],
            )
        except (TypeError, ValueError):
            continue

    return [
        veredictos.get(i, (False, "el crítico no emitió veredicto para este caso"))
        for i in range(len(items))
    ]


# --- Orquestación ------------------------------------------------------------

def _indice_secciones(texto: str) -> str:
    return "\n".join(re.findall(r"^#{1,6}\s+.*$", texto, re.MULTILINE)) or texto[:600]


def main() -> None:
    p = argparse.ArgumentParser(description="Generador de casos sintéticos validados")
    p.add_argument("--por-fragmento", type=int, default=2)
    p.add_argument("--variantes", type=int, default=2)
    p.add_argument("--fuera-de-alcance", type=int, default=3)
    p.add_argument("--semillas", type=int, default=12, help="Casos curados a reformular")
    p.add_argument("--salida", default=str(RAIZ_DATASETS / "sinteticos_consultas.jsonl"))
    p.add_argument("--sin-critico", action="store_true", help="Saltar la revisión del segundo modelo")
    p.add_argument("--lote-fragmentos", type=int, default=6,
                   help="Fragmentos por llamada de generación (cuota del plan gratuito)")
    p.add_argument("--lote-critico", type=int, default=8,
                   help="Candidatos por llamada de crítica")
    args = p.parse_args()

    cfg = load_config()
    # El constructor del banco no puede ser el modelo evaluado (ver cabecera).
    if cfg.builder_model == cfg.model_generator:
        sys.exit(
            "[gen] BUILDER_MODEL coincide con el generador evaluado: el banco lo estaría "
            "escribiendo el propio sistema bajo prueba. Cambia BUILDER_MODEL."
        )
    chat = GeminiChat(cfg) if cfg.builder_model.startswith("gemini") else AnthropicChat(cfg)
    modelo = cfg.builder_model
    print(f"[gen] Constructor y crítico: {modelo} (evaluado: {cfg.model_generator})")

    curados = cargar_consultas(RAIZ_DATASETS / "golden_consultas.jsonl")
    existentes = [c.consulta for c in curados]

    textos_corpus: dict[str, str] = {}
    for fuente_dir in sorted(Path(cfg.corpus_path).iterdir()):
        if fuente_dir.is_dir():
            for archivo in fuente_dir.glob("*.md"):
                textos_corpus[archivo.name] = archivo.read_text(encoding="utf-8")

    candidatos: list[tuple[Candidato, str]] = []  # (candidato, contexto para el crítico)

    fragmentos = fragmentos_corpus(cfg)
    print(f"[gen] {len(fragmentos)} fragmentos del corpus")
    for i in range(0, len(fragmentos), args.lote_fragmentos):
        lote = fragmentos[i:i + args.lote_fragmentos]
        for cand in generar_desde_fragmentos(chat, modelo, lote, args.por_fragmento):
            texto = next(t for f, a, t in lote if a == cand.archivo)
            candidatos.append((cand, texto))
        print(f"\r[gen] fragmentos {min(i + args.lote_fragmentos, len(fragmentos))}/"
              f"{len(fragmentos)}", end="", flush=True)
    print()

    semillas = [c for c in curados if c.debe_contener][: args.semillas]
    print(f"[gen] {len(semillas)} casos curados como semilla de variantes")
    for i in range(0, len(semillas), args.lote_fragmentos):
        lote_semillas = semillas[i:i + args.lote_fragmentos]
        for cand in generar_variantes(chat, modelo, lote_semillas, args.variantes):
            candidatos.append((cand, textos_corpus.get(cand.archivo, "")))

    for fuente in FUENTES_VALIDAS:
        completo = "\n\n".join(t for n, t in textos_corpus.items() if _fuente_de(n, cfg) == fuente)
        if not completo:
            continue
        for cand in generar_fuera_de_alcance(
            chat, modelo, fuente, _indice_secciones(completo), args.fuera_de_alcance
        ):
            candidatos.append((cand, completo))

    print(f"[gen] {len(candidatos)} candidatos generados. Validando...")

    # Puerta 1: validación programática. Es gratis y filtra lo indefendible
    # antes de gastar una sola llamada del crítico.
    supervivientes: list[tuple[Candidato, str]] = []
    rechazados: list[dict] = []
    vistos = list(existentes)

    for cand, contexto in candidatos:
        ok, motivo = validar_programatico(cand, textos_corpus, vistos)
        if not ok:
            rechazados.append(
                {"consulta": cand.consulta, "dimension": cand.dimension, "motivo": motivo}
            )
            continue
        supervivientes.append((cand, contexto))
        vistos.append(cand.consulta)

    print(f"[gen] {len(supervivientes)} superan la validación programática.")

    # Puerta 2: crítica del segundo modelo, por lotes.
    veredictos: list[tuple[bool, str]]
    if args.sin_critico:
        veredictos = [(True, "")] * len(supervivientes)
    else:
        veredictos = []
        for i in range(0, len(supervivientes), args.lote_critico):
            lote = supervivientes[i:i + args.lote_critico]
            veredictos.extend(validar_juez_lote(chat, modelo, lote))
            print(f"\r[gen] criticados {min(i + args.lote_critico, len(supervivientes))}/"
                  f"{len(supervivientes)}", end="", flush=True)
        print()

    aceptados: list[CasoConsulta] = []
    contador: dict[str, int] = {}

    for (cand, _), (ok, motivo) in zip(supervivientes, veredictos):
        if not ok:
            rechazados.append(
                {
                    "consulta": cand.consulta,
                    "dimension": cand.dimension,
                    "motivo": f"crítico: {motivo}",
                }
            )
            continue

        contador[cand.categoria] = contador.get(cand.categoria, 0) + 1
        aceptados.append(
            CasoConsulta(
                id=f"syn-{cand.dimension[:4]}-{cand.categoria}-{contador[cand.categoria]:03d}",
                dimension=Dimension(cand.dimension),
                consulta=cand.consulta,
                categoria_esperada=cand.categoria,
                archivos_esperados=[cand.archivo] if cand.archivo else [],
                respuesta_esperada=cand.respuesta_esperada,
                debe_contener=cand.debe_contener,
                comportamiento_esperado=(
                    "abstenerse" if cand.dimension == Dimension.fuera_de_alcance.value
                    else "responder"
                ),
                origen="sintetico",
                semilla=cand.semilla,
                nota="Generado y validado automáticamente.",
            )
        )
        vistos.append(cand.consulta)

    escribir_jsonl(args.salida, aceptados)

    informe = _informe(aceptados, rechazados, len(candidatos))
    ruta_informe = Path(args.salida).with_name("sinteticos_informe.md")
    ruta_informe.write_text(informe, encoding="utf-8")

    print(f"[OK] {len(aceptados)} aceptados / {len(rechazados)} rechazados -> {args.salida}")
    print(f"[OK] Informe de generación: {ruta_informe}")


def _fuente_de(nombre_archivo: str, cfg: Config) -> str:
    for fuente_dir in Path(cfg.corpus_path).iterdir():
        if fuente_dir.is_dir() and (fuente_dir / nombre_archivo).exists():
            return fuente_dir.name
    return ""


def _informe(aceptados, rechazados, total: int) -> str:
    por_dim: dict[str, int] = {}
    por_cat: dict[str, int] = {}
    for c in aceptados:
        por_dim[c.dimension.value] = por_dim.get(c.dimension.value, 0) + 1
        por_cat[c.categoria_esperada] = por_cat.get(c.categoria_esperada, 0) + 1

    motivos: dict[str, int] = {}
    for r in rechazados:
        clave = r["motivo"].split(":")[0][:60]
        motivos[clave] = motivos.get(clave, 0) + 1

    lineas = [
        "# Generación de casos sintéticos",
        "",
        f"- Candidatos generados: {total}",
        f"- Aceptados: {len(aceptados)} ({len(aceptados) / total:.0%})" if total else "- Aceptados: 0",
        f"- Rechazados: {len(rechazados)}",
        "",
        "La tasa de rechazo es el dato interesante: mide cuánto de lo que produce un",
        "generador de casos no sirve como prueba. Aceptarlo todo sin filtrar habría",
        "metido esos casos defectuosos en el banco y habría hecho parecer peor (o mejor)",
        "al sistema por motivos que no tienen que ver con el sistema.",
        "",
        "## Aceptados por dimensión",
        "",
        "| Dimensión | Casos |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(por_dim.items())],
        "",
        "## Aceptados por categoría",
        "",
        "| Categoría | Casos |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(por_cat.items())],
        "",
        "## Motivos de rechazo",
        "",
        "| Motivo | Casos |", "|---|---|",
        *[f"| {k} | {v}  |" for k, v in sorted(motivos.items(), key=lambda kv: -kv[1])],
        "",
        "## Detalle de los rechazos",
        "",
        "| Dimensión | Consulta | Motivo |", "|---|---|---|",
        *[
            f"| {r['dimension']} | {r['consulta'][:90]} | {r['motivo'][:120]} |"
            for r in rechazados
        ],
        "",
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    main()
