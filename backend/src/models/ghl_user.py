"""
GHL User Model
Stores users from GoHighLevel locations
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class GHLUser(Base):
    """
    GHL User model - represents a user within a GoHighLevel location

    Attributes:
        id: Primary key
        ghl_user_id: GoHighLevel user ID
        ghl_location_id: Foreign key to ghl_locations
        name: User full name
        email: User email
        phone: User phone number
        role: User role (admin, user, etc)
        is_active: Whether user is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "ghl_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ghl_user_id = Column(String(50), unique=True, nullable=False, index=True)
    ghl_location_id = Column(
        String(50),
        ForeignKey('ghl_locations.ghl_location_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to GHLLocation
    location = relationship("GHLLocation", backref="users", foreign_keys=[ghl_location_id])

    # Indexes
    __table_args__ = (
        Index('idx_ghl_users_location', 'ghl_location_id'),
        Index('idx_ghl_users_active', 'is_active'),
    )

    def __repr__(self):
        return f"<GHLUser(id={self.id}, name='{self.name}', location='{self.ghl_location_id}')>"

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "ghl_user_id": self.ghl_user_id,
            "ghl_location_id": self.ghl_location_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
