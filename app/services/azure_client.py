"""
Asynchronous client for interacting with Azure Storage services.

This module provides functions to connect to Azure Blob Storage for reading
Parquet files and to Azure Data Lake Storage Gen2 for writing logs.
It uses a cached factory pattern to reuse service clients and credentials,
improving performance and resource management.
"""

from functools import lru_cache
from typing import Union

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.filedatalake.aio import DataLakeServiceClient

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_credential() -> Union[str, DefaultAzureCredential]:
    """
    Gets the appropriate Azure credential based on settings.
    Uses a connection string if available, otherwise DefaultAzureCredential.
    This function is cached to avoid re-creating the credential object.

    Returns:
        The configured Azure credential.
    """
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        return settings.AZURE_STORAGE_CONNECTION_STRING
    # DefaultAzureCredential will use env vars for service principal
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def get_blob_service_client() -> BlobServiceClient:
    """
    Creates and returns a single, cached instance of BlobServiceClient.

    Returns:
        An asynchronous BlobServiceClient instance.
    """
    credential = _get_credential()
    if isinstance(credential, str):
        return BlobServiceClient.from_connection_string(credential)

    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=credential)


@lru_cache(maxsize=1)
def get_datalake_service_client() -> DataLakeServiceClient:
    """
    Creates and returns a single, cached instance of DataLakeServiceClient.

    Returns:
        An asynchronous DataLakeServiceClient instance.
    """
    credential = _get_credential()
    if isinstance(credential, str):
        return DataLakeServiceClient.from_connection_string(credential)

    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
    return DataLakeServiceClient(account_url=account_url, credential=credential)


async def download_parquet_file_async(file_name: str) -> bytes:
    """
    Downloads a specified Parquet file from Azure Blob Storage.

    Args:
        file_name: The name of the blob (file) to download.

    Returns:
        The content of the file as bytes.

    Raises:
        FileNotFoundError: If the specified file does not exist in the container.
    """
    blob_service_client = get_blob_service_client()
    async with blob_service_client:
        container_client = blob_service_client.get_container_client(settings.AZURE_BLOB_CONTAINER_NAME)
        try:
            blob_client = container_client.get_blob_client(file_name)
            download_stream = await blob_client.download_blob()
            data = await download_stream.readall()
            return data
        except ResourceNotFoundError:
            raise FileNotFoundError(
                f"Parquet file '{file_name}' not found in container "
                f"'{settings.AZURE_BLOB_CONTAINER_NAME}'."
            )


async def write_log_async(file_path: str, log_data: bytes):
    """
    Appends a log entry to a file in Azure Data Lake Storage.

    This function handles file creation if it doesn't exist and appends data
    atomically. However, to prevent race conditions from multiple concurrent
    writers (e.g., in a scaled-out environment), this function should be
    called from a serialized context, like a single background worker task.

    Args:
        file_path: The full path to the log file in the Data Lake.
        log_data: The log data to append, encoded as bytes.
    """
    datalake_service_client = get_datalake_service_client()
    async with datalake_service_client:
        file_system_client = datalake_service_client.get_file_system_client(
            settings.AZURE_DATALAKE_FILESYSTEM_NAME
        )
        file_client = file_system_client.get_file_client(file_path)

        try:
            properties = await file_client.get_properties()
            offset = properties.size
        except ResourceNotFoundError:
            await file_client.create_file()
            offset = 0

        await file_client.append_data(data=log_data, offset=offset)
        await file_client.flush_data(offset=offset + len(log_data))
