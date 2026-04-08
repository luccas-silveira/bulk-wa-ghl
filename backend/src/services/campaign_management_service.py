"""
Campaign Management Service
Handles campaign listing, details, logs, statistics, and deletion operations
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from src.models.campaign import Campaign
from src.models.message import Message


class CampaignManagementService:
    """
    Service for campaign management operations

    This service handles read operations and management actions for campaigns,
    separate from campaign execution logic (handled by CampaignExecutorService).
    """

    def __init__(self, db: Session):
        """
        Initialize the service with a database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def list_campaigns(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List campaigns with filters and pagination

        Args:
            filters: Optional filters (status, ghl_user_id, ghl_location_id, from_date, to_date)
            limit: Maximum number of campaigns to return
            offset: Number of campaigns to skip

        Returns:
            List of campaign dictionaries with message statistics
        """
        query = self.db.query(Campaign)

        # Apply filters
        if filters:
            if 'status' in filters:
                query = query.filter(Campaign.status == filters['status'])
            if 'ghl_user_id' in filters:
                query = query.filter(Campaign.ghl_user_id == filters['ghl_user_id'])
            if 'ghl_location_id' in filters:
                query = query.filter(Campaign.ghl_location_id == filters['ghl_location_id'])
            if 'from_date' in filters:
                query = query.filter(Campaign.created_at >= filters['from_date'])
            if 'to_date' in filters:
                query = query.filter(Campaign.created_at <= filters['to_date'])

        # Order by created_at DESC, apply pagination
        campaigns = query.order_by(Campaign.created_at.desc()).limit(limit).offset(offset).all()

        # Build result with message statistics
        result = []
        for campaign in campaigns:
            # Get message stats for this campaign
            msg_stats = self.db.query(
                func.count(Message.id).label('total'),
                func.sum(case((Message.status == 'sent', 1), else_=0)).label('sent'),
                func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
                func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
                func.sum(case((Message.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((Message.status == 'pending', 1), else_=0)).label('pending')
            ).filter(Message.campaign_id == campaign.id).first()

            campaign_dict = campaign.to_dict()
            campaign_dict['message_stats'] = {
                'total': msg_stats.total or 0,
                'sent': msg_stats.sent or 0,
                'delivered': msg_stats.delivered or 0,
                'read': msg_stats.read or 0,
                'failed': msg_stats.failed or 0,
                'pending': msg_stats.pending or 0
            }

            # Calculate progress_percent for executing campaigns
            if campaign.status == 'executing':
                total = msg_stats.total or 0
                completed = (msg_stats.sent or 0) + (msg_stats.delivered or 0) + (msg_stats.read or 0) + (msg_stats.failed or 0)
                campaign_dict['progress_percent'] = round((completed / total * 100), 2) if total > 0 else 0.0

            result.append(campaign_dict)

        return result

    def get_campaign_details(self, campaign_id: int) -> Dict[str, Any]:
        """
        Get detailed campaign information including statistics and timeline

        Args:
            campaign_id: Campaign ID

        Returns:
            Dictionary with campaign, statistics, progress, timeline, recent_messages

        Raises:
            ValueError: If campaign not found
        """
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign with id {campaign_id} not found")

        # Get message statistics
        msg_stats = self.db.query(
            func.count(Message.id).label('total_messages'),
            func.sum(case((Message.status == 'sent', 1), else_=0)).label('sent'),
            func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
            func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
            func.sum(case((Message.status == 'failed', 1), else_=0)).label('failed'),
            func.sum(case((Message.status == 'pending', 1), else_=0)).label('pending')
        ).filter(Message.campaign_id == campaign_id).first()

        total = msg_stats.total_messages or 0
        delivered = msg_stats.delivered or 0
        read = msg_stats.read or 0

        statistics = {
            'total_messages': total,
            'sent': msg_stats.sent or 0,
            'delivered': delivered,
            'read': read,
            'failed': msg_stats.failed or 0,
            'pending': msg_stats.pending or 0,
            'delivery_rate': round((delivered / total * 100), 2) if total > 0 else 0.0,
            'read_rate': round((read / total * 100), 2) if total > 0 else 0.0
        }

        # Generate timeline events
        timeline = []
        timeline.append({
            'event': 'Campaign Created',
            'timestamp': campaign.created_at.isoformat() if campaign.created_at else None
        })

        if campaign.scheduled_time:
            timeline.append({
                'event': 'Campaign Scheduled',
                'timestamp': campaign.scheduled_time.isoformat()
            })

        if campaign.status == 'executing' or campaign.status == 'completed':
            # Find first sent message
            first_msg = self.db.query(Message).filter(
                Message.campaign_id == campaign_id,
                Message.sent_at.isnot(None)
            ).order_by(Message.sent_at.asc()).first()
            if first_msg:
                timeline.append({
                    'event': 'Campaign Started',
                    'timestamp': first_msg.sent_at.isoformat()
                })

        if campaign.paused_at:
            timeline.append({
                'event': 'Campaign Paused',
                'timestamp': campaign.paused_at.isoformat()
            })

        if campaign.status == 'completed':
            timeline.append({
                'event': 'Campaign Completed',
                'timestamp': campaign.updated_at.isoformat() if campaign.updated_at else None
            })

        # Get last 50 messages
        recent_messages = self.db.query(Message).filter(
            Message.campaign_id == campaign_id
        ).order_by(Message.sent_at.desc()).limit(50).all()

        return {
            'campaign': campaign.to_dict(),
            'statistics': statistics,
            'timeline': timeline,
            'recent_messages': [msg.to_dict() for msg in recent_messages]
        }

    def get_campaign_logs(
        self,
        campaign_id: int,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get campaign message logs with filtering and pagination

        Args:
            campaign_id: Campaign ID
            filters: Optional filters (status, recipient)
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of message dictionaries

        Raises:
            ValueError: If campaign not found
        """
        # Verify campaign exists
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign with id {campaign_id} not found")

        # Build query
        query = self.db.query(Message).filter(Message.campaign_id == campaign_id)

        # Apply filters
        if filters:
            if 'status' in filters:
                query = query.filter(Message.status == filters['status'])
            if 'recipient' in filters:
                escaped = filters['recipient'].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                query = query.filter(Message.recipient_phone.like(f"%{escaped}%", escape="\\"))

        # Order by sent_at DESC, apply pagination
        messages = query.order_by(Message.sent_at.desc()).limit(limit).offset(offset).all()

        return [msg.to_dict() for msg in messages]

    def get_campaign_statistics(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics across campaigns

        Args:
            filters: Optional filters (ghl_user_id, ghl_location_id, from_date, to_date)

        Returns:
            Dictionary with campaign_counts, delivery_metrics, recent_campaigns, top_performing_campaigns
        """
        # Build base query for campaigns
        campaign_query = self.db.query(Campaign)

        # Apply filters
        if filters:
            if 'ghl_user_id' in filters:
                campaign_query = campaign_query.filter(Campaign.ghl_user_id == filters['ghl_user_id'])
            if 'ghl_location_id' in filters:
                campaign_query = campaign_query.filter(Campaign.ghl_location_id == filters['ghl_location_id'])
            if 'from_date' in filters:
                campaign_query = campaign_query.filter(Campaign.created_at >= filters['from_date'])
            if 'to_date' in filters:
                campaign_query = campaign_query.filter(Campaign.created_at <= filters['to_date'])

        # Campaign counts by status
        campaign_counts = {}
        for status in ['draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled']:
            count = campaign_query.filter(Campaign.status == status).count()
            campaign_counts[status] = count

        # Get all campaign IDs matching filters
        campaign_ids = [c.id for c in campaign_query.all()]

        # Calculate delivery metrics across all messages
        if campaign_ids:
            msg_agg = self.db.query(
                func.count(Message.id).label('total'),
                func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
                func.sum(case((Message.status == 'read', 1), else_=0)).label('read')
            ).filter(Message.campaign_id.in_(campaign_ids)).first()

            total_messages = msg_agg.total or 0
            delivered = msg_agg.delivered or 0
            read = msg_agg.read or 0

            delivery_metrics = {
                'total_messages': total_messages,
                'avg_delivery_rate': round((delivered / total_messages * 100), 2) if total_messages > 0 else 0.0,
                'avg_read_rate': round((read / total_messages * 100), 2) if total_messages > 0 else 0.0
            }
        else:
            delivery_metrics = {
                'total_messages': 0,
                'avg_delivery_rate': 0.0,
                'avg_read_rate': 0.0
            }

        # Recent 10 campaigns
        recent_campaigns_query = campaign_query.order_by(Campaign.created_at.desc()).limit(10).all()
        recent_campaigns = [c.to_dict() for c in recent_campaigns_query]

        # Top 10 performing campaigns by read rate (single query instead of N+1)
        top_performers = []
        if campaign_ids:
            campaign_stats = self.db.query(
                Campaign,
                func.count(Message.id).label('total'),
                func.sum(case((Message.status == 'read', 1), else_=0)).label('read')
            ).outerjoin(Message, Message.campaign_id == Campaign.id).filter(
                Campaign.id.in_(campaign_ids)
            ).group_by(Campaign.id).all()

            for campaign, total, read_count in campaign_stats:
                total = total or 0
                read_count = read_count or 0
                read_rate = round((read_count / total * 100), 2) if total > 0 else 0.0

                campaign_dict = campaign.to_dict()
                campaign_dict['read_rate'] = read_rate
                top_performers.append(campaign_dict)

            # Sort by read_rate descending and take top 10
            top_performers = sorted(top_performers, key=lambda x: x['read_rate'], reverse=True)[:10]

        return {
            'campaign_counts': campaign_counts,
            'delivery_metrics': delivery_metrics,
            'recent_campaigns': recent_campaigns,
            'top_performing_campaigns': top_performers
        }

    def delete_campaign(self, campaign_id: int) -> bool:
        """
        Delete a campaign and all its messages

        Args:
            campaign_id: Campaign ID

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If campaign not found or has invalid status for deletion
        """
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign with id {campaign_id} not found")

        # Cannot delete executing or scheduled campaigns
        if campaign.status in ['executing', 'scheduled']:
            raise ValueError(f"Cannot delete campaign with status '{campaign.status}'. Please pause or cancel it first.")

        # Delete campaign (messages will be cascade deleted)
        self.db.delete(campaign)
        self.db.commit()

        return True
