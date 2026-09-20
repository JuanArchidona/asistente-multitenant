"""Salida estructurada del enrutador.

Cambio respecto a la 3.3: `categoria` era un Enum fijo con las cuatro fuentes de
la empresa de la 2.3. Eso hacía imposible un segundo inquilino sin editar el
núcleo, que es justo lo que este proyecto tiene que evitar. Ahora la categoría
es una cadena y **quién decide si es válida es el inquilino**
(`Tenant.categorias_validas`), no el tipo.

La validación no desaparece, se mueve: el enrutador comprueba la categoría
contra las del inquilino y, si no encaja, marca `fallback`. Es el mismo criterio
que ya se aplicaba a un JSON malformado — un modelo que devuelve una categoría
inexistente se ha roto igual, y se contabiliza igual.
"""
from pydantic import BaseModel, Field

from .tenant import CATEGORIA_OTRO


class Enrutamiento(BaseModel):
    """Salida estructurada del enrutador: a qué fuente debe ir la consulta."""

    categoria: str = Field(
        min_length=1, description="Categoría de la consulta, declarada por el inquilino"
    )
    justificacion: str = Field(
        description="Breve explicación de por qué se asigna esa categoría"
    )
    confianza: float = Field(
        ge=0.0, le=1.0, description="Confianza del modelo en la clasificación (0-1)"
    )
    fallback: bool = Field(
        default=False,
        description=(
            "True si esta clasificación NO viene del modelo sino del fallback por "
            "fallo de parseo o por categoría desconocida. Lo rellena el enrutador, "
            "no el LLM."
        ),
    )

    @property
    def sin_fuente(self) -> bool:
        """No hay fuente documental que consultar para esta categoría."""
        return self.categoria == CATEGORIA_OTRO
