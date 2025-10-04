"""
Contract tests for GHL Webhooks API
Tests the webhook processing contract without implementation
Following TDD: These tests should FAIL before implementation
"""
import pytest
import hmac
import hashlib
import json
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestGHLWebhooksAPI:
    """Test suite for /webhooks/ghl/messages endpoint"""

    def _generate_webhook_signature(self, payload_bytes: bytes, secret: str = "test_webhook_secret") -> str:
        """Generate HMAC-SHA256 signature for webhook payload"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    async def test_webhook_processes_message_delivered(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages processes MessageDelivered event"""
        payload = {
            "type": "MessageDelivered",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_xyz789",
            "contactId": "contact_123",
            "timestamp": "2025-09-30T20:00:00Z"
        }

        # Generate signature from the actual bytes that will be sent
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_webhook_signature(payload_bytes)

        response = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_webhook_processes_message_read(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages processes MessageRead event"""
        payload = {
            "type": "MessageRead",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_xyz789",
            "contactId": "contact_123",
            "timestamp": "2025-09-30T20:05:00Z"
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_webhook_signature(payload_bytes)

        response = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_webhook_processes_inbound_message(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages processes InboundMessage event"""
        payload = {
            "type": "InboundMessage",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_inbound_123",
            "contactId": "contact_123",
            "contactPhone": "+5511999999999",
            "messageText": "Hello from customer",
            "timestamp": "2025-09-30T20:10:00Z"
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_webhook_signature(payload_bytes)

        response = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_webhook_validates_signature(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages rejects invalid signatures"""
        payload = {
            "type": "MessageDelivered",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_xyz789"
        }

        # Use an invalid signature
        invalid_signature = "invalid_signature_12345"

        response = await async_client.post(
            "/webhooks/ghl/messages",
            json=payload,
            headers={"X-GHL-Signature": invalid_signature}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_webhook_requires_signature_header(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages requires X-GHL-Signature header"""
        payload = {
            "type": "MessageDelivered",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_xyz789"
        }

        # No signature header
        response = await async_client.post(
            "/webhooks/ghl/messages",
            json=payload
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_webhook_idempotency_duplicate_processing(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages handles duplicate webhooks (idempotency)"""
        payload = {
            "type": "MessageDelivered",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_duplicate_test",
            "timestamp": "2025-09-30T20:15:00Z"
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_webhook_signature(payload_bytes)
        headers = {
            "X-GHL-Signature": signature,
            "Content-Type": "application/json"
        }

        # First request
        response1 = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers=headers
        )

        assert response1.status_code == status.HTTP_200_OK

        # Duplicate request with same payload
        response2 = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers=headers
        )

        # Should still return 200 but not process again
        assert response2.status_code == status.HTTP_200_OK

        # Verify in response data that it was already processed
        data = response2.json()
        assert data.get("already_processed") is True or data.get("status") == "duplicate"

    async def test_webhook_handles_message_failed(self, async_client: AsyncClient):
        """Test POST /webhooks/ghl/messages processes MessageFailed event"""
        payload = {
            "type": "MessageFailed",
            "locationId": "loc_test123",
            "conversationId": "conv_abc456",
            "messageId": "msg_failed_789",
            "contactId": "contact_123",
            "errorCode": "PHONE_NOT_WHATSAPP",
            "errorMessage": "Phone number is not on WhatsApp",
            "timestamp": "2025-09-30T20:20:00Z"
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_webhook_signature(payload_bytes)

        response = await async_client.post(
            "/webhooks/ghl/messages",
            content=payload_bytes,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == status.HTTP_200_OK
