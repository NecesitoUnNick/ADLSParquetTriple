"""
Cliente asíncrono para interactuar con los servicios de Azure Storage.

Este módulo proporciona una gestión centralizada del ciclo de vida para los clientes de
servicios de Azure, asegurando que se inicialicen al inicio de la aplicación y se
cierren de forma segura al apagarse. Esto previene errores de 'Conexión cerrada'
bajo cargas concurrentes al reutilizar una única sesión de transporte.
"""
import logging
from typing import Optional, Union

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.filedatalake.aio import DataLakeServiceClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Instancias de Cliente Gestionadas Globalmente ---
_blob_service_client: Optional[BlobServiceClient] = None
_datalake_service_client: Optional[DataLakeServiceClient] = None


def _get_credential() -> Union[str, DefaultAzureCredential]:
    """
    Obtiene la credencial de Azure apropiada según la configuración.
    Usa una cadena de conexión si está disponible, de lo contrario, DefaultAzureCredential.
    """
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        return settings.AZURE_STORAGE_CONNECTION_STRING
    return DefaultAzureCredential()


async def initialize_azure_clients():
    """
    Inicializa los clientes de servicio de Azure asíncronos al inicio de la aplicación.
    Esto abre las sesiones de transporte que serán reutilizadas en toda la aplicación.
    """
    global _blob_service_client, _datalake_service_client
    logger.info("Inicializando clientes de Azure...")

    credential = _get_credential()
    if isinstance(credential, str):
        # Usar cadena de conexión
        blob_account_url = None
        datalake_account_url = None
        _blob_service_client = BlobServiceClient.from_connection_string(credential)
        _datalake_service_client = DataLakeServiceClient.from_connection_string(credential)
    else:
        # Usar DefaultAzureCredential
        blob_account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        datalake_account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
        _blob_service_client = BlobServiceClient(account_url=blob_account_url, credential=credential)
        _datalake_service_client = DataLakeServiceClient(account_url=datalake_account_url, credential=credential)

    # Entra en el contexto del gestor para abrir la sesión de red
    await _blob_service_client.__aenter__()
    await _datalake_service_client.__aenter__()
    logger.info("Clientes de Azure inicializados y listos.")


async def close_azure_clients():
    """
    Cierra de forma segura los clientes de servicio de Azure durante el apagado de la aplicación.
    """
    global _blob_service_client, _datalake_service_client
    logger.info("Cerrando clientes de Azure...")
    if _blob_service_client:
        await _blob_service_client.__aexit__(None, None, None)
    if _datalake_service_client:
        await _datalake_service_client.__aexit__(None, None, None)
    logger.info("Clientes de Azure cerrados de forma segura.")


def get_blob_service_client() -> BlobServiceClient:
    """
    Devuelve la instancia global inicializada de BlobServiceClient.
    """
    if not _blob_service_client:
        raise RuntimeError("El BlobServiceClient no ha sido inicializado.")
    return _blob_service_client


def get_datalake_service_client() -> DataLakeServiceClient:
    """
    Devuelve la instancia global inicializada de DataLakeServiceClient.
    """
    if not _datalake_service_client:
        raise RuntimeError("El DataLakeServiceClient no ha sido inicializado.")
    return _datalake_service_client


async def download_parquet_file_async(file_name: str) -> bytes:
    """
    Descarga un archivo Parquet específico desde Azure Blob Storage.
    Utiliza el cliente de servicio gestionado globalmente.
    """
    blob_service_client = get_blob_service_client()
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
    Utiliza el cliente de servicio gestionado globalmente.
    """
    datalake_service_client = get_datalake_service_client()
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
