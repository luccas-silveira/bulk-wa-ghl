"""
GHL OAuth Token Model
Stores encrypted OAuth tokens for GHL locations
"""
from sqlalchemy import Column, Integer, String, LargeBinary, TIMESTAMP, Text, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class GHLOAuthToken(Base):
    """
    GHL OAuth Token model - stores encrypted OAuth 2.0 tokens for GHL API access

    Attributes:
        id: Primary key
        ghl_location_id: Foreign key to ghl_locations.ghl_location_id (UNIQUE)
        access_token_encrypted: Encrypted access token (binary)
        refresh_token_encrypted: Encrypted refresh token (binary)
        token_type: Token type (usually "Bearer")
        expires_at: Token expiration timestamp
        scope: OAuth scopes granted (space-separated string)
        raw_response: Complete OAuth response from GHL (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "ghl_oauth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ghl_location_id = Column(
        String(50),
        ForeignKey('ghl_locations.ghl_location_id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True
    )
    access_token_encrypted = Column(LargeBinary, nullable=False)
    refresh_token_encrypted = Column(LargeBinary, nullable=False)
    token_type = Column(String(20), default='Bearer', nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    scope = Column(Text, nullable=False)
    raw_response = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to GHLLocation
    location = relationship("GHLLocation", backref="oauth_token", foreign_keys=[ghl_location_id])

    # Indexes
    __table_args__ = (
        Index('idx_ghl_oauth_tokens_expiry', 'expires_at'),
        Index('idx_ghl_oauth_tokens_location', 'ghl_location_id'),
    )

    def is_expired(self) -> bool:
        """
        Check if access token is expired

        Returns:
            True if token is expired or about to expire (within 5 minutes)
        """
        from datetime import datetime, timedelta

        if not self.expires_at:
            return True

        # Consider token expired if it expires within 5 minutes
        buffer = timedelta(minutes=5)
        return datetime.utcnow() + buffer >= self.expires_at

    def __repr__(self):
        return f"<GHLOAuthToken(id={self.id}, location_id='{self.ghl_location_id}', expires_at={self.expires_at})>"

    def to_dict(self, include_tokens: bool = False):
        """
        Convert model to dictionary for JSON serialization

        Args:
            include_tokens: Whether to include encrypted tokens (default: False for security)

        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "ghl_location_id": self.ghl_location_id,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope,
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_tokens:
            data["access_token_encrypted"] = self.access_token_encrypted
            data["refresh_token_encrypted"] = self.refresh_token_encrypted

        return data
