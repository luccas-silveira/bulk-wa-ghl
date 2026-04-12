"""
Campaign Management Service
Handles campaign listing, details, logs, statistics, and deletion operations
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from src.models.campaign import Campaign
from src.models.message import Message


class CampaignManagementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_campaigns(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        stmt = select(Campaign)
        if filters:
            if 'status' in filters:
                stmt = stmt.where(Campaign.status == filters['status'])
            if 'ghl_user_id' in filters:
                stmt = stmt.where(Campaign.ghl_user_id == filters['ghl_user_id'])
            if 'ghl_location_id' in filters:
                stmt = stmt.where(Campaign.ghl_location_id == filters['ghl_location_id'])
            if 'from_date' in filters:
                stmt = stmt.where(Campaign.created_at >= filters['from_date'])
            if 'to_date' in filters:
                stmt = stmt.where(Campaign.created_at <= filters['to_date'])

        stmt = stmt.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        campaigns = result.scalars().all()

        out = []
        for campaign in campaigns:
            msg_result = await self.db.execute(
                select(
                    func.count(Message.id).label('total'),
                    func.sum(case((Message.status == 'sent', 1), else_=0)).label('sent'),
                    func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
                    func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
                    func.sum(case((Message.status == 'failed', 1), else_=0)).label('failed'),
                    func.sum(case((Message.status == 'pending', 1), else_=0)).label('pending'),
                ).where(Message.campaign_id == campaign.id)
            )
            msg_stats = msg_result.one()

            campaign_dict = campaign.to_dict()
            campaign_dict['message_stats'] = {
                'total': msg_stats.total or 0,
                'sent': msg_stats.sent or 0,
                'delivered': msg_stats.delivered or 0,
                'read': msg_stats.read or 0,
                'failed': msg_stats.failed or 0,
                'pending': msg_stats.pending or 0,
            }
            if campaign.status == 'executing':
                total = msg_stats.total or 0
                completed = (
                    (msg_stats.sent or 0) + (msg_stats.delivered or 0)
                    + (msg_stats.read or 0) + (msg_stats.failed or 0)
                )
                campaign_dict['progress_percent'] = round(completed / total * 100, 2) if total > 0 else 0.0
            out.append(campaign_dict)
        return out

    async def get_campaign_details(self, campaign_id: int) -> Dict[str, Any]:
        result = await self.db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign with id {campaign_id} not found")

        msg_result = await self.db.execute(
            select(
                func.count(Message.id).label('total_messages'),
                func.sum(case((Message.status == 'sent', 1), else_=0)).label('sent'),
                func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
                func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
                func.sum(case((Message.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((Message.status == 'pending', 1), else_=0)).label('pending'),
            ).where(Message.campaign_id == campaign_id)
        )
        msg_stats = msg_result.one()

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
            'delivery_rate': round(delivered / total * 100, 2) if total > 0 else 0.0,
            'read_rate': round(read / total * 100, 2) if total > 0 else 0.0,
        }

        timeline = [{'event': 'Campaign Created', 'timestamp': campaign.created_at.isoformat() if campaign.created_at else None}]
        if campaign.scheduled_time:
            timeline.append({'event': 'Campaign Scheduled', 'timestamp': campaign.scheduled_time.isoformat()})

        if campaign.status in ('executing', 'completed'):
            first_result = await self.db.execute(
                select(Message).where(
                    Message.campaign_id == campaign_id,
                    Message.sent_at.isnot(None),
                ).order_by(Message.sent_at.asc()).limit(1)
            )
            first_msg = first_result.scalar_one_or_none()
            if first_msg:
                timeline.append({'event': 'Campaign Started', 'timestamp': first_msg.sent_at.isoformat()})

        if campaign.paused_at:
            timeline.append({'event': 'Campaign Paused', 'timestamp': campaign.paused_at.isoformat()})
        if campaign.status == 'completed':
            timeline.append({'event': 'Campaign Completed', 'timestamp': campaign.updated_at.isoformat() if campaign.updated_at else None})

        recent_result = await self.db.execute(
            select(Message).where(Message.campaign_id == campaign_id).order_by(Message.sent_at.desc()).limit(50)
        )
        recent_messages = recent_result.scalars().all()

        return {
            'campaign': campaign.to_dict(),
            'statistics': statistics,
            'timeline': timeline,
            'recent_messages': [msg.to_dict() for msg in recent_messages],
        }

    async def get_campaign_logs(
        self,
        campaign_id: int,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        c_result = await self.db.execute(select(Campaign).where(Campaign.id == campaign_id))
        if not c_result.scalar_one_or_none():
            raise ValueError(f"Campaign with id {campaign_id} not found")

        stmt = select(Message).where(Message.campaign_id == campaign_id)
        if filters:
            if 'status' in filters:
                stmt = stmt.where(Message.status == filters['status'])
            if 'recipient' in filters:
                escaped = filters['recipient'].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                stmt = stmt.where(Message.recipient_phone.like(f"%{escaped}%", escape="\\"))

        stmt = stmt.order_by(Message.sent_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return [msg.to_dict() for msg in result.scalars().all()]

    async def get_campaign_statistics(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        base_conditions = []
        if filters:
            if 'ghl_user_id' in filters:
                base_conditions.append(Campaign.ghl_user_id == filters['ghl_user_id'])
            if 'ghl_location_id' in filters:
                base_conditions.append(Campaign.ghl_location_id == filters['ghl_location_id'])
            if 'from_date' in filters:
                base_conditions.append(Campaign.created_at >= filters['from_date'])
            if 'to_date' in filters:
                base_conditions.append(Campaign.created_at <= filters['to_date'])

        campaign_counts = {}
        for status in ['draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled']:
            count_result = await self.db.execute(
                select(func.count(Campaign.id)).where(Campaign.status == status, *base_conditions)
            )
            campaign_counts[status] = count_result.scalar() or 0

        ids_result = await self.db.execute(select(Campaign.id).where(*base_conditions))
        campaign_ids = ids_result.scalars().all()

        if campaign_ids:
            agg_result = await self.db.execute(
                select(
                    func.count(Message.id).label('total'),
                    func.sum(case((Message.status == 'delivered', 1), else_=0)).label('delivered'),
                    func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
                ).where(Message.campaign_id.in_(campaign_ids))
            )
            agg = agg_result.one()
            total_messages = agg.total or 0
            delivered = agg.delivered or 0
            read = agg.read or 0
            delivery_metrics = {
                'total_messages': total_messages,
                'avg_delivery_rate': round(delivered / total_messages * 100, 2) if total_messages > 0 else 0.0,
                'avg_read_rate': round(read / total_messages * 100, 2) if total_messages > 0 else 0.0,
            }
        else:
            delivery_metrics = {'total_messages': 0, 'avg_delivery_rate': 0.0, 'avg_read_rate': 0.0}

        recent_result = await self.db.execute(
            select(Campaign).where(*base_conditions).order_by(Campaign.created_at.desc()).limit(10)
        )
        recent_campaigns = [c.to_dict() for c in recent_result.scalars().all()]

        top_performers = []
        if campaign_ids:
            perf_result = await self.db.execute(
                select(
                    Campaign,
                    func.count(Message.id).label('total'),
                    func.sum(case((Message.status == 'read', 1), else_=0)).label('read'),
                ).outerjoin(Message, Message.campaign_id == Campaign.id)
                .where(Campaign.id.in_(campaign_ids))
                .group_by(Campaign.id)
            )
            for campaign, total, read_count in perf_result.all():
                total = total or 0
                read_count = read_count or 0
                d = campaign.to_dict()
                d['read_rate'] = round(read_count / total * 100, 2) if total > 0 else 0.0
                top_performers.append(d)
            top_performers = sorted(top_performers, key=lambda x: x['read_rate'], reverse=True)[:10]

        return {
            'campaign_counts': campaign_counts,
            'delivery_metrics': delivery_metrics,
            'recent_campaigns': recent_campaigns,
            'top_performing_campaigns': top_performers,
        }

    async def delete_campaign(self, campaign_id: int) -> bool:
        result = await self.db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign with id {campaign_id} not found")
        if campaign.status in ('executing', 'scheduled'):
            raise ValueError(f"Cannot delete campaign with status '{campaign.status}'. Please pause or cancel it first.")
        await self.db.delete(campaign)
        await self.db.commit()
        return True
