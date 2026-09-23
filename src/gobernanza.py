"""Control de acceso a la información, en las dos ramas de recuperación.

## Por qué no se arregla con el prompt

La 3.3 midió que endurecer el prompt elimina las fugas documentales, pero a costa
de bajar la relevancia de 0,880 a 0,778: el modelo se vuelve receloso con todo.
Y aun así el control seguiría siendo una petición educada a un modelo, no una
garantía: basta una formulación ingeniosa para saltárselo.

Aquí el control es estructural y va **antes** del modelo:

- En la rama documental, un documento restringido no se recupera si quien
  pregunta no tiene el rol. El generador nunca lo ve, así que no puede filtrarlo
  aunque quiera.
- En la rama estructurada, los campos sensibles del resultado de una herramienta
  se sustituyen antes de dárselo al modelo. Lo mismo: no puede revelar lo que no
  ha recibido.

La diferencia con el prompt no es de grado. Un prompt que dice "no reveles el
DNI" deja el DNI dentro de la ventana de contexto, donde una inyección o una
petición hábil pueden sacarlo, y donde además queda en los registros del
proveedor. Esto no lo mete nunca.

## Por qué la política vive en el manifiesto

Cada cliente clasifica su información distinto. Que la política sea datos del
inquilino y no código es lo que permite dar de alta un cliente con otras reglas
sin tocar el núcleo, igual que con las categorías y los servidores MCP.

## El riesgo de pasarse

Un sistema que deniega todo saca un pleno en las métricas de confidencialidad y
no sirve para nada. Por eso el banco incluye casos de acceso **autorizado**: si
la dirección pregunta por los ingresos de un cliente y el sistema se niega, eso
también es un fallo, y sale en rojo.
"""
import json
from typing import Any

from pydantic import BaseModel, Field

# Marca que ocupa el lugar de un dato restringido. Se deja visible a propósito:
# el modelo tiene que poder decir "ese dato existe pero no te lo puedo dar", que
# es una respuesta útil, en vez de comportarse como si el campo no existiera.
MARCA_RESTRINGIDO = "[dato restringido]"

# Nivel de un documento sin restricción declarada. Centinela explícito en vez
# de cadena vacía: viaja como metadato al índice, sale en los informes y se
# distingue de "el campo no está" al depurar.
SIN_RESTRICCION = "publico"


class DocumentoRestringido(BaseModel):
    """Un documento del corpus que no puede ver cualquiera."""

    archivo: str
    requiere: str = Field(min_length=1, description="Rol necesario para recuperarlo")
    motivo: str = ""


class CampoSensible(BaseModel):
    """Una clave que las herramientas devuelven y que no puede salir sin permiso."""

    campo: str
    requiere: str = Field(min_length=1)
    motivo: str = ""


class PoliticaAcceso(BaseModel):
    """Qué protege este inquilino y quién puede verlo."""

    documentos_restringidos: list[DocumentoRestringido] = Field(default_factory=list)
    campos_sensibles: list[CampoSensible] = Field(default_factory=list)

    def requisito_de_documento(self, archivo: str) -> str:
        for doc in self.documentos_restringidos:
            if doc.archivo == archivo:
                return doc.requiere
        return SIN_RESTRICCION

    def requisito_de_campo(self, campo: str) -> str:
        for c in self.campos_sensibles:
            if c.campo == campo:
                return c.requiere
        return SIN_RESTRICCION

    @property
    def roles_declarados(self) -> set[str]:
        return {d.requiere for d in self.documentos_restringidos} | {
            c.requiere for c in self.campos_sensibles
        }


class Usuario(BaseModel):
    """Quién pregunta. Sin esto no hay control de acceso posible, solo buenos modales."""

    id: str
    nombre: str = ""
    roles: list[str] = Field(default_factory=list)

    def puede(self, requisito: str) -> bool:
        return requisito == SIN_RESTRICCION or requisito in self.roles

    @property
    def niveles_visibles(self) -> list[str]:
        """Valores del metadato de restricción que este usuario puede recuperar."""
        return [SIN_RESTRICCION, *self.roles]


# Usuario por defecto: un empleado cualquiera, sin privilegios. Es el que usa el
# banco salvo que un caso diga otra cosa, porque el escenario a medir es
# precisamente el del empleado que pide lo que no le corresponde.
USUARIO_ANONIMO = Usuario(id="empleado", nombre="Empleado sin privilegios", roles=[])


def redactar(
    datos: Any, politica: PoliticaAcceso, usuario: Usuario
) -> tuple[Any, list[str]]:
    """Sustituye los campos sensibles que el usuario no puede ver.

    Recorre la estructura completa, no solo el primer nivel: los datos personales
    de una operación viven anidados dentro de `parte_compradora`, y una redacción
    que solo mirase las claves de arriba no vería nada.
    """
    redactados: list[str] = []

    def _recorrer(nodo: Any, ruta: str = "") -> Any:
        if isinstance(nodo, dict):
            salida = {}
            for clave, valor in nodo.items():
                completa = f"{ruta}.{clave}" if ruta else clave
                requisito = politica.requisito_de_campo(clave)
                if requisito and not usuario.puede(requisito):
                    redactados.append(completa)
                    salida[clave] = MARCA_RESTRINGIDO
                else:
                    salida[clave] = _recorrer(valor, completa)
            return salida
        if isinstance(nodo, list):
            return [_recorrer(v, f"{ruta}[{i}]") for i, v in enumerate(nodo)]
        return nodo

    return _recorrer(datos), redactados


MARCA_NO_ESTRUCTURADA = "<salida no estructurada: no se pudo redactar>"
MARCA_RETENIDA = "<salida no estructurada: RETENIDA, la política exige redactar campos>"
TEXTO_RETENIDO = (
    "[resultado de la herramienta retenido: no llegó como JSON y la política de "
    "acceso de este inquilino exige redactar campos sensibles, así que no se puede "
    "garantizar la redacción. Dilo al usuario en vez de presentarlo como que no hay "
    "datos.]"
)


def redactar_json(
    bruto: str, politica: PoliticaAcceso, usuario: Usuario
) -> tuple[str, list[str]]:
    """Redacta el resultado de una herramienta, que llega serializado.

    Si no es JSON no se intenta adivinar con expresiones regulares sobre texto
    libre: un filtro que falla a veces es peor que no tenerlo, y el banco lo
    daría por bueno. Lo que se hace depende de lo que el inquilino declara:

    - Sin campos sensibles en la política, no hay nada que redactar: el texto
      pasa intacto y se deja constancia.
    - Con campos sensibles, **se retiene entero** y se deja constancia. Pasarlo
      con una marca era un fallback silencioso: se vio el 23-09-2026 en el
      servicio desplegado, donde un resultado de 6.028 caracteres llegó
      recortado (y por tanto sin ser JSON) y pasó al modelo sin redactar con
      la marca al lado (HALLAZGOS.md §41). Que no llevara datos personales fue
      suerte, no diseño.
    """
    try:
        datos = json.loads(bruto)
    except json.JSONDecodeError:
        if politica.campos_sensibles:
            return TEXTO_RETENIDO, [MARCA_RETENIDA]
        return bruto, [MARCA_NO_ESTRUCTURADA]
    limpio, redactados = redactar(datos, politica, usuario)
    return json.dumps(limpio, ensure_ascii=False), redactados
