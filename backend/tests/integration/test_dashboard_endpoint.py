"""
Integration tests for Dashboard Analytics Endpoint
Tests the /api/v1/analytics/dashboard endpoint with various filters
Following TDD: These tests MUST FAIL before implementation (T011)
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta, timezone

from src.models.campaign import Campaign
from src.models.message import Message


@pytest.mark.asyncio
class TestDashboardEndpoint:
    """Test suite for dashboard analytics endpoint"""

    async def test_dashboard_without_filters(self, async_client: AsyncClient, db_session):
        """Test GET /api/v1/analytics/dashboard without any filters"""
        # Create test campaigns
        campaign1 = Campaign(
            name="Campaign 1",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc)
        )
        campaign2 = Campaign(
            name="Campaign 2",
            status="executing",
            ghl_location_id="loc_test456",
            ghl_user_id="user_456",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(campaign1)
        db_session.add(campaign2)
        db_session.commit()
        db_session.refresh(campaign1)
        db_session.refresh(campaign2)

        # Create test messages
        message1 = Message(
            campaign_id=campaign1.id,
            recipient_phone="+5511999999999",
            content="Test message 1",
            status="sent",
            ghl_status="delivered",
            sent_at=datetime.now(timezone.utc)
        )
        message2 = Message(
            campaign_id=campaign2.id,
            recipient_phone="+5511888888888",
            content="Test message 2",
            status="sent",
            ghl_status="read",
            sent_at=datetime.now(timezone.utc)
        )
        db_session.add(message1)
        db_session.add(message2)
        db_session.commit()

        # Make request
        response = await async_client.get("/api/v1/analytics/dashboard")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "campaign_metrics" in data
        assert "delivery_metrics" in data
        assert "recent_campaigns" in data
        assert "top_performing_campaigns" in data
        assert "time_range" in data
        assert "filter_info" in data

        # Verify campaign metrics
        assert data["campaign_metrics"]["total_campaigns"] == 2
        assert data["campaign_metrics"]["completed_campaigns"] == 1
        assert data["campaign_metrics"]["active_campaigns"] == 1

        # Verify delivery metrics
        assert data["delivery_metrics"]["sent"] >= 0
        assert data["delivery_metrics"]["delivered"] >= 0
        assert "delivery_rate" in data["delivery_metrics"]
        assert "read_rate" in data["delivery_metrics"]

        # Verify time range
        assert "30 dias" in data["time_range"]

        # Verify filter info
        assert "todos os usuários" in data["filter_info"].lower()

    async def test_dashboard_with_ghl_user_id_filter(self, async_client: AsyncClient, db_session):
        """Test GET /api/v1/analytics/dashboard with ghl_user_id filter"""
        # Create campaigns for different users
        campaign1 = Campaign(
            name="User 1 Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc)
        )
        campaign2 = Campaign(
            name="User 2 Campaign",
            status="completed",
            ghl_location_id="loc_test456",
            ghl_user_id="user_456",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(campaign1)
        db_session.add(campaign2)
        db_session.commit()

        # Make request with user filter
        response = await async_client.get("/api/v1/analytics/dashboard?ghl_user_id=user_123")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify only user_123 campaigns are counted
        assert data["campaign_metrics"]["total_campaigns"] == 1

        # Verify filter info shows user filtering
        assert "user_123" in data["filter_info"]

    async def test_dashboard_with_days_parameter(self, async_client: AsyncClient, db_session):
        """Test GET /api/v1/analytics/dashboard with days parameter"""
        # Create campaign from 40 days ago (outside 30-day default)
        old_campaign = Campaign(
            name="Old Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc) - timedelta(days=40)
        )
        # Create recent campaign (within 30 days)
        recent_campaign = Campaign(
            name="Recent Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db_session.add(old_campaign)
        db_session.add(recent_campaign)
        db_session.commit()

        # Request with 30 days - should only get recent campaign
        response = await async_client.get("/api/v1/analytics/dashboard?days=30")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["campaign_metrics"]["total_campaigns"] == 1

        # Request with 60 days - should get both campaigns
        response = await async_client.get("/api/v1/analytics/dashboard?days=60")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["campaign_metrics"]["total_campaigns"] == 2

        # Verify time range string
        assert "60 dias" in data["time_range"]

    async def test_dashboard_with_combined_filters(self, async_client: AsyncClient, db_session):
        """Test GET /api/v1/analytics/dashboard with both ghl_user_id and days"""
        # Create campaigns
        campaign1 = Campaign(
            name="User 1 Recent",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        campaign2 = Campaign(
            name="User 1 Old",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now(timezone.utc) - timedelta(days=40)
        )
        campaign3 = Campaign(
            name="User 2 Recent",
            status="completed",
            ghl_location_id="loc_test456",
            ghl_user_id="user_456",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db_session.add_all([campaign1, campaign2, campaign3])
        db_session.commit()

        # Request with both filters
        response = await async_client.get(
            "/api/v1/analytics/dashboard?ghl_user_id=user_123&days=30"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only get campaign1 (user_123 + within 30 days)
        assert data["campaign_metrics"]["total_campaigns"] == 1

    async def test_dashboard_empty_state(self, async_client: AsyncClient, db_session):
        """Test GET /api/v1/analytics/dashboard with no campaigns"""
        # Don't create any campaigns

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all metrics are zero
        assert data["campaign_metrics"]["total_campaigns"] == 0
        assert data["campaign_metrics"]["draft_campaigns"] == 0
        assert data["campaign_metrics"]["scheduled_campaigns"] == 0
        assert data["campaign_metrics"]["active_campaigns"] == 0
        assert data["campaign_metrics"]["completed_campaigns"] == 0
        assert data["campaign_metrics"]["failed_campaigns"] == 0
        assert data["campaign_metrics"]["cancelled_campaigns"] == 0

        assert data["delivery_metrics"]["sent"] == 0
        assert data["delivery_metrics"]["delivered"] == 0
        assert data["delivery_metrics"]["failed"] == 0
        assert data["delivery_metrics"]["delivery_rate"] == 0.0
        assert data["delivery_metrics"]["read_rate"] == 0.0

        # Verify empty lists
        assert data["recent_campaigns"] == []
        assert data["top_performing_campaigns"] == []

    async def test_dashboard_response_has_all_required_fields(self, async_client: AsyncClient, db_session):
        """Test that dashboard response contains all required fields from contract"""
        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Required top-level fields
        required_fields = [
            "campaign_metrics",
            "delivery_metrics",
            "recent_campaigns",
            "top_performing_campaigns",
            "time_range",
            "filter_info"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Campaign metrics required fields
        campaign_fields = [
            "total_campaigns",
            "draft_campaigns",
            "scheduled_campaigns",
            "active_campaigns",
            "completed_campaigns",
            "failed_campaigns",
            "cancelled_campaigns"
        ]
        for field in campaign_fields:
            assert field in data["campaign_metrics"], f"Missing campaign metric: {field}"

        # Delivery metrics required fields
        delivery_fields = ["sent", "delivered", "failed", "delivery_rate", "read_rate"]
        for field in delivery_fields:
            assert field in data["delivery_metrics"], f"Missing delivery metric: {field}"

    async def test_dashboard_invalid_days_parameter(self, async_client: AsyncClient, db_session):
        """Test dashboard rejects invalid days parameter"""
        # Test days > 365 - FastAPI Query validation returns 422
        response = await async_client.get("/api/v1/analytics/dashboard?days=400")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test days < 1
        response = await async_client.get("/api/v1/analytics/dashboard?days=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test negative days
        response = await async_client.get("/api/v1/analytics/dashboard?days=-10")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
