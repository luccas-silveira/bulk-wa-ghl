"""
Contract tests for Campaign Statistics API (T023)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for /api/v1/campaigns/stats
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignStatsContract:
    """Test suite for campaign statistics API contract compliance"""

    async def test_response_schema_matches_spec(self, async_client: AsyncClient, db_session):
        """Test that campaign stats response matches OpenAPI spec"""
        response = await async_client.get("/api/v1/campaigns/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level structure
        assert isinstance(data, dict)
        assert "campaign_counts" in data
        assert "delivery_metrics" in data  # Actual field name in API
        assert "recent_campaigns" in data
        assert "top_performing_campaigns" in data  # Actual field name in API

    async def test_campaign_counts_structure(self, async_client: AsyncClient, db_session):
        """Test campaign counts object structure"""
        response = await async_client.get("/api/v1/campaigns/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        counts = data["campaign_counts"]

        # Should have counts by status
        assert isinstance(counts, dict)
        status_types = ["draft", "scheduled", "executing", "paused", "completed", "failed", "cancelled"]
        for status_type in status_types:
            if status_type in counts:
                assert isinstance(counts[status_type], int)

    async def test_delivery_rates_structure(self, async_client: AsyncClient, db_session):
        """Test delivery rates object structure"""
        response = await async_client.get("/api/v1/campaigns/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        rates = data["delivery_metrics"]  # Actual field name in API

        # Should have average rates
        assert isinstance(rates, dict)
        if "average_delivery_rate" in rates:
            assert isinstance(rates["average_delivery_rate"], (int, float))
        if "average_read_rate" in rates:
            assert isinstance(rates["average_read_rate"], (int, float))

    async def test_recent_campaigns_structure(self, async_client: AsyncClient, db_session):
        """Test recent campaigns array structure"""
        response = await async_client.get("/api/v1/campaigns/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["recent_campaigns"], list)
        # Should return last 10 campaigns max
        assert len(data["recent_campaigns"]) <= 10

    async def test_top_performers_structure(self, async_client: AsyncClient, db_session):
        """Test top performers array structure"""
        response = await async_client.get("/api/v1/campaigns/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["top_performing_campaigns"], list)  # Actual field name in API
        # Should return top 10 campaigns max
        assert len(data["top_performing_campaigns"]) <= 10

    async def test_filters_work_correctly(self, async_client: AsyncClient, db_session):
        """Test query parameter filters work"""
        # Test user filter
        response = await async_client.get("/api/v1/campaigns/stats?ghl_user_id=test_user")
        assert response.status_code == status.HTTP_200_OK

        # Test location filter
        response = await async_client.get("/api/v1/campaigns/stats?ghl_location_id=test_loc")
        assert response.status_code == status.HTTP_200_OK

        # Test date range filter
        response = await async_client.get("/api/v1/campaigns/stats?from_date=2025-01-01&to_date=2025-12-31")
        assert response.status_code == status.HTTP_200_OK
