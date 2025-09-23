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

    Esta clase carga la configuración desde un archivo .env y la valida.
    La autenticación con Azure se realiza exclusivamente mediante una cadena de conexión.

    Atributos:
        AZURE_STORAGE_CONNECTION_STRING (str): La cadena de conexión para la
            cuenta de Azure Storage. Es obligatoria.
        AZURE_BLOB_CONTAINER_NAME (str): El nombre del contenedor en Azure Blob
            Storage donde se encuentran los archivos Parquet.
        AZURE_DATALAKE_FILESYSTEM_NAME (str): El nombre del sistema de archivos en Azure
            Data Lake Storage Gen2 donde se escribirán los registros.
        LOG_FILE_PATH_TEMPLATE (str): Una cadena de plantilla para la ruta del archivo de registro en
            el Data Lake, con marcadores de posición para partes de la fecha.
    """
    # --- Configuración de Azure Storage ---
    AZURE_STORAGE_CONNECTION_STRING: str
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

    # Configura Pydantic para cargar desde un archivo .env e ignorar variables extra
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Crea una única instancia reutilizable de la configuración.
# Esta instancia será importada por otros módulos.
settings = Settings()
