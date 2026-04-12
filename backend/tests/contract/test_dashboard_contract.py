"""
Contract tests for Dashboard Analytics API
Tests response schema against OpenAPI specification
Following TDD: These tests MUST FAIL before implementation (T012)
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta

from src.models.campaign import Campaign
from src.models.message import Message


@pytest.mark.asyncio
class TestDashboardContract:
    """Test suite for dashboard API contract compliance"""

    async def test_response_schema_matches_openapi_spec(self, async_client: AsyncClient, db_session):
        """Test that response schema matches OpenAPI specification"""
        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Test top-level structure
        assert isinstance(data, dict)
        assert "campaign_metrics" in data
        assert "delivery_metrics" in data
        assert "recent_campaigns" in data
        assert "top_performing_campaigns" in data
        assert "time_range" in data
        assert "filter_info" in data

        # Test campaign_metrics structure
        campaign_metrics = data["campaign_metrics"]
        assert isinstance(campaign_metrics, dict)
        assert isinstance(campaign_metrics["total_campaigns"], int)
        assert isinstance(campaign_metrics["draft_campaigns"], int)
        assert isinstance(campaign_metrics["scheduled_campaigns"], int)
        assert isinstance(campaign_metrics["active_campaigns"], int)
        assert isinstance(campaign_metrics["completed_campaigns"], int)
        assert isinstance(campaign_metrics["failed_campaigns"], int)
        assert isinstance(campaign_metrics["cancelled_campaigns"], int)

        # Test delivery_metrics structure
        delivery_metrics = data["delivery_metrics"]
        assert isinstance(delivery_metrics, dict)
        assert isinstance(delivery_metrics["sent"], int)
        assert isinstance(delivery_metrics["delivered"], int)
        assert isinstance(delivery_metrics["failed"], int)
        assert isinstance(delivery_metrics["delivery_rate"], (int, float))
        assert isinstance(delivery_metrics["read_rate"], (int, float))

        # Test recent_campaigns is array
        assert isinstance(data["recent_campaigns"], list)

        # Test top_performing_campaigns is array
        assert isinstance(data["top_performing_campaigns"], list)

        # Test time_range is string
        assert isinstance(data["time_range"], str)

        # Test filter_info is string
        assert isinstance(data["filter_info"], str)

    async def test_all_required_fields_present(self, async_client: AsyncClient, db_session):
        """Test all required fields from OpenAPI spec are present"""
        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level required fields
        required_top_level = [
            "campaign_metrics",
            "delivery_metrics",
            "recent_campaigns",
            "top_performing_campaigns",
            "time_range",
            "filter_info"
        ]
        for field in required_top_level:
            assert field in data, f"Missing required field: {field}"

        # CampaignMetrics required fields
        campaign_required = [
            "total_campaigns",
            "draft_campaigns",
            "scheduled_campaigns",
            "active_campaigns",
            "completed_campaigns",
            "failed_campaigns",
            "cancelled_campaigns"
        ]
        for field in campaign_required:
            assert field in data["campaign_metrics"], f"Missing campaign_metrics.{field}"

        # DeliveryMetrics required fields
        delivery_required = ["sent", "delivered", "failed", "delivery_rate", "read_rate"]
        for field in delivery_required:
            assert field in data["delivery_metrics"], f"Missing delivery_metrics.{field}"

    async def test_field_types_match_schema(self, async_client: AsyncClient, db_session):
        """Test all field types match OpenAPI schema definitions"""
        # Create sample data to test with
        campaign = Campaign(
            name="Test Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now()
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        message = Message(
            campaign_id=campaign.id,
            recipient_phone="+5511999999999",
            content="Test",
            status="sent",
            ghl_status="delivered",
            sent_at=datetime.now()
        )
        db_session.add(message)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Campaign metrics - all integers >= 0
        cm = data["campaign_metrics"]
        assert isinstance(cm["total_campaigns"], int) and cm["total_campaigns"] >= 0
        assert isinstance(cm["draft_campaigns"], int) and cm["draft_campaigns"] >= 0
        assert isinstance(cm["scheduled_campaigns"], int) and cm["scheduled_campaigns"] >= 0
        assert isinstance(cm["active_campaigns"], int) and cm["active_campaigns"] >= 0
        assert isinstance(cm["completed_campaigns"], int) and cm["completed_campaigns"] >= 0
        assert isinstance(cm["failed_campaigns"], int) and cm["failed_campaigns"] >= 0
        assert isinstance(cm["cancelled_campaigns"], int) and cm["cancelled_campaigns"] >= 0

        # Delivery metrics - integers and floats with ranges
        dm = data["delivery_metrics"]
        assert isinstance(dm["sent"], int) and dm["sent"] >= 0
        assert isinstance(dm["delivered"], int) and dm["delivered"] >= 0
        assert isinstance(dm["failed"], int) and dm["failed"] >= 0
        assert isinstance(dm["delivery_rate"], (int, float))
        assert 0.0 <= dm["delivery_rate"] <= 100.0
        assert isinstance(dm["read_rate"], (int, float))
        assert 0.0 <= dm["read_rate"] <= 100.0

        # Recent campaigns array
        assert isinstance(data["recent_campaigns"], list)
        assert len(data["recent_campaigns"]) <= 5  # maxItems: 5

        # Top performing campaigns array
        assert isinstance(data["top_performing_campaigns"], list)
        assert len(data["top_performing_campaigns"]) <= 10  # maxItems: 10

    async def test_enum_values_for_status_fields(self, async_client: AsyncClient, db_session):
        """Test campaign status values match enum specification"""
        valid_statuses = ["draft", "scheduled", "executing", "completed", "failed", "cancelled"]

        # Create campaigns with different statuses
        for status_value in valid_statuses:
            campaign = Campaign(
                name=f"Campaign {status_value}",
                status=status_value,
                ghl_location_id="loc_test123",
                ghl_user_id="user_123",
                created_at=datetime.now()
            )
            db_session.add(campaign)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check recent campaigns have valid status enum values
        for campaign in data["recent_campaigns"]:
            if "status" in campaign:
                assert campaign["status"] in valid_statuses

    async def test_example_with_data_matches_contract(self, async_client: AsyncClient, db_session):
        """Test response structure matches 'withData' example from contract"""
        # Create sample campaigns to match example
        campaign1 = Campaign(
            name="Promoção Black Friday",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now() - timedelta(days=5)
        )
        campaign2 = Campaign(
            name="Lançamento Produto",
            status="executing",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now() - timedelta(days=2)
        )
        db_session.add_all([campaign1, campaign2])
        await db_session.commit()
        await db_session.refresh(campaign1)
        await db_session.refresh(campaign2)

        # Create messages
        for i in range(100):
            msg = Message(
                campaign_id=campaign1.id,
                recipient_phone=f"+551199999{i:04d}",
                content="Test",
                status="sent",
                ghl_status="delivered" if i < 97 else "sent",
                sent_at=datetime.now()
            )
            db_session.add(msg)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure matches example
        assert "campaign_metrics" in data
        assert data["campaign_metrics"]["total_campaigns"] >= 2
        assert data["campaign_metrics"]["completed_campaigns"] >= 1
        assert data["campaign_metrics"]["active_campaigns"] >= 1

        assert "delivery_metrics" in data
        assert data["delivery_metrics"]["sent"] >= 0
        assert data["delivery_metrics"]["delivered"] >= 0

        assert isinstance(data["recent_campaigns"], list)
        assert isinstance(data["top_performing_campaigns"], list)

        assert data["time_range"] == "Últimos 30 dias"
        assert "usuários" in data["filter_info"].lower()

    async def test_example_empty_state_matches_contract(self, async_client: AsyncClient, db_session):
        """Test response structure matches 'emptyState' example from contract"""
        # Don't create any campaigns

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify empty state matches contract example
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

        assert data["recent_campaigns"] == []
        assert data["top_performing_campaigns"] == []

        assert data["time_range"] == "Últimos 30 dias"
        assert "usuários" in data["filter_info"].lower()

    async def test_example_user_filtered_matches_contract(self, async_client: AsyncClient, db_session):
        """Test response structure matches 'userFiltered' example from contract"""
        # Create campaigns for specific user
        campaign = Campaign(
            name="Minha Campanha",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_abc123",
            created_at=datetime.now()
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Create messages for delivery metrics
        for i in range(60):
            msg = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+551199999{i:04d}",
                content="Test",
                status="sent",
                ghl_status="delivered" if i < 57 else "sent",
                sent_at=datetime.now()
            )
            db_session.add(msg)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard?ghl_user_id=user_abc123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify user filtering
        assert data["campaign_metrics"]["total_campaigns"] >= 1
        assert data["time_range"] == "Últimos 30 dias"
        assert "user_abc123" in data["filter_info"]

    async def test_recent_campaign_fields_match_schema(self, async_client: AsyncClient, db_session):
        """Test RecentCampaign objects have all required fields"""
        campaign = Campaign(
            name="Test Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now()
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Add message for delivery rate calculation
        msg = Message(
            campaign_id=campaign.id,
            recipient_phone="+5511999999999",
            content="Test",
            status="sent",
            ghl_status="delivered",
            sent_at=datetime.now()
        )
        db_session.add(msg)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check recent_campaigns structure
        if len(data["recent_campaigns"]) > 0:
            recent = data["recent_campaigns"][0]
            assert "id" in recent and isinstance(recent["id"], int)
            assert "name" in recent and isinstance(recent["name"], str)
            assert "status" in recent and isinstance(recent["status"], str)
            assert "delivery_rate" in recent and isinstance(recent["delivery_rate"], (int, float))
            assert "created_at" in recent and isinstance(recent["created_at"], str)
            assert "messages_sent" in recent and isinstance(recent["messages_sent"], int)

            # Validate delivery_rate range
            assert 0.0 <= recent["delivery_rate"] <= 100.0

            # Validate created_at is ISO 8601 format
            datetime.fromisoformat(recent["created_at"].replace('Z', '+00:00'))

    async def test_top_campaign_fields_match_schema(self, async_client: AsyncClient, db_session):
        """Test TopCampaign objects have all required fields"""
        campaign = Campaign(
            name="Top Campaign",
            status="completed",
            ghl_location_id="loc_test123",
            ghl_user_id="user_123",
            created_at=datetime.now()
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Add messages for metrics
        for i in range(10):
            msg = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+551199999{i:04d}",
                content="Test",
                status="sent",
                ghl_status="read" if i < 8 else "delivered",
                sent_at=datetime.now()
            )
            db_session.add(msg)
        await db_session.commit()

        response = await async_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check top_performing_campaigns structure
        if len(data["top_performing_campaigns"]) > 0:
            top = data["top_performing_campaigns"][0]
            assert "id" in top and isinstance(top["id"], int)
            assert "name" in top and isinstance(top["name"], str)
            assert "delivered_count" in top and isinstance(top["delivered_count"], int)
            assert "read_rate" in top and isinstance(top["read_rate"], (int, float))
            assert "delivery_rate" in top and isinstance(top["delivery_rate"], (int, float))

            # Validate ranges
            assert top["delivered_count"] >= 0
            assert 0.0 <= top["read_rate"] <= 100.0
            assert 0.0 <= top["delivery_rate"] <= 100.0

    async def test_error_response_schema_for_invalid_days(self, async_client: AsyncClient, db_session):
        """Test error response schema matches specification"""
        # FastAPI Query validation returns 422, not 400
        response = await async_client.get("/api/v1/analytics/dashboard?days=500")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Error schema from contract (FastAPI validation includes detail)
        assert "detail" in data


@pytest.mark.asyncio
class TestDashboardTimeout:
    """ANA-17: dashboard must return 504 when analytics takes too long."""

    async def test_returns_504_on_timeout(self, async_client: AsyncClient):
        import asyncio
        from unittest.mock import MagicMock
        from src.main import app
        from src.database import get_db

        # Simulate a slow DB session — execute sleeps forever
        mock_db = MagicMock()
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(60)  # longer than the 5 s timeout
        mock_db.execute = slow_execute

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            response = await async_client.get(
                "/api/v1/analytics/dashboard",
                timeout=15.0,
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 504
        data = response.json()
        assert "detail" in data
