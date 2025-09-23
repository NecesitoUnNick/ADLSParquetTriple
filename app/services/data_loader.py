"""
Servicio para cargar conjuntos de datos desde Azure a la memoria en el inicio de la aplicación.
"""

import asyncio
import io
import logging
import os
from typing import Dict, Tuple

import polars as pl

from app.core.config import settings
from app.services.azure_client import download_parquet_file_async

logger = logging.getLogger(__name__)


# Un mapeo de nombres de archivo a las columnas por las que deben ordenarse para optimización.
SORT_KEY_MAP = {
    "api_movimientoaction0.parquet": [
        "OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr", "Reference"
    ],
    "api_movimientoaction1.parquet": [
        "OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr"
    ],
    "api_movimientoaction2.parquet": [
        "OrdenanteId", "TipoIdOrdenante", "Product", "EventNum", "Reference"
    ],
}


async def _download_and_load_one_parquet(file_name: str) -> Tuple[str, pl.DataFrame]:
    """
    Descarga un único archivo Parquet desde Azure, lo carga en un DataFrame de Polars,
    y lo pre-ordena para optimización de consultas.

    Args:
        file_name: El nombre del archivo Parquet a procesar.

    Returns:
        Una tupla que contiene la clave del conjunto de datos y el DataFrame cargado y ordenado.

    Raises:
        FileNotFoundError: Si no se encuentra el archivo en Azure Blob Storage.
        Exception: Para otros errores durante la descarga o el procesamiento.
    """
    logger.info(f"Iniciando descarga de '{file_name}'...")
    try:
        parquet_bytes = await download_parquet_file_async(file_name)
        dataframe = pl.read_parquet(io.BytesIO(parquet_bytes))

        # Extrae solo el nombre del archivo para usarlo como clave y para la búsqueda de ordenación
        base_file_name = os.path.basename(file_name)
        dataset_key = base_file_name.removesuffix(".parquet")

        logger.info(f"'{file_name}' cargado exitosamente. Shape: {dataframe.shape}. Pre-ordenando...")

        # Pre-ordena el DataFrame para rendimiento si se define una clave de ordenación
        if base_file_name in SORT_KEY_MAP:
            sort_columns = SORT_KEY_MAP[base_file_name]
            # Asegura que todas las columnas de ordenación existan en el DataFrame antes de ordenar
            missing_cols = [col for col in sort_columns if col not in dataframe.columns]
            if not missing_cols:
                dataframe = dataframe.sort(sort_columns)
                logger.info(f"DataFrame '{dataset_key}' ordenado por {sort_columns}.")
            else:
                logger.warning(
                    f"No se puede ordenar '{dataset_key}': Faltan columnas {missing_cols}. "
                    "Continuando con datos sin ordenar."
                )
        else:
            logger.info(f"No se ha definido una clave de pre-ordenación para '{base_file_name}'.")

        logger.info(f"Procesamiento de '{dataset_key}' finalizado.")
        return dataset_key, dataframe
    except FileNotFoundError:
        logger.critical(f"No se encontró el conjunto de datos '{file_name}'. La aplicación podría no funcionar correctamente.")
        raise
    except Exception as e:
        logger.critical(f"Fallo al cargar el conjunto de datos '{file_name}': {e}", exc_info=True)
        raise


async def load_datasets_into_memory() -> Dict[str, pl.DataFrame]:
    """
    Descarga concurrentemente todos los archivos Parquet especificados desde Azure Blob Storage
    y los carga en un diccionario de DataFrames de Polars.

    Esta función está destinada a ser llamada una vez en el inicio de la aplicación.

    Returns:
        Un diccionario donde las claves son nombres de conjuntos de datos (ej., 'dataset1') y
        los valores son los correspondientes DataFrames de Polars.

    Raises:
        Exception: Si alguno de los conjuntos de datos falla al cargar, la excepción se
                   propaga para detener el inicio de la aplicación.
    """
    file_names = settings.parquet_files
    logger.info(f"Iniciando proceso de carga de datos para los archivos: {file_names}")

    tasks = [_download_and_load_one_parquet(file_name) for file_name in file_names]

    # asyncio.gather ejecuta todas las tareas de descarga/carga concurrentemente.
    # Si alguna tarea lanza una excepción, gather la propagará inmediatamente.
    try:
        results = await asyncio.gather(*tasks)

        dataframes = {key: df for key, df in results}

        if len(dataframes) != len(file_names):
            logger.warning("Discrepancia entre los dataframes cargados y los nombres de archivo solicitados.")

        logger.info(f"{len(dataframes)} conjunto(s) de datos cargado(s) exitosamente en memoria.")
        return dataframes
    except Exception as e:
        logger.critical(
            f"Ocurrió un error crítico durante la carga del conjunto de datos: {e}. "
            "El inicio de la aplicación será abortado."
        )
        # Re-lanza la excepción para detener el proceso de inicio de FastAPI.
        raise


