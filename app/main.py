"""
Main application entrypoint for the FastParquetFilterAPI.

This file creates the FastAPI application instance, sets up lifecycle events
for startup and shutdown, and includes the API routers.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.endpoints import api_router
from app.core.config import settings
from app.core.logging import start_log_worker, stop_log_worker
from app.services.data_loader import load_datasets_into_memory
from app.services.filter_service import FilterService

# Configure logging for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application lifecycle events using the modern lifespan protocol.
    - On startup: Starts the log worker, loads data, and initializes services.
    - On shutdown: Gracefully stops the log worker.
    """
    logger.info("Application startup commencing...")
    start_log_worker()

    try:
        dataframes = await load_datasets_into_memory()
        app.state.filter_service = FilterService(dataframes)
        logger.info("Filter service initialized successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize application during startup: {e}", exc_info=True)
        await stop_log_worker()
        raise

    logger.info("Application startup complete.")

    yield

    logger.info("Application shutdown commencing...")
    await stop_log_worker()
    logger.info("Application shutdown complete.")


# Create the FastAPI app instance with the lifespan handler and metadata
app = FastAPI(
    title="FastParquetFilterAPI",
    description="A high-speed microservice for filtering Parquet data from Azure.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)


# --- Include API Routers ---

# This makes all endpoints from app/api/endpoints.py available under the /api/v1 prefix.
app.include_router(api_router, prefix="/api/v1")


# --- Root Endpoint ---

@app.get("/", tags=["Root"])
async def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the FastParquetFilterAPI. See docs at /api/docs"}
