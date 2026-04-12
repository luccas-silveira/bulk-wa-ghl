"""
Contract tests for /health endpoint.
TDD: these tests MUST FAIL before the implementation in Task 11 Step 2.
Following the pattern of tests/contract/test_dashboard_contract.py.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestHealthContract:
    """Contract tests for the /health endpoint."""

    async def test_healthy_response_schema(self, async_client: AsyncClient, db_session):
        """GET /health returns 200 with the correct JSON schema when DB is reachable."""
        response = await async_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Required top-level keys
        assert "status" in data, "Missing 'status' field"
        assert "database" in data, "Missing 'database' field"
        assert "service" in data, "Missing 'service' field"
        assert "timestamp" in data, "Missing 'timestamp' field"
        assert "ghl_enabled" in data, "Missing 'ghl_enabled' field"

        # Type assertions
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert isinstance(data["service"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["ghl_enabled"], bool)

    async def test_ghl_enabled_reflects_config(self, async_client: AsyncClient, db_session):
        """ghl_enabled in /health response matches runtime GHL_ENABLED config value."""
        from src.config import GHL_ENABLED

        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["ghl_enabled"] == GHL_ENABLED, (
            f"Expected ghl_enabled={GHL_ENABLED} (from config), got {data['ghl_enabled']}"
        )

    async def test_unhealthy_response_on_db_failure(self, async_client: AsyncClient):
        """GET /health returns 503 when DB is unreachable."""
        from unittest.mock import MagicMock, AsyncMock
        from sqlalchemy.exc import OperationalError

        # Simulate DB failure by making execute() raise OperationalError
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=OperationalError(
            "connection refused", params=None, orig=None
        ))

        from src.database import get_db
        from src.main import app

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            response = await async_client.get("/health")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "error" in data
