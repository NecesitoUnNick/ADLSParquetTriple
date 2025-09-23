"""
Modelos Pydantic para los cuerpos de solicitud y respuesta de la API.

Estos modelos definen las estructuras de datos y proporcionan validación automática
para los endpoints de la API. Son utilizados por FastAPI para serializar los datos de respuesta
y para generar el esquema OpenAPI.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class HealthCheck(BaseModel):
    """
    Modelo de respuesta para el endpoint de comprobación de estado.
    """

    status: str = Field(
        default="ok",
        json_schema_extra={"example": "ok"},
        description="El estado operativo del servicio.",
    )


class FilterResponse(BaseModel):
    """
    Modelo de respuesta estándar para todos los endpoints de filtrado de datos.

    Proporciona una estructura consistente para devolver datos filtrados,
    incluyendo metadatos sobre la consulta y el conjunto de resultados.
    """

    # Pydantic v2 usa model_config en lugar de una clase Config anidada
    model_config = ConfigDict(from_attributes=True)

    query: Dict[str, Any] = Field(
        ...,
        json_schema_extra={"example": {"categoria": "A", "valor_min": 100}},
        description="Los parámetros de filtro utilizados para la consulta.",
    )
    row_count: int = Field(..., json_schema_extra={"example": 42}, description="El número de filas devueltas en el resultado.")
    data: List[Dict[str, Any]] = Field(
        ...,
        json_schema_extra=[
            {"categoria": "A", "valor": 150, "id": "xyz"},
            {"categoria": "A", "valor": 200, "id": "abc"},
        ],
        description="La lista de registros que coinciden con los criterios de filtro.",
    )


# --- Modelos de Solicitud para Endpoints Específicos ---


class MovimientoAction0Filter(BaseModel):
    """Cuerpo de la solicitud para el endpoint /query/movimientoaction0."""

    OrdenanteId: str
    TipoIdOrdenante: str
    Product: str
    EffectiveDateStart: str
    EffectiveDateEnd: str
    Reference: str


class MovimientoAction1Filter(BaseModel):
    """Cuerpo de la solicitud para el endpoint /query/movimientoaction1."""

    OrdenanteId: str
    TipoIdOrdenante: str
    Product: str
    EffectiveDateStart: str
    EffectiveDateEnd: str


class MovimientoAction2Filter(BaseModel):
    """Cuerpo de la solicitud para el endpoint /query/movimientoaction2."""

    OrdenanteId: str
    TipoIdOrdenante: str
    Product: str
    EventNum: str
    Reference: str
