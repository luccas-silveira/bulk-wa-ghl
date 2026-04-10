"""
GHL Location Model
Represents a GoHighLevel location (sub-account) with WhatsApp integration
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, JSON, Index
from sqlalchemy.sql import func
from src.database import Base
import re


class GHLLocation(Base):
    """
    GHL Location model - represents a GoHighLevel location (sub-account)

    Attributes:
        id: Primary key
        ghl_location_id: Unique GHL location identifier
        name: Location name
        company_id: Parent company ID in GHL
        email: Location contact email
        phone: Location phone number
        has_whatsapp: Whether location has WhatsApp enabled
        whatsapp_number: WhatsApp business phone number (E.164 format)
        whatsapp_status: Current WhatsApp status (active, pending, disconnected)
        is_active: Whether location is active
        metadata: Additional location data (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "ghl_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ghl_location_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company_id = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    has_whatsapp = Column(Boolean, default=False, nullable=False)
    whatsapp_number = Column(String(20), nullable=True)
    whatsapp_status = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column('metadata', JSON, nullable=True)  # Column name in DB is 'metadata'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_ghl_locations_company', 'company_id'),
        Index('idx_ghl_locations_active', 'is_active', postgresql_where=(is_active == True)),
        Index('idx_ghl_locations_whatsapp', 'has_whatsapp', postgresql_where=(has_whatsapp == True)),
    )

    @staticmethod
    def validate_e164_phone(phone: str) -> bool:
        """
        Validate phone number in E.164 format
        Format: +[country code][number] (e.g., +5511999999999)

        Args:
            phone: Phone number string

        Returns:
            True if valid E.164 format, False otherwise
        """
        if not phone:
            return False

        # E.164 format: + followed by 1-15 digits
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))

    def __repr__(self):
        return f"<GHLLocation(id={self.id}, ghl_location_id='{self.ghl_location_id}', name='{self.name}', has_whatsapp={self.has_whatsapp})>"

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "ghl_location_id": self.ghl_location_id,
            "name": self.name,
            "company_id": self.company_id,
            "email": self.email,
            "phone": self.phone,
            "has_whatsapp": self.has_whatsapp,
            "whatsapp_number": self.whatsapp_number,
            "whatsapp_status": self.whatsapp_status,
            "is_active": self.is_active,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
