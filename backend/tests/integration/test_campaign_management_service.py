"""
Integration tests for CampaignManagementService
Tests with real database
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.services.campaign_management_service import CampaignManagementService
from src.models.campaign import Campaign
from src.models.message import Message
from src.models.ghl_location import GHLLocation


# Test database setup
TEST_DATABASE_URL = "postgresql://luccassilveira@localhost:5432/wpp_disp_test"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def service(db_session):
    """CampaignManagementService with test database"""
    return CampaignManagementService(db_session)


@pytest.fixture
def sample_location(db_session):
    """Create a sample GHL location"""
    location = GHLLocation(
        ghl_location_id="loc_test_123",
        name="Test Location",
        company_id="company_123",
        has_whatsapp=True,
        whatsapp_number="+5511999999999",
        whatsapp_status="active"
    )
    db_session.add(location)
    db_session.commit()
    return location


@pytest.fixture
def sample_campaign(db_session, sample_location):
    """Create a sample campaign"""
    campaign = Campaign(
        name="Test Campaign",
        status="draft",
        ghl_location_id=sample_location.ghl_location_id,
        ghl_location_name=sample_location.name,
        ghl_user_id="user_123",
        ghl_user_name="Test User"
    )
    db_session.add(campaign)
    db_session.commit()
    return campaign


@pytest.fixture
def sample_messages(db_session, sample_campaign):
    """Create sample messages for a campaign"""
    messages = []
    for i in range(10):
        status = 'sent' if i < 3 else 'delivered' if i < 6 else 'read' if i < 9 else 'failed'
        msg = Message(
            campaign_id=sample_campaign.id,
            recipient_phone=f"+551199999{i:04d}",
            content="Test message",
            status=status,
            sent_at=datetime.now() if status != 'pending' else None
        )
        messages.append(msg)
        db_session.add(msg)
    db_session.commit()
    return messages


# T005-T009: Tests for service methods
class TestListCampaigns:
    """Tests for list_campaigns method"""

    def test_list_campaigns_empty(self, service):
        """Should return empty list when no campaigns exist"""
        result = service.list_campaigns()
        assert result == []

    def test_list_campaigns_with_data(self, service, sample_campaign, sample_messages):
        """Should return campaigns with message stats"""
        result = service.list_campaigns()
        assert len(result) == 1
        assert result[0]['id'] == sample_campaign.id
        assert result[0]['name'] == sample_campaign.name
        assert 'message_stats' in result[0]
        assert result[0]['message_stats']['total'] == 10
        assert result[0]['message_stats']['sent'] == 3
        assert result[0]['message_stats']['delivered'] == 3
        assert result[0]['message_stats']['read'] == 3
        assert result[0]['message_stats']['failed'] == 1

    def test_list_campaigns_status_filter(self, service, sample_campaign):
        """Should filter by status"""
        result = service.list_campaigns(filters={"status": "draft"})
        assert len(result) == 1

        result = service.list_campaigns(filters={"status": "executing"})
        assert len(result) == 0

    def test_list_campaigns_pagination(self, service, db_session, sample_location):
        """Should paginate correctly"""
        # Create 5 campaigns
        for i in range(5):
            campaign = Campaign(
                name=f"Campaign {i}",
                status="draft",
                ghl_location_id=sample_location.ghl_location_id
            )
            db_session.add(campaign)
        db_session.commit()

        result = service.list_campaigns(limit=2, offset=0)
        assert len(result) == 2

        result = service.list_campaigns(limit=2, offset=2)
        assert len(result) == 2


class TestGetCampaignDetails:
    """Tests for get_campaign_details method"""

    def test_get_campaign_details_valid(self, service, sample_campaign, sample_messages):
        """Should return campaign details"""
        result = service.get_campaign_details(sample_campaign.id)

        assert 'campaign' in result
        assert result['campaign']['id'] == sample_campaign.id

        assert 'statistics' in result
        assert result['statistics']['total_messages'] == 10
        assert result['statistics']['sent'] == 3

        assert 'timeline' in result
        assert isinstance(result['timeline'], list)
        assert len(result['timeline']) > 0

        assert 'recent_messages' in result
        assert len(result['recent_messages']) == 10

    def test_get_campaign_details_invalid_id(self, service):
        """Should raise ValueError for invalid ID"""
        with pytest.raises(ValueError, match="Campaign with id 99999 not found"):
            service.get_campaign_details(99999)


class TestGetCampaignLogs:
    """Tests for get_campaign_logs method"""

    def test_get_campaign_logs_valid(self, service, sample_campaign, sample_messages):
        """Should return campaign logs"""
        result = service.get_campaign_logs(sample_campaign.id)
        assert len(result) == 10

    def test_get_campaign_logs_status_filter(self, service, sample_campaign, sample_messages):
        """Should filter by status"""
        result = service.get_campaign_logs(sample_campaign.id, filters={"status": "sent"})
        assert len(result) == 3

    def test_get_campaign_logs_invalid_campaign(self, service):
        """Should raise ValueError for invalid campaign"""
        with pytest.raises(ValueError):
            service.get_campaign_logs(99999)


class TestGetCampaignStatistics:
    """Tests for get_campaign_statistics method"""

    def test_get_campaign_statistics(self, service, sample_campaign, sample_messages):
        """Should return statistics"""
        result = service.get_campaign_statistics()

        assert 'campaign_counts' in result
        assert result['campaign_counts']['draft'] == 1

        assert 'delivery_metrics' in result
        assert result['delivery_metrics']['total_messages'] == 10

        assert 'recent_campaigns' in result
        assert len(result['recent_campaigns']) == 1

        assert 'top_performing_campaigns' in result


class TestDeleteCampaign:
    """Tests for delete_campaign method"""

    def test_delete_campaign_draft(self, service, sample_campaign, sample_messages):
        """Should delete draft campaign"""
        result = service.delete_campaign(sample_campaign.id)
        assert result is True

    def test_delete_campaign_executing_fails(self, service, db_session, sample_location):
        """Should not delete executing campaign"""
        campaign = Campaign(
            name="Executing Campaign",
            status="executing",
            ghl_location_id=sample_location.ghl_location_id
        )
        db_session.add(campaign)
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot delete campaign"):
            service.delete_campaign(campaign.id)

    def test_delete_campaign_not_found(self, service):
        """Should raise ValueError for non-existent campaign"""
        with pytest.raises(ValueError, match="not found"):
            service.delete_campaign(99999)
