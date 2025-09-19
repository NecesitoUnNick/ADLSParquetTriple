"""
Configuration module for the FastParquetFilterAPI.

This module uses pydantic-settings to load and validate configuration
from environment variables and a .env file.
"""

from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Manages application configuration using environment variables.

    This class loads settings from a .env file and validates them,
    ensuring that a valid Azure authentication method is provided.

    Attributes:
        AZURE_STORAGE_CONNECTION_STRING (Optional[str]): The connection string for the
            Azure Storage Account. Preferred for simplicity.
        AZURE_STORAGE_ACCOUNT_NAME (Optional[str]): The name of the storage account.
            Used for service principal authentication.
        AZURE_TENANT_ID (Optional[str]): The Azure Active Directory tenant ID.
        AZURE_CLIENT_ID (Optional[str]): The client ID of the service principal.
        AZURE_CLIENT_SECRET (Optional[str]): The client secret of the service principal.
        AZURE_BLOB_CONTAINER_NAME (str): The name of the container in Azure Blob
            Storage where the Parquet files are located.
        AZURE_DATALAKE_FILESYSTEM_NAME (str): The name of the file system in Azure
            Data Lake Storage Gen2 where logs will be written.
        PARQUET_FILE_NAMES (List[str]): A list of the Parquet file names to be
            loaded at startup.
        LOG_FILE_PATH_TEMPLATE (str): A template string for the log file path in
            the Data Lake, with placeholders for date parts.
    """
    # --- Azure Storage General Configuration ---
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None

    # --- Container and File System Names ---
    AZURE_BLOB_CONTAINER_NAME: str
    AZURE_DATALAKE_FILESYSTEM_NAME: str

    # --- Data and Logging Configuration ---
    PARQUET_FILE_NAMES: List[str]
    LOG_FILE_PATH_TEMPLATE: str = "fast-parquet-api/{year}/{month}/{day}/log.jsonl"

    @model_validator(mode='after')
    def _check_azure_auth_method(self) -> 'Settings':
        """
        Validates that exactly one Azure authentication method is configured.

        Raises:
            ValueError: If both or neither authentication methods are configured.
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
                "Ambiguous configuration: Both AZURE_STORAGE_CONNECTION_STRING and "
                "service principal credentials are provided. Please use only one."
            )

        if not using_connection_string and not using_service_principal:
            raise ValueError(
                "Missing configuration: Please provide either AZURE_STORAGE_CONNECTION_STRING or "
                "all service principal credentials (AZURE_STORAGE_ACCOUNT_NAME, "
                "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)."
            )
        return self

    # Configure Pydantic to load from a .env file and ignore extra vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create a single, reusable instance of the settings.
# This instance will be imported by other modules.
settings = Settings()
