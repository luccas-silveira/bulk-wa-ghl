"""
Campaign Model
Represents a WhatsApp message campaign
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
import json


class Campaign(Base):
    """
    Campaign model - represents a WhatsApp messaging campaign

    Attributes:
        id: Primary key
        name: Campaign name
        status: Campaign status (draft, scheduled, executing, paused, completed, failed, cancelled)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        sending_speed: Sending speed (slow, medium, fast)
        schedule_type: Schedule type (immediate, scheduled)
        scheduled_time: When to start execution (for scheduled campaigns)
        paused_at: When campaign was paused (NULL if not paused)
        ghl_location_id: Foreign key to ghl_locations.ghl_location_id
        ghl_location_name: Cached location name for quick access
        ghl_user_id: User that will send messages
        ghl_user_name: Cached user name for quick access
    """

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default='draft', index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    sending_speed = Column(String(20), default='medium')
    schedule_type = Column(String(50), default='immediate')
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=True)

    # Pause/resume functionality (Feature 004)
    paused_at = Column(TIMESTAMP(timezone=True), nullable=True)  # When campaign was paused (NULL if not paused)

    # GHL integration fields (NEW)
    ghl_location_id = Column(
        String(50),
        ForeignKey('ghl_locations.ghl_location_id', ondelete='RESTRICT'),
        nullable=True,  # Nullable during migration phase
        index=True
    )
    ghl_location_name = Column(String(255), nullable=True)
    ghl_user_id = Column(String(50), nullable=True, index=True)  # Primary user (backwards compat)
    ghl_user_name = Column(String(255), nullable=True)  # Cached user name
    ghl_user_ids = Column(Text, nullable=True)  # JSON array of user IDs for multi-user round-robin

    # Persisted campaign data for scheduled campaigns and resume support
    contacts_data = Column(JSONB, nullable=True)  # CSV contact list for scheduled/resumable campaigns
    messages_template = Column(JSONB, nullable=True)  # Message templates for scheduled/resumable campaigns

    # Relationship to GHLLocation
    ghl_location = relationship("GHLLocation", backref="campaigns", foreign_keys=[ghl_location_id])

    # Relationship to messages
    messages = relationship("Message", back_populates="campaign", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_campaigns_status', 'status'),
        Index('idx_campaigns_created_at', 'created_at'),
        Index('idx_campaigns_ghl_location', 'ghl_location_id'),
    )

    def __repr__(self):
        return (f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}', "
                f"ghl_location_id='{self.ghl_location_id}')>")

    def get_user_ids_list(self):
        """Get list of user IDs from JSON field"""
        if self.ghl_user_ids:
            try:
                return json.loads(self.ghl_user_ids)
            except (json.JSONDecodeError, TypeError):
                return []
        # Fallback to single user for backwards compatibility
        return [self.ghl_user_id] if self.ghl_user_id else []

    def set_user_ids_list(self, user_ids: list):
        """Set user IDs as JSON string"""
        if user_ids:
            self.ghl_user_ids = json.dumps(user_ids)
            # Set first user as primary for backwards compatibility
            self.ghl_user_id = user_ids[0] if user_ids else None
        else:
            self.ghl_user_ids = None
            self.ghl_user_id = None

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "ghl_location_id": self.ghl_location_id,
            "ghl_location_name": self.ghl_location_name,
            "ghl_user_id": self.ghl_user_id,
            "ghl_user_name": self.ghl_user_name,
            "ghl_user_ids": self.get_user_ids_list(),  # Return as list, not JSON string
            "sending_speed": self.sending_speed,
            "schedule_type": self.schedule_type,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
