"""
Contract tests for Campaign Logs API (T021)
Tests response schema against OpenAPI specification
Following TDD: These tests define the contract for /api/v1/campaigns/{id}/logs
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCampaignLogsContract:
    """Test suite for campaign logs API contract compliance"""

    async def test_response_schema_matches_spec(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test that campaign logs response matches OpenAPI spec"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level structure
        assert isinstance(data, dict)
        assert "logs" in data
        assert "count" in data
        assert "limit" in data
        assert "offset" in data

        # Verify types
        assert isinstance(data["logs"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)

    async def test_log_message_structure(self, async_client: AsyncClient, db_session, sample_campaign_with_messages):
        """Test log message object structure"""
        campaign_id = sample_campaign_with_messages.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["logs"]) > 0:
            log = data["logs"][0]

            # Required fields
            required_fields = [
                "id", "recipient_phone", "content", "status"
            ]
            for field in required_fields:
                assert field in log

    async def test_filters_work_correctly(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test query parameter filters work"""
        campaign_id = sample_campaign.id

        # Test status filter
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs?status=sent")
        assert response.status_code == status.HTTP_200_OK

        # Test recipient filter
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs?recipient=%2B5511999999999")
        assert response.status_code == status.HTTP_200_OK

    async def test_pagination_parameters(self, async_client: AsyncClient, db_session, sample_campaign):
        """Test pagination works correctly"""
        campaign_id = sample_campaign.id
        response = await async_client.get(f"/api/v1/campaigns/{campaign_id}/logs?limit=50&offset=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["logs"]) <= 50

    async def test_nonexistent_campaign_returns_404(self, async_client: AsyncClient, db_session):
        """Test logs for non-existent campaign returns 404"""
        response = await async_client.get("/api/v1/campaigns/99999/logs")
        assert response.status_code == status.HTTP_404_NOT_FOUND
