"""
Cliente asíncrono para interactuar con los servicios de Azure Storage.

Este módulo proporciona funciones para conectarse a Azure Blob Storage para leer
archivos Parquet y a Azure Data Lake Storage Gen2 para escribir registros.
Utiliza un patrón de fábrica con caché para reutilizar los clientes de servicio y
las credenciales, mejorando el rendimiento y la gestión de recursos.
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
    Obtiene la credencial de Azure apropiada según la configuración.
    Usa una cadena de conexión si está disponible, de lo contrario, DefaultAzureCredential.
    Esta función se almacena en caché para evitar volver a crear el objeto de credencial.

    Returns:
        La credencial de Azure configurada.
    """
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        return settings.AZURE_STORAGE_CONNECTION_STRING
    # DefaultAzureCredential usará variables de entorno para el principal de servicio
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def get_blob_service_client() -> BlobServiceClient:
    """
    Crea y devuelve una única instancia en caché de BlobServiceClient.

    Returns:
        Una instancia asíncrona de BlobServiceClient.
    """
    credential = _get_credential()
    if isinstance(credential, str):
        return BlobServiceClient.from_connection_string(credential)

    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=credential)


@lru_cache(maxsize=1)
def get_datalake_service_client() -> DataLakeServiceClient:
    """
    Crea y devuelve una única instancia en caché de DataLakeServiceClient.

    Returns:
        Una instancia asíncrona de DataLakeServiceClient.
    """
    credential = _get_credential()
    if isinstance(credential, str):
        return DataLakeServiceClient.from_connection_string(credential)

    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
    return DataLakeServiceClient(account_url=account_url, credential=credential)


async def download_parquet_file_async(file_name: str) -> bytes:
    """
    Descarga un archivo Parquet específico desde Azure Blob Storage.

    Args:
        file_name: El nombre del blob (archivo) a descargar.

    Returns:
        El contenido del archivo como bytes.

    Raises:
        FileNotFoundError: Si el archivo especificado no existe en el contenedor.
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
                f"El archivo Parquet '{file_name}' no se encontró en el contenedor "
                f"'{settings.AZURE_BLOB_CONTAINER_NAME}'."
            )


async def write_log_async(file_path: str, log_data: bytes):
    """
    Añade una entrada de registro a un archivo en Azure Data Lake Storage.

    Esta función maneja la creación del archivo si no existe y añade los datos
    de forma atómica. Sin embargo, para prevenir condiciones de carrera de múltiples
    escritores concurrentes (ej., en un entorno escalado horizontalmente), esta función
    debería ser llamada desde un contexto serializado, como una única tarea trabajadora
    en segundo plano.

    Args:
        file_path: La ruta completa al archivo de registro en el Data Lake.
        log_data: Los datos de registro a añadir, codificados como bytes.
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
