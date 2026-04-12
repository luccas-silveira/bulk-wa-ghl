"""
Campaign Scheduler Service
Handles scheduling and execution of campaigns using APScheduler
"""
import logging
from datetime import datetime
from typing import Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import async_session_factory
from src.metrics import campaign_queue_gauge, scheduler_jobs_gauge
from src.models.campaign import Campaign
from src.services.campaign_executor_service import CampaignExecutorService

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """
    Service for scheduling campaign execution

    Features:
    - Schedule campaigns for future execution
    - Load pending campaigns on startup
    - Execute campaigns at scheduled time
    - Cancel scheduled campaigns
    """

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = AsyncIOScheduler()
        self.campaign_data_store = {}  # Store campaign data for scheduled execution

    async def start(self):
        """Start scheduler and load pending campaigns."""
        logger.info("Starting Campaign Scheduler...")
        self.scheduler.start()
        await self._load_pending_campaigns()
        logger.info("Campaign Scheduler started successfully")
        self._refresh_metrics()

    def shutdown(self):
        """Shutdown scheduler gracefully"""
        logger.info("Shutting down Campaign Scheduler...")
        self.scheduler.shutdown()
        logger.info("Campaign Scheduler shut down")

    def schedule_campaign(
        self,
        campaign_id: int,
        scheduled_time: datetime,
        csv_data: List[Dict],
        messages: List[Dict]
    ):
        """
        Schedule a campaign for future execution

        Args:
            campaign_id: Campaign ID
            scheduled_time: When to execute the campaign
            csv_data: Contact data for the campaign
            messages: Message templates
        """
        # Store campaign data
        self.campaign_data_store[campaign_id] = {
            'csv_data': csv_data,
            'messages': messages
        }

        # Schedule job
        job_id = f"campaign_{campaign_id}"

        try:
            self.scheduler.add_job(
                func=self._execute_scheduled_campaign,
                trigger=DateTrigger(run_date=scheduled_time),
                args=[campaign_id],
                id=job_id,
                replace_existing=True
            )

            logger.info(f"📅 Scheduled campaign {campaign_id} for {scheduled_time}")
            self._refresh_metrics()

        except Exception as e:
            logger.error(f"Failed to schedule campaign {campaign_id}: {str(e)}")
            raise

    def cancel_campaign(self, campaign_id: int):
        """
        Cancel a scheduled campaign

        Args:
            campaign_id: Campaign ID to cancel
        """
        job_id = f"campaign_{campaign_id}"

        try:
            self.scheduler.remove_job(job_id)

            # Remove stored data
            if campaign_id in self.campaign_data_store:
                del self.campaign_data_store[campaign_id]

            logger.info(f"❌ Cancelled scheduled campaign {campaign_id}")
            self._refresh_metrics()

        except Exception as e:
            logger.warning(f"Failed to cancel campaign {campaign_id}: {str(e)}")

    async def _execute_scheduled_campaign(self, campaign_id: int):
        logger.info(f"Executing scheduled campaign {campaign_id}")
        async with async_session_factory() as db_session:
            try:
                c_result = await db_session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign = c_result.scalar_one_or_none()
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found in database")
                    return

                csv_data = campaign.contacts_data
                messages = campaign.messages_template

                if not csv_data or not messages:
                    campaign_data = self.campaign_data_store.get(campaign_id)
                    if not campaign_data:
                        logger.error(f"No data found for campaign {campaign_id} (neither DB nor memory)")
                        return
                    csv_data = campaign_data['csv_data']
                    messages = campaign_data['messages']

                executor = CampaignExecutorService(db_session)
                result = await executor.execute_campaign(
                    campaign_id=campaign_id,
                    contacts=csv_data,
                    messages_template=messages,
                )
                logger.info(f"Scheduled campaign {campaign_id} completed: {result}")
                self.campaign_data_store.pop(campaign_id, None)

            except Exception as e:
                logger.error(f"Error executing scheduled campaign {campaign_id}: {str(e)}", exc_info=True)
            finally:
                self._refresh_metrics()

    async def _load_pending_campaigns(self):
        """Load campaigns scheduled for the future on startup."""
        async with async_session_factory() as db:
            try:
                result = await db.execute(
                    select(Campaign).where(
                        Campaign.status == 'scheduled',
                        Campaign.scheduled_time > datetime.now(),
                    )
                )
                pending_campaigns = result.scalars().all()
                logger.info(f"Loading {len(pending_campaigns)} pending scheduled campaigns...")
                for campaign in pending_campaigns:
                    csv_data = campaign.contacts_data or []
                    messages = campaign.messages_template or []
                    self.schedule_campaign(
                        campaign_id=campaign.id,
                        scheduled_time=campaign.scheduled_time,
                        csv_data=csv_data,
                        messages=messages,
                    )
            except Exception as e:
                logger.error(f"Failed to load pending campaigns: {e}", exc_info=True)

    def get_scheduled_jobs(self) -> List[Dict]:
        """
        Get list of currently scheduled jobs

        Returns:
            List of scheduled job information
        """
        jobs = []

        for job in self.scheduler.get_jobs():
            campaign_id = int(job.id.replace('campaign_', ''))

            jobs.append({
                'campaign_id': campaign_id,
                'scheduled_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'job_id': job.id
            })

        return jobs

    def _refresh_metrics(self) -> None:
        """Push scheduler and queue sizes to Prometheus gauges."""

        scheduler_jobs_gauge.set(len(self.scheduler.get_jobs()))
        campaign_queue_gauge.set(len(self.campaign_data_store))
