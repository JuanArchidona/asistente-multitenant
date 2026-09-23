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

from .gobernanza import PoliticaAcceso

DIRECTORIO_TENANTS = Path("tenants")

# Categoría universal: "ninguna fuente interna aplica". Ningún inquilino la
# declara porque todos la tienen, y por eso su nombre está reservado.
CATEGORIA_OTRO = "otro"

_RE_IDENTIFICADOR = re.compile(r"^[a-z][a-z0-9_]*$")

# A dónde lleva una categoría. Es la bifurcación del flujo original: duda
# documental al RAG, duda de estado a la API de negocio vía MCP.
DESTINO_DOCUMENTAL = "documental"
DESTINO_ESTRUCTURADO = "estructurado"
DESTINOS = (DESTINO_DOCUMENTAL, DESTINO_ESTRUCTURADO)


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


class ServidorMCP(BaseModel):
    """Un servidor MCP que expone los datos de negocio de este inquilino.

    Se lanza como proceso independiente y se habla con él por stdio. Que sea un
    proceso aparte y no una importación es deliberado: el sistema de negocio de
    un cliente real no es código de este repositorio, y tratarlo como tal
    escondería justo los fallos que importan (arranque, timeouts, caídas).
    """

    nombre: str
    comando: str
    args: list[str] = Field(default_factory=list)
    descripcion: str = ""

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return _validar_identificador(v, "nombre de servidor MCP")


class CategoriaTenant(BaseModel):
    """Una categoría de enrutado y el sitio al que dirige la recuperación."""

    nombre: str
    descripcion: str = Field(min_length=1)
    destino: str = DESTINO_DOCUMENTAL
    fuente: str = ""

    @field_validator("destino")
    @classmethod
    def _destino_valido(cls, v: str) -> str:
        if v not in DESTINOS:
            raise ValueError(f"destino inválido: {v!r}. Usa uno de {DESTINOS}.")
        return v

    @model_validator(mode="after")
    def _fuente_coherente_con_destino(self) -> "CategoriaTenant":
        if self.destino == DESTINO_DOCUMENTAL and not self.fuente:
            raise ValueError(
                f"la categoría {self.nombre!r} es documental y no declara fuente"
            )
        if self.destino == DESTINO_ESTRUCTURADO and self.fuente:
            raise ValueError(
                f"la categoría {self.nombre!r} es estructurada: no consulta el corpus, "
                "así que no puede declarar fuente"
            )
        return self

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
        return _validar_identificador(v, "fuente") if v else v


# Clasificación por el Reglamento (UE) 2024/1689 (AI Act), artículo 6.
#
# Va en el manifiesto y no en código porque **el mismo sistema cae en casillas
# distintas según el inquilino**: el corpus de uno toca el anexo III (salarios
# y evaluaciones de la plantilla, punto 4) y el de otro toca otro punto
# (solvencia de personas físicas, punto 5). Lo que no cambia es la regla, y la
# regla es lo que este modelo valida:
#
#   - Tocar el anexo III sin declararse de alto riesgo exige alegar la
#     excepción del artículo 6.3 con su condición, su justificación y los usos
#     que se excluyen para sostenerla. El apartado 4 dice que quien la alegue
#     "documentará su evaluación": aquí la documentación es este bloque, y la
#     evaluación es un ValueError si falta.
#   - El último párrafo del 6.3 dice que un sistema que perfile personas
#     "siempre se considerará de alto riesgo". Una excepción con perfilado se
#     rechaza.
#   - El artículo 50.1 exige que quien interactúa sepa que lo hace con una IA.
#     El texto con el que se cumple es `aviso_usuario`, y lo imprime la
#     interfaz delante de cada respuesta.
#
# Las citas literales y el calendario vigente (Reglamento (UE) 2026/1744, que
# retrasa el alto riesgo del anexo III al 2 de diciembre de 2027) están en
# docs/MODULO_4.md, sección del artículo 6. Registro de riesgos: docs/RIESGOS.md.

CLASIFICACION_TRANSPARENCIA = "transparencia_art_50"
CLASIFICACION_ALTO_RIESGO = "alto_riesgo_anexo_iii"
CLASIFICACIONES_AI_ACT = (CLASIFICACION_TRANSPARENCIA, CLASIFICACION_ALTO_RIESGO)

