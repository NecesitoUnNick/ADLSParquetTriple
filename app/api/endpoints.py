"""
Endpoints de la API para FastParquetFilterAPI.

Este módulo define las rutas para las comprobaciones de estado y el filtrado de datos.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas import (
    FilterResponse,
    HealthCheck,
    MovimientoAction0Filter,
    MovimientoAction1Filter,
    MovimientoAction2Filter,
)
from app.services.filter_service import FilterService

api_router = APIRouter()


# --- Dependencia ---


def get_filter_service(request: Request) -> FilterService:
    """
    Una dependencia de FastAPI para recuperar la instancia compartida de FilterService.
    """
    return request.app.state.filter_service


# --- Endpoints de la API ---


@api_router.get(
    "/health",
    response_model=HealthCheck,
    tags=["Monitoreo"],
    summary="Realiza una comprobación de estado",
    description="Devuelve un estado 200 OK si el servicio está activo y en funcionamiento.",
)
async def health_check():
    """Endpoint para verificar que el servicio está en funcionamiento."""
    return HealthCheck(status="ok")


@api_router.post(
    "/query/movimientoaction0",
    response_model=FilterResponse,
    tags=["Filtrado de Datos"],
    summary="Filtra el conjunto de datos 'movimientoaction0'.",
)
async def query_movimientoaction0(
    filters: MovimientoAction0Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filtra el conjunto de datos 'api_movimientoaction0.parquet' según criterios específicos.
    """
    try:
        result_data = service.filter_movimientoaction0(filters)
        return FilterResponse(
            query=filters.model_dump(),
            row_count=len(result_data),
            data=result_data,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error interno: {e}")


@api_router.post(
    "/query/movimientoaction1",
    response_model=FilterResponse,
    tags=["Filtrado de Datos"],
    summary="Filtra el conjunto de datos 'movimientoaction1'.",
)
async def query_movimientoaction1(
    filters: MovimientoAction1Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filtra el conjunto de datos 'api_movimientoaction1.parquet' según criterios específicos.
    """
    try:
        result_data = service.filter_movimientoaction1(filters)
        return FilterResponse(
            query=filters.model_dump(),
            row_count=len(result_data),
            data=result_data,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error interno: {e}")


@api_router.post(
    "/query/movimientoaction2",
    response_model=FilterResponse,
    tags=["Filtrado de Datos"],
    summary="Filtra el conjunto de datos 'movimientoaction2'.",
)
async def query_movimientoaction2(
    filters: MovimientoAction2Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filtra el conjunto de datos 'api_movimientoaction2.parquet' según criterios específicos.
    """
    try:
        result_data = service.filter_movimientoaction2(filters)
        return FilterResponse(
            query=filters.model_dump(),
            row_count=len(result_data),
            data=result_data,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error interno: {e}")
