"""
Analytics Service
Provides dashboard analytics and metrics for campaigns and messages
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.models.campaign import Campaign
from src.models.message import Message


def get_campaign_metrics(
    db: Session,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    """
    Get campaign counts by status within time range

    Args:
        db: Database session
        ghl_user_id: Optional filter by GHL user ID
        days: Number of days to look back (default 30)

    Returns:
        Dictionary with campaign counts by status
    """
    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query with time filter
    query = db.query(Campaign).filter(Campaign.created_at >= date_threshold)

    # Add user filter if provided
    if ghl_user_id:
        query = query.filter(Campaign.ghl_user_id == ghl_user_id)

    # Get all campaigns
    campaigns = query.all()

    # Count by status
    total = len(campaigns)
    draft = len([c for c in campaigns if c.status == 'draft'])
    scheduled = len([c for c in campaigns if c.status == 'scheduled'])
    active = len([c for c in campaigns if c.status == 'executing'])
    completed = len([c for c in campaigns if c.status == 'completed'])
    failed = len([c for c in campaigns if c.status == 'failed'])
    cancelled = len([c for c in campaigns if c.status == 'cancelled'])

    return {
        'total_campaigns': total,
        'draft_campaigns': draft,
        'scheduled_campaigns': scheduled,
        'active_campaigns': active,
        'completed_campaigns': completed,
        'failed_campaigns': failed,
        'cancelled_campaigns': cancelled
    }


def get_delivery_metrics(
    db: Session,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    """
    Get message delivery statistics and rates

    Args:
        db: Database session
        ghl_user_id: Optional filter by GHL user ID
        days: Number of days to look back (default 30)

    Returns:
        Dictionary with delivery metrics and rates
    """
    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query: messages in time range (include both sent and failed)
    query = db.query(Message).filter(Message.created_at >= date_threshold)

    # Filter by user through campaign relationship if provided
    if ghl_user_id:
        query = query.join(Campaign).filter(
            Campaign.ghl_user_id == ghl_user_id
        )

    # Get all messages
    messages = query.all()

    # Count by status
    sent = len([m for m in messages if m.status == 'sent'])
    delivered = len([m for m in messages if m.status in ('delivered', 'read')])
    failed = len([m for m in messages if m.status == 'failed'])
    read = len([m for m in messages if m.status == 'read'])

    # Calculate total — include pending to avoid inflating rate during execution
    pending = len([m for m in messages if m.status == 'pending'])
    total = pending + sent + delivered + failed

    # Calculate rates
    if total > 0:
        delivery_rate = round((sent + delivered) / total * 100, 1)
        read_rate = round(read / total * 100, 1)
    else:
        delivery_rate = 0.0
        read_rate = 0.0

    return {
        'sent': sent,
        'delivered': delivered,
        'failed': failed,
        'delivery_rate': delivery_rate,
        'read_rate': read_rate
    }


def get_recent_campaigns(
    db: Session,
    ghl_user_id: Optional[str] = None,
    days: int = 30,
    limit: int = 5
) -> List[Dict]:
    """
    Get most recent campaigns with delivery metrics

    Args:
        db: Database session
        ghl_user_id: Optional filter by GHL user ID
        days: Number of days to look back (default 30)
        limit: Maximum number of campaigns to return (default 5)

    Returns:
        List of campaign dictionaries with metrics
    """
    from sqlalchemy import desc

    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query with filters
    query = db.query(Campaign).filter(Campaign.created_at >= date_threshold)

    # Add user filter if provided
    if ghl_user_id:
        query = query.filter(Campaign.ghl_user_id == ghl_user_id)

    # Order by created_at DESC and limit
    campaigns = query.order_by(desc(Campaign.created_at)).limit(limit).all()

    # Build result with delivery metrics for each campaign
    result = []
    for campaign in campaigns:
        # Get messages for this campaign
        messages = db.query(Message).filter(
            Message.campaign_id == campaign.id,
            Message.sent_at.isnot(None)
        ).all()

        total_messages = len(messages)
        delivered = len([m for m in messages if m.status in ('delivered', 'read')])

        # Calculate delivery rate
        delivery_rate = round(delivered / total_messages * 100, 1) if total_messages > 0 else 0.0

        result.append({
            'id': campaign.id,
            'name': campaign.name,
            'status': campaign.status,
            'delivery_rate': delivery_rate,
            'created_at': campaign.created_at.isoformat(),
            'messages_sent': total_messages
        })

    return result


def get_top_campaigns(
    db: Session,
    ghl_user_id: Optional[str] = None,
    days: int = 30,
    limit: int = 10
) -> List[Dict]:
    """
    Get top performing campaigns ranked by read rate

    Args:
        db: Database session
        ghl_user_id: Optional filter by GHL user ID
        days: Number of days to look back (default 30)
        limit: Maximum number of campaigns to return (default 10)

    Returns:
        List of campaign dictionaries ranked by performance
    """
    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query with filters
    query = db.query(Campaign).filter(Campaign.created_at >= date_threshold)

    # Add user filter if provided
    if ghl_user_id:
        query = query.filter(Campaign.ghl_user_id == ghl_user_id)

    campaigns = query.all()

    # Calculate metrics for each campaign
    campaign_metrics = []
    for campaign in campaigns:
        # Get messages for this campaign
        messages = db.query(Message).filter(
            Message.campaign_id == campaign.id,
            Message.sent_at.isnot(None)
        ).all()

        total = len(messages)
        if total == 0:
            continue  # Skip campaigns with no messages

        delivered = len([m for m in messages if m.status in ('delivered', 'read')])
        read = len([m for m in messages if m.status == 'read'])

        delivery_rate = round(delivered / total * 100, 1)
        read_rate = round(read / total * 100, 1)

        campaign_metrics.append({
            'id': campaign.id,
            'name': campaign.name,
            'delivered_count': delivered,
            'delivery_rate': delivery_rate,
            'read_rate': read_rate
        })

    # Sort by read_rate DESC, then delivery_rate DESC
    campaign_metrics.sort(key=lambda x: (x['read_rate'], x['delivery_rate']), reverse=True)

    return campaign_metrics[:limit]
