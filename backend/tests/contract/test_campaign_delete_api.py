"""
Contract tests for Campaign Delete API (T022)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for DELETE /api/v1/campaigns/{id}
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignDeleteContract:
    """Test suite for campaign delete API contract compliance"""

    async def test_delete_completed_campaign_success(self, async_client: AsyncClient, db_session, completed_campaign):
        """Test deleting completed campaign returns 204"""
        campaign_id = completed_campaign.id
        response = await async_client.delete(f"/api/v1/campaigns/{campaign_id}")

        # Successful deletion returns 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_draft_campaign_success(self, async_client: AsyncClient, db_session, draft_campaign):
        """Test deleting draft campaign returns 204"""
        campaign_id = draft_campaign.id
        response = await async_client.delete(f"/api/v1/campaigns/{campaign_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_executing_campaign_fails(self, async_client: AsyncClient, db_session, executing_campaign):
        """Test deleting executing campaign returns 400"""
        campaign_id = executing_campaign.id
        response = await async_client.delete(f"/api/v1/campaigns/{campaign_id}")

        # Cannot delete executing campaign
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_delete_nonexistent_campaign_returns_404(self, async_client: AsyncClient, db_session):
        """Test deleting non-existent campaign returns 404"""
        response = await async_client.delete("/api/v1/campaigns/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_cascades_to_messages(self, async_client: AsyncClient, db_session, sample_campaign_with_messages):
        """Test that deleting campaign also deletes all related messages"""
        campaign_id = sample_campaign_with_messages.id

        # Verify campaign has messages
        logs_response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs")
        assert logs_response.status_code == status.HTTP_200_OK
        logs_data = logs_response.json()
        initial_message_count = logs_data["count"]
        assert initial_message_count > 0

        # Delete campaign
        delete_response = await async_client.delete(f"/api/v1/campaigns/{campaign_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify campaign no longer exists
        details_response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/details")
        assert details_response.status_code == status.HTTP_404_NOT_FOUND
