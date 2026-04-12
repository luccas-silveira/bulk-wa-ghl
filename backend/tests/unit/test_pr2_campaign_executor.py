from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timezone
import pytest


class TestGetCampaignStatusAggregation:
    """CAMP-08: get_campaign_status deve usar SQL aggregation"""

    def _make_service(self):
        from src.services.campaign_executor_service import CampaignExecutorService
        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
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

    @pytest.mark.asyncio
    async def test_returns_correct_status_counts_from_aggregation(self):
        """get_campaign_status retorna contagens corretas do SQL aggregation."""
        svc, db = self._make_service()

        campaign = self._make_campaign()

        # Mock SQL aggregation result: list of (status, count) rows
        agg_rows = [("sent", 10), ("delivered", 5), ("failed", 2), ("pending", 1)]

        # First execute call returns campaign; second returns aggregation rows
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign

        agg_result = MagicMock()
        agg_result.all.return_value = agg_rows

        db.execute = AsyncMock(side_effect=[campaign_result, agg_result])

        result = await svc.get_campaign_status(1)

        assert result["messages"]["by_status"]["sent"] == 10
        assert result["messages"]["by_status"]["delivered"] == 5
        assert result["messages"]["by_status"]["failed"] == 2
        assert result["messages"]["by_status"]["pending"] == 1
        assert result["messages"]["by_status"]["read"] == 0  # not in rows → 0
        assert result["messages"]["total"] == 18  # sum of all counts

    @pytest.mark.asyncio
    async def test_raises_if_campaign_not_found(self):
        svc, db = self._make_service()

        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        with pytest.raises(ValueError, match="not found"):
            await svc.get_campaign_status(999)


class TestSendingSpeedWarning:
    """CAMP-10: aviso quando sending_speed não reconhecida"""

    def test_speed_delays_has_known_values(self):
        from src.services.campaign_executor_service import CampaignExecutorService
        assert "slow" in CampaignExecutorService.SPEED_DELAYS
        assert "medium" in CampaignExecutorService.SPEED_DELAYS
        assert "fast" in CampaignExecutorService.SPEED_DELAYS
        assert CampaignExecutorService.SPEED_DELAYS.get("turbo") is None

    @pytest.mark.asyncio
    async def test_warns_on_unknown_sending_speed(self):
        """execute_campaign emite logger.warning quando sending_speed é desconhecida."""
        from src.services.campaign_executor_service import CampaignExecutorService
        from datetime import datetime, timezone

        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        svc = CampaignExecutorService(db)

        campaign = MagicMock()
        campaign.id = 1
        campaign.sending_speed = "turbo"  # unknown value
        campaign.status = "draft"
        campaign.ghl_location_id = "loc1"
        campaign.get_user_ids_list.return_value = ["user_1"]

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=execute_result)

        with patch("src.services.campaign_executor_service.logger") as mock_logger:
            with patch.object(svc.contacts_service, "get_or_create_contact", new_callable=AsyncMock):
                with patch.object(svc.conversations_service, "send_message", new_callable=AsyncMock):
                    await svc.execute_campaign(1, [], [])  # empty contacts — exits loop immediately

        mock_logger.warning.assert_called()
        warning_call = str(mock_logger.warning.call_args_list)
        assert "turbo" in warning_call


class TestResumeUserIndex:
    """CAMP-04: resume deve continuar o round-robin de onde parou."""

    @pytest.mark.asyncio
    async def test_start_user_index_is_sent_count_mod_users(self):
        """execute_campaign() aceita start_user_index e o round-robin começa nele."""
        from src.services.campaign_executor_service import CampaignExecutorService

        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
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

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=execute_result)

        contacts = [{'phone_number': '+5511999990001', 'name': 'Alice'}]

        # start_user_index=5 → 5 % 3 = index 2 → user_C
        await svc.execute_campaign(42, contacts, [{'text': 'Hello'}], start_user_index=5)

        call_kwargs = mock_contact.call_args.kwargs
        assert call_kwargs.get('assigned_to') == 'user_C'

    @pytest.mark.asyncio
    async def test_resume_passes_sent_count_as_start_user_index(self):
        """resume_campaign() passa len(sent_phones) como start_user_index."""
        from src.services.campaign_executor_service import CampaignExecutorService

        db = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
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

        # 2 phones already sent ("+1111", "+2222")
        sent_rows = [('+1111',), ('+2222',)]

        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign

        sent_result = MagicMock()
        sent_result.all.return_value = sent_rows

        db.execute = AsyncMock(side_effect=[campaign_result, sent_result])

        captured = {}
        async def mock_execute(campaign_id, contacts, messages_template, start_user_index=0):
            captured['start_user_index'] = start_user_index
            captured['contacts'] = contacts
            return {'campaign_id': campaign_id, 'status': 'completed',
                    'total_contacts': len(contacts), 'successful_sends': 1, 'failed_sends': 0}
        svc.execute_campaign = mock_execute

        await svc.resume_campaign(10)

        assert captured['start_user_index'] == 2  # len(sent_phones) = 2
        assert len(captured['contacts']) == 1  # only '+3333' remaining


