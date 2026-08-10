"""Entrypoint de ingesta. Construye el índice vectorial desde corpus/."""
from .config import load_config
from .ingest import construir_indice


def main():
    cfg = load_config()
    print(f"[*] Indexando corpus desde {cfg.corpus_path}/ -> {cfg.chroma_path}/")
    print(
        f"[*] Estrategia: {cfg.chunk_strategy} (size={cfg.chunk_size}, "
        f"overlap={cfg.chunk_overlap}) | embed {cfg.embed_model}@{cfg.embed_dims}d"
    )
    info = construir_indice(cfg)
    print(f"[OK] {info['documentos']} chunks indexados en la colección '{info['coleccion']}'.")
    print(f"[OK] Fuentes: {', '.join(info['fuentes'])}")


if __name__ == "__main__":
    main()
