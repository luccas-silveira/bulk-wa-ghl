"""
Contract tests for Campaign Details API (T018)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for /api/v1/campaigns/{id}/details
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignDetailsContract:
    """Test suite for campaign details API contract compliance"""

    async def test_response_schema_matches_spec(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test that campaign details response matches OpenAPI spec"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level structure
        assert isinstance(data, dict)
        assert "campaign" in data
        assert "statistics" in data
        assert "timeline" in data
        assert "recent_messages" in data

    async def test_campaign_field_structure(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test campaign object contains all required fields"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        campaign = data["campaign"]

        # Required fields
        required_fields = [
            "id", "name", "status", "created_at", "updated_at",
            "ghl_location_id", "ghl_user_id", "sending_speed", "schedule_type"
        ]
        for field in required_fields:
            assert field in campaign

    async def test_statistics_structure(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test statistics object structure"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        stats = data["statistics"]

        # Required stats fields
        required_fields = [
            "total_messages", "sent", "delivered", "read", "failed",
            "pending", "delivery_rate", "read_rate"
        ]
        for field in required_fields:
            assert field in stats
            assert isinstance(stats[field], (int, float))

    async def test_timeline_structure(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test timeline array structure"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["timeline"], list)
        if len(data["timeline"]) > 0:
            event = data["timeline"][0]
            assert "event" in event
            assert "timestamp" in event

    async def test_recent_messages_structure(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test recent messages array structure"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["recent_messages"], list)
        # Should return last 50 messages max
        assert len(data["recent_messages"]) <= 50

    async def test_not_found_returns_404(self, async_client: AsyncClient, db_session):
        """Test that non-existent campaign returns 404"""
        response = await async_client.get("/api/v1/campaigns/99999/details")
        assert response.status_code == status.HTTP_404_NOT_FOUND
