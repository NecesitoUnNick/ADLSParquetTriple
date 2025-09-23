"""
Módulo de configuración para FastParquetFilterAPI.

Este módulo utiliza pydantic-settings para cargar y validar la configuración
desde variables de entorno y un archivo .env.
"""

from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Gestiona la configuración de la aplicación mediante variables de entorno.

    Esta clase carga la configuración desde un archivo .env y la valida,
    asegurando que se proporcione un método de autenticación de Azure válido.

    Atributos:
        AZURE_STORAGE_CONNECTION_STRING (Optional[str]): La cadena de conexión para la
            cuenta de Azure Storage. Preferido por simplicidad.
        AZURE_STORAGE_ACCOUNT_NAME (Optional[str]): El nombre de la cuenta de almacenamiento.
            Utilizado para la autenticación con principal de servicio.
        AZURE_TENANT_ID (Optional[str]): El ID del inquilino de Azure Active Directory.
        AZURE_CLIENT_ID (Optional[str]): El ID de cliente del principal de servicio.
        AZURE_CLIENT_SECRET (Optional[str]): El secreto de cliente del principal de servicio.
        AZURE_BLOB_CONTAINER_NAME (str): El nombre del contenedor en Azure Blob
            Storage donde se encuentran los archivos Parquet.
        AZURE_DATALAKE_FILESYSTEM_NAME (str): El nombre del sistema de archivos en Azure
            Data Lake Storage Gen2 donde se escribirán los registros.
        LOG_FILE_PATH_TEMPLATE (str): Una cadena de plantilla para la ruta del archivo de registro en
            el Data Lake, con marcadores de posición para partes de la fecha.
    """
    # --- Configuración General de Azure Storage ---
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None

    # --- Nombres de Contenedores y Sistemas de Archivos ---
    AZURE_BLOB_CONTAINER_NAME: str
    AZURE_DATALAKE_FILESYSTEM_NAME: str

    # --- Configuración de Datos y Logging ---
    PARQUET_FILE_NAME_0: Optional[str] = None
    PARQUET_FILE_NAME_1: Optional[str] = None
    PARQUET_FILE_NAME_2: Optional[str] = None
    LOG_FILE_PATH_TEMPLATE: str = "/Raw/DataEngineering/FiduX/LogsParquets/{year}/{month}/{day}/log.jsonl"

    parquet_files: List[str] = []

    @model_validator(mode='after')
    def _assemble_parquet_files(self) -> 'Settings':
        """
        Construye una lista de nombres de archivos Parquet que no son None.
        """
        self.parquet_files = [
            name
            for name in [
                self.PARQUET_FILE_NAME_0,
                self.PARQUET_FILE_NAME_1,
                self.PARQUET_FILE_NAME_2,
            ]
            if name is not None
        ]
        return self

    @model_validator(mode='after')
    def _check_azure_auth_method(self) -> 'Settings':
        """
        Valida que se haya configurado exactamente un método de autenticación de Azure.

        Raises:
            ValueError: Si ambos o ninguno de los métodos de autenticación están configurados.
        """
        sp_auth_vars = [
            self.AZURE_STORAGE_ACCOUNT_NAME,
            self.AZURE_TENANT_ID,
            self.AZURE_CLIENT_ID,
            self.AZURE_CLIENT_SECRET,
        ]

        using_connection_string = self.AZURE_STORAGE_CONNECTION_STRING is not None
        using_service_principal = all(v is not None for v in sp_auth_vars)

        if using_connection_string and using_service_principal:
            raise ValueError(
                "Configuración ambigua: Se proporcionaron tanto AZURE_STORAGE_CONNECTION_STRING como "
                "las credenciales del principal de servicio. Por favor, use solo uno."
            )

        if not using_connection_string and not using_service_principal:
            raise ValueError(
                "Configuración faltante: Proporcione AZURE_STORAGE_CONNECTION_STRING o "
                "todas las credenciales del principal de servicio (AZURE_STORAGE_ACCOUNT_NAME, "
                "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)."
            )
        return self

    # Configura Pydantic para cargar desde un archivo .env e ignorar variables extra
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Crea una única instancia reutilizable de la configuración.
# Esta instancia será importada por otros módulos.
settings = Settings()
