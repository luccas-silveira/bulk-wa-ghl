"""
Campaign Executor Service
Handles the execution of WhatsApp campaigns through GHL Conversations API
"""
import asyncio
import os
from typing import List, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import logging

from src.models.campaign import Campaign
from src.models.message import Message
from src.services.ghl_conversations_service import GHLConversationsService, RateLimitExceeded
from src.services.ghl_contacts_service import GHLContactsService
from src.logging_config import reset_campaign_context, set_campaign_context
from src.metrics import messages_sent_total, campaigns_active_gauge

logger = logging.getLogger(__name__)


class CampaignExecutorService:
    """
    Service for executing WhatsApp campaigns

    Features:
    - Send messages to contacts from CSV
    - Respect sending speed limits
    - Track message status
    - Handle errors gracefully
    - Update campaign status
    """

    # Sending speed delays (seconds between contacts)
    SPEED_DELAYS = {
        'slow': 420.0,   # 1 contact every 7 minutes
        'medium': 240.0, # 1 contact every 4 minutes
        'fast': 60.0     # 1 contact every 1 minute
    }

    # Batch commit size: commit to DB every N messages to reduce pool contention
    BATCH_COMMIT_SIZE = 10

    def __init__(self, db: AsyncSession):
        """
        Initialize campaign executor

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db
        self.conversations_service = GHLConversationsService(db)
        self.contacts_service = GHLContactsService(db)

    async def execute_campaign(
        self,
        campaign_id: int,
        contacts: List[Dict[str, str]],
        messages_template: List[Dict[str, str]],
        start_user_index: int = 0,   # CAMP-04: resume from correct round-robin position
    ) -> Dict:
        """
        Execute a campaign by sending messages to all contacts

        Args:
            campaign_id: Campaign database ID
            contacts: List of contact dictionaries with phone_number, name, email
            messages_template: List of message templates to send

        Returns:
            Dictionary with execution summary
        """
        c_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id).with_for_update()
        )
        campaign = c_result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign_token = set_campaign_context(campaign_id)
        logger.info(f"Starting execution of campaign {campaign_id}: {campaign.name}")

        # Update campaign status to executing
        campaign.transition_to('executing')
        await self.db.commit()

        # Get sending delay based on speed
        delay = self.SPEED_DELAYS.get(campaign.sending_speed)
        if delay is None:
            logger.warning(
                f"Unknown sending_speed '{campaign.sending_speed}' for campaign {campaign_id}, "
                "defaulting to 2s delay"
            )
            delay = 2.0

        # Get list of users for round-robin distribution
        user_ids = campaign.get_user_ids_list()
        if not user_ids:
            raise ValueError(f"Campaign {campaign_id} has no users assigned")

        logger.info(f"👥 Round-robin users: {user_ids} ({len(user_ids)} users)")

        # Statistics
        total_contacts = len(contacts)
        successful_sends = 0
        failed_sends = 0
        user_index = start_user_index  # Resume from correct position in round-robin (CAMP-04)
        _pending_commits = 0  # batch commit counter

        campaigns_active_gauge.inc()
        try:
            # Send messages to each contact
            for idx, contact in enumerate(contacts, 1):
                # Check if campaign has been paused (with lock to avoid stale read)
                c_result = await self.db.execute(
                    select(Campaign).where(Campaign.id == campaign_id).with_for_update()
                )
                campaign = c_result.scalar_one_or_none()
                if campaign.status == 'paused':
                    logger.info(f"Campaign {campaign_id} paused, stopping execution")
                    break

                phone_number = contact.get('phone_number')
                name = contact.get('name', '')
                email = contact.get('email')

                # ROUND-ROBIN: Select next user in rotation
                current_user_id = user_ids[user_index % len(user_ids)]
                logger.info(f"[{idx}/{total_contacts}] Processing {phone_number} ({name}) → User: {current_user_id}")

                try:
                    # Step 1: Get or create contact in GHL and assign to current user
                    ghl_contact = await self.contacts_service.get_or_create_contact(
                        location_id=campaign.ghl_location_id,
                        phone=phone_number,
                        name=name,
                        email=email,
                        assigned_to=current_user_id  # Use round-robin user
                    )
                    contact_id = ghl_contact.get('id')
                    logger.info(f"✓ Contact ready: {contact_id} (assigned to {current_user_id})")

                    # Step 2: Send each message in the template
                    for msg_template in messages_template:
                        message_text = msg_template.get('text', '')
                        media_url = msg_template.get('media_url')

                        # Create message record (do NOT commit yet — batch below)
                        message = Message(
                            campaign_id=campaign_id,
                            recipient_phone=phone_number,
                            content=message_text,
                            media_url=media_url,
                            status='pending'
                        )
                        self.db.add(message)

                        try:
                            # Send via GHL using contact_id with attachments
                            result = await self.conversations_service.send_message(
                                location_id=campaign.ghl_location_id,
                                contact_id=contact_id,
                                message_text=message_text,
                                media_url=media_url
                            )
                            # Update message with success
                            message.status = 'sent'
                            message.sent_at = datetime.now(timezone.utc)
                            message.ghl_message_id = result.get('messageId')
                            message.ghl_conversation_id = result.get('conversationId')
                            message.ghl_status = result.get('status')
                            successful_sends += 1
                            messages_sent_total.labels(status='sent').inc()
                            logger.info(f'✓ Message sent successfully to {phone_number}')

                        except RateLimitExceeded:
                            # CAMP-12: wait for rate limiter to refill and retry once
                            wait_time = self.conversations_service.rate_limiter.wait_time()
                            logger.warning(
                                f'Rate limit hit sending to {phone_number}, waiting {max(wait_time, 1.0):.1f}s'
                            )
                            await asyncio.sleep(max(wait_time, 1.0))
                            try:
                                result = await self.conversations_service.send_message(
                                    location_id=campaign.ghl_location_id,
                                    contact_id=contact_id,
                                    message_text=message_text,
                                    media_url=media_url,
                                )
                                message.status = 'sent'
                                message.sent_at = datetime.now(timezone.utc)
                                message.ghl_message_id = result.get('messageId')
                                message.ghl_conversation_id = result.get('conversationId')
                                message.ghl_status = result.get('status')
                                successful_sends += 1
                                messages_sent_total.labels(status='sent').inc()
                                logger.info(f'✓ Message sent on retry to {phone_number}')
                            except Exception as retry_err:
                                message.status = 'failed'
                                message.error_message = f'Rate limit retry failed: {retry_err}'
                                failed_sends += 1
                                messages_sent_total.labels(status='failed').inc()
                                logger.error(f'✗ Retry also failed for {phone_number}: {retry_err}')

                        except Exception as e:
                            # Update message with error
                            message.status = 'failed'
                            message.error_message = str(e)
                            failed_sends += 1
                            messages_sent_total.labels(status='failed').inc()
                            logger.error(f'✗ Failed to send to {phone_number}: {str(e)}')

                        finally:
                            _pending_commits += 1
                            if _pending_commits >= self.BATCH_COMMIT_SIZE:
                                await self.db.commit()
                                _pending_commits = 0

                except Exception as e:
                    # Failed to get/create contact - record the failure
                    failed_sends += 1
                    logger.error(f"Failed to prepare contact {phone_number}: {str(e)}")
                    for msg_template in messages_template:
                        failed_message = Message(
                            campaign_id=campaign_id,
                            recipient_phone=phone_number or 'unknown',
                            content=msg_template.get('text', ''),
                            media_url=msg_template.get('media_url'),
                            status='failed',
                            error_message=f"Contact preparation failed: {str(e)}"
                        )
                        self.db.add(failed_message)
                    _pending_commits += len(messages_template)
                    if _pending_commits >= self.BATCH_COMMIT_SIZE:
                        await self.db.commit()
                        _pending_commits = 0

                # Move to next user in round-robin sequence
                user_index += 1

                # Wait before sending to next contact (rate limiting)
                if idx < total_contacts:  # Don't wait after last contact
                    await asyncio.sleep(delay)

            # Flush any remaining uncommitted messages
            if _pending_commits > 0:
                await self.db.commit()
                _pending_commits = 0

            # Mark campaign as completed (only if not paused)
            await self.db.refresh(campaign)
            if campaign.status != 'paused':
                campaign.transition_to('completed')
                logger.info(f"Campaign {campaign_id} completed successfully")
            else:
                logger.info(f"Campaign {campaign_id} execution stopped (paused)")

        except Exception as e:
            # Mark campaign as failed
            await self.db.rollback()
            c_result = await self.db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = c_result.scalar_one_or_none()
            if campaign:
                campaign.transition_to('failed')
            logger.error(f"Campaign {campaign_id} failed: {str(e)}")
            raise

        finally:
            campaigns_active_gauge.dec()
            await self.db.commit()
            reset_campaign_context(campaign_token)

        return {
            'campaign_id': campaign_id,
            'status': campaign.status,
            'total_contacts': total_contacts,
            'successful_sends': successful_sends,
            'failed_sends': failed_sends,
            'completion_rate': (successful_sends / (successful_sends + failed_sends) * 100) if (successful_sends + failed_sends) > 0 else 0
        }

    async def get_campaign_status(self, campaign_id: int) -> Dict:
        """
        Get current status of a campaign execution

        Args:
            campaign_id: Campaign database ID

        Returns:
            Dictionary with campaign status and statistics
        """
        c_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = c_result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        agg_result = await self.db.execute(
            select(Message.status, func.count(Message.id).label("cnt"))
            .where(Message.campaign_id == campaign_id)
            .group_by(Message.status)
        )
        agg_rows = agg_result.all()

        status_counts = {'pending': 0, 'sent': 0, 'delivered': 0, 'read': 0, 'failed': 0}
        total = 0
        for status, cnt in agg_rows:
            if status in status_counts:
                status_counts[status] = cnt
            total += cnt

        return {
            'campaign_id': campaign_id,
            'name': campaign.name,
            'status': campaign.status,
            'ghl_location_id': campaign.ghl_location_id,
            'sending_speed': campaign.sending_speed,
            'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
            'messages': {'total': total, 'by_status': status_counts},
        }

    async def get_campaign_messages(
        self,
        campaign_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get messages sent in a campaign

        Args:
            campaign_id: Campaign database ID
            limit: Maximum number of messages to return
            offset: Offset for pagination

        Returns:
            List of message dictionaries
        """
        msg_result = await self.db.execute(
            select(Message)
            .where(Message.campaign_id == campaign_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        messages = msg_result.scalars().all()

        return [msg.to_dict() for msg in messages]

    async def resume_campaign(self, campaign_id: int) -> Dict:
        """
        Resume a paused campaign from where it left off.
        Uses persisted contacts_data and messages_template to re-execute
        only the contacts that haven't been sent to yet.

        Returns a consistent dict with keys:
            campaign_id, status, resumed_contacts, successful_sends, failed_sends,
            message (optional, early-exit paths only)
        """
        c_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id).with_for_update()
        )
        campaign = c_result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f'Campaign {campaign_id} not found')

        # Early-exit: no persisted data
        if not campaign.contacts_data or not campaign.messages_template:
            logger.warning(f'Campaign {campaign_id} has no persisted data, marking as completed')
            campaign.transition_to('completed')
            await self.db.commit()
            return {
                'campaign_id': campaign_id,
                'status': 'completed',
                'resumed_contacts': 0,
                'successful_sends': 0,
                'failed_sends': 0,
                'message': 'No persisted data available for resume',
            }

        # Find phones that already received messages
        sent_phones = set()
        existing_msg_result = await self.db.execute(
            select(Message.recipient_phone)
            .where(Message.campaign_id == campaign_id)
            .where(Message.status.in_(['sent', 'delivered', 'read']))
        )
        existing_messages = existing_msg_result.all()
        for (phone,) in existing_messages:
            sent_phones.add(phone)

        # Filter contacts to only those not yet sent
        remaining_contacts = [
            c for c in campaign.contacts_data if c.get('phone_number') not in sent_phones
        ]

        # Early-exit: all contacts already sent
        if not remaining_contacts:
            logger.info(f'Campaign {campaign_id}: all contacts already sent, marking completed')
            campaign.transition_to('completed')
            await self.db.commit()
            return {
                'campaign_id': campaign_id,
                'status': 'completed',
                'resumed_contacts': 0,
                'successful_sends': 0,
                'failed_sends': 0,
                'message': 'All contacts already sent',
            }

        start_user_index = len(sent_phones)  # CAMP-04: continue round-robin from correct position
        logger.info(
            f'Resuming campaign {campaign_id}: {len(remaining_contacts)} contacts remaining, '
            f'start_user_index={start_user_index}'
        )

        result = await self.execute_campaign(
            campaign_id,
            remaining_contacts,
            campaign.messages_template,
            start_user_index,
        )

        # CAMP-09: normalize schema
        return {
            'campaign_id': campaign_id,
            'status': result['status'],
            'resumed_contacts': result['total_contacts'],
            'successful_sends': result['successful_sends'],
            'failed_sends': result['failed_sends'],
        }
