"""
Contract tests for GHL Messages API
Tests the API contract without implementation
Following TDD: These tests should FAIL before implementation
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestGHLMessagesAPI:
    """Test suite for /ghl/messages endpoint"""

    @patch('src.services.ghl_conversations_service.GHLConversationsService.send_message')
    @patch('src.services.ghl_oauth_service.GHLOAuthService.get_valid_access_token')
    async def test_send_message_via_ghl_returns_201(
        self,
        mock_token: AsyncMock,
        mock_send: AsyncMock,
        async_client: AsyncClient,
        sample_ghl_locations
    ):
        """Test POST /ghl/messages/send returns 201 Created"""
        # Mock OAuth token retrieval
        mock_token.return_value = "test_access_token"

        # Mock GHL API response
        mock_send.return_value = {
            "messageId": "msg_mock123",
            "conversationId": "conv_mock123",
            "contactId": "contact_mock123",
            "status": "sent",
            "sentAt": "2025-10-01T00:00:00Z"
        }

        payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "+5511999999999",
            "message_text": "Test message"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    @patch('src.services.ghl_conversations_service.GHLConversationsService.send_message')
    @patch('src.services.ghl_oauth_service.GHLOAuthService.get_valid_access_token')
    async def test_send_message_returns_message_details(
        self,
        mock_token: AsyncMock,
        mock_send: AsyncMock,
        async_client: AsyncClient,
        sample_ghl_locations
    ):
        """Test POST /ghl/messages/send returns message ID and conversation ID"""
        # Mock OAuth token retrieval
        mock_token.return_value = "test_access_token"

        # Mock GHL API response
        mock_send.return_value = {
            "messageId": "msg_mock123",
            "conversationId": "conv_mock123",
            "contactId": "contact_mock123",
            "status": "sent",
            "sentAt": "2025-10-01T00:00:00Z"
        }

        payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "+5511999999999",
            "message_text": "Test message"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        data = response.json()

        assert "message_id" in data
        assert "conversation_id" in data
        assert "ghl_message_id" in data
        assert "status" in data

    @patch('src.services.ghl_conversations_service.GHLConversationsService.send_message')
    @patch('src.services.ghl_oauth_service.GHLOAuthService.get_valid_access_token')
    async def test_send_message_with_media(
        self,
        mock_token: AsyncMock,
        mock_send: AsyncMock,
        async_client: AsyncClient,
        sample_ghl_locations
    ):
        """Test POST /ghl/messages/send with media URL"""
        # Mock OAuth token retrieval
        mock_token.return_value = "test_access_token"

        # Mock GHL API response
        mock_send.return_value = {
            "messageId": "msg_mock123",
            "conversationId": "conv_mock123",
            "contactId": "contact_mock123",
            "status": "sent",
            "sentAt": "2025-10-01T00:00:00Z"
        }

        payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "+5511999999999",
            "message_text": "Check this image",
            "media_url": "https://example.com/image.jpg"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "message_id" in data

    async def test_send_message_validates_required_fields(self, async_client: AsyncClient):
        """Test POST /ghl/messages/send validates required fields"""
        # Missing message_text
        payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "+5511999999999"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_send_message_validates_phone_format(self, async_client: AsyncClient):
        """Test POST /ghl/messages/send validates phone number format (E.164)"""
        payload = {
            "ghl_location_id": "loc_test123",
            "contact_phone": "invalid_phone",  # Invalid format
            "message_text": "Test message"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_send_message_validates_location_exists(self, async_client: AsyncClient):
        """Test POST /ghl/messages/send returns 404 if location doesn't exist"""
        payload = {
            "ghl_location_id": "nonexistent_location_12345",
            "contact_phone": "+5511999999999",
            "message_text": "Test message"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_send_message_validates_location_has_whatsapp(
        self,
        async_client: AsyncClient,
        sample_ghl_locations
    ):
        """Test POST /ghl/messages/send returns 422 if location doesn't have WhatsApp"""
        payload = {
            "ghl_location_id": "loc_no_whatsapp",
            "contact_phone": "+5511999999999",
            "message_text": "Test message"
        }

        response = await async_client.post("/ghl/messages/send", json=payload)
        # Should fail validation or return error
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]
