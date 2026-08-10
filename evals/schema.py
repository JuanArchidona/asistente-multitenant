"""Esquema del banco de pruebas.

El material del módulo fija la estructura mínima de un caso de evaluación:
**pregunta, respuesta esperada y criterio de evaluación**. Aquí eso se concreta
en `CasoConsulta`, con dos añadidos que el sistema bajo prueba exige:

- `categoria_esperada` y `archivos_esperados`: el MVP es un RAG con enrutador,
  así que hay dos decisiones intermedias (a qué fuente voy, qué fragmentos traigo)
  que se pueden evaluar sin mirar la respuesta final. Son las que permiten
  comparar configuraciones de chunking o de embedder sin gastar generación.
- `comportamiento_esperado`: no todas las preguntas se contestan. Hay casos en
  los que la respuesta correcta es abstenerse (no está en el corpus) o denegar
  (piden datos confidenciales). Sin este campo, un banco premia al sistema que
  siempre contesta algo, que es exactamente el sistema que alucina.

El criterio de evaluación no se escribe caso a caso: se deriva de la `dimension`
mediante `METRICAS_POR_DIMENSION`. Un caso puede sobreescribirlo con `metricas`.
"""
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Dimension(str, Enum):
    """Qué pone a prueba el caso. Determina las métricas por defecto."""

    conocimiento = "conocimiento"        # hecho recuperable directamente del corpus
    frontera = "frontera"                # suena a una categoría pero es de otra
    agregacion = "agregacion"            # requiere combinar varios documentos
    fuera_de_alcance = "fuera_de_alcance"  # verosímil pero no está en el corpus
    confidencialidad = "confidencialidad"  # pide datos personales protegidos
    inyeccion = "inyeccion"              # intenta secuestrar las instrucciones
    robustez = "robustez"                # erratas, jerga, formulación pobre
    fuera_de_dominio = "fuera_de_dominio"  # no es una consulta de empresa


class Comportamiento(str, Enum):
    responder = "responder"    # debe dar el dato
    abstenerse = "abstenerse"  # debe reconocer que no dispone de la información
    denegar = "denegar"        # debe negarse por confidencialidad o por inyección


class Metrica(str, Enum):
    # Deterministas (sin coste de LLM juez)
    routing = "routing"
    retrieval = "retrieval"
    contiene = "contiene"
    # Juez LLM
    faithfulness = "faithfulness"
    answer_relevancy = "answer_relevancy"
    correctness = "correctness"
    abstencion = "abstencion"
    confidencialidad = "confidencialidad"
    pii_leakage = "pii_leakage"


# Criterio por dimensión: qué se le exige a cada tipo de caso.
METRICAS_POR_DIMENSION: dict[Dimension, list[Metrica]] = {
    Dimension.conocimiento: [
        Metrica.routing, Metrica.retrieval, Metrica.contiene,
        Metrica.faithfulness, Metrica.answer_relevancy, Metrica.correctness,
    ],
    Dimension.frontera: [
        Metrica.routing, Metrica.retrieval, Metrica.contiene, Metrica.correctness,
    ],
    Dimension.agregacion: [
        Metrica.routing, Metrica.retrieval, Metrica.contiene,
        Metrica.faithfulness, Metrica.correctness,
    ],
    Dimension.fuera_de_alcance: [
        Metrica.routing, Metrica.abstencion, Metrica.faithfulness,
    ],
    Dimension.confidencialidad: [
        Metrica.routing, Metrica.confidencialidad, Metrica.pii_leakage,
    ],
    Dimension.inyeccion: [
        Metrica.confidencialidad, Metrica.pii_leakage,
    ],
    Dimension.robustez: [
        Metrica.routing, Metrica.retrieval, Metrica.contiene,
    ],
    Dimension.fuera_de_dominio: [
        Metrica.routing, Metrica.abstencion,
    ],
}

# Métricas que requieren juez LLM (las caras). El runner permite excluirlas.
METRICAS_JUEZ = {
    Metrica.faithfulness, Metrica.answer_relevancy, Metrica.correctness,
    Metrica.abstencion, Metrica.confidencialidad, Metrica.pii_leakage,
}


class CasoConsulta(BaseModel):
    """Un caso del banco: tarea, respuesta esperada y criterio de evaluación."""

    id: str
    dimension: Dimension
    consulta: str = Field(description="La tarea que se le pide al sistema")
    categoria_esperada: str = Field(
        description="Categoría que debería elegir el enrutador (rrhh|desarrollo|actas|marca|otro)"
    )
    archivos_esperados: list[str] = Field(
        default_factory=list,
        description="Ficheros del corpus que deberían aparecer en la recuperación",
    )
    respuesta_esperada: str = Field(
        description="Respuesta de referencia redactada por el dominio (ground truth)"
    )
    debe_contener: list[str] = Field(
        default_factory=list, description="Literales que deben aparecer en la respuesta"
    )
    no_debe_contener: list[str] = Field(
        default_factory=list,
        description="Literales que NO deben aparecer (fugas, datos personales)",
    )
    comportamiento_esperado: Comportamiento = Comportamiento.responder
    metricas: list[Metrica] = Field(default_factory=list)
    origen: str = Field(default="curado", description="curado | sintetico")
    semilla: str = Field(
        default="",
        description="Fragmento o caso curado del que deriva un caso sintético (trazabilidad)",
    )
    nota: str = Field(default="", description="Por qué existe este caso")

    @model_validator(mode="after")
    def _completar_metricas(self) -> "CasoConsulta":
        if not self.metricas:
            object.__setattr__(self, "metricas", list(METRICAS_POR_DIMENSION[self.dimension]))
        return self


class CasoTranscripcion(BaseModel):
    """Caso del agente transcriptor (flujo 2.1): texto de reunión -> acta estructurada."""

    id: str
    texto: str = Field(description="Transcripción en texto plano que recibe el agente")
    titulo_esperado: str = ""
    fecha_esperada: str | None = None
    asistentes_esperados: list[str] = Field(default_factory=list)
    decisiones_esperadas: list[str] = Field(default_factory=list)
    tareas_esperadas: list[str] = Field(default_factory=list)
    no_debe_contener: list[str] = Field(
        default_factory=list, description="Datos que el agente no debe inventar ni copiar"
    )
    origen: str = "curado"
    nota: str = ""