# Las cuatro condiciones del artículo 6.3, por su letra.
CONDICIONES_ART_6_3 = {
    "a": "tarea de procedimiento limitada",
    "b": "mejorar el resultado de una actividad humana previamente realizada",
    "c": "detectar patrones de decisión sin sustituir la valoración humana",
    "d": "tarea preparatoria para una evaluación",
}

_RE_PUNTO_ANEXO_III = re.compile(r"^[1-8][a-z]?$")


class ExcepcionArt63(BaseModel):
    """La alegación de que un sistema del anexo III no es de alto riesgo."""

    condicion: str
    justificacion: str = Field(min_length=20)
    usos_excluidos: list[str] = Field(min_length=1)
    perfila_personas: bool

    @field_validator("condicion")
    @classmethod
    def _condicion_valida(cls, v: str) -> str:
        if v not in CONDICIONES_ART_6_3:
            raise ValueError(
                f"condición del artículo 6.3 inválida: {v!r}. "
                f"Usa una letra de {sorted(CONDICIONES_ART_6_3)}."
            )
        return v

    @model_validator(mode="after")
    def _el_perfilado_siempre_es_alto_riesgo(self) -> "ExcepcionArt63":
        if self.perfila_personas:
            raise ValueError(
                "no cabe la excepción del artículo 6.3 en un sistema que perfila "
                "personas: el último párrafo del apartado 3 lo declara siempre de "
                "alto riesgo. Clasifícalo como alto_riesgo_anexo_iii."
            )
        return self


class ClasificacionAIAct(BaseModel):
    """Lo que el inquilino declara sobre sí mismo ante el artículo 6."""

    clasificacion: str
    puntos_anexo_iii: list[str] = Field(default_factory=list)
    excepcion_art_6_3: ExcepcionArt63 | None = None
    aviso_usuario: str = Field(min_length=10)
    evaluado: str = Field(min_length=10)  # fecha ISO de la evaluación
    fuentes: list[str] = Field(min_length=1)

    @field_validator("clasificacion")
    @classmethod
    def _clasificacion_valida(cls, v: str) -> str:
        if v not in CLASIFICACIONES_AI_ACT:
            raise ValueError(
                f"clasificación inválida: {v!r}. Usa una de {CLASIFICACIONES_AI_ACT}."
            )
        return v

    @field_validator("puntos_anexo_iii")
    @classmethod
    def _puntos_validos(cls, v: list[str]) -> list[str]:
        malos = [p for p in v if not _RE_PUNTO_ANEXO_III.match(p)]
        if malos:
            raise ValueError(
                f"puntos del anexo III inválidos: {malos}. Usa el número del punto "
                "y, si procede, la letra: '4', '5b'."
            )
        return v

    @model_validator(mode="after")
    def _anexo_iii_sin_salida_es_alto_riesgo(self) -> "ClasificacionAIAct":
        toca_anexo = bool(self.puntos_anexo_iii)
        if (
            self.clasificacion == CLASIFICACION_TRANSPARENCIA
            and toca_anexo
            and self.excepcion_art_6_3 is None
        ):
            raise ValueError(
                f"el inquilino toca el anexo III ({self.puntos_anexo_iii}) y se "
                "declara de transparencia sin alegar la excepción del artículo "
                "6.3. O se alega y se documenta, o es alto_riesgo_anexo_iii."
            )
        if self.clasificacion == CLASIFICACION_ALTO_RIESGO and not toca_anexo:
            raise ValueError(
                "alto_riesgo_anexo_iii exige declarar qué puntos del anexo III lo "
                "sitúan ahí."
            )
        if self.excepcion_art_6_3 is not None and not toca_anexo:
            raise ValueError(
                "se alega la excepción del artículo 6.3 sin tocar el anexo III: la "
                "excepción no tiene de qué exceptuar."
            )
        return self


