"""
Contract tests for POST /api/v1/campaigns (RAIZ-09)
Moved from legacy POST /campaigns in main.py to the /api/v1/campaigns router.
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone, timedelta


VALID_PAYLOAD = {
    "name": "Test Campaign",
    "ghl_location_id": "loc_test_123",
    "ghl_user_ids": ["user_test_001"],
    "sending_speed": "medium",
    "schedule_type": "immediate",
    "messages": [{"text": "Hello {{name}}", "media_url": None}],
    "audience_criteria": {
        "csv_data": [
            {"phone_number": "+5511999990001", "name": "Alice"},
            {"phone_number": "+5511999990002", "name": "Bob"},
        ]
    },
}


@pytest.mark.asyncio
class TestCampaignCreateContract:

    async def test_create_immediate_campaign_returns_201(
        self, async_client: AsyncClient, db_session
    ):
        response = await async_client.post("/api/v1/campaigns", json=VALID_PAYLOAD)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "id" in data
        assert data["name"] == "Test Campaign"
        assert data["status"] in ("draft", "executing")
        assert data["ghl_location_id"] == "loc_test_123"
        assert data["sending_speed"] == "medium"
        assert data["schedule_type"] == "immediate"
        assert "created_at" in data
        assert data["estimated_recipients"] == 2

    async def test_create_scheduled_campaign_returns_201(
        self, async_client: AsyncClient, db_session
    ):
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            **VALID_PAYLOAD,
            "schedule_type": "scheduled",
            "scheduled_time": future_time,
        }

        response = await async_client.post("/api/v1/campaigns", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] in ("draft", "scheduled")
        assert data["schedule_type"] == "scheduled"

    async def test_missing_required_fields_returns_422(
        self, async_client: AsyncClient, db_session
    ):
        response = await async_client.post(
            "/api/v1/campaigns",
            json={"name": "Incomplete"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_scheduled_without_time_returns_422(
        self, async_client: AsyncClient, db_session
    ):
        payload = {**VALID_PAYLOAD, "schedule_type": "scheduled", "scheduled_time": None}
        response = await async_client.post("/api/v1/campaigns", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_scheduled_time_in_past_returns_422(
        self, async_client: AsyncClient, db_session
    ):
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        payload = {
            **VALID_PAYLOAD,
            "schedule_type": "scheduled",
            "scheduled_time": past_time,
        }
        response = await async_client.post("/api/v1/campaigns", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_old_endpoint_no_longer_exists(
        self, async_client: AsyncClient, db_session
    ):
        """Legacy POST /campaigns must return 404 after RAIZ-09."""
        response = await async_client.post("/campaigns", json=VALID_PAYLOAD)
        assert response.status_code == status.HTTP_404_NOT_FOUND
