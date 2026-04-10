"""
GHL Conversation Model
Represents a WhatsApp conversation thread in GoHighLevel
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class GHLConversation(Base):
    """
    GHL Conversation model - represents a WhatsApp conversation in GHL

    Attributes:
        id: Primary key
        ghl_conversation_id: Unique GHL conversation identifier
        ghl_location_id: Foreign key to ghl_locations.ghl_location_id
        ghl_contact_id: GHL contact identifier
        contact_phone: Contact's phone number (E.164 format)
        contact_name: Contact's display name
        last_message_at: Timestamp of last message
        last_message_type: Type of last message (text, image, etc.)
        unread_count: Number of unread messages
        metadata: Additional conversation data (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "ghl_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ghl_conversation_id = Column(String(50), unique=True, nullable=False, index=True)
    ghl_location_id = Column(
        String(50),
        ForeignKey('ghl_locations.ghl_location_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    ghl_contact_id = Column(String(50), nullable=False, index=True)
    contact_phone = Column(String(20), nullable=False, index=True)
    contact_name = Column(String(255), nullable=True)
    last_message_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_message_type = Column(String(50), nullable=True)
    unread_count = Column(Integer, default=0, nullable=False)
    extra_metadata = Column('metadata', JSON, nullable=True)  # Column name in DB is 'metadata'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to GHLLocation
    location = relationship("GHLLocation", backref="conversations", foreign_keys=[ghl_location_id])

    # Indexes and constraints
    __table_args__ = (
        Index('idx_ghl_conversations_location', 'ghl_location_id'),
        Index('idx_ghl_conversations_contact', 'ghl_contact_id'),
        Index('idx_ghl_conversations_phone', 'contact_phone'),
        UniqueConstraint('ghl_location_id', 'ghl_contact_id', name='idx_ghl_conversations_unique'),
    )

    def __repr__(self):
        return (f"<GHLConversation(id={self.id}, conversation_id='{self.ghl_conversation_id}', "
                f"contact='{self.contact_name}', phone='{self.contact_phone}')>")

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "ghl_conversation_id": self.ghl_conversation_id,
            "ghl_location_id": self.ghl_location_id,
            "ghl_contact_id": self.ghl_contact_id,
            "contact_phone": self.contact_phone,
            "contact_name": self.contact_name,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_message_type": self.last_message_type,
            "unread_count": self.unread_count,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
