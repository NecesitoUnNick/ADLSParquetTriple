"""
Pruebas unitarias y de integración para los endpoints de la API.

Esta suite de pruebas utiliza pytest y httpx para probar la aplicación FastAPI
de forma asíncrona. Simula servicios externos como las interacciones con Azure
para garantizar que las pruebas sean rápidas, aisladas y no requieran
credenciales reales.
"""

import pytest
import pytest_asyncio
import polars as pl
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.filter_service import FilterService

# Marca todas las pruebas en este módulo como pruebas asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def sample_dataframes() -> dict[str, pl.DataFrame]:
    """
    Proporciona DataFrames de Polars de muestra para las pruebas.
    Esta fixture tiene un alcance de sesión ya que los datos son de solo lectura.
    """
    # Datos para movimientoaction0
    df0 = pl.DataFrame({
        "OrdenanteId": ["900707908", "900707908", "12345"],
        "TipoIdOrdenante": ["N", "N", "N"],
        "Product": ["FCO", "FCO", "FCO"],
        "EffectiveDateStr": ["2024-12-05", "2024-12-15", "2024-12-20"],
        "Reference": ["301000315559", "other", "301000315559"],
        "EventNum": ["1", "2", "3"]
    }).sort(["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr", "Reference"])

    # Datos para movimientoaction1
    df1 = pl.DataFrame({
        "OrdenanteId": ["900859943", "900859943", "12345"],
        "TipoIdOrdenante": ["N", "N", "N"],
        "Product": ["FCO", "FCO", "OTHER"],
        "EffectiveDateStr": ["2025-03-02", "2025-03-08", "2025-03-09"],
    }).sort(["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr"])

    # Datos para movimientoaction2
    df2 = pl.DataFrame({
        "OrdenanteId": ["900707908", "900707908", "900707908"],
        "TipoIdOrdenante": ["N", "N", "C"],
        "Product": ["FCO", "FCO", "FCO"],
        "EventNum": ["3327598", "12345", "3327598"],
        "Reference": ["301000307726", "301000307726", "other"],
    }).sort(["OrdenanteId", "TipoIdOrdenante", "Product", "EventNum", "Reference"])

    return {
        "api_movimientoaction0": df0,
        "api_movimientoaction1": df1,
        "api_movimientoaction2": df2,
    }


@pytest_asyncio.fixture
async def client(mocker, sample_dataframes) -> AsyncClient:
    """
    Proporciona un cliente de prueba asíncrono completamente configurado.
    """
    # Simula las llamadas de E/S externas
    mocker.patch(
        "app.services.data_loader.load_datasets_into_memory",
        return_value=sample_dataframes
    )
    # Inicializa manualmente el servicio y establece el estado de la aplicación para las pruebas
    app.state.filter_service = FilterService(sample_dataframes)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # Limpia el estado después de la prueba para garantizar el aislamiento
    delattr(app.state, "filter_service")


async def test_health_check(client: AsyncClient):
    """Prueba el endpoint /health para una respuesta 200 OK."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Pruebas para /query/movimientoaction0 ---

async def test_query_movimientoaction0_success(client: AsyncClient):
    """Prueba un filtro exitoso en el endpoint movimientoaction0."""
    payload = {
        "OrdenanteId": "900707908",
        "TipoIdOrdenante": "N",
        "Product": "FCO",
        "EffectiveDateStart": "2024-12-02",
        "EffectiveDateEnd": "2024-12-31",
        "Reference": "301000315559"
    }
    response = await client.post("/api/v1/query/movimientoaction0", json=payload)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 1
    assert len(json_response["data"]) == 1
    assert json_response["data"][0]["Reference"] == "301000315559"
    assert json_response["data"][0]["EffectiveDateStr"] == "2024-12-05"


async def test_query_movimientoaction0_not_found(client: AsyncClient):
    """Prueba un filtro que no devuelve resultados en movimientoaction0."""
    payload = {
        "OrdenanteId": "900707908",
        "TipoIdOrdenante": "N",
        "Product": "FCO",
        "EffectiveDateStart": "2024-12-02",
        "EffectiveDateEnd": "2024-12-31",
        "Reference": "non_existent_ref"
    }
    response = await client.post("/api/v1/query/movimientoaction0", json=payload)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 0
    assert len(json_response["data"]) == 0


# --- Pruebas para /query/movimientoaction1 ---

async def test_query_movimientoaction1_success(client: AsyncClient):
    """Prueba un filtro exitoso en el endpoint movimientoaction1."""
    payload = {
        "OrdenanteId": "900859943",
        "TipoIdOrdenante": "N",
        "Product": "FCO",
        "EffectiveDateStart": "2025-03-01",
        "EffectiveDateEnd": "2025-03-10"
    }
    response = await client.post("/api/v1/query/movimientoaction1", json=payload)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 2
    assert len(json_response["data"]) == 2


async def test_query_movimientoaction1_bad_date_range(client: AsyncClient):
    """Prueba un filtro con un rango de fechas que no coincide con ningún dato en movimientoaction1."""
    payload = {
        "OrdenanteId": "900859943",
        "TipoIdOrdenante": "N",
        "Product": "FCO",
        "EffectiveDateStart": "2026-01-01",
        "EffectiveDateEnd": "2026-01-31"
    }
    response = await client.post("/api/v1/query/movimientoaction1", json=payload)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 0


# --- Pruebas para /query/movimientoaction2 ---

async def test_query_movimientoaction2_success(client: AsyncClient):
    """Prueba un filtro exitoso en el endpoint movimientoaction2."""
    payload = {
        "OrdenanteId": "900707908",
        "TipoIdOrdenante": "N",
        "Product": "FCO",
        "EventNum": "3327598",
        "Reference": "301000307726"
    }
    response = await client.post("/api/v1/query/movimientoaction2", json=payload)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 1
    assert len(json_response["data"]) == 1
    assert json_response["data"][0]["EventNum"] == "3327598"


async def test_query_invalid_body(client: AsyncClient):
    """Prueba el envío de un payload incompleto a un endpoint."""
    payload = {
        "OrdenanteId": "900707908"
        # Faltan otros campos requeridos
    }
    response = await client.post("/api/v1/query/movimientoaction2", json=payload)
    assert response.status_code == 422  # Entidad no procesable
    assert "field required" in response.text.lower()
