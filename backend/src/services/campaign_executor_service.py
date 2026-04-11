"""
Campaign Executor Service
Handles the execution of WhatsApp campaigns through GHL Conversations API
"""
import asyncio
import os
from typing import List, Dict, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.models.campaign import Campaign
from src.models.message import Message
from src.services.ghl_conversations_service import GHLConversationsService
from src.services.ghl_contacts_service import GHLContactsService
from src.logging_config import reset_campaign_context, set_campaign_context

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

    def __init__(self, db: Session):
        """
        Initialize campaign executor

        Args:
            db: SQLAlchemy database session
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
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).with_for_update().first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign_token = set_campaign_context(campaign_id)
        logger.info(f"Starting execution of campaign {campaign_id}: {campaign.name}")

        # Update campaign status to executing
        campaign.transition_to('executing')
        self.db.commit()

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

        try:
            # Send messages to each contact
            for idx, contact in enumerate(contacts, 1):
                # Check if campaign has been paused
                self.db.refresh(campaign)
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

                        # Create message record
                        message = Message(
                            campaign_id=campaign_id,
                            recipient_phone=phone_number,
                            content=message_text,
                            media_url=media_url,  # Save media URL
                            status='pending'
                        )
                        self.db.add(message)
                        self.db.commit()

                        try:
                            # Send via GHL using contact_id with attachments
                            result = await self.conversations_service.send_message(
                                location_id=campaign.ghl_location_id,
                                contact_id=contact_id,
                                message_text=message_text,
                                media_url=media_url  # Send as attachment
                            )

                            # Update message with success
                            message.status = 'sent'
                            message.sent_at = datetime.utcnow()
                            message.ghl_message_id = result.get('messageId')
                            message.ghl_conversation_id = result.get('conversationId')
                            message.ghl_status = result.get('status')

                            successful_sends += 1
                            logger.info(f"✓ Message sent successfully to {phone_number}")

                        except Exception as e:
                            # Update message with error
                            message.status = 'failed'
                            message.error_message = str(e)

                            failed_sends += 1
                            logger.error(f"✗ Failed to send to {phone_number}: {str(e)}")

                        finally:
                            self.db.commit()

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
                    self.db.commit()

                # Move to next user in round-robin sequence
                user_index += 1

                # Wait before sending to next contact (rate limiting)
                if idx < total_contacts:  # Don't wait after last contact
                    await asyncio.sleep(delay)

            # Mark campaign as completed (only if not paused)
            self.db.refresh(campaign)
            if campaign.status != 'paused':
                campaign.transition_to('completed')
                logger.info(f"Campaign {campaign_id} completed successfully")
            else:
                logger.info(f"Campaign {campaign_id} execution stopped (paused)")

        except Exception as e:
            # Mark campaign as failed
            self.db.rollback()
            campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign:
                campaign.transition_to('failed')
            logger.error(f"Campaign {campaign_id} failed: {str(e)}")
            raise

        finally:
            self.db.commit()
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
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        agg_rows = (
            self.db.query(Message.status, func.count(Message.id).label("cnt"))
            .filter(Message.campaign_id == campaign_id)
            .group_by(Message.status)
            .all()
        )

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
        messages = (
            self.db.query(Message)
            .filter(Message.campaign_id == campaign_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

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
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).with_for_update().first()
        if not campaign:
            raise ValueError(f'Campaign {campaign_id} not found')

        # Early-exit: no persisted data
        if not campaign.contacts_data or not campaign.messages_template:
            logger.warning(f'Campaign {campaign_id} has no persisted data, marking as completed')
            campaign.transition_to('completed')
            self.db.commit()
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
        existing_messages = (
            self.db.query(Message.recipient_phone)
            .filter(Message.campaign_id == campaign_id)
            .filter(Message.status.in_(['sent', 'delivered', 'read']))
            .all()
        )
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
            self.db.commit()
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
