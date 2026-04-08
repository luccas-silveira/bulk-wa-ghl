"""
Message Model
Represents a WhatsApp message sent through a campaign
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class Message(Base):
    """
    Message model - represents a WhatsApp message sent in a campaign

    Attributes:
        id: Primary key
        campaign_id: Foreign key to campaigns.id
        recipient_phone: Recipient phone number (E.164 format)
        content: Message text content
        media_url: Optional media attachment URL
        status: Message status (pending, sent, delivered, read, failed)
        sent_at: Timestamp when message was sent
        delivered_at: Timestamp when message was delivered
        read_at: Timestamp when message was read
        error_message: Error message if failed
        created_at: Creation timestamp
        updated_at: Last update timestamp
        ghl_conversation_id: GHL conversation ID (NEW for GHL)
        ghl_message_id: GHL message ID (NEW for GHL)
        ghl_status: GHL-specific status (NEW for GHL)
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(
        Integer,
        ForeignKey('campaigns.id', ondelete='CASCADE'),
        nullable=True,  # Nullable to support standalone messages
        index=True
    )
    recipient_phone = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False)
    media_url = Column(Text, nullable=True)  # Optional media attachment URL
    status = Column(String(50), nullable=False, default='pending', index=True)
    sent_at = Column(TIMESTAMP, nullable=True)
    delivered_at = Column(TIMESTAMP, nullable=True)
    read_at = Column(TIMESTAMP, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # GHL integration fields (NEW)
    ghl_conversation_id = Column(String(50), nullable=True, index=True)
    ghl_message_id = Column(String(50), nullable=True, unique=True, index=True)
    ghl_status = Column(String(50), nullable=True, index=True)

    # Relationship to Campaign
    campaign = relationship("Campaign", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index('idx_messages_campaign', 'campaign_id'),
        Index('idx_messages_status', 'status'),
        Index('idx_messages_recipient', 'recipient_phone'),
        Index('idx_messages_ghl_conversation', 'ghl_conversation_id'),
        Index('idx_messages_ghl_message_id', 'ghl_message_id'),
        Index('idx_messages_ghl_status', 'ghl_status'),
    )

    def __repr__(self):
        return (f"<Message(id={self.id}, campaign_id={self.campaign_id}, recipient='{self.recipient_phone}', "
                f"status='{self.status}', ghl_message_id='{self.ghl_message_id}')>")

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "recipient_phone": self.recipient_phone,
            "content": self.content,
            "media_url": self.media_url,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "error_message": self.error_message,
            "ghl_conversation_id": self.ghl_conversation_id,
            "ghl_message_id": self.ghl_message_id,
            "ghl_status": self.ghl_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
