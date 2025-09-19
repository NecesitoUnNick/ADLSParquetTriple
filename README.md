# FastParquetFilterAPI

## Descripción

**FastParquetFilterAPI** es un microservicio de alto rendimiento construido con Python, FastAPI y Polars. Su propósito es exponer una API RESTful para filtrar datos desde archivos Parquet alojados en Azure Blob Storage con una latencia extremadamente baja.

El servicio carga los datos en memoria al iniciar, aprovecha el motor de procesamiento ultra rápido de Polars para los filtrados y utiliza un caché en memoria para devolver resultados instantáneos en peticiones repetidas. Además, implementa un sistema de logging asíncrono a Azure Data Lake Storage Gen2.

## Requisitos Previos

- Python 3.12+
- Docker (Opcional, para ejecución en contenedores)
- Una cuenta de Azure con un Storage Account configurado.

## Configuración

La configuración del servicio se gestiona a través de variables de entorno. Cree un archivo llamado `.env` en la raíz del proyecto y añada las siguientes variables.

Puede usar un **Connection String** (más simple) o credenciales de **Service Principal** (más seguro para producción).

```dotenv
# --- Elija un método de autenticación ---

# Opción 1: Connection String (recomendado para desarrollo)
AZURE_STORAGE_CONNECTION_STRING="your_storage_account_connection_string"

# Opción 2: Service Principal (recomendado para producción)
# AZURE_STORAGE_ACCOUNT_NAME="your_storage_account_name"
# AZURE_TENANT_ID="your_tenant_id"
# AZURE_CLIENT_ID="your_client_id"
# AZURE_CLIENT_SECRET="your_client_secret"

# --- Nombres de contenedores y archivos ---

# El contenedor de Blob Storage donde se encuentran los archivos Parquet.
AZURE_BLOB_CONTAINER_NAME="parquet-data"

# El file system de Data Lake donde se guardarán los logs.
AZURE_DATALAKE_FILESYSTEM_NAME="logs"

# Una lista en formato JSON de los archivos Parquet a cargar.
PARQUET_FILE_NAMES='["dataset1.parquet", "dataset2.parquet", "dataset3.parquet"]'

# (Opcional) Plantilla para la ruta del archivo de log.
# LOG_FILE_PATH_TEMPLATE="fast-parquet-api/{year}/{month}/{day}/log.jsonl"
```

**Nota:** El servicio validará que solo uno de los dos métodos de autenticación esté completamente configurado.

## Instalación

1.  Clone el repositorio:
    ```sh
    git clone <repository_url>
    cd FastParquetFilterAPI
    ```

2.  Cree un entorno virtual e instale las dependencias:
    ```sh
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Ejecución Local

Para iniciar el servicio localmente, use `uvicorn`. El flag `--reload` recargará el servidor automáticamente al detectar cambios en el código.

```sh
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servicio estará disponible en `http://localhost:8000`.

## Ejecución con Docker

1.  Construya la imagen de Docker:
    ```sh
    docker build -t fast-parquet-filter-api .
    ```

2.  Ejecute el contenedor. El flag `--env-file .env` inyecta las variables de entorno desde su archivo `.env` local al contenedor.
    ```sh
    docker run -p 8000:8000 --env-file .env fast-parquet-filter-api
    ```
La API estará accesible en `http://localhost:8000`.

## Estructura de la API

La documentación interactiva de la API (Swagger UI) está disponible en `http://localhost:8000/api/docs`.

| Método | Ruta                                  | Parámetros de Consulta                                                              | Descripción y Ejemplo de Respuesta                                                                                                                              |
| :----- | :------------------------------------ | :---------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/health`                      | Ninguno                                                                             | Devuelve el estado de salud del servicio. <br> **Respuesta:** `{ "status": "ok" }`                                                                               |
| `GET`  | `/api/v1/filter/{dataset_name}`       | **Dinámicos**. <br> - `columna=valor` (igualdad) <br> - `columna_min=valor` (>=) <br> - `columna_max=valor` (<=) | Filtra un dataset específico. Reemplace `{dataset_name}` con uno de los configurados (ej. `dataset1`). <br> **Respuesta:** <pre>{<br>  "query": { "categoria": "A" },<br>  "row_count": 2,<br>  "data": [...]<br>}</pre> |

### Ejemplo de Petición de Filtrado

`GET http://localhost:8000/api/v1/filter/dataset1?categoria=A&valor_min=20`

Esta petición filtrará `dataset1` para obtener registros donde la columna `categoria` es igual a "A" y la columna `valor` es mayor o igual a 20.
