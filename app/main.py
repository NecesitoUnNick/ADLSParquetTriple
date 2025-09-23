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
from app.services.data_loader import load_data_synchronously
from app.services.filter_service import FilterService

# Configura el logging para la aplicación
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Carga de Datos de Manera Síncrona en el Proceso Principal ---
# Almacena los DataFrames cargados en una variable global.
# Esto asegura que los datos se carguen solo una vez cuando el módulo es importado
# por el proceso principal de Uvicorn, antes de que los workers sean bifurcados.
preloaded_dataframes = load_data_synchronously()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona los eventos del ciclo de vida de la aplicación utilizando el protocolo lifespan moderno.
    - Al inicio: Inicia el worker de logs, carga los datos e inicializa los servicios.
    - Al apagar: Detiene de forma segura el worker de logs.
    """
    logger.info("Iniciando la aplicación...")
    start_log_worker()

    try:
        # Los datos ya están cargados en la variable global `preloaded_dataframes`.
        # Simplemente inicializa el servicio con los datos pre-cargados.
        app.state.filter_service = FilterService(preloaded_dataframes)
        logger.info("Servicio de filtrado inicializado con datos pre-cargados.")
    except Exception as e:
        logger.critical(f"CRÍTICO: Fallo al inicializar la aplicación durante el inicio: {e}", exc_info=True)
        await stop_log_worker()
        raise

    logger.info("Inicio de la aplicación completado.")

    yield

    logger.info("Comenzando el apagado de la aplicación...")
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
