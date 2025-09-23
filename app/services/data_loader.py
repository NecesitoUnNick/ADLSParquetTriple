"""
Servicio para cargar y procesar cada conjunto de datos Parquet de forma independiente
desde Azure a la memoria al inicio de la aplicación.
"""

import asyncio
import io
import logging
import os
from typing import Dict, Optional, Tuple

import polars as pl

from app.core.config import settings
from app.services.azure_client import download_parquet_file_async

logger = logging.getLogger(__name__)


async def _load_movimientoaction0(file_name: str) -> Optional[Tuple[str, pl.DataFrame]]:
    """
    Descarga, carga y pre-ordena el archivo 'movimientoaction0'.
    """
    logger.info(f"Procesando '{file_name}'...")
    try:
        parquet_bytes = await download_parquet_file_async(file_name)
        df = pl.read_parquet(io.BytesIO(parquet_bytes))
        logger.info(f"'{file_name}' cargado. Shape: {df.shape}. Pre-ordenando...")

        sort_columns = ["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr", "Reference"]
        df = df.sort(sort_columns)
        logger.info(f"DataFrame 'api_movimientoaction0' ordenado por {sort_columns}.")
        return "api_movimientoaction0", df
    except (FileNotFoundError, Exception) as e:
        logger.critical(f"Fallo al cargar o procesar '{file_name}': {e}", exc_info=True)
        raise


async def _load_movimientoaction1(file_name: str) -> Optional[Tuple[str, pl.DataFrame]]:
    """
    Descarga, carga y pre-ordena el archivo 'movimientoaction1'.
    """
    logger.info(f"Procesando '{file_name}'...")
    try:
        parquet_bytes = await download_parquet_file_async(file_name)
        df = pl.read_parquet(io.BytesIO(parquet_bytes))
        logger.info(f"'{file_name}' cargado. Shape: {df.shape}. Pre-ordenando...")

        sort_columns = ["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr"]
        df = df.sort(sort_columns)
        logger.info(f"DataFrame 'api_movimientoaction1' ordenado por {sort_columns}.")
        return "api_movimientoaction1", df
    except (FileNotFoundError, Exception) as e:
        logger.critical(f"Fallo al cargar o procesar '{file_name}': {e}", exc_info=True)
        raise


async def _load_movimientoaction2(file_name: str) -> Optional[Tuple[str, pl.DataFrame]]:
    """
    Descarga, carga y pre-ordena el archivo 'movimientoaction2'.
    """
    logger.info(f"Procesando '{file_name}'...")
    try:
        parquet_bytes = await download_parquet_file_async(file_name)
        df = pl.read_parquet(io.BytesIO(parquet_bytes))
        logger.info(f"'{file_name}' cargado. Shape: {df.shape}. Pre-ordenando...")

        sort_columns = ["OrdenanteId", "TipoIdOrdenante", "Product", "EventNum", "Reference"]
        df = df.sort(sort_columns)
        logger.info(f"DataFrame 'api_movimientoaction2' ordenado por {sort_columns}.")
        return "api_movimientoaction2", df
    except (FileNotFoundError, Exception) as e:
        logger.critical(f"Fallo al cargar o procesar '{file_name}': {e}", exc_info=True)
        raise


async def load_datasets_into_memory() -> Dict[str, pl.DataFrame]:
    """
    Descarga y carga de forma concurrente los conjuntos de datos Parquet configurados.

    Cada conjunto de datos se carga mediante una función específica que maneja su
    propia lógica de procesamiento y ordenación.
    """
    tasks = []
    file_mapping = {
        "PARQUET_FILE_NAME_0": (_load_movimientoaction0, settings.PARQUET_FILE_NAME_0),
        "PARQUET_FILE_NAME_1": (_load_movimientoaction1, settings.PARQUET_FILE_NAME_1),
        "PARQUET_FILE_NAME_2": (_load_movimientoaction2, settings.PARQUET_FILE_NAME_2),
    }

    pid = os.getpid()
    logger.info(f"[PID: {pid}] Iniciando carga de datos para los archivos: {settings.parquet_files}")

    for key, (loader_func, file_name) in file_mapping.items():
        if file_name:
            tasks.append(loader_func(file_name))

    if not tasks:
        logger.warning(f"[PID: {pid}] No se ha configurado ningún archivo Parquet para cargar.")
        return {}

    try:
        results = await asyncio.gather(*tasks)
        # Filtra cualquier resultado None que pueda ocurrir si una tarea falla y es manejada
        dataframes = {key: df for key, df in results if key and df is not None}

        logger.info(f"[PID: {pid}] {len(dataframes)} conjunto(s) de datos cargado(s) exitosamente en memoria.")
        return dataframes
    except Exception as e:
        logger.critical(
            f"[PID: {pid}] Ocurrió un error crítico durante la carga concurrente de datos: {e}. "
            "El inicio de la aplicación será abortado."
        )
        raise


