import asyncio
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.database.connection import check_database_connection


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """
    Test GET /api/v1/health
    Must return 200 OK with expected JSON structure:
    {
      "status": "healthy",
      "application": "FLOWSTATE",
      "version": "1.0.0"
    }
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "healthy",
        "application": "FLOWSTATE",
        "version": "1.0.0",
    }


@pytest.mark.asyncio
async def test_health_ready_unconfigured_contract(async_client: AsyncClient):
    """
    Test GET /api/v1/health/ready when database is unconfigured.
    Should accurately report not_ready and unconfigured without pretending to be connected.
    """
    with patch(
        "app.routes.health.check_database_connection",
        return_value=(False, "unconfigured", "Database URL is not configured. Backend foundation is operational."),
    ):
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "unconfigured"
        assert "not configured" in data["details"].lower()


@pytest.mark.asyncio
async def test_health_ready_connected_contract(async_client: AsyncClient):
    """
    Test GET /api/v1/health/ready when database connection succeeds.
    """
    with patch(
        "app.routes.health.check_database_connection",
        return_value=(True, "connected", "Database connection verified successfully (SELECT 1 succeeded)."),
    ):
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_ready_disconnected_contract(async_client: AsyncClient):
    """
    Test GET /api/v1/health/ready when database connection fails.
    """
    with patch(
        "app.routes.health.check_database_connection",
        return_value=(False, "disconnected", "Database connection could not be established."),
    ):
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"


@pytest.mark.asyncio
async def test_health_ready_live_probe(async_client: AsyncClient):
    """
    Test live GET /api/v1/health/ready against current environment configuration.
    Validates that the live endpoint never pretends to be connected unless SELECT 1 passes.
    """
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "not_ready"]
    assert data["database"] in ["connected", "disconnected", "unconfigured"]
    if data["status"] == "ready":
        assert data["database"] == "connected"
    else:
        assert data["database"] in ["disconnected", "unconfigured"]


@pytest.mark.asyncio
async def test_check_database_connection_timeout():
    """
    Test that check_database_connection handles timeouts safely without crashing.
    """
    mock_engine = MagicMock()
    mock_connect = MagicMock()

    async def slow_connect():
        await asyncio.sleep(0.5)

    mock_connect.__aenter__ = AsyncMock(side_effect=slow_connect)
    mock_connect.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect = MagicMock(return_value=mock_connect)

    with patch("app.database.connection.engine", mock_engine), patch.object(
        settings, "DATABASE_URL", "postgresql+asyncpg://mock:mock@localhost:5432/db"
    ):
        is_connected, status_str, details = await check_database_connection(timeout_seconds=0.05)
        assert is_connected is False
        assert status_str == "disconnected"
        assert "timed out" in details.lower()


@pytest.mark.asyncio
async def test_cors_headers(async_client: AsyncClient):
    """
    Test CORS configuration permits frontend origin http://localhost:3000.
    """
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = await async_client.options("/api/v1/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_openapi_schema(async_client: AsyncClient):
    """
    Test OpenAPI specification is accessible under /api/v1/openapi.json
    and docs are accessible at /docs.
    """
    docs_resp = await async_client.get("/docs")
    assert docs_resp.status_code == 200

    schema_resp = await async_client.get("/api/v1/openapi.json")
    assert schema_resp.status_code == 200
    schema = schema_resp.json()
    assert schema["info"]["title"] == "FLOWSTATE API"
    assert schema["info"]["version"] == "1.0.0"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]


@pytest.mark.asyncio
async def test_not_found_exception_handling(async_client: AsyncClient):
    """
    Test centralized exception handling for non-existent routes (404).
    """
    response = await async_client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
