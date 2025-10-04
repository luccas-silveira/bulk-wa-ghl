"""
Campaign Executor Service
Handles the execution of WhatsApp campaigns through GHL Conversations API
"""
import asyncio
import os
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.models.campaign import Campaign
from src.models.message import Message
from src.services.ghl_conversations_service import GHLConversationsService
from src.services.ghl_contacts_service import GHLContactsService

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
        messages_template: List[Dict[str, str]]
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
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        logger.info(f"Starting execution of campaign {campaign_id}: {campaign.name}")

        # Update campaign status to executing
        campaign.status = 'executing'
        self.db.commit()

        # Get sending delay based on speed
        delay = self.SPEED_DELAYS.get(campaign.sending_speed, 2.0)

        # Get list of users for round-robin distribution
        user_ids = campaign.get_user_ids_list()
        if not user_ids:
            raise ValueError(f"Campaign {campaign_id} has no users assigned")

        logger.info(f"👥 Round-robin users: {user_ids} ({len(user_ids)} users)")

        # Statistics
        total_contacts = len(contacts)
        successful_sends = 0
        failed_sends = 0
        user_index = 0  # Track current user in round-robin

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
                    # Failed to get/create contact
                    failed_sends += 1
                    logger.error(f"✗ Failed to prepare contact {phone_number}: {str(e)}")

                # Move to next user in round-robin sequence
                user_index += 1

                # Wait before sending to next contact (rate limiting)
                if idx < total_contacts:  # Don't wait after last contact
                    await asyncio.sleep(delay)

            # Mark campaign as completed (only if not paused)
            self.db.refresh(campaign)
            if campaign.status != 'paused':
                campaign.status = 'completed'
                logger.info(f"Campaign {campaign_id} completed successfully")
            else:
                logger.info(f"Campaign {campaign_id} execution stopped (paused)")

        except Exception as e:
            # Mark campaign as failed
            campaign.status = 'failed'
            logger.error(f"Campaign {campaign_id} failed: {str(e)}")
            raise

        finally:
            self.db.commit()

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

        # Get message statistics
        messages = self.db.query(Message).filter(Message.campaign_id == campaign_id).all()

        status_counts = {
            'pending': 0,
            'sent': 0,
            'delivered': 0,
            'read': 0,
            'failed': 0
        }

        for msg in messages:
            status = msg.status
            if status in status_counts:
                status_counts[status] += 1

        return {
            'campaign_id': campaign_id,
            'name': campaign.name,
            'status': campaign.status,
            'ghl_location_id': campaign.ghl_location_id,
            'sending_speed': campaign.sending_speed,
            'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
            'messages': {
                'total': len(messages),
                'by_status': status_counts
            }
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
        Resume a paused campaign from where it left off

        LIMITATION: Cannot resume campaigns - original contact list and message templates
        are not stored in the database. This method will mark the campaign as completed
        to clear the inconsistent state.

        Args:
            campaign_id: Campaign database ID

        Returns:
            Dictionary with execution summary
        """
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        logger.warning(f"Resume requested for campaign {campaign_id}, but resume is not fully implemented")
        logger.info(f"Marking campaign {campaign_id} as completed to clear inconsistent state")

        # Mark as completed since we cannot re-execute
        campaign.status = 'completed'
        self.db.commit()

        # Get statistics
        messages = self.db.query(Message).filter(Message.campaign_id == campaign_id).all()
        successful = len([m for m in messages if m.status == 'sent'])
        failed = len([m for m in messages if m.status == 'failed'])

        return {
            'campaign_id': campaign_id,
            'status': 'completed',
            'total_contacts': len(messages),
            'successful_sends': successful,
            'failed_sends': failed,
            'completion_rate': (successful / len(messages) * 100) if messages else 0,
            'message': 'Campaign marked as completed (resume not fully implemented)'
        }
