"""
Test fixtures for contract and integration tests
Provides sample data for GHL locations, OAuth tokens, and messages
"""
import pytest
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet

from src.models.ghl_location import GHLLocation
from src.models.ghl_oauth_token import GHLOAuthToken
from src.models.campaign import Campaign
from src.models.message import Message
from src.services.token_encryption_service import TokenEncryptionService


@pytest.fixture
def sample_ghl_locations(db_session):
    """Create sample GHL locations for testing"""
    # Generate a test encryption key
    test_key = Fernet.generate_key().decode()
    import os
    os.environ["GHL_TOKEN_ENCRYPTION_KEY"] = test_key

    encryption_service = TokenEncryptionService()

    locations = [
        GHLLocation(
            ghl_location_id="loc_test123",
            name="Test Location 1",
            company_id="comp_123",
            email="test@location1.com",
            has_whatsapp=True,
            whatsapp_number="+5511999999999",
            whatsapp_status="active",
            is_active=True
        ),
        GHLLocation(
            ghl_location_id="loc_test456",
            name="Test Location 2",
            company_id="comp_123",
            email="test@location2.com",
            has_whatsapp=True,
            whatsapp_number="+5511888888888",
            whatsapp_status="active",
            is_active=True
        ),
        GHLLocation(
            ghl_location_id="loc_no_whatsapp",
            name="Location Without WhatsApp",
            company_id="comp_123",
            has_whatsapp=False,
            is_active=True
        ),
    ]

    for location in locations:
        db_session.add(location)

    db_session.commit()

    # Add OAuth tokens for active locations
    for location in locations[:2]:  # Only for locations with WhatsApp
        token = GHLOAuthToken(
            ghl_location_id=location.ghl_location_id,
            access_token_encrypted=encryption_service.encrypt("test_access_token"),
            refresh_token_encrypted=encryption_service.encrypt("test_refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scope="conversations.readonly conversations.write",
            raw_response={"test": "data"}
        )
        db_session.add(token)

    db_session.commit()

    return locations


@pytest.fixture
def sample_campaign(db_session, sample_ghl_locations):
    """Create a sample campaign for testing"""
    campaign = Campaign(
        name="Test Campaign",
        status="active",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1"
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def sample_messages(db_session, sample_campaign):
    """Create sample messages for webhook testing"""
    messages = [
        Message(
            campaign_id=sample_campaign.id,
            recipient_phone="+5511999999999",
            content="Test message 1",
            status="sent",
            ghl_message_id="msg_test123",
            ghl_conversation_id="conv_test123",
            ghl_status="sent"
        ),
        Message(
            campaign_id=sample_campaign.id,
            recipient_phone="+5511888888888",
            content="Test message 2",
            status="sent",
            ghl_message_id="msg_test456",
            ghl_conversation_id="conv_test456",
            ghl_status="sent"
        ),
    ]

    for message in messages:
        db_session.add(message)

    db_session.commit()
    return messages


@pytest.fixture
def mock_ghl_api_response():
    """Mock GHL API response for message sending"""
    return {
        "id": "msg_mock_12345",
        "conversationId": "conv_mock_12345",
        "contactId": "contact_mock_12345",
        "status": "sent",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }


# Campaign test fixtures for contract tests
@pytest.fixture
def executing_campaign(db_session, sample_ghl_locations):
    """Create a campaign in executing status"""
    campaign = Campaign(
        name="Executing Campaign",
        status="executing",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1",
        ghl_user_id="user_123",
        ghl_user_ids='["user_123"]',  # JSON string, not Python list
        sending_speed="medium",
        schedule_type="immediate"
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def paused_campaign(db_session, sample_ghl_locations):
    """Create a campaign in paused status"""
    campaign = Campaign(
        name="Paused Campaign",
        status="paused",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1",
        ghl_user_id="user_123",
        ghl_user_ids='["user_123"]',  # JSON string, not Python list
        sending_speed="medium",
        schedule_type="immediate",
        paused_at=datetime.now(timezone.utc)
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def completed_campaign(db_session, sample_ghl_locations):
    """Create a campaign in completed status"""
    campaign = Campaign(
        name="Completed Campaign",
        status="completed",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1",
        ghl_user_id="user_123",
        ghl_user_ids='["user_123"]',  # JSON string, not Python list
        sending_speed="medium",
        schedule_type="immediate"
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def draft_campaign(db_session, sample_ghl_locations):
    """Create a campaign in draft status"""
    campaign = Campaign(
        name="Draft Campaign",
        status="draft",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1",
        ghl_user_id="user_123",
        ghl_user_ids='["user_123"]',  # JSON string, not Python list
        sending_speed="medium",
        schedule_type="immediate"
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def sample_campaign_with_messages(db_session, sample_ghl_locations):
    """Create a campaign with messages for testing logs and cascade delete"""
    campaign = Campaign(
        name="Campaign with Messages",
        status="completed",
        ghl_location_id="loc_test123",
        ghl_location_name="Test Location 1",
        ghl_user_id="user_123",
        ghl_user_ids='["user_123"]',  # JSON string, not Python list
        sending_speed="medium",
        schedule_type="immediate"
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    # Add some messages
    messages = [
        Message(
            campaign_id=campaign.id,
            recipient_phone="+5511999999999",
            content="Test message 1",
            status="sent",
            ghl_message_id="msg_1",
            ghl_conversation_id="conv_1",
            ghl_status="sent"
        ),
        Message(
            campaign_id=campaign.id,
            recipient_phone="+5511888888888",
            content="Test message 2",
            status="delivered",
            ghl_message_id="msg_2",
            ghl_conversation_id="conv_2",
            ghl_status="delivered"
        ),
    ]

    for message in messages:
        db_session.add(message)

    db_session.commit()
    return campaign
