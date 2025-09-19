"""
API endpoints for the FastParquetFilterAPI.

This module defines the routes for health checks and data filtering.
"""

import time

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request)

from app.api.schemas import FilterResponse, HealthCheck
from app.core.logging import queue_log_message
from app.services.filter_service import FilterService

api_router = APIRouter()


# --- Dependency ---

def get_filter_service(request: Request) -> FilterService:
    """
    A FastAPI dependency to retrieve the shared FilterService instance.

    The FilterService is initialized at application startup and stored in the
    app's state. This dependency makes it available to endpoint functions.

    Args:
        request: The incoming request object.

    Returns:
        The singleton FilterService instance.
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


@api_router.get(
    "/filter/{dataset_name}",
    response_model=FilterResponse,
    tags=["Data Filtering"],
    summary="Filters a specified dataset by dynamic query parameters",
    description="""
    Filters records from the specified dataset based on query parameters.

    **Filtering Conventions:**
    - **Exact match:** `?column_name=value`
    - **Range queries:** `?column_name_min=value` (for >=) and `?column_name_max=value` (for <=)

    Example: `/api/v1/filter/dataset1?categoria=A&valor_min=100`
    """,
)
async def filter_data(
    dataset_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    service: FilterService = Depends(get_filter_service),
):
    """
    Filters a dataset by dynamic query parameters, logs the request, and returns the result.

    Args:
        dataset_name: The name of the dataset to filter (e.g., 'dataset1').
        request: The incoming request object, used to access client IP and query params.
        background_tasks: FastAPI mechanism for running tasks after responding.
        service: The injected FilterService instance.

    Returns:
        A FilterResponse object containing the query, row count, and data.
    """
    start_time = time.perf_counter()

    if dataset_name not in service.dataframes:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_name}' not found. Available: {list(service.dataframes.keys())}"
        )

    filters = dict(request.query_params)

    try:
        result_data, was_cached = service.filter_dataframe(dataset_name, filters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

    processing_time_ms = (time.perf_counter() - start_time) * 1000

    response = FilterResponse(
        query=filters,
        row_count=len(result_data),
        data=result_data
    )

    # Queue the log message to be written asynchronously in the background.
    log_summary = {
        "row_count": response.row_count,
        "cache_status": "hit" if was_cached else "miss"
    }
    background_tasks.add_task(
        queue_log_message,
        client_ip=request.client.host if request.client else "unknown",
        request_path=request.url.path,
        request_params=filters,
        response_payload_summary=log_summary,
        processing_time_ms=processing_time_ms,
    )

    return response
