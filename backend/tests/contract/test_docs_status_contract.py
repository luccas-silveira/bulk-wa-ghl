"""
Contract tests for /docs-status endpoint.
Verifies that the endpoint reflects the actual GHL_ENABLED runtime config.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDocsStatusContract:

    async def test_returns_200_with_required_keys(self, async_client: AsyncClient, db_session):
        response = await async_client.get("/docs-status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "endpoints" in data
        assert "ghl_enabled" in data
        assert isinstance(data["endpoints"], list)
        assert isinstance(data["ghl_enabled"], bool)

    async def test_ghl_endpoints_match_ghl_enabled(self, async_client: AsyncClient, db_session):
        from src.config import GHL_ENABLED
        response = await async_client.get("/docs-status")
        assert response.status_code == 200
        data = response.json()
        ghl_endpoints = [e for e in data["endpoints"] if "/ghl/" in e]
        if GHL_ENABLED:
            assert len(ghl_endpoints) > 0, "GHL_ENABLED=True but no GHL endpoints listed"
        else:
            assert len(ghl_endpoints) == 0, f"GHL_ENABLED=False but found GHL endpoints: {ghl_endpoints}"

    async def test_always_includes_core_endpoints(self, async_client: AsyncClient, db_session):
        response = await async_client.get("/docs-status")
        data = response.json()
        endpoints_str = " ".join(data["endpoints"])
        assert "/api/v1/campaigns" in endpoints_str
        assert "/health" in endpoints_str
