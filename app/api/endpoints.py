"""
API endpoints for the FastParquetFilterAPI.

This module defines the routes for health checks and data filtering.
"""

import time
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


# --- Dependency ---

def get_filter_service(request: Request) -> FilterService:
    """
    A FastAPI dependency to retrieve the shared FilterService instance.
    """
    return request.app.state.filter_service


# --- API Endpoints ---

@api_router.get(
    "/health",
    response_model=HealthCheck,
    tags=["Monitoring"],
    summary="Performs a Health Check",
    description="Returns a 200 OK status if the service is active and running.",
)
async def health_check():
    """Endpoint to verify that the service is running."""
    return HealthCheck(status="ok")


@api_router.post(
    "/query/movimientoaction0",
    response_model=FilterResponse,
    tags=["Data Filtering"],
    summary="Filters the 'movimientoaction0' dataset.",
)
async def query_movimientoaction0(
    filters: MovimientoAction0Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filters the 'api_movimientoaction0.parquet' dataset based on specific criteria.
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
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


@api_router.post(
    "/query/movimientoaction1",
    response_model=FilterResponse,
    tags=["Data Filtering"],
    summary="Filters the 'movimientoaction1' dataset.",
)
async def query_movimientoaction1(
    filters: MovimientoAction1Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filters the 'api_movimientoaction1.parquet' dataset based on specific criteria.
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
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


@api_router.post(
    "/query/movimientoaction2",
    response_model=FilterResponse,
    tags=["Data Filtering"],
    summary="Filters the 'movimientoaction2' dataset.",
)
async def query_movimientoaction2(
    filters: MovimientoAction2Filter,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filters the 'api_movimientoaction2.parquet' dataset based on specific criteria.
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
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
