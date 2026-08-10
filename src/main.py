"""CLI de una consulta contra el sistema bajo prueba.

La interfaz web del MVP (Streamlit + Render) es la entrega 3.1; aquí basta con
poder lanzar una consulta y ver la traza completa, que es lo que el banco de
pruebas consume.

    uv run python -m src.main "¿Cuántos días de vacaciones tengo?"
"""
import json
import sys

from .agent import Sistema
from .config import load_config


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python -m src.main "tu consulta"')

    consulta = " ".join(sys.argv[1:])
    cfg = load_config()
    sistema = Sistema(cfg)
    traza = sistema.responder(consulta)

    print(traza["respuesta"])
    print("\n--- traza ---")
    detalle = {k: v for k, v in traza.items() if k not in ("respuesta", "contexto_recuperado")}
    print(json.dumps(detalle, ensure_ascii=False, indent=2))
    print(f"--- uso: {json.dumps(sistema.chat.uso.resumen(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
