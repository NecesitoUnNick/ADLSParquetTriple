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
from app.api import endpoints as api_endpoints_module

# Mark all tests in this module as asyncio tests
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def sample_dataframes() -> dict[str, pl.DataFrame]:
    """
    Provides sample Polars DataFrames for testing.
    This fixture is session-scoped as the data is read-only.
    """
    df1 = pl.DataFrame({
        "categoria": ["A", "B", "A", "C", "B"],
        "valor": [10, 25, 30, 40, 50],
        "flag": [True, False, True, False, True]
    })
    return {"dataset1": df1}


@pytest_asyncio.fixture
async def client(mocker, sample_dataframes) -> AsyncClient:
    """
    Provides a fully configured asynchronous test client.

    This fixture handles mocking of external services and directly injects
    the necessary state into the app object. This is a robust way to
    bypass potential test-runner-specific issues with lifespan events
    and ensure the app state is ready for testing.
    """
    # Mock external I/O calls
    mocker.patch(
        "app.services.data_loader.load_datasets_into_memory",
        return_value=sample_dataframes
    )
    mocker.patch("app.api.endpoints.queue_log_message")

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


async def test_filter_no_params(client: AsyncClient):
    """Tests a successful filter request with no query parameters."""
    response = await client.get("/api/v1/filter/dataset1")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 5
    assert len(json_response["data"]) == 5
    assert json_response["query"] == {}


async def test_filter_with_params(client: AsyncClient):
    """Tests a successful filter request with valid query parameters."""
    response = await client.get("/api/v1/filter/dataset1?categoria=A&valor_min=20")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["row_count"] == 1
    assert len(json_response["data"]) == 1
    assert json_response["data"][0]["categoria"] == "A"
    assert json_response["data"][0]["valor"] == 30
    assert json_response["query"] == {"categoria": "A", "valor_min": "20"}


async def test_filter_caching(mocker, client: AsyncClient):
    """
    Tests that the in-memory cache is being used correctly.
    It spies on the internal filter method to check call counts.
    """
    # The service is on app.state, we can spy on its instance methods
    apply_filters_spy = mocker.spy(app.state.filter_service, "_apply_filters")

    # First call - should be a cache miss, so the method is called
    res1 = await client.get("/api/v1/filter/dataset1?categoria=B")
    assert res1.status_code == 200
    assert res1.json()["row_count"] == 2
    assert apply_filters_spy.call_count == 1

    # Second, identical call - should be a cache hit, method is NOT called again
    res2 = await client.get("/api/v1/filter/dataset1?categoria=B")
    assert res2.status_code == 200
    assert res2.json()["row_count"] == 2
    assert apply_filters_spy.call_count == 1

    # Third call with different params - should be a miss again
    res3 = await client.get("/api/v1/filter/dataset1?flag=True")
    assert res3.status_code == 200
    assert res3.json()["row_count"] == 3
    assert apply_filters_spy.call_count == 2


async def test_filter_dataset_not_found(client: AsyncClient):
    """Tests that a 404 is returned for a non-existent dataset."""
    response = await client.get("/api/v1/filter/unknown_dataset")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_filter_invalid_column(client: AsyncClient):
    """Tests that a 400 is returned for a filter on a non-existent column."""
    response = await client.get("/api/v1/filter/dataset1?bad_column=123")
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


async def test_filter_invalid_value_type(client: AsyncClient):
    """Tests that a 400 is returned for a filter with an uncastable value."""
    response = await client.get("/api/v1/filter/dataset1?valor_min=abc")
    assert response.status_code == 400
    assert "could not cast" in response.json()["detail"]


async def test_logging_is_called(mocker, client: AsyncClient):
    """Tests that the background logging task is correctly queued."""
    log_spy = mocker.spy(api_endpoints_module, 'queue_log_message')

    await client.get("/api/v1/filter/dataset1?categoria=A")

    assert log_spy.call_count == 1
    # Check some of the arguments passed to the logger
    call_args = log_spy.call_args[1]
    assert call_args["request_path"] == "/api/v1/filter/dataset1"
    assert call_args["request_params"] == {"categoria": "A"}
    assert call_args["response_payload_summary"]["row_count"] == 2
    assert "processing_time_ms" in call_args
