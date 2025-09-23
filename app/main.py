"""
Punto de entrada principal de la aplicación para FastParquetFilterAPI.

Este archivo crea la instancia de la aplicación FastAPI, configura los eventos del ciclo de vida
para el inicio y el apagado, e incluye los enrutadores de la API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.endpoints import api_router
from app.core.logging import start_log_worker, stop_log_worker
from app.services import azure_client
from app.services.data_loader import load_datasets_into_memory
from app.services.filter_service import FilterService

# Configura el logging para la aplicación
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona los eventos del ciclo de vida de la aplicación utilizando el protocolo lifespan moderno.
    - Al inicio: Inicia servicios (logs, clientes de Azure) y precarga los datos.
    - Al apagar: Cierra de forma segura los servicios en segundo plano.
    """
    logger.info("Iniciando la aplicación...")
    # Inicia los servicios en segundo plano primero
    start_log_worker()
    await azure_client.initialize_azure_clients()

    try:
        # Carga los datos de forma asíncrona y los almacena en el estado de la aplicación.
        preloaded_dataframes = await load_datasets_into_memory()
        app.state.filter_service = FilterService(preloaded_dataframes)
        logger.info("Servicio de filtrado inicializado con datos pre-cargados.")
    except Exception as e:
        logger.critical(f"CRÍTICO: Fallo al inicializar la aplicación durante el inicio: {e}", exc_info=True)
        # Asegura que los servicios iniciados se cierren en caso de fallo
        await azure_client.close_azure_clients()
        await stop_log_worker()
        raise

    logger.info("Inicio de la aplicación completado.")

    yield

    # --- Apagado de la aplicación ---
    logger.info("Comenzando el apagado de la aplicación...")
    await azure_client.close_azure_clients()
    await stop_log_worker()
    logger.info("Apagado de la aplicación completado.")


# Crea la instancia de la aplicación FastAPI con el manejador de ciclo de vida y metadatos
app = FastAPI(
    title="FastParquetFilterAPI",
    description="Un microservicio de alta velocidad para filtrar datos Parquet desde Azure.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)


# --- Incluir Enrutadores de la API ---

# Esto hace que todos los endpoints de app/api/endpoints.py estén disponibles bajo el prefijo /api/v1.
app.include_router(api_router, prefix="/api/v1")


# --- Endpoint Raíz ---


@app.get("/", tags=["Raíz"])
async def read_root():
    """Un endpoint raíz simple para confirmar que la API está en funcionamiento."""
    return {"message": "Bienvenido a FastParquetFilterAPI. Consulta la documentación en /api/docs"}
