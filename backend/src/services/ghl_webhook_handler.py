"""
GHL Webhook Handler
Processes webhooks from GoHighLevel for message status updates
"""
import os
import hmac
import hashlib
import json
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.models.processed_webhook import ProcessedWebhook
from src.models.message import Message
from src.models.ghl_conversation import GHLConversation

load_dotenv()


class GHLWebhookHandler:
    """
    Service for handling GoHighLevel webhooks

    Features:
    - HMAC-SHA256 signature validation
    - Idempotent webhook processing
    - Message status updates
    - Conversation tracking
    """

    def __init__(self, db: Session):
        """
        Initialize webhook handler

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.webhook_secret = os.getenv("GHL_WEBHOOK_SECRET")

        if not self.webhook_secret:
            raise ValueError("GHL_WEBHOOK_SECRET environment variable is not set")

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature using HMAC-SHA256

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from X-GHL-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            return False

        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)

    async def process_webhook(self, event_type: str, payload: Dict) -> Dict:
        """
        Process a webhook event

        Args:
            event_type: Type of webhook event
            payload: Webhook payload data

        Returns:
            Processing result dictionary

        Raises:
            ValueError: If webhook processing fails
        """
        # Generate webhook ID for idempotency
        webhook_id = self._generate_webhook_id(event_type, payload)

        # Check if already processed
        existing = self.db.query(ProcessedWebhook).filter(
            ProcessedWebhook.webhook_id == webhook_id
        ).first()

        if existing:
            return {
                "status": "duplicate",
                "already_processed": True,
                "webhook_id": webhook_id,
                "processed_at": existing.processed_at.isoformat()
            }

        # Process based on event type
        result = None
        if event_type == "MessageDelivered":
            result = await self.handle_message_delivered(payload)
        elif event_type == "MessageRead":
            result = await self.handle_message_read(payload)
        elif event_type == "MessageFailed":
            result = await self.handle_message_failed(payload)
        elif event_type == "InboundMessage":
            result = await self.handle_inbound_message(payload)
        else:
            raise ValueError(f"Unknown event type: {event_type}")

        # Record webhook as processed
        payload_hash = ProcessedWebhook.hash_payload(payload)
        processed_webhook = ProcessedWebhook(
            webhook_id=webhook_id,
            event_type=event_type,
            ghl_location_id=payload.get("locationId"),
            payload_hash=payload_hash
        )
        self.db.add(processed_webhook)
        self.db.commit()

        return {
            "status": "processed",
            "webhook_id": webhook_id,
            "event_type": event_type,
            "result": result
        }

    async def handle_message_delivered(self, payload: Dict) -> Dict:
        """
        Handle MessageDelivered webhook event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        message_id = payload.get("messageId")
        conversation_id = payload.get("conversationId")

        # Find message in database by ghl_message_id
        message = self.db.query(Message).filter(
            Message.ghl_message_id == message_id
        ).first()

        if message:
            # Update message status
            message.status = "delivered"
            message.ghl_status = "delivered"
            message.delivered_at = datetime.utcnow()
            self.db.commit()

            return {
                "message_id": message.id,
                "status_updated": "delivered"
            }

        return {"message_id": message_id, "status": "not_found"}

    async def handle_message_read(self, payload: Dict) -> Dict:
        """
        Handle MessageRead webhook event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        message_id = payload.get("messageId")

        message = self.db.query(Message).filter(
            Message.ghl_message_id == message_id
        ).first()

        if message:
            message.status = "read"
            message.ghl_status = "read"
            message.read_at = datetime.utcnow()
            self.db.commit()

            return {
                "message_id": message.id,
                "status_updated": "read"
            }

        return {"message_id": message_id, "status": "not_found"}

    async def handle_message_failed(self, payload: Dict) -> Dict:
        """
        Handle MessageFailed webhook event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        message_id = payload.get("messageId")
        error_code = payload.get("errorCode")
        error_message = payload.get("errorMessage")

        message = self.db.query(Message).filter(
            Message.ghl_message_id == message_id
        ).first()

        if message:
            message.status = "failed"
            message.ghl_status = "failed"
            message.error_message = f"{error_code}: {error_message}" if error_code else error_message
            self.db.commit()

            return {
                "message_id": message.id,
                "status_updated": "failed",
                "error": message.error_message
            }

        return {"message_id": message_id, "status": "not_found"}

    async def handle_inbound_message(self, payload: Dict) -> Dict:
        """
        Handle InboundMessage webhook event

        Args:
            payload: Webhook payload

        Returns:
            Processing result
        """
        conversation_id = payload.get("conversationId")
        location_id = payload.get("locationId")
        contact_id = payload.get("contactId")
        contact_phone = payload.get("contactPhone")
        message_text = payload.get("messageText")

        # Update or create conversation record
        conversation = self.db.query(GHLConversation).filter(
            GHLConversation.ghl_conversation_id == conversation_id
        ).first()

        if conversation:
            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_type = "text"
            conversation.unread_count += 1
        else:
            # Create new conversation record
            conversation = GHLConversation(
                ghl_conversation_id=conversation_id,
                ghl_location_id=location_id,
                ghl_contact_id=contact_id,
                contact_phone=contact_phone,
                last_message_at=datetime.utcnow(),
                last_message_type="text",
                unread_count=1
            )
            self.db.add(conversation)

        self.db.commit()

        return {
            "conversation_id": conversation.id,
            "inbound_message_received": True,
            "message_preview": message_text[:50] if message_text else None
        }

    def _generate_webhook_id(self, event_type: str, payload: Dict) -> str:
        """
        Generate unique webhook ID for idempotency

        Args:
            event_type: Type of webhook event
            payload: Webhook payload

        Returns:
            Unique webhook identifier
        """
        message_id = payload.get("messageId")
        timestamp = payload.get("timestamp")

        return ProcessedWebhook.generate_webhook_id(
            event_type=event_type,
            message_id=message_id,
            timestamp=timestamp
        )
