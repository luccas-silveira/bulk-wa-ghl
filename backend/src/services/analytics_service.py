"""
Analytics Service
Provides dashboard analytics and metrics for campaigns and messages
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.models.campaign import Campaign
from src.models.message import Message


async def get_campaign_metrics(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Campaign).where(Campaign.created_at >= date_threshold)
    if ghl_user_id:
        stmt = stmt.where(Campaign.ghl_user_id == ghl_user_id)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    return {
        'total_campaigns': len(campaigns),
        'draft_campaigns': sum(1 for c in campaigns if c.status == 'draft'),
        'scheduled_campaigns': sum(1 for c in campaigns if c.status == 'scheduled'),
        'active_campaigns': sum(1 for c in campaigns if c.status == 'executing'),
        'completed_campaigns': sum(1 for c in campaigns if c.status == 'completed'),
        'failed_campaigns': sum(1 for c in campaigns if c.status == 'failed'),
        'cancelled_campaigns': sum(1 for c in campaigns if c.status == 'cancelled'),
    }


async def get_delivery_metrics(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Message).where(Message.created_at >= date_threshold)
    if ghl_user_id:
        stmt = stmt.join(Campaign).where(Campaign.ghl_user_id == ghl_user_id)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    sent = sum(1 for m in messages if m.status == 'sent')
    delivered = sum(1 for m in messages if m.status in ('delivered', 'read'))
    failed = sum(1 for m in messages if m.status == 'failed')
    read = sum(1 for m in messages if m.status == 'read')
    pending = sum(1 for m in messages if m.status == 'pending')
    total = pending + sent + delivered + failed

    return {
        'sent': sent,
        'delivered': delivered,
        'failed': failed,
        'delivery_rate': round((sent + delivered) / total * 100, 1) if total > 0 else 0.0,
        'read_rate': round(read / total * 100, 1) if total > 0 else 0.0,
    }


async def get_recent_campaigns(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30,
    limit: int = 5
) -> List[Dict]:
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Campaign).where(Campaign.created_at >= date_threshold)
    if ghl_user_id:
        stmt = stmt.where(Campaign.ghl_user_id == ghl_user_id)
    stmt = stmt.order_by(desc(Campaign.created_at)).limit(limit)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    out = []
    for campaign in campaigns:
        msgs_result = await db.execute(
            select(Message).where(
                Message.campaign_id == campaign.id,
                Message.sent_at.isnot(None),
            )
        )
        messages = msgs_result.scalars().all()
        total_messages = len(messages)
        delivered = sum(1 for m in messages if m.status in ('delivered', 'read'))
        out.append({
            'id': campaign.id,
            'name': campaign.name,
            'status': campaign.status,
            'delivery_rate': round(delivered / total_messages * 100, 1) if total_messages > 0 else 0.0,
            'created_at': campaign.created_at.isoformat(),
            'messages_sent': total_messages,
        })
    return out


async def get_top_campaigns(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30,
    limit: int = 10
) -> List[Dict]:
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Campaign).where(Campaign.created_at >= date_threshold)
    if ghl_user_id:
        stmt = stmt.where(Campaign.ghl_user_id == ghl_user_id)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    campaign_metrics = []
    for campaign in campaigns:
        msgs_result = await db.execute(
            select(Message).where(
                Message.campaign_id == campaign.id,
                Message.sent_at.isnot(None),
            )
        )
        messages = msgs_result.scalars().all()
        total = len(messages)
        if total == 0:
            continue
        delivered = sum(1 for m in messages if m.status in ('delivered', 'read'))
        read = sum(1 for m in messages if m.status == 'read')
        campaign_metrics.append({
            'id': campaign.id,
            'name': campaign.name,
            'delivered_count': delivered,
            'delivery_rate': round(delivered / total * 100, 1),
            'read_rate': round(read / total * 100, 1),
        })

    campaign_metrics.sort(key=lambda x: (x['read_rate'], x['delivery_rate']), reverse=True)
    return campaign_metrics[:limit]


async def get_delivery_timeline(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    from collections import defaultdict

    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Message).where(
        Message.sent_at >= date_threshold,
        Message.sent_at.isnot(None),
    )
    if ghl_user_id:
        stmt = stmt.join(Campaign).where(Campaign.ghl_user_id == ghl_user_id)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    by_date: dict = defaultdict(lambda: {'sent': 0, 'delivered': 0, 'read': 0, 'total': 0})
    for m in messages:
        day = m.sent_at.date()
        by_date[day]['total'] += 1
        if m.status == 'sent':
            by_date[day]['sent'] += 1
        elif m.status in ('delivered', 'read'):
            by_date[day]['delivered'] += 1
            if m.status == 'read':
                by_date[day]['read'] += 1

    sorted_dates = sorted(by_date.keys())
    labels = [d.strftime('%d/%m') for d in sorted_dates]
    sent_list = [by_date[d]['sent'] for d in sorted_dates]
    delivered_list = [by_date[d]['delivered'] for d in sorted_dates]

    delivery_rate = []
    read_rate = []
    for d in sorted_dates:
        t = by_date[d]['total']
        delivery_rate.append(round(by_date[d]['delivered'] / t * 100, 1) if t > 0 else 0.0)
        read_rate.append(round(by_date[d]['read'] / t * 100, 1) if t > 0 else 0.0)

    return {
        'labels': labels,
        'sent': sent_list,
        'delivered': delivered_list,
        'delivery_rate': delivery_rate,
        'read_rate': read_rate,
    }
