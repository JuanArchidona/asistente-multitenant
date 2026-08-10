from enum import Enum

from pydantic import BaseModel, Field


class Categoria(str, Enum):
    """Categorías fijas que reconoce el enrutador. Cada una mapea a una fuente."""

    rrhh = "rrhh"              # convenio, políticas, vacaciones, nóminas
    desarrollo = "desarrollo"  # guías técnicas, estándares de código
    actas = "actas"            # actas de reuniones (producidas por el agente 2.1)
    marca = "marca"            # marketing, comunicación, identidad de marca
    otro = "otro"              # no encaja en ninguna fuente interna


class Enrutamiento(BaseModel):
    """Salida estructurada del enrutador: a qué fuente debe ir la consulta."""

    categoria: Categoria = Field(description="Categoría de la consulta del usuario")
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
            "fallo de parseo. Lo rellena el enrutador, no el LLM."
        ),
    )


# Mapa categoría -> nombre de la fuente (metadato en ChromaDB).
# 'otro' no tiene fuente interna: se responde sin RAG o se deriva.
CATEGORIA_A_FUENTE = {
    Categoria.rrhh: "rrhh",
    Categoria.desarrollo: "desarrollo",
    Categoria.actas: "actas",
    Categoria.marca: "marca",
}
