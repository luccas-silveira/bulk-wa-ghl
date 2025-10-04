"""
Contract tests for Campaign Resume API (T020)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for PATCH /api/v1/campaigns/{id}/resume
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignResumeContract:
    """Test suite for campaign resume API contract compliance"""

    async def test_resume_paused_campaign_success(self, async_client: AsyncClient, db_session, paused_campaign):
        """Test resuming paused campaign returns correct response"""
        campaign_id = paused_campaign.id
        response = await async_client.patch(f"/api/v1/campaigns/{campaign_id}/resume")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Response structure
        assert isinstance(data, dict)
        assert "message" in data
        assert "campaign" in data

        # Campaign should now be completed (current limitation)
        campaign = data["campaign"]
        assert campaign["status"] == "completed"

    async def test_resume_non_paused_campaign_fails(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test resuming non-paused campaign returns 400"""
        campaign_id = sample_campaign.id
        response = await async_client.patch(f"/api/v1/campaigns/{campaign_id}/resume")

        # Should return 400 for invalid status
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_resume_nonexistent_campaign_returns_404(self, async_client: AsyncClient, db_session):
        """Test resuming non-existent campaign returns 404"""
        response = await async_client.patch("/api/v1/campaigns/99999/resume")
        assert response.status_code == status.HTTP_404_NOT_FOUND
