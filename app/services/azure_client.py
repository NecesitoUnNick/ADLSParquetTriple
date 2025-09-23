"""
Cliente asíncrono para interactuar con Azure Blob Storage.

Este módulo proporciona una gestión centralizada del ciclo de vida para el cliente
de Blob Storage, asegurando que se inicialice al inicio de la aplicación y se
cierre de forma segura al apagarse. Esto previene errores de 'Conexión cerrada'
bajo cargas concurrentes al reutilizar una única sesión de transporte.
La autenticación se realiza exclusivamente mediante la cadena de conexión.
"""
import logging
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Instancia de Cliente Gestionada Globalmente ---
_blob_service_client: Optional[BlobServiceClient] = None


async def initialize_azure_clients():
    """
    Inicializa el BlobServiceClient asíncrono usando la cadena de conexión
    al inicio de la aplicación. Esto abre la sesión de transporte que será
    reutilizada en toda la aplicación.
    """
    global _blob_service_client
    logger.info("Inicializando cliente de Azure Blob Storage...")

    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING no está configurada.")

    _blob_service_client = BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING
    )

    # Entra en el contexto del gestor para abrir la sesión de red
    await _blob_service_client.__aenter__()
    logger.info("Cliente de Azure Blob Storage inicializado y listo.")


async def close_azure_clients():
    """
    Cierra de forma segura el BlobServiceClient durante el apagado de la aplicación.
    """
    global _blob_service_client
    logger.info("Cerrando cliente de Azure Blob Storage...")
    if _blob_service_client:
        await _blob_service_client.__aexit__(None, None, None)
    logger.info("Cliente de Azure Blob Storage cerrado de forma segura.")


def get_blob_service_client() -> BlobServiceClient:
    """
    Devuelve la instancia global inicializada de BlobServiceClient.

    Raises:
        RuntimeError: Si el cliente no ha sido inicializado.
    """
    if not _blob_service_client:
        raise RuntimeError("El BlobServiceClient no ha sido inicializado. "
                           "Asegúrate de que se llame a `initialize_azure_clients` "
                           "al inicio de la aplicación.")
    return _blob_service_client


async def download_parquet_file_async(file_name: str) -> bytes:
    """
    Descarga un archivo Parquet específico desde Azure Blob Storage.
    Utiliza el cliente de servicio gestionado globalmente.

    Args:
        file_name: El nombre del archivo a descargar.

    Returns:
        Los bytes del archivo descargado.

    Raises:
        FileNotFoundError: Si el archivo no se encuentra en el contenedor.
        RuntimeError: Si el cliente de blob no está inicializado.
    """
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(settings.AZURE_BLOB_CONTAINER_NAME)
    try:
        blob_client = container_client.get_blob_client(file_name)
        download_stream = await blob_client.download_blob()
        data = await download_stream.readall()
        return data
    except ResourceNotFoundError:
        logger.error(f"El archivo Parquet '{file_name}' no se encontró en el contenedor "
                     f"'{settings.AZURE_BLOB_CONTAINER_NAME}'.")
        raise FileNotFoundError(
            f"El archivo Parquet '{file_name}' no se encontró en el contenedor "
            f"'{settings.AZURE_BLOB_CONTAINER_NAME}'."
        )
