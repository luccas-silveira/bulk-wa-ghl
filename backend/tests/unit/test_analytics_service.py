"""
Unit tests for Analytics Service
Following TDD approach - tests written before implementation
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from src.models.campaign import Campaign
from src.models.message import Message
from src.services.analytics_service import (
    get_campaign_metrics,
    get_delivery_metrics,
    get_recent_campaigns,
    get_top_campaigns
)


@pytest.mark.asyncio
class TestGetCampaignMetrics:
    """Tests for get_campaign_metrics() function"""

    async def test_no_campaigns_returns_all_zeros(self, db_session):
        """Test with no campaigns returns all zeros"""
        result = await get_campaign_metrics(db_session)

        assert result == {
            'total_campaigns': 0,
            'draft_campaigns': 0,
            'scheduled_campaigns': 0,
            'active_campaigns': 0,
            'completed_campaigns': 0,
            'failed_campaigns': 0,
            'cancelled_campaigns': 0
        }

    async def test_campaigns_of_different_statuses(self, db_session):
        """Test with campaigns of different statuses"""
        # Create campaigns with different statuses
        statuses = ['draft', 'scheduled', 'executing', 'completed', 'failed', 'cancelled']
        for i, status in enumerate(statuses):
            campaign = Campaign(
                name=f"Campaign {i}",
                status=status,
                ghl_location_id="loc_123"
            )
            db_session.add(campaign)
        await db_session.commit()

        result = await get_campaign_metrics(db_session)

        assert result['total_campaigns'] == 6
        assert result['draft_campaigns'] == 1
        assert result['scheduled_campaigns'] == 1
        assert result['active_campaigns'] == 1
        assert result['completed_campaigns'] == 1
        assert result['failed_campaigns'] == 1
        assert result['cancelled_campaigns'] == 1

    async def test_with_user_filter(self, db_session):
        """Test with user filter (ghl_user_id)"""
        # Create campaigns for different users
        for i in range(3):
            campaign = Campaign(
                name=f"Campaign User1 {i}",
                status='completed',
                ghl_location_id="loc_123",
                ghl_user_id="user_1"
            )
            db_session.add(campaign)

        for i in range(2):
            campaign = Campaign(
                name=f"Campaign User2 {i}",
                status='completed',
                ghl_location_id="loc_123",
                ghl_user_id="user_2"
            )
            db_session.add(campaign)
        await db_session.commit()

        result = await get_campaign_metrics(db_session, ghl_user_id="user_1")

        assert result['total_campaigns'] == 3
        assert result['completed_campaigns'] == 3

    async def test_with_time_range_filter(self, db_session):
        """Test with time range filter (days)"""
        now = datetime.now()

        # Campaign within range (20 days ago)
        campaign1 = Campaign(
            name="Recent Campaign",
            status='completed',
            ghl_location_id="loc_123",
            created_at=now - timedelta(days=20)
        )
        db_session.add(campaign1)

        # Campaign outside range (40 days ago)
        campaign2 = Campaign(
            name="Old Campaign",
            status='completed',
            ghl_location_id="loc_123",
            created_at=now - timedelta(days=40)
        )
        db_session.add(campaign2)
        await db_session.commit()

        result = await get_campaign_metrics(db_session, days=30)

        assert result['total_campaigns'] == 1
        assert result['completed_campaigns'] == 1

    async def test_with_combined_filters(self, db_session):
        """Test with combined user and time filters"""
        now = datetime.now()

        # Campaign matching both filters
        campaign1 = Campaign(
            name="Matching Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign1)

        # Campaign matching only user filter (outside time range)
        campaign2 = Campaign(
            name="Old User Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=40)
        )
        db_session.add(campaign2)

        # Campaign matching only time filter (different user)
        campaign3 = Campaign(
            name="Different User Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_2",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign3)
        await db_session.commit()

        result = await get_campaign_metrics(db_session, ghl_user_id="user_1", days=30)

        assert result['total_campaigns'] == 1
        assert result['completed_campaigns'] == 1


@pytest.mark.asyncio
class TestGetDeliveryMetrics:
    """Tests for get_delivery_metrics() function"""

    async def test_no_messages_returns_zeros(self, db_session):
        """Test with no messages returns zeros and 0.0 rates"""
        result = await get_delivery_metrics(db_session)

        assert result == {
            'sent': 0,
            'delivered': 0,
            'failed': 0,
            'delivery_rate': 0.0,
            'read_rate': 0.0
        }

    async def test_delivery_rate_calculation(self, db_session):
        """Test delivery rate calculation"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # Create 10 messages: 8 delivered, 2 failed
        for i in range(8):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(2):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='failed',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_delivery_metrics(db_session)

        assert result['delivered'] == 8
        assert result['failed'] == 2
        assert result['delivery_rate'] == 80.0  # (8/10) * 100

    async def test_read_rate_calculation(self, db_session):
        """Test read rate calculation"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # Create 10 messages: 6 read, 4 only delivered
        for i in range(6):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='read',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(4):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_delivery_metrics(db_session)

        assert result['read_rate'] == 60.0  # (6/10) * 100
        assert result['delivery_rate'] == 100.0  # All delivered

    async def test_with_failed_messages(self, db_session):
        """Test with failed messages"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # 5 sent, 3 delivered, 2 failed
        for i in range(5):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='sent',
                ghl_status='sent',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(3):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(2):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511777{i:06d}",
                content="Test message",
                status='failed',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_delivery_metrics(db_session)

        assert result['sent'] == 5
        assert result['delivered'] == 3
        assert result['failed'] == 2
        # delivery_rate = (sent + delivered) / total * 100 = (5 + 3) / 10 * 100 = 80.0
        assert result['delivery_rate'] == 80.0

    async def test_division_by_zero_safety(self, db_session):
        """Test division by zero safety"""
        # No messages at all
        result = await get_delivery_metrics(db_session)

        assert result['delivery_rate'] == 0.0
        assert result['read_rate'] == 0.0

    async def test_with_user_filter(self, db_session):
        """Test with user filter through campaign relationship"""
        campaign1 = Campaign(
            name="User1 Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1"
        )
        campaign2 = Campaign(
            name="User2 Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_2"
        )
        db_session.add(campaign1)
        db_session.add(campaign2)
        await db_session.commit()

        now = datetime.now()

        # 3 messages for user_1
        for i in range(3):
            message = Message(
                campaign_id=campaign1.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        # 2 messages for user_2
        for i in range(2):
            message = Message(
                campaign_id=campaign2.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_delivery_metrics(db_session, ghl_user_id="user_1")

        assert result['delivered'] == 3

    async def test_with_time_filter(self, db_session):
        """Test with time range filter"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # Recent messages (within 30 days)
        for i in range(3):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=10)
            )
            db_session.add(message)

        # Old messages (outside 30 days — set created_at explicitly so the service time filter excludes them)
        for i in range(2):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='delivered',
                created_at=now - timedelta(days=40),
                sent_at=now - timedelta(days=40)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_delivery_metrics(db_session, days=30)

        assert result['delivered'] == 3

    async def test_pending_messages_included_in_denominator(self, db_session):
        """ANA-03: pending messages dilute delivery rate — not counted as success"""
        campaign = Campaign(
            name="Test Campaign",
            status='executing',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # 5 delivered, 5 still pending → delivery rate must be 50%, not 100%
        for i in range(5):
            db_session.add(Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=1)
            ))
        for i in range(5):
            db_session.add(Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='pending',
                sent_at=None
            ))
        await db_session.commit()

        result = await get_delivery_metrics(db_session)

        assert result['delivered'] == 5
        assert result['delivery_rate'] == 50.0  # 5 / (5 delivered + 5 pending) = 50%


@pytest.mark.asyncio
class TestGetRecentCampaigns:
    """Tests for get_recent_campaigns() function"""

    async def test_ordering_by_created_at_desc(self, db_session):
        """Test ordering by created_at DESC"""
        now = datetime.now()

        # Create campaigns with different dates
        for i in range(5):
            campaign = Campaign(
                name=f"Campaign {i}",
                status='completed',
                ghl_location_id="loc_123",
                created_at=now - timedelta(days=i)
            )
            db_session.add(campaign)
        await db_session.commit()

        result = await get_recent_campaigns(db_session)

        assert len(result) == 5
        # Most recent should be first (days=0)
        assert result[0]['name'] == "Campaign 0"
        assert result[4]['name'] == "Campaign 4"

    async def test_limit_parameter(self, db_session):
        """Test limit parameter (default 5)"""
        now = datetime.now()

        # Create 10 campaigns
        for i in range(10):
            campaign = Campaign(
                name=f"Campaign {i}",
                status='completed',
                ghl_location_id="loc_123",
                created_at=now - timedelta(days=i)
            )
            db_session.add(campaign)
        await db_session.commit()

        # Default limit (5)
        result = await get_recent_campaigns(db_session)
        assert len(result) == 5

        # Custom limit (3)
        result = await get_recent_campaigns(db_session, limit=3)
        assert len(result) == 3

    async def test_with_user_and_time_filters(self, db_session):
        """Test with user and time filters"""
        now = datetime.now()

        # Campaign matching filters
        campaign1 = Campaign(
            name="Matching Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign1)

        # Campaign not matching (different user)
        campaign2 = Campaign(
            name="Different User",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_2",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign2)

        # Campaign not matching (outside time range)
        campaign3 = Campaign(
            name="Old Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=40)
        )
        db_session.add(campaign3)
        await db_session.commit()

        result = await get_recent_campaigns(db_session, ghl_user_id="user_1", days=30)

        assert len(result) == 1
        assert result[0]['name'] == "Matching Campaign"

    async def test_delivery_rate_calculation_per_campaign(self, db_session):
        """Test delivery rate calculation per campaign"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()

        # 7 delivered, 3 failed = 70% delivery rate
        for i in range(7):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(3):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511888{i:06d}",
                content="Test message",
                status='failed',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_recent_campaigns(db_session)

        assert len(result) == 1
        assert result[0]['id'] == campaign.id
        assert result[0]['name'] == "Test Campaign"
        assert result[0]['status'] == 'completed'
        assert result[0]['delivery_rate'] == 70.0
        assert result[0]['messages_sent'] == 10
        assert 'created_at' in result[0]

    async def test_with_campaigns_having_no_messages(self, db_session):
        """Test with campaigns having no messages"""
        campaign = Campaign(
            name="Empty Campaign",
            status='draft',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        result = await get_recent_campaigns(db_session)

        assert len(result) == 1
        assert result[0]['delivery_rate'] == 0.0
        assert result[0]['messages_sent'] == 0


@pytest.mark.asyncio
class TestGetTopCampaigns:
    """Tests for get_top_campaigns() function"""

    async def test_ranking_by_read_rate_desc(self, db_session):
        """Test ranking by read_rate DESC"""
        now = datetime.now()

        # Create campaigns with different read rates
        campaigns_data = [
            ("Campaign 30% read", 0.3),
            ("Campaign 80% read", 0.8),
            ("Campaign 50% read", 0.5),
        ]

        for name, read_rate in campaigns_data:
            campaign = Campaign(
                name=name,
                status='completed',
                ghl_location_id="loc_123"
            )
            db_session.add(campaign)
            await db_session.commit()

            # Create 10 messages with specific read rate
            read_count = int(10 * read_rate)
            for i in range(read_count):
                message = Message(
                    campaign_id=campaign.id,
                    recipient_phone=f"+5511{campaign.id:03d}{i:06d}",
                    content="Test message",
                    status='read',
                    sent_at=now - timedelta(days=5)
                )
                db_session.add(message)

            for i in range(10 - read_count):
                message = Message(
                    campaign_id=campaign.id,
                    recipient_phone=f"+5511{campaign.id:03d}{i+read_count:06d}",
                    content="Test message",
                    status='delivered',
                    sent_at=now - timedelta(days=5)
                )
                db_session.add(message)
            await db_session.commit()

        result = await get_top_campaigns(db_session)

        assert len(result) == 3
        # Should be ordered by read_rate DESC: 80%, 50%, 30%
        assert result[0]['name'] == "Campaign 80% read"
        assert result[0]['read_rate'] == 80.0
        assert result[1]['name'] == "Campaign 50% read"
        assert result[1]['read_rate'] == 50.0
        assert result[2]['name'] == "Campaign 30% read"
        assert result[2]['read_rate'] == 30.0

    async def test_secondary_sort_by_delivery_rate(self, db_session):
        """Test secondary sort by delivery_rate when read_rate is equal"""
        now = datetime.now()

        # Create 2 campaigns with same read rate but different delivery rates
        # Campaign 1: 50% read, 80% delivery
        campaign1 = Campaign(
            name="Campaign 1",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign1)
        await db_session.commit()

        for i in range(5):
            message = Message(
                campaign_id=campaign1.id,
                recipient_phone=f"+551199900{i:04d}",
                content="Test message",
                status='read',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(3):
            message = Message(
                campaign_id=campaign1.id,
                recipient_phone=f"+551199901{i:04d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(2):
            message = Message(
                campaign_id=campaign1.id,
                recipient_phone=f"+551199902{i:04d}",
                content="Test message",
                status='failed',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        # Campaign 2: 50% read, 90% delivery
        campaign2 = Campaign(
            name="Campaign 2",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign2)
        await db_session.commit()

        for i in range(5):
            message = Message(
                campaign_id=campaign2.id,
                recipient_phone=f"+551188800{i:04d}",
                content="Test message",
                status='read',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(4):
            message = Message(
                campaign_id=campaign2.id,
                recipient_phone=f"+551188801{i:04d}",
                content="Test message",
                status='delivered',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)

        for i in range(1):
            message = Message(
                campaign_id=campaign2.id,
                recipient_phone=f"+551188802{i:04d}",
                content="Test message",
                status='failed',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_top_campaigns(db_session)

        assert len(result) == 2
        # Both have 50% read rate, but Campaign 2 has higher delivery rate
        assert result[0]['name'] == "Campaign 2"
        assert result[0]['read_rate'] == 50.0
        assert result[0]['delivery_rate'] == 90.0
        assert result[1]['name'] == "Campaign 1"
        assert result[1]['read_rate'] == 50.0
        assert result[1]['delivery_rate'] == 80.0

    async def test_limit_parameter(self, db_session):
        """Test limit parameter (default 10)"""
        now = datetime.now()

        # Create 15 campaigns
        for i in range(15):
            campaign = Campaign(
                name=f"Campaign {i}",
                status='completed',
                ghl_location_id="loc_123"
            )
            db_session.add(campaign)
            await db_session.commit()

            # Each with 10 messages, all delivered
            for j in range(10):
                message = Message(
                    campaign_id=campaign.id,
                    recipient_phone=f"+5511{i:03d}{j:06d}",
                    content="Test message",
                    status='delivered',
                    sent_at=now - timedelta(days=5)
                )
                db_session.add(message)
            await db_session.commit()

        # Default limit (10)
        result = await get_top_campaigns(db_session)
        assert len(result) == 10

        # Custom limit (5)
        result = await get_top_campaigns(db_session, limit=5)
        assert len(result) == 5

    async def test_excludes_campaigns_with_no_messages(self, db_session):
        """Test excludes campaigns with no messages"""
        # Campaign with messages
        campaign1 = Campaign(
            name="Campaign with messages",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign1)
        await db_session.commit()

        now = datetime.now()
        message = Message(
            campaign_id=campaign1.id,
            recipient_phone="+5511999000001",
            content="Test message",
            status='delivered',
            sent_at=now - timedelta(days=5)
        )
        db_session.add(message)

        # Campaign without messages
        campaign2 = Campaign(
            name="Empty Campaign",
            status='draft',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign2)
        await db_session.commit()

        result = await get_top_campaigns(db_session)

        assert len(result) == 1
        assert result[0]['name'] == "Campaign with messages"

    async def test_with_user_and_time_filters(self, db_session):
        """Test with user and time filters"""
        now = datetime.now()

        # Campaign matching filters
        campaign1 = Campaign(
            name="Matching Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign1)
        await db_session.commit()

        message = Message(
            campaign_id=campaign1.id,
            recipient_phone="+5511999000001",
            content="Test message",
            status='delivered',
            sent_at=now - timedelta(days=5)
        )
        db_session.add(message)

        # Campaign not matching (different user)
        campaign2 = Campaign(
            name="Different User",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_2",
            created_at=now - timedelta(days=10)
        )
        db_session.add(campaign2)
        await db_session.commit()

        message = Message(
            campaign_id=campaign2.id,
            recipient_phone="+5511999000002",
            content="Test message",
            status='delivered',
            sent_at=now - timedelta(days=5)
        )
        db_session.add(message)

        # Campaign not matching (outside time range)
        campaign3 = Campaign(
            name="Old Campaign",
            status='completed',
            ghl_location_id="loc_123",
            ghl_user_id="user_1",
            created_at=now - timedelta(days=40)
        )
        db_session.add(campaign3)
        await db_session.commit()

        message = Message(
            campaign_id=campaign3.id,
            recipient_phone="+5511999000003",
            content="Test message",
            status='delivered',
            sent_at=now - timedelta(days=35)
        )
        db_session.add(message)
        await db_session.commit()

        result = await get_top_campaigns(db_session, ghl_user_id="user_1", days=30)

        assert len(result) == 1
        assert result[0]['name'] == "Matching Campaign"

    async def test_result_structure(self, db_session):
        """Test result structure has all required fields"""
        campaign = Campaign(
            name="Test Campaign",
            status='completed',
            ghl_location_id="loc_123"
        )
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now()
        for i in range(10):
            message = Message(
                campaign_id=campaign.id,
                recipient_phone=f"+5511999{i:06d}",
                content="Test message",
                status='read',
                sent_at=now - timedelta(days=5)
            )
            db_session.add(message)
        await db_session.commit()

        result = await get_top_campaigns(db_session)

        assert len(result) == 1
        assert 'id' in result[0]
        assert 'name' in result[0]
        assert 'delivered_count' in result[0]
        assert 'read_rate' in result[0]
        assert 'delivery_rate' in result[0]
        assert result[0]['delivered_count'] == 10
        assert result[0]['read_rate'] == 100.0
        assert result[0]['delivery_rate'] == 100.0


@pytest.mark.asyncio
class TestGetDeliveryTimeline:
    """ANA-01: timeline data for dashboard charts"""

    async def test_returns_empty_when_no_messages(self, db_session):
        from src.services.analytics_service import get_delivery_timeline
        result = await get_delivery_timeline(db_session, days=30)
        assert result == {
            'labels': [],
            'sent': [],
            'delivered': [],
            'delivery_rate': [],
            'read_rate': [],
        }

    async def test_groups_messages_by_date(self, db_session):
        from src.services.analytics_service import get_delivery_timeline
        from datetime import datetime, timedelta, timezone

        campaign = Campaign(name="TL", status='completed', ghl_location_id="loc1")
        db_session.add(campaign)
        await db_session.commit()

        today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)

        # Today: 3 sent, 2 delivered
        for _ in range(3):
            db_session.add(Message(campaign_id=campaign.id, recipient_phone="+5511000000001",
                                   content="m", status='sent', sent_at=today))
        for _ in range(2):
            db_session.add(Message(campaign_id=campaign.id, recipient_phone="+5511000000002",
                                   content="m", status='delivered', sent_at=today))
        # Yesterday: 4 delivered, 1 read
        for _ in range(4):
            db_session.add(Message(campaign_id=campaign.id, recipient_phone="+5511000000003",
                                   content="m", status='delivered', sent_at=yesterday))
        db_session.add(Message(campaign_id=campaign.id, recipient_phone="+5511000000004",
                               content="m", status='read', sent_at=yesterday))
        await db_session.commit()

        result = await get_delivery_timeline(db_session, days=30)

        assert len(result['labels']) == 2
        # Labels sorted ascending (yesterday first)
        assert result['labels'][0] == yesterday.strftime('%d/%m')
        assert result['labels'][1] == today.strftime('%d/%m')
        # Yesterday: 5 total, 5 delivered/read → 100% delivery rate, 20% read rate
        assert result['sent'][0] == 0
        assert result['delivered'][0] == 5   # 4 delivered + 1 read
        assert result['delivery_rate'][0] == 100.0
        assert result['read_rate'][0] == 20.0  # 1/5
        # Today: 5 total, 2 delivered → 40% delivery rate
        assert result['sent'][1] == 3
        assert result['delivered'][1] == 2
        assert result['delivery_rate'][1] == 40.0  # 2/5

    async def test_respects_days_filter(self, db_session):
        from src.services.analytics_service import get_delivery_timeline
        from datetime import datetime, timedelta, timezone

        campaign = Campaign(name="TL2", status='completed', ghl_location_id="loc1")
        db_session.add(campaign)
        await db_session.commit()

        now = datetime.now(timezone.utc)
        # One message 40 days ago (outside 30-day window)
        db_session.add(Message(campaign_id=campaign.id, recipient_phone="+5511000000005",
                               content="m", status='sent', sent_at=now - timedelta(days=40)))
        await db_session.commit()

        result = await get_delivery_timeline(db_session, days=30)
        assert result['labels'] == []
