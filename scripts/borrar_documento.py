"""Borrado efectivo de un documento del indice, cronometrado.

    TENANT_ID=agencia_inmobiliaria uv run python scripts/borrar_documento.py \
        --archivo expediente_2026_118_confidencial.md --restaurar --etiqueta borrado_agencia

Es el camino del derecho de supresion del RGPD (articulo 17) sobre un RAG,
que el Modulo 4.4 nombra y que docs/RIESGOS.md registra como R-17: un RAG
guarda fragmentos de documentos que pueden referirse a personas, y "borrar el
documento" no basta si el indice conserva sus fragmentos. Lo que se mide es
cuanto tarda un borrado **efectivo**: desde que se retira el fichero hasta que
el indice no devuelve ningun fragmento suyo, comprobado contra la coleccion y
no supuesto.

Como funciona: se retira el fichero del corpus, se reconstruye el indice del
inquilino (la ingesta es una reconstruccion completa, asi que el borrado cuesta
lo que cuesta reindexar el corpus entero), y se cuenta cuantos fragmentos del
fichero quedan en la coleccion. Cero o no es borrado. Con `--restaurar` se
devuelve el fichero y se reindexa otra vez, para que el repositorio quede como
estaba; la restauracion tambien se cronometra porque es el camino del derecho
de rectificacion (articulo 16): sustituir un documento es borrarlo y volverlo a
indexar.

Lo que NO cubre, y se dice: el registro de observabilidad guarda las consultas
(quien pregunto que), y borrar un documento no borra las consultas que lo
citaron. Eso es otro camino (R-16).

Coste: dos reindexaciones del corpus del inquilino, o sea dos pasadas de
embeddings sobre todos sus documentos. Los tokens de embeddings no los
contabiliza nadie (HALLAZGOS.md §35), asi que el informe da caracteres
embebidos como aproximacion y lo dice.
"""
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.config import load_config
from src.ingest import construir_indice


def fragmentos_de(cfg, archivo: str) -> int:
    """Cuantos fragmentos del fichero hay en la coleccion. Cero si la coleccion
    no existe: no hay nada que devolver."""
    client = chromadb.PersistentClient(path=cfg.chroma_path)
    nombres = [getattr(c, "name", c) for c in client.list_collections()]
    if cfg.collection not in nombres:
        return 0
    col = client.get_collection(cfg.collection)
    return len(col.get(where={"archivo": archivo}, include=[])["ids"])


def total_fragmentos(cfg) -> int:
    client = chromadb.PersistentClient(path=cfg.chroma_path)
    return client.get_collection(cfg.collection).count()


