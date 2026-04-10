"""
Processed Webhook Model
Tracks processed webhooks for idempotency
"""
from sqlalchemy import Column, String, TIMESTAMP, Index
from sqlalchemy.sql import func
from src.database import Base


class ProcessedWebhook(Base):
    """
    Processed Webhook model - tracks webhooks that have been processed for idempotency

    Attributes:
        webhook_id: Primary key - unique webhook identifier (from GHL or generated)
        event_type: Type of webhook event (MessageDelivered, MessageRead, etc.)
        ghl_location_id: GHL location identifier
        processed_at: Timestamp when webhook was processed
        payload_hash: SHA-256 hash of webhook payload for deduplication
    """

    __tablename__ = "processed_webhooks"

    webhook_id = Column(String(100), primary_key=True)
    event_type = Column(String(50), nullable=False)
    ghl_location_id = Column(String(50), nullable=True, index=True)
    processed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    payload_hash = Column(String(64), nullable=True)  # SHA-256 hash

    # Indexes
    __table_args__ = (
        Index('idx_processed_webhooks_ttl', 'processed_at'),
        Index('idx_processed_webhooks_location', 'ghl_location_id'),
    )

    @staticmethod
    def generate_webhook_id(event_type: str, message_id: str = None, timestamp: str = None) -> str:
        """
        Generate a unique webhook ID from event data

        Args:
            event_type: Type of webhook event
            message_id: Message ID if available
            timestamp: Timestamp if available

        Returns:
            Unique webhook identifier
        """
        import hashlib

        components = [event_type]
        if message_id:
            components.append(message_id)
        if timestamp:
            components.append(timestamp)

        combined = "_".join(components)
        return hashlib.md5(combined.encode()).hexdigest()

    @staticmethod
    def hash_payload(payload: dict) -> str:
        """
        Generate SHA-256 hash of webhook payload

        Args:
            payload: Webhook payload dictionary

        Returns:
            SHA-256 hash string
        """
        import hashlib
        import json

        # Sort keys for consistent hashing
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def __repr__(self):
        return (f"<ProcessedWebhook(webhook_id='{self.webhook_id}', event_type='{self.event_type}', "
                f"location_id='{self.ghl_location_id}', processed_at={self.processed_at})>")

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "webhook_id": self.webhook_id,
            "event_type": self.event_type,
            "ghl_location_id": self.ghl_location_id,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "payload_hash": self.payload_hash,
        }
