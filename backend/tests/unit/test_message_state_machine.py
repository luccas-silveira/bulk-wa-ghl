"""Unit tests for Message status guard (GHL-11, PERS-28)."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from src.models.message import Message, STATUS_ORDER


class TestStatusOrder:
    def test_pending_before_sent(self):
        assert STATUS_ORDER['pending'] < STATUS_ORDER['sent']

    def test_sent_before_delivered(self):
        assert STATUS_ORDER['sent'] < STATUS_ORDER['delivered']

    def test_delivered_before_read(self):
        assert STATUS_ORDER['delivered'] < STATUS_ORDER['read']

    def test_failed_is_minus_one(self):
        assert STATUS_ORDER['failed'] == -1


class TestMessageValidates:
    def test_invalid_status_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid message status"):
            Message(status='unknown')

    def test_all_valid_statuses_accepted(self):
        for s in ('pending', 'sent', 'delivered', 'read', 'failed'):
            m = Message(status=s)
            assert m.status == s


class TestWebhookNoRegression:
    """Test the STATUS_ORDER guard logic directly."""

    def test_delivered_advances_from_sent(self):
        assert STATUS_ORDER.get('delivered', 0) > STATUS_ORDER.get('sent', 0)

    def test_delivered_does_not_advance_from_read(self):
        assert not (STATUS_ORDER.get('delivered', 0) > STATUS_ORDER.get('read', 0))

    def test_read_advances_from_delivered(self):
        assert STATUS_ORDER.get('read', 0) > STATUS_ORDER.get('delivered', 0)

    def test_read_does_not_advance_from_read(self):
        assert not (STATUS_ORDER.get('read', 0) > STATUS_ORDER.get('read', 0))

    def test_failed_has_order_minus_one(self):
        assert STATUS_ORDER['failed'] == -1


@pytest.mark.asyncio
class TestWebhookHandlerDelivered:
    def _make_handler_with_message(self, current_status: str):
        from src.services.ghl_webhook_handler import GHLWebhookHandler
        db = MagicMock()
        msg = MagicMock()
        msg.id = 1
        msg.status = current_status
        msg.ghl_status = current_status
        # Mock async execute that returns a result with scalar_one_or_none() = msg
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = msg
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        with patch('src.services.ghl_webhook_handler.GHL_WEBHOOK_SECRET', 'secret'):
            handler = GHLWebhookHandler(db=db)
        return handler, msg

    async def test_delivered_updates_sent_message(self):
        handler, msg = self._make_handler_with_message('sent')
        await handler.handle_message_delivered({'messageId': 'x', 'conversationId': 'y'})
        assert msg.status == 'delivered'
        assert msg.ghl_status == 'delivered'

    async def test_delivered_skips_read_message(self):
        handler, msg = self._make_handler_with_message('read')
        await handler.handle_message_delivered({'messageId': 'x', 'conversationId': 'y'})
        assert msg.status == 'read'  # unchanged

    async def test_read_updates_delivered_message(self):
        handler, msg = self._make_handler_with_message('delivered')
        await handler.handle_message_read({'messageId': 'x'})
        assert msg.status == 'read'

    async def test_read_skips_already_read_message(self):
        handler, msg = self._make_handler_with_message('read')
        await handler.handle_message_read({'messageId': 'x'})
        assert msg.status == 'read'
