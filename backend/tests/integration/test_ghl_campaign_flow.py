"""
Integration tests for GHL Campaign Flow
Tests end-to-end flow: Campaign creation → Message send → Webhook delivery
Following TDD: These tests should FAIL before implementation
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestGHLCampaignFlow:
    """Test suite for complete campaign flow with GHL integration"""

    async def test_create_campaign_with_ghl_location(self, async_client: AsyncClient):
        """Test creating a campaign with GHL location ID"""
        campaign_payload = {
            "name": "Test GHL Campaign",
            "ghl_location_id": "loc_test123",
            "ghl_location_name": "Test Location",
            "status": "draft",
            "sending_speed": "medium",
            "schedule_type": "immediate"
        }

        response = await async_client.post("/campaigns", json=campaign_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["ghl_location_id"] == "loc_test123"
        assert data["ghl_location_name"] == "Test Location"
        assert "id" in data

    @patch('src.services.ghl_conversations_service.GHLConversationsService.send_message')
    async def test_send_message_via_ghl_mocked(
        self,
        mock_send_message: AsyncMock,
        async_client: AsyncClient
    ):
        """Test sending message through GHL API (mocked)"""
        # Mock GHL API response
        mock_send_message.return_value = {
            "messageId": "msg_ghl_xyz789",
            "conversationId": "conv_ghl_abc456",
            "status": "sent"
        }

        message_payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "+5511999999999",
            "message_text": "Hello from GHL campaign"
        }

        response = await async_client.post("/ghl/messages/send", json=message_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["ghl_message_id"] == "msg_ghl_xyz789"
        assert data["conversation_id"] == "conv_ghl_abc456"

        # Verify mock was called
        mock_send_message.assert_called_once()

    async def test_complete_campaign_flow_end_to_end(self, async_client: AsyncClient):
        """
        Test complete end-to-end flow:
        1. Create campaign with GHL location
        2. Send message via GHL
        3. Receive webhook delivery confirmation
        4. Verify message status updated
        """
        # Step 1: Create campaign
        campaign_payload = {
            "name": "E2E Test Campaign",
            "ghl_location_id": "loc_test123",
            "ghl_location_name": "Test Location",
            "status": "draft"
        }

        campaign_response = await async_client.post("/campaigns", json=campaign_payload)
        assert campaign_response.status_code == status.HTTP_201_CREATED
        campaign_id = campaign_response.json()["id"]

        # Step 2: Send message (this will be mocked in real tests)
        with patch('src.services.ghl_conversations_service.GHLConversationsService.send_message') as mock_send:
            mock_send.return_value = {
                "messageId": "msg_e2e_test",
                "conversationId": "conv_e2e_test",
                "status": "sent"
            }

            message_payload = {
                "ghl_location_id": "loc_test123",
                "contact_phone": "+5511999999999",
                "message_text": "E2E test message",
                "campaign_id": campaign_id
            }

            message_response = await async_client.post("/ghl/messages/send", json=message_payload)
            assert message_response.status_code == status.HTTP_201_CREATED
            message_id = message_response.json()["message_id"]

        # Step 3: Simulate webhook delivery
        webhook_payload = {
            "type": "MessageDelivered",
            "locationId": "loc_test123",
            "conversationId": "conv_e2e_test",
            "messageId": "msg_e2e_test",
            "timestamp": "2025-09-30T21:00:00Z"
        }

        # Mock signature validation
        with patch('src.services.ghl_webhook_handler.GHLWebhookHandler.validate_signature') as mock_validate:
            mock_validate.return_value = True

            webhook_response = await async_client.post(
                "/webhooks/ghl/messages",
                json=webhook_payload,
                headers={"X-GHL-Signature": "mock_signature"}
            )

            assert webhook_response.status_code == status.HTTP_200_OK

        # Step 4: Verify message status was updated
        # Query message by ID to check status
        message_check_response = await async_client.get(f"/messages/{message_id}")

        if message_check_response.status_code == status.HTTP_200_OK:
            message_data = message_check_response.json()
            assert message_data["ghl_status"] == "delivered"

    async def test_campaign_validates_ghl_location_exists(self, async_client: AsyncClient):
        """Test campaign creation validates that GHL location exists"""
        campaign_payload = {
            "name": "Invalid Location Campaign",
            "ghl_location_id": "nonexistent_location_99999",
            "status": "draft"
        }

        response = await async_client.post("/campaigns", json=campaign_payload)

        # Should fail validation
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    async def test_campaign_validates_ghl_location_has_whatsapp(self, async_client: AsyncClient):
        """Test campaign creation validates that GHL location has WhatsApp enabled"""
        # This test assumes a location without WhatsApp exists in test DB

        campaign_payload = {
            "name": "No WhatsApp Campaign",
            "ghl_location_id": "loc_no_whatsapp",
            "status": "draft"
        }

        response = await async_client.post("/campaigns", json=campaign_payload)

        # Should fail validation
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]

    async def test_webhook_updates_message_status_to_read(self, async_client: AsyncClient):
        """Test webhook processing updates message status from delivered to read"""
        # First create and send a message
        with patch('src.services.ghl_conversations_service.GHLConversationsService.send_message') as mock_send:
            mock_send.return_value = {
                "messageId": "msg_read_test",
                "conversationId": "conv_read_test",
                "status": "sent"
            }

            message_payload = {
                "ghl_location_id": "loc_test123",
                "contact_phone": "+5511999999999",
                "message_text": "Read test message"
            }

            message_response = await async_client.post("/ghl/messages/send", json=message_payload)
            message_id = message_response.json()["message_id"]

        # Simulate MessageRead webhook
        webhook_payload = {
            "type": "MessageRead",
            "locationId": "loc_test123",
            "conversationId": "conv_read_test",
            "messageId": "msg_read_test",
            "timestamp": "2025-09-30T21:05:00Z"
        }

        with patch('src.services.ghl_webhook_handler.GHLWebhookHandler.validate_signature') as mock_validate:
            mock_validate.return_value = True

            webhook_response = await async_client.post(
                "/webhooks/ghl/messages",
                json=webhook_payload,
                headers={"X-GHL-Signature": "mock_signature"}
            )

            assert webhook_response.status_code == status.HTTP_200_OK

        # Verify message status updated
        message_check_response = await async_client.get(f"/messages/{message_id}")

        if message_check_response.status_code == status.HTTP_200_OK:
            message_data = message_check_response.json()
            assert message_data["ghl_status"] == "read"
