"""
Analytics Service
Provides dashboard analytics and metrics for campaigns and messages
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, desc

from src.models.campaign import Campaign
from src.models.message import Message


async def get_campaign_metrics(
    db: AsyncSession,
    ghl_user_id: Optional[str] = None,
    days: int = 30
) -> Dict:
    """Return campaign status counts via a single SQL GROUP BY (ANA-07)."""
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(Campaign.status, func.count(Campaign.id).label("cnt"))
        .where(Campaign.created_at >= date_threshold)
    )
    if ghl_user_id:
        stmt = stmt.where(Campaign.ghl_user_id == ghl_user_id)
    stmt = stmt.group_by(Campaign.status)

    rows = (await db.execute(stmt)).all()
    counts = {row.status: row.cnt for row in rows}

    return {
        "total_campaigns": sum(counts.values()),
        "draft_campaigns": counts.get("draft", 0),
        "scheduled_campaigns": counts.get("scheduled", 0),
        "active_campaigns": counts.get("executing", 0) + counts.get("paused", 0),
        "completed_campaigns": counts.get("completed", 0),
        "failed_campaigns": counts.get("failed", 0),
        "cancelled_campaigns": counts.get("cancelled", 0),
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
    """Return recent campaigns with delivery stats — single JOIN query (ANA-04)."""
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    delivered_statuses = ("delivered", "read")
    msg_subq = (
        select(
            Message.campaign_id,
            func.count(Message.id).label("total"),
            func.sum(
                case((Message.status.in_(delivered_statuses), 1), else_=0)
            ).label("delivered"),
        )
        .where(Message.sent_at.isnot(None))
        .group_by(Message.campaign_id)
        .subquery("msg_stats")
    )

    stmt = (
        select(
            Campaign.id,
            Campaign.name,
            Campaign.status,
            Campaign.created_at,
            func.coalesce(msg_subq.c.total, 0).label("total"),
            func.coalesce(msg_subq.c.delivered, 0).label("delivered"),
        )
        .outerjoin(msg_subq, Campaign.id == msg_subq.c.campaign_id)
        .where(Campaign.created_at >= date_threshold)
    )
    if ghl_user_id:
        stmt = stmt.where(Campaign.ghl_user_id == ghl_user_id)
    stmt = stmt.order_by(Campaign.created_at.desc()).limit(limit)

    rows = (await db.execute(stmt)).all()
    result = []
    for row in rows:
        total = row.total or 0
        delivered = row.delivered or 0
        rate = round((delivered / total) * 100, 1) if total > 0 else 0.0
        result.append({
            "id": row.id,
            "name": row.name,
            "status": row.status,
            "delivery_rate": rate,
            "created_at": row.created_at.isoformat(),
            "messages_sent": total,
        })
    return result


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
