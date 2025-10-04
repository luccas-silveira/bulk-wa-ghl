"""
Contract tests for Campaign Pause API (T019)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for PATCH /api/v1/campaigns/{id}/pause
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignPauseContract:
    """Test suite for campaign pause API contract compliance"""

    async def test_pause_executing_campaign_success(self, async_client: AsyncClient, db_session, executing_campaign):
        """Test pausing executing campaign returns correct response"""
        campaign_id = executing_campaign.id
        response = await async_client.patch(f"/api/v1/campaigns/{campaign_id}/pause")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Response structure
        assert isinstance(data, dict)
        assert "message" in data
        assert "campaign" in data

        # Campaign should now be paused
        campaign = data["campaign"]
        assert campaign["status"] == "paused"
        assert "paused_at" in campaign

    async def test_pause_non_executing_campaign_fails(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test pausing non-executing campaign returns 400"""
        campaign_id = sample_campaign.id
        response = await async_client.patch(f"/api/v1/campaigns/{campaign_id}/pause")

        # Should return 400 for invalid status
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_pause_nonexistent_campaign_returns_404(self, async_client: AsyncClient, db_session):
        """Test pausing non-existent campaign returns 404"""
        response = await async_client.patch("/api/v1/campaigns/99999/pause")
        assert response.status_code == status.HTTP_404_NOT_FOUND