class TestResumeSchemaConsistency:
    """CAMP-09: resume_campaign retorna schema consistente em todos os caminhos."""

    EXPECTED_KEYS = {'campaign_id', 'status', 'resumed_contacts', 'successful_sends', 'failed_sends'}

    def _base_setup(self, campaign, db, sent_rows=None):
        from src.services.campaign_executor_service import CampaignExecutorService

        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()

        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign

        sent_result = MagicMock()
        sent_result.all.return_value = sent_rows if sent_rows is not None else []

        db.execute = AsyncMock(side_effect=[campaign_result, sent_result])
        svc = CampaignExecutorService(db)
        return svc

    @pytest.mark.asyncio
    async def test_no_data_path_has_consistent_schema(self):
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 1
        campaign.contacts_data = None
        campaign.messages_template = None
        campaign.status = 'paused'
        svc = self._base_setup(campaign, db)

        result = await svc.resume_campaign(1)
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 0
        assert result['successful_sends'] == 0

    @pytest.mark.asyncio
    async def test_all_sent_path_has_consistent_schema(self):
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 2
        campaign.contacts_data = [{'phone_number': '+1111'}]
        campaign.messages_template = [{'text': 'Hi'}]
        svc = self._base_setup(campaign, db, sent_rows=[('+1111',)])

        result = await svc.resume_campaign(2)
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 0

    @pytest.mark.asyncio
    async def test_normal_execution_path_has_consistent_schema(self):
        db = MagicMock()
        campaign = MagicMock()
        campaign.id = 3
        campaign.contacts_data = [{'phone_number': '+5555'}]
        campaign.messages_template = [{'text': 'Hi'}]
        svc = self._base_setup(campaign, db, sent_rows=[])

        async def fake_execute(cid, contacts, messages_template, start_user_index=0):
            return {'campaign_id': cid, 'status': 'completed', 'total_contacts': 1,
                    'successful_sends': 1, 'failed_sends': 0, 'completion_rate': 100.0}
        svc.execute_campaign = fake_execute

        result = await svc.resume_campaign(3)
        assert self.EXPECTED_KEYS.issubset(result.keys()), f'Missing: {self.EXPECTED_KEYS - result.keys()}'
        assert result['resumed_contacts'] == 1
        assert result['successful_sends'] == 1


class TestRateLimitHandling:
    """CAMP-12: RateLimitExceeded é capturado separadamente com retry."""

    @pytest.mark.asyncio
    async def test_rate_limit_retries_after_wait_and_succeeds(self):
        """Após RateLimitExceeded, aguarda e reenvia — se retry OK, mensagem fica 'sent'."""
        from src.services.campaign_executor_service import CampaignExecutorService
        from src.services.ghl_conversations_service import RateLimitExceeded

        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        svc = CampaignExecutorService(db)

        campaign = MagicMock()
        campaign.id = 1
        campaign.status = 'draft'
        campaign.sending_speed = 'fast'
        campaign.ghl_location_id = 'loc1'
        campaign.get_user_ids_list.return_value = ['user1']

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=execute_result)

        svc.contacts_service.get_or_create_contact = AsyncMock(return_value={'id': 'c1'})

        # First call raises RateLimitExceeded, second call succeeds
        mock_send = AsyncMock(side_effect=[
            RateLimitExceeded('Rate limit'),
            {'messageId': 'm1', 'conversationId': 'cv1'},
        ])
        svc.conversations_service.send_message = mock_send
        svc.conversations_service.rate_limiter = MagicMock()
        svc.conversations_service.rate_limiter.wait_time.return_value = 0.0

        contacts = [{'phone_number': '+5511999990001', 'name': 'Alice'}]

        with patch('src.services.campaign_executor_service.asyncio.sleep', new_callable=AsyncMock):
            result = await svc.execute_campaign(1, contacts, [{'text': 'Hi'}])

        assert result['successful_sends'] == 1
        assert result['failed_sends'] == 0
        assert mock_send.call_count == 2  # original + 1 retry

    @pytest.mark.asyncio
    async def test_rate_limit_retry_also_fails_marks_message_failed(self):
        """Se o retry também falhar, mensagem fica 'failed' e campanha não lança exceção."""
        from src.services.campaign_executor_service import CampaignExecutorService
        from src.services.ghl_conversations_service import RateLimitExceeded

        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        svc = CampaignExecutorService(db)

        campaign = MagicMock()
        campaign.id = 2
        campaign.status = 'draft'
        campaign.sending_speed = 'fast'
        campaign.ghl_location_id = 'loc1'
        campaign.get_user_ids_list.return_value = ['user1']

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = campaign
        db.execute = AsyncMock(return_value=execute_result)

        svc.contacts_service.get_or_create_contact = AsyncMock(return_value={'id': 'c1'})

        # Both calls fail with RateLimitExceeded
        svc.conversations_service.send_message = AsyncMock(
            side_effect=RateLimitExceeded('Still rate limited')
        )
        svc.conversations_service.rate_limiter = MagicMock()
        svc.conversations_service.rate_limiter.wait_time.return_value = 0.0

        contacts = [{'phone_number': '+5511999990001', 'name': 'Alice'}]

        with patch('src.services.campaign_executor_service.asyncio.sleep', new_callable=AsyncMock):
            result = await svc.execute_campaign(2, contacts, [{'text': 'Hi'}])

        assert result['successful_sends'] == 0
        assert result['failed_sends'] == 1
