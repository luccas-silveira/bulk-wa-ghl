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

    def test_warns_on_unknown_sending_speed(self):
        """execute_campaign emite logger.warning quando sending_speed é desconhecida."""
        import asyncio
        from unittest.mock import patch, MagicMock, AsyncMock
        from src.services.campaign_executor_service import CampaignExecutorService
        from datetime import datetime, timezone

        db = MagicMock()
        svc = CampaignExecutorService(db)

        campaign = MagicMock()
        campaign.id = 1
        campaign.sending_speed = "turbo"  # unknown value
        campaign.status = "draft"
        campaign.ghl_location_id = "loc1"
        campaign.get_user_ids_list.return_value = ["user_1"]

        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign

        with patch("src.services.campaign_executor_service.logger") as mock_logger:
            with patch.object(svc.contacts_service, "get_or_create_contact", new_callable=AsyncMock):
                with patch.object(svc.conversations_service, "send_message", new_callable=AsyncMock):
                    asyncio.run(svc.execute_campaign(1, [], []))  # empty contacts — exits loop immediately

        mock_logger.warning.assert_called()
        warning_call = str(mock_logger.warning.call_args_list)
        assert "turbo" in warning_call


class TestResumeUserIndex:
    """CAMP-04: resume deve continuar o round-robin de onde parou."""

    def test_start_user_index_is_sent_count_mod_users(self):
        """execute_campaign() aceita start_user_index e o round-robin começa nele."""
        import asyncio
        from src.services.campaign_executor_service import CampaignExecutorService
        from unittest.mock import AsyncMock, MagicMock, patch

        db = MagicMock()
        svc = CampaignExecutorService(db)

        mock_contact = AsyncMock(return_value={'id': 'contact_1'})
        mock_send = AsyncMock(return_value={'messageId': 'm1', 'conversationId': 'c1'})
        svc.contacts_service.get_or_create_contact = mock_contact
        svc.conversations_service.send_message = mock_send

        campaign = MagicMock()
        campaign.id = 42
        campaign.status = 'draft'
        campaign.sending_speed = 'fast'
        campaign.ghl_location_id = 'loc1'
        campaign.get_user_ids_list.return_value = ['user_A', 'user_B', 'user_C']

        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign
        db.query.return_value.filter.return_value.first.return_value = campaign

        contacts = [{'phone_number': '+5511999990001', 'name': 'Alice'}]

        # start_user_index=5 → 5 % 3 = index 2 → user_C
        asyncio.run(svc.execute_campaign(42, contacts, [{'text': 'Hello'}], start_user_index=5))

        call_kwargs = mock_contact.call_args.kwargs
        assert call_kwargs.get('assigned_to') == 'user_C'

    def test_resume_passes_sent_count_as_start_user_index(self):
        """resume_campaign() passa len(sent_phones) como start_user_index."""
        import asyncio
        from src.services.campaign_executor_service import CampaignExecutorService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        svc = CampaignExecutorService(db)

        campaign = MagicMock()
        campaign.id = 10
        campaign.status = 'paused'
        campaign.contacts_data = [
            {'phone_number': '+1111'},
            {'phone_number': '+2222'},
            {'phone_number': '+3333'},
        ]
        campaign.messages_template = [{'text': 'Hi'}]
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign

        # 2 phones already sent ("+1111", "+2222")
        sent_rows = [('+1111',), ('+2222',)]
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = sent_rows

        captured = {}
        async def mock_execute(campaign_id, contacts, messages_template, start_user_index=0):
            captured['start_user_index'] = start_user_index
            captured['contacts'] = contacts
            return {'campaign_id': campaign_id, 'status': 'completed',
                    'total_contacts': len(contacts), 'successful_sends': 1, 'failed_sends': 0}
        svc.execute_campaign = mock_execute

        asyncio.run(svc.resume_campaign(10))

        assert captured['start_user_index'] == 2  # len(sent_phones) = 2
        assert len(captured['contacts']) == 1  # only '+3333' remaining


class TestResumeSchemaConsistency:
    """CAMP-09: resume_campaign retorna schema consistente em todos os caminhos."""

    EXPECTED_KEYS = {'campaign_id', 'status', 'resumed_contacts', 'successful_sends', 'failed_sends'}

    def _base_setup(self, campaign, db):
        from src.services.campaign_executor_service import CampaignExecutorService
        svc = CampaignExecutorService(db)
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign
        return svc

    def test_no_data_path_has_consistent_schema(self):
        import asyncio
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 1
        campaign.contacts_data = None
        campaign.messages_template = None
        campaign.status = 'paused'
        svc = self._base_setup(campaign, db)

        result = asyncio.run(svc.resume_campaign(1))
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 0
        assert result['successful_sends'] == 0

    def test_all_sent_path_has_consistent_schema(self):
        import asyncio
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 2
        campaign.contacts_data = [{'phone_number': '+1111'}]
        campaign.messages_template = [{'text': 'Hi'}]
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [('+1111',)]
        svc = self._base_setup(campaign, db)

        result = asyncio.run(svc.resume_campaign(2))
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 0

    def test_normal_execution_path_has_consistent_schema(self):
        import asyncio
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 3
        campaign.contacts_data = [{'phone_number': '+5555'}]
        campaign.messages_template = [{'text': 'Hi'}]
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

        svc = self._base_setup(campaign, db)

        async def fake_execute(cid, contacts, messages_template, start_user_index=0):
            return {'campaign_id': cid, 'status': 'completed', 'total_contacts': 1,
                    'successful_sends': 1, 'failed_sends': 0, 'completion_rate': 100.0}
        svc.execute_campaign = fake_execute

        result = asyncio.run(svc.resume_campaign(3))
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 1
        assert result['successful_sends'] == 1