class Tenant(BaseModel):
    """Un cliente del sistema, con todo lo que lo distingue de los demás."""

    id: str
    nombre: str = Field(min_length=1)
    descripcion: str = ""
    contexto_enrutador: str = Field(min_length=1)
    categorias: list[CategoriaTenant] = Field(min_length=1)
    # Grupos de categorías que se consultan juntas. Ver `categorias_a_consultar`.
    solapamientos: list[list[str]] = Field(default_factory=list)
    servidores_mcp: list[ServidorMCP] = Field(default_factory=list)
    politica: PoliticaAcceso = Field(default_factory=PoliticaAcceso)
    # Obligatorio: un inquilino sin clasificación no arranca. Es la forma de
    # que el alta de un cliente nuevo incluya la evaluación del artículo 6.
    ai_act: ClasificacionAIAct

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

    @model_validator(mode="after")
    def _la_rama_estructurada_tiene_a_donde_ir(self) -> "Tenant":
        """Una categoría estructurada sin servidor declarado enruta a la nada.

        El usuario vería "no tengo esa información" y parecería un corpus
        incompleto, cuando lo que falta es la mitad del sistema.
        """
        if self.categorias_estructuradas and not self.servidores_mcp:
            nombres = sorted(c.nombre for c in self.categorias_estructuradas)
            raise ValueError(
                f"el inquilino {self.id!r} declara categorías estructuradas {nombres} "
                "pero ningún servidor MCP que las atienda"
            )
        return self

    @model_validator(mode="after")
    def _solapamientos_coherentes(self) -> "Tenant":
        """Un grupo mal declarado enrutaría a una categoría inexistente.

        Se exige además que una categoría esté en **un solo** grupo: con dos,
        qué consultar depende de por dónde se entre, que es exactamente la
        ambigüedad que el grupo viene a quitar.
        """
        declaradas = {c.nombre for c in self.categorias}
        vistas: set[str] = set()
        for grupo in self.solapamientos:
            if len(grupo) < 2:
                raise ValueError(
                    f"solapamiento {grupo} en {self.id!r}: un grupo de menos de dos "
                    "categorías no solapa con nada"
                )
            if len(set(grupo)) != len(grupo):
                raise ValueError(f"solapamiento {grupo} en {self.id!r}: nombres repetidos")
            desconocidas = sorted(set(grupo) - declaradas)
            if desconocidas:
                raise ValueError(
                    f"solapamiento {grupo} en {self.id!r} cita categorías no "
                    f"declaradas: {desconocidas}"
                )
            repetidas = sorted(set(grupo) & vistas)
            if repetidas:
                raise ValueError(
                    f"las categorías {repetidas} de {self.id!r} están en más de un "
                    "solapamiento: qué consultar dejaría de estar determinado"
                )
            vistas |= set(grupo)
        return self

    def categorias_a_consultar(self, categoria: str) -> list[str]:
        """Qué se consulta cuando el enrutador elige `categoria`.

        Normalmente, solo ella. Si está en un grupo de solapamiento, **todas
        las del grupo**, con la elegida primero.

        Existe porque hay pares de categorías cuyo solapamiento no es un
        problema de redacción: el dato vive de verdad en las dos fuentes. En el
        inquilino C, quiénes son las partes de una operación está en el
        expediente documental y en el CRM, y se midió dos veces que ninguna
        redacción del prompt lo arregla (HALLAZGOS.md §6 y §12). Pedirle al
        enrutador que elija es pedirle que resuelva una ambigüedad que no está
        en la pregunta sino en el modelo de datos; la salida es no elegir.

        Es declarativo a propósito: un inquilino sin solapamientos declarados
        —como el heredado— no cambia de comportamiento en absoluto, y por eso
        las métricas de sus 53 casos siguen siendo comparables.
        """
        for grupo in self.solapamientos:
            if categoria in grupo:
                return [categoria] + [c for c in grupo if c != categoria]
        return [categoria]

    @property
    def categorias_documentales(self) -> list[CategoriaTenant]:
        return [c for c in self.categorias if c.destino == DESTINO_DOCUMENTAL]

    @property
    def categorias_estructuradas(self) -> list[CategoriaTenant]:
        return [c for c in self.categorias if c.destino == DESTINO_ESTRUCTURADO]

    def destino_de(self, categoria: str) -> str:
        """A qué rama va una categoría. `otro` no va a ninguna."""
        for c in self.categorias:
            if c.nombre == categoria:
                return c.destino
        raise KeyError(f"categoría {categoria!r} no declarada en el inquilino {self.id!r}")

    @property
    def categorias_validas(self) -> set[str]:
        """Lo que el enrutador puede devolver legítimamente para este inquilino."""
        return {c.nombre for c in self.categorias} | {CATEGORIA_OTRO}

    def fuente_de(self, categoria: str) -> str:
        """Fuente documental de una categoría. `otro` no tiene: no se pregunta por ella."""
        for c in self.categorias:
            if c.nombre == categoria:
                if c.destino != DESTINO_DOCUMENTAL:
                    raise KeyError(
                        f"la categoría {categoria!r} es {c.destino}: no tiene fuente documental"
                    )
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
