"""
Unit and integration tests for the API endpoints.

This test suite uses pytest and httpx to test the FastAPI application
asynchronously. It mocks external services like Azure interactions to ensure
tests are fast, isolated, and don't require real credentials.
"""

import pytest
import pytest_asyncio
import polars as pl
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.filter_service import FilterService

# Mark all tests in this module as asyncio tests
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def sample_dataframes() -> dict[str, pl.DataFrame]:
    """
    Provides sample Polars DataFrames for testing.
    This fixture is session-scoped as the data is read-only.
    """
    # Data for movimientoaction0
    df0 = pl.DataFrame({
        "OrdenanteId": ["900707908", "900707908", "12345"],
        "TipoIdOrdenante": ["N", "N", "N"],
        "Product": ["FCO", "FCO", "FCO"],
        "EffectiveDateStr": ["2024-12-05", "2024-12-15", "2024-12-20"],
        "Reference": ["301000315559", "other", "301000315559"],
        "EventNum": ["1", "2", "3"]
    }).sort(["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr", "Reference"])

    # Data for movimientoaction1
    df1 = pl.DataFrame({
        "OrdenanteId": ["900859943", "900859943", "12345"],
        "TipoIdOrdenante": ["N", "N", "N"],
        "Product": ["FCO", "FCO", "OTHER"],
        "EffectiveDateStr": ["2025-03-02", "2025-03-08", "2025-03-09"],
    }).sort(["OrdenanteId", "TipoIdOrdenante", "Product", "EffectiveDateStr"])

    # Data for movimientoaction2
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
    Provides a fully configured asynchronous test client.
    """
    # Mock external I/O calls
    mocker.patch(
        "app.services.data_loader.load_datasets_into_memory",
        return_value=sample_dataframes
    )
    # Manually initialize the service and set the app state for tests
    app.state.filter_service = FilterService(sample_dataframes)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # Clean up state after test to ensure isolation
    delattr(app.state, "filter_service")


async def test_health_check(client: AsyncClient):
    """Tests the /health endpoint for a 200 OK response."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Tests for /query/movimientoaction0 ---

async def test_query_movimientoaction0_success(client: AsyncClient):
    """Tests a successful filter on the movimientoaction0 endpoint."""
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
    """Tests a filter that returns no results on movimientoaction0."""
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


# --- Tests for /query/movimientoaction1 ---

async def test_query_movimientoaction1_success(client: AsyncClient):
    """Tests a successful filter on the movimientoaction1 endpoint."""
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
    """Tests a filter with a date range that matches no data on movimientoaction1."""
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


# --- Tests for /query/movimientoaction2 ---

async def test_query_movimientoaction2_success(client: AsyncClient):
    """Tests a successful filter on the movimientoaction2 endpoint."""
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
    """Tests sending an incomplete payload to an endpoint."""
    payload = {
        "OrdenanteId": "900707908"
        # Missing other required fields
    }
    response = await client.post("/api/v1/query/movimientoaction2", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
    assert "field required" in response.text.lower()
