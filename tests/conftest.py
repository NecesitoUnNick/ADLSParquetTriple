"""
Configuration and fixtures for the pytest test suite.

This file is automatically discovered by pytest. It defines session-wide
fixtures and hooks to set up the test environment before any tests run.
"""

import os

def pytest_configure(config):
    """
    Hook that runs before test collection.

    This sets mock environment variables to ensure the app's settings module
    can be imported without validation errors during test discovery, which
    happens before any fixtures are set up.
    """
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=https;AccountName=mock;AccountKey=mock;EndpointSuffix=core.windows.net'
    os.environ['AZURE_BLOB_CONTAINER_NAME'] = 'test-parquets'
    os.environ['AZURE_DATALAKE_FILESYSTEM_NAME'] = 'test-logs'
    os.environ['PARQUET_FILE_NAMES'] = '["dataset1.parquet"]'
