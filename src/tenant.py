"""Definición declarativa de un inquilino.

Un inquilino es un cliente del sistema: su corpus, sus categorías de enrutado y
su colección en el índice vectorial. Vive en `tenants/<id>.json` y **no en
código**, porque dar de alta un cliente nuevo tiene que ser escribir un
manifiesto, un corpus y un golden set, sin tocar el núcleo. Esa afirmación no es
retórica: se mide cronometrando el alta de un inquilino nuevo al final del
proyecto. Si para darlo de alta hay que editar un `.py`, la costura está mal
puesta y el número lo delata.

## Por qué una colección por inquilino y no un filtro por metadato

La alternativa barata sería un único índice con `tenant_id` en cada fragmento y
un filtro en cada consulta. Se descarta: deja la confidencialidad en manos de
que ese filtro esté bien construido **en todas las rutas de consulta**, y un
descuido devuelve documentos de otro cliente sin que nada lo señale. Con una
colección por inquilino, una fuga entre clientes exige abrir la colección
equivocada entera: un fallo mucho más grosero, que además se comprueba con un
test (`tests/test_tenant.py`).

El precio es real y está asumido: más colecciones que mantener y una reindexación
por cliente. Ese coste es justo lo que se mide en el alta cronometrada, así que
queda contabilizado en vez de escondido.
"""
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

DIRECTORIO_TENANTS = Path("tenants")

# Categoría universal: "ninguna fuente interna aplica". Ningún inquilino la
# declara porque todos la tienen, y por eso su nombre está reservado.
CATEGORIA_OTRO = "otro"

_RE_IDENTIFICADOR = re.compile(r"^[a-z][a-z0-9_]*$")


def _validar_identificador(valor: str, campo: str) -> str:
    """Identificadores en minúsculas: acaban en rutas de disco y en nombres de
    colección de Chroma, donde un espacio o un acento se convierte en un fallo
    lejos de su causa."""
    if not _RE_IDENTIFICADOR.match(valor):
        raise ValueError(
            f"{campo} inválido: {valor!r}. Usa minúsculas, dígitos y guion bajo, "
            "empezando por letra."
        )
    return valor


class CategoriaTenant(BaseModel):
    """Una categoría de enrutado y la fuente documental a la que dirige."""

    nombre: str
    descripcion: str = Field(min_length=1)
    fuente: str

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        if v == CATEGORIA_OTRO:
            raise ValueError(
                f"{CATEGORIA_OTRO!r} es una categoría reservada: la tienen todos los "
                "inquilinos y no se declara."
            )
        return _validar_identificador(v, "nombre de categoría")

    @field_validator("fuente")
    @classmethod
    def _fuente_valida(cls, v: str) -> str:
        return _validar_identificador(v, "fuente")


class Tenant(BaseModel):
    """Un cliente del sistema, con todo lo que lo distingue de los demás."""

    id: str
    nombre: str = Field(min_length=1)
    descripcion: str = ""
    contexto_enrutador: str = Field(min_length=1)
    categorias: list[CategoriaTenant] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _id_valido(cls, v: str) -> str:
        return _validar_identificador(v, "id de inquilino")

    @model_validator(mode="after")
    def _categorias_sin_duplicados(self) -> "Tenant":
        nombres = [c.nombre for c in self.categorias]
        repetidos = {n for n in nombres if nombres.count(n) > 1}
        if repetidos:
            raise ValueError(f"categorías repetidas en {self.id!r}: {sorted(repetidos)}")
        return self

    @property
    def categorias_validas(self) -> set[str]:
        """Lo que el enrutador puede devolver legítimamente para este inquilino."""
        return {c.nombre for c in self.categorias} | {CATEGORIA_OTRO}

    def fuente_de(self, categoria: str) -> str:
        """Fuente documental de una categoría. `otro` no tiene: no se pregunta por ella."""
        for c in self.categorias:
            if c.nombre == categoria:
                return c.fuente
        raise KeyError(f"categoría {categoria!r} no declarada en el inquilino {self.id!r}")

    def coleccion(self, base: str) -> str:
        """Nombre de la colección de Chroma de este inquilino.

        El id va en el nombre, no en un metadato: es lo que hace que el
        aislamiento sea estructural.
        """
        return f"{base}__{self.id}"

    def corpus(self, raiz: str) -> str:
        return f"{raiz}/{self.id}"


def cargar_tenant(tenant_id: str, raiz: Path = DIRECTORIO_TENANTS) -> Tenant:
    """Carga `tenants/<id>.json`.

    Falla ruidosamente si no existe o no valida. Un inquilino mal definido tiene
    que romper en el arranque y no a mitad de una consulta, cuando el síntoma
    sería un índice vacío o una categoría que no enruta a ninguna parte.
    """
    ruta = raiz / f"{tenant_id}.json"
    if not ruta.is_file():
        disponibles = listar_tenants(raiz)
        raise ValueError(
            f"No existe el inquilino {tenant_id!r} en {raiz}/. "
            f"Disponibles: {disponibles or 'ninguno'}."
        )
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{ruta} no es JSON válido: {error}") from error

    tenant = Tenant.model_validate(datos)
    if tenant.id != tenant_id:
        raise ValueError(
            f"{ruta} declara id={tenant.id!r} pero el fichero se llama {tenant_id!r}. "
            "El nombre del fichero es la referencia."
        )
    return tenant


def listar_tenants(raiz: Path = DIRECTORIO_TENANTS) -> list[str]:
    if not raiz.is_dir():
        return []
    return sorted(p.stem for p in raiz.glob("*.json"))
