"""
Service for loading datasets from Azure into memory at application startup.
"""

import asyncio
import io
import logging
from typing import Dict, Tuple

import polars as pl

from app.core.config import settings
from app.services.azure_client import download_parquet_file_async

logger = logging.getLogger(__name__)


async def _download_and_load_one_parquet(file_name: str) -> Tuple[str, pl.DataFrame]:
    """
    Downloads a single Parquet file from Azure and loads it into a Polars DataFrame.

    This is a helper coroutine for `load_datasets_into_memory`.

    Args:
        file_name: The name of the Parquet file to process.

    Returns:
        A tuple containing the dataset key (file name without extension) and the
        loaded Polars DataFrame.

    Raises:
        FileNotFoundError: If the file is not found in Azure Blob Storage.
        Exception: For any other errors during download or parsing.
    """
    logger.info(f"Starting download of '{file_name}'...")
    try:
        parquet_bytes = await download_parquet_file_async(file_name)
        # Use io.BytesIO to treat the byte content as a file for Polars
        dataframe = pl.read_parquet(io.BytesIO(parquet_bytes))

        # Use the file name without the .parquet extension as the key
        dataset_key = file_name.removesuffix(".parquet")
        logger.info(
            f"Successfully downloaded and loaded '{file_name}' into memory. "
            f"Shape: {dataframe.shape}"
        )
        return dataset_key, dataframe
    except FileNotFoundError:
        logger.critical(
            f"Dataset '{file_name}' not found. Application may not function correctly."
        )
        raise
    except Exception as e:
        logger.critical(f"Failed to load dataset '{file_name}': {e}", exc_info=True)
        raise


async def load_datasets_into_memory() -> Dict[str, pl.DataFrame]:
    """
    Concurrently downloads all specified Parquet files from Azure Blob Storage
    and loads them into a dictionary of Polars DataFrames.

    This function is intended to be called once at application startup.

    Returns:
        A dictionary where keys are dataset names (e.g., 'dataset1') and
        values are the corresponding Polars DataFrames.

    Raises:
        Exception: If any of the datasets fail to load, the exception is
                   propagated to halt application startup.
    """
    file_names = settings.PARQUET_FILE_NAMES
    logger.info(f"Starting data loading process for files: {file_names}")

    tasks = [_download_and_load_one_parquet(file_name) for file_name in file_names]

    # asyncio.gather runs all download/load tasks concurrently.
    # If any task raises an exception, gather will propagate it immediately.
    try:
        results = await asyncio.gather(*tasks)

        dataframes = {key: df for key, df in results}

        if len(dataframes) != len(file_names):
            logger.warning("Mismatch in loaded dataframes and requested file names.")

        logger.info(f"Successfully loaded {len(dataframes)} dataset(s) into memory.")
        return dataframes
    except Exception as e:
        logger.critical(
            f"A critical error occurred during dataset loading: {e}. "
            "Application startup will be aborted."
        )
        # Re-raise the exception to stop the FastAPI startup process.
        raise
