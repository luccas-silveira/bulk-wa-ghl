"""
Contract tests for Campaign List API (T017)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for /api/v1/campaigns
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignListContract:
    """Test suite for campaign list API contract compliance"""

    async def test_response_schema_matches_spec(self, async_client: AsyncClient, db_session):
        """Test that list campaigns response matches OpenAPI spec"""
        response = await async_client.get("/api/v1/campaigns")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level structure
        assert isinstance(data, dict)
        assert "campaigns" in data
        assert "count" in data
        assert "limit" in data
        assert "offset" in data

        # Verify types
        assert isinstance(data["campaigns"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)

    async def test_campaign_object_structure(self, async_client: AsyncClient, db_session):
        """Test campaign object contains all required fields"""
        response = await async_client.get("/api/v1/campaigns")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["campaigns"]) > 0:
            campaign = data["campaigns"][0]

            # Required fields
            required_fields = [
                "id", "name", "status", "created_at", "ghl_location_id",
                "ghl_user_id", "ghl_user_ids", "sending_speed", "schedule_type",
                "message_stats"
            ]
            for field in required_fields:
                assert field in campaign

            # Message stats structure
            stats = campaign["message_stats"]
            assert isinstance(stats, dict)
            assert "total" in stats
            assert "sent" in stats
            assert "delivered" in stats
            assert "read" in stats
            assert "failed" in stats

    async def test_filters_work_correctly(self, async_client: AsyncClient, db_session):
        """Test query parameter filters work"""
        # Test status filter
        response = await async_client.get("/api/v1/campaigns?status=completed")
        assert response.status_code == status.HTTP_200_OK

        # Test user filter
        response = await async_client.get("/api/v1/campaigns?ghl_user_id=test_user")
        assert response.status_code == status.HTTP_200_OK

        # Test location filter
        response = await async_client.get("/api/v1/campaigns?ghl_location_id=test_loc")
        assert response.status_code == status.HTTP_200_OK

    async def test_pagination_parameters(self, async_client: AsyncClient, db_session):
        """Test pagination works correctly"""
        response = await async_client.get("/api/v1/campaigns?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["campaigns"]) <= 10
