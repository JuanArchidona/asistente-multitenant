"""Autenticación y tope de gasto de la interfaz desplegada.

Sin dependencias y sin Streamlit, para que se pueda probar entero sin
levantar nada. La interfaz (`app.py`) solo llama a lo que hay aquí.

## Quién entra, y a qué inquilino

Los usuarios viven en un JSON (`usuarios.local.json`, no versionado; el
formato está en `usuarios.example.json`). Cada usuario lleva **su inquilino y
sus roles**: el inquilino no se elige en la interfaz, lo fija la credencial.
Es la misma idea que la colección por inquilino (`CLAUDE.md` §4): que un
usuario de un cliente vea el corpus de otro tiene que exigir una credencial
equivocada, no un desplegable mal puesto.

Las contraseñas se guardan como SHA-256 de `sal:contraseña`. No es un KDF
lento y no pretende serlo: es una interfaz de demostración con usuarios
sintéticos, y el riesgo que cubre es que las credenciales no viajen en claro
por el repositorio ni por la configuración del despliegue. Un despliegue con
usuarios reales cambiaría esto por un proveedor de identidad, y eso está
escrito en `docs/DESPLIEGUE.md`.

## El tope de gasto

Dos topes, y conviene no confundirlos. El **duro** es el prepago sin recarga
automática de las cuentas de los proveedores: no depende de este código y es
el que de verdad limita la pérdida (`CLAUDE.md` §8). El **blando** es este:
la interfaz suma lo gastado según el registro de producción de todos los
inquilinos y deja de responder cuando supera `TOPE_GASTO_USD`. Es blando
porque mide lo que el registro sabe, y el registro no sabe lo que gastan los
embeddings ni lo que se gasta fuera de la interfaz (§16, §37).
"""
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .gobernanza import Usuario
from .observabilidad import RAIZ_POR_DEFECTO, inquilinos, leer, resumir

FICHERO_USUARIOS = Path("usuarios.local.json")
FICHERO_EJEMPLO = Path("usuarios.example.json")
SAL_DE_EJEMPLO = "ejemplo"
TOPE_GASTO_POR_DEFECTO_USD = 2.0


class Credencial(BaseModel):
    usuario: str = Field(min_length=1)
    nombre: str = ""
    tenant: str = Field(min_length=1)
    roles: list[str] = Field(default_factory=list)
    password_sha256: str = Field(min_length=64, max_length=64)

    def como_usuario(self) -> Usuario:
        return Usuario(id=self.usuario, nombre=self.nombre or self.usuario, roles=list(self.roles))


class Directorio(BaseModel):
    """El fichero de usuarios entero."""

    sal: str = Field(min_length=1)
    usuarios: list[Credencial] = Field(min_length=1)

    @property
    def es_de_ejemplo(self) -> bool:
        return self.sal == SAL_DE_EJEMPLO

    def buscar(self, usuario: str) -> Credencial | None:
        for c in self.usuarios:
            if c.usuario == usuario:
                return c
        return None

    def verificar(self, usuario: str, password: str) -> Credencial | None:
        """La credencial si usuario y contraseña casan; None si no.

        Comparación en tiempo constante, y se calcula el hash aunque el usuario
        no exista, para que el tiempo de respuesta no diga qué usuarios hay.
        """
        credencial = self.buscar(usuario)
        esperado = credencial.password_sha256 if credencial else "0" * 64
        if hmac.compare_digest(hash_password(self.sal, password), esperado) and credencial:
            return credencial
        return None


def hash_password(sal: str, password: str) -> str:
    return hashlib.sha256(f"{sal}:{password}".encode()).hexdigest()


def cargar_directorio(ruta: Path | str | None = None) -> Directorio:
    """El fichero de usuarios: el indicado, o el local, o el de ejemplo.

    Que se caiga al de ejemplo es deliberado y **visible**: `es_de_ejemplo`
    lo dice y la interfaz lo muestra. Un despliegue que arranque con las
    credenciales de ejemplo tiene que enterarse, no funcionar en silencio.
    """
    candidatos = [Path(ruta)] if ruta else [FICHERO_USUARIOS, FICHERO_EJEMPLO]
    for candidato in candidatos:
        if candidato.is_file():
            try:
                return Directorio.model_validate(json.loads(candidato.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ValidationError) as error:
                raise ValueError(f"{candidato} no es un directorio de usuarios válido: {error}") from error
    raise ValueError(f"No hay fichero de usuarios: ni {FICHERO_USUARIOS} ni {FICHERO_EJEMPLO}.")


def tope_gasto_usd() -> float:
    bruto = os.getenv("TOPE_GASTO_USD", "").strip()
    return float(bruto) if bruto else TOPE_GASTO_POR_DEFECTO_USD


def gasto_registrado_usd(raiz: Path | str = RAIZ_POR_DEFECTO) -> float:
    """Lo gastado según el registro de producción, todos los inquilinos.

    Excluye los embeddings y todo lo que no pase por la interfaz: es un suelo
    (HALLAZGOS.md §16 y §37), y por eso el tope que lo usa es blando.
    """
    return round(
        sum(resumir(leer(t, raiz)).get("coste_usd_acumulado", 0.0) for t in inquilinos(raiz)), 6
    )


def tope_superado(raiz: Path | str = RAIZ_POR_DEFECTO) -> tuple[bool, float, float]:
    """(superado, gastado, tope)."""
    gastado = gasto_registrado_usd(raiz)
    tope = tope_gasto_usd()
    return gastado >= tope, gastado, tope


def main(argv: list[str]) -> int:
    """`python -m src.acceso hash --sal S --password P` imprime el hash."""
    if len(argv) >= 5 and argv[0] == "hash" and argv[1] == "--sal" and argv[3] == "--password":
        print(hash_password(argv[2], argv[4]))
        return 0
    print("Uso: python -m src.acceso hash --sal SAL --password CONTRASEÑA", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
