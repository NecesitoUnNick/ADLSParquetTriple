"""
Pydantic models for the API request and response bodies.

These models define the data structures and provide automatic validation
for the API endpoints. They are used by FastAPI to serialize response data
and to generate the OpenAPI schema.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class HealthCheck(BaseModel):
    """
    Response model for the health check endpoint.
    """
    status: str = Field(
        default="ok",
        json_schema_extra={"example": "ok"},
        description="The operational status of the service."
    )


class FilterResponse(BaseModel):
    """
    Standard response model for all data filtering endpoints.

    This provides a consistent structure for returning filtered data,
    including metadata about the query and the result set.
    """
    # Pydantic v2 uses model_config instead of a nested Config class
    model_config = ConfigDict(from_attributes=True)

    query: Dict[str, Any] = Field(
        ...,
        json_schema_extra={"example": {"categoria": "A", "valor_min": 100}},
        description="The filter parameters used for the query."
    )
    row_count: int = Field(
        ...,
        json_schema_extra={"example": 42},
        description="The number of rows returned in the result."
    )
    data: List[Dict[str, Any]] = Field(
        ...,
        json_schema_extra={"example": [
            {"categoria": "A", "valor": 150, "id": "xyz"},
            {"categoria": "A", "valor": 200, "id": "abc"}
        ]},
        description="The list of records matching the filter criteria."
    )
