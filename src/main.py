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
from .observabilidad import desde_config


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python -m src.main "tu consulta"')

    consulta = " ".join(sys.argv[1:])
    cfg = load_config()
    # Este es el punto de entrada de produccion, asi que aqui si se registra.
    # El banco crea su `Sistema` sin registro a proposito.
    registro = desde_config(cfg)
    sistema = Sistema(cfg, registro=registro)
    traza = sistema.responder(consulta)

    print(traza["respuesta"])
    print("\n--- traza ---")
    detalle = {k: v for k, v in traza.items() if k not in ("respuesta", "contexto_recuperado")}
    print(json.dumps(detalle, ensure_ascii=False, indent=2))
    print(f"--- uso: {json.dumps(sistema.chat.uso.resumen(), ensure_ascii=False)}")
    if registro.fallos:
        print(f"[!] El registro fallo {registro.fallos} veces: {registro.ultimo_error}")
    else:
        print(f"--- anotado en {registro.ruta}")


if __name__ == "__main__":
    main()