def caracteres_del_corpus(cfg) -> int:
    return sum(
        len(p.read_text(encoding="utf-8"))
        for p in Path(cfg.corpus_path).glob("*/*.md")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--archivo", required=True, help="nombre del .md dentro de corpus/<tenant>/<fuente>/")
    parser.add_argument("--restaurar", action="store_true", help="devolver el fichero y reindexar al final")
    parser.add_argument("--etiqueta", default=None, help="carpeta de reports/ donde dejar el informe")
    args = parser.parse_args()

    cfg = load_config()
    corpus = Path(cfg.corpus_path)
    candidatos = list(corpus.glob(f"*/{args.archivo}"))
    if len(candidatos) != 1:
        sys.exit(f"[!] Esperaba un fichero llamado {args.archivo!r} en {corpus}/*/ y hay {len(candidatos)}.")
    ruta = candidatos[0]
    fuente = ruta.parent.name
    aparte = RAIZ / "data" / "borrado_en_curso" / cfg.tenant.id / args.archivo
    aparte.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Inquilino {cfg.tenant.id}, fichero {fuente}/{args.archivo}, coleccion {cfg.collection}")

    # Estado inicial. Si el indice no existe o el fichero no esta en el, se
    # construye primero: sin fragmentos que borrar no hay medida.
    antes = fragmentos_de(cfg, args.archivo)
    if antes == 0:
        print("[*] El fichero no esta en el indice (o el indice no existe): indexando antes de medir.")
        construir_indice(cfg)
        antes = fragmentos_de(cfg, args.archivo)
        if antes == 0:
            sys.exit("[!] Tras indexar sigue sin haber fragmentos del fichero. Nada que medir.")
    total_antes = total_fragmentos(cfg)
    caracteres = caracteres_del_corpus(cfg)
    print(f"[*] Antes: {antes} fragmentos del fichero de {total_antes} en la coleccion.")

    # Borrado: retirar el fichero y reconstruir.
    t0 = time.perf_counter()
    shutil.move(str(ruta), str(aparte))
    try:
        info = construir_indice(cfg)
        t_borrado = time.perf_counter() - t0
        despues = fragmentos_de(cfg, args.archivo)
        total_despues = total_fragmentos(cfg)
        print(f"[*] Borrado en {t_borrado:.1f} s: {despues} fragmentos del fichero, {total_despues} en la coleccion.")
        efectivo = despues == 0 and total_despues == total_antes - antes

        t_restauracion = None
        tras_restaurar = None
        if args.restaurar:
            t1 = time.perf_counter()
            shutil.move(str(aparte), str(ruta))
            construir_indice(cfg)
            t_restauracion = time.perf_counter() - t1
            tras_restaurar = fragmentos_de(cfg, args.archivo)
            print(f"[*] Restaurado en {t_restauracion:.1f} s: {tras_restaurar} fragmentos del fichero (antes {antes}).")
    finally:
        # Pase lo que pase, el fichero vuelve al corpus: un fallo a mitad no
        # puede dejar el repositorio sin un documento.
        if aparte.exists():
            shutil.move(str(aparte), str(ruta))
            print("[!] Fichero devuelto al corpus tras un fallo; el indice puede estar desfasado: reindexa.")

    resumen = {
        "tenant": cfg.tenant.id,
        "archivo": args.archivo,
        "fuente": fuente,
        "fragmentos_del_fichero_antes": antes,
        "fragmentos_del_fichero_despues": despues,
        "fragmentos_coleccion_antes": total_antes,
        "fragmentos_coleccion_despues": total_despues,
        "borrado_efectivo": efectivo,
        "segundos_borrado": round(t_borrado, 2),
        "segundos_restauracion": round(t_restauracion, 2) if t_restauracion is not None else None,
        "fragmentos_tras_restaurar": tras_restaurar,
        "restauracion_completa": (tras_restaurar == antes) if args.restaurar else None,
        "caracteres_corpus_embebidos_por_pasada": caracteres,
        "embed_model": cfg.embed_model,
        "embed_dims": cfg.embed_dims,
        "chunk_strategy": cfg.chunk_strategy,
        "coste_embeddings": "no contabilizado (HALLAZGOS.md §35); caracteres como aproximacion",
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "estrategia": info["estrategia"],
    }

    if args.etiqueta:
        carpeta = RAIZ / "reports" / args.etiqueta
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "resumen.json").write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (carpeta / "informe.md").write_text(informe(resumen), encoding="utf-8")
        print(f"[OK] Informe en {carpeta.relative_to(RAIZ)}/")

    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if efectivo else 1


def informe(r: dict) -> str:
    veredicto = "**EFECTIVO**" if r["borrado_efectivo"] else "**NO EFECTIVO**"
    lineas = [
        f"# Borrado cronometrado: `{r['archivo']}` ({r['tenant']})",
        "",
        (
            f"Fecha: {r['fecha']}. Estrategia `{r['chunk_strategy']}`, embeddings "
            f"`{r['embed_model']}` a {r['embed_dims']} dimensiones."
        ),
        "",
        "| Medida | Valor |",
        "|---|---|",
        f"| Fragmentos del fichero en el indice, antes | {r['fragmentos_del_fichero_antes']} |",
        f"| Fragmentos del fichero en el indice, despues | {r['fragmentos_del_fichero_despues']} |",
        f"| Fragmentos totales, antes / despues | {r['fragmentos_coleccion_antes']} / {r['fragmentos_coleccion_despues']} |",
        f"| Borrado efectivo (cero fragmentos y el resto intacto) | {veredicto} |",
        f"| Tiempo hasta borrado efectivo | **{r['segundos_borrado']} s** |",
    ]
    if r["segundos_restauracion"] is not None:
        lineas += [
            f"| Tiempo de restauracion (camino de rectificacion) | **{r['segundos_restauracion']} s** |",
            f"| Fragmentos tras restaurar / antes | {r['fragmentos_tras_restaurar']} / {r['fragmentos_del_fichero_antes']} |",
        ]
    lineas += [
        f"| Caracteres embebidos por pasada | {r['caracteres_corpus_embebidos_por_pasada']} |",
        "",
        "El borrado es una reconstruccion completa del indice del inquilino, asi que",
        "cuesta lo que cuesta reindexar su corpus entero, y ese coste crece con el",
        "corpus. Un borrado incremental (eliminar por metadato `archivo` sin",
        "reindexar) seria O(1) y esta fuera del sprint; lo que se defiende aqui es",
        "que el camino existe, es verificable contra la coleccion y esta medido.",
        "",
        "No cubre el registro de observabilidad: las consultas que citaron el",
        "documento siguen registradas (RIESGOS.md R-16).",
        "",
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.exit(main())
