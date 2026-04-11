from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
import pytest


class TestGetCampaignStatusAggregation:
    """CAMP-08: get_campaign_status deve usar SQL aggregation"""

    def _make_service(self):
        from src.services.campaign_executor_service import CampaignExecutorService
        db = MagicMock()
        return CampaignExecutorService(db), db

    def _make_campaign(self, id=1):
        c = MagicMock()
        c.id = id
        c.name = "Test Campaign"
        c.status = "executing"
        c.ghl_location_id = "loc_abc"
        c.sending_speed = "medium"
        c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return c

    def test_returns_correct_status_counts_from_aggregation(self):
        """get_campaign_status retorna contagens corretas do SQL aggregation."""
        import asyncio
        svc, db = self._make_service()

        campaign = self._make_campaign()
        db.query.return_value.filter.return_value.first.return_value = campaign

        # Mock SQL aggregation result: list of (status, count) rows
        agg_rows = [("sent", 10), ("delivered", 5), ("failed", 2), ("pending", 1)]
        # The aggregation query chain: db.query(Message.status, func.count).filter().group_by().all()
        db.query.return_value.filter.return_value.group_by.return_value.all.return_value = agg_rows

        result = asyncio.run(svc.get_campaign_status(1))

        assert result["messages"]["by_status"]["sent"] == 10
        assert result["messages"]["by_status"]["delivered"] == 5
        assert result["messages"]["by_status"]["failed"] == 2
        assert result["messages"]["by_status"]["pending"] == 1
        assert result["messages"]["by_status"]["read"] == 0  # not in rows → 0
        assert result["messages"]["total"] == 18  # sum of all counts

    def test_raises_if_campaign_not_found(self):
        import asyncio
        svc, db = self._make_service()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            asyncio.run(svc.get_campaign_status(999))


class TestSendingSpeedWarning:
    """CAMP-10: aviso quando sending_speed não reconhecida"""

    def test_speed_delays_has_known_values(self):
        from src.services.campaign_executor_service import CampaignExecutorService
        assert "slow" in CampaignExecutorService.SPEED_DELAYS
        assert "medium" in CampaignExecutorService.SPEED_DELAYS
        assert "fast" in CampaignExecutorService.SPEED_DELAYS
        assert CampaignExecutorService.SPEED_DELAYS.get("turbo") is None
