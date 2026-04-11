"""
GHL OAuth Service
Handles OAuth 2.0 authentication flow with GoHighLevel
"""
import os
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.services.token_encryption_service import TokenEncryptionService
from src.models.ghl_oauth_token import GHLOAuthToken
from src.models.ghl_location import GHLLocation

load_dotenv()

logger = logging.getLogger(__name__)


class GHLOAuthService:
    """
    Service for managing OAuth 2.0 authentication with GoHighLevel

    Handles:
    - Authorization URL generation
    - Token exchange
    - Token refresh
    - Automatic token refresh when expired
    """

    GHL_OAUTH_BASE_URL = "https://marketplace.gohighlevel.com/oauth"
    GHL_API_BASE_URL = "https://services.leadconnectorhq.com"

    def __init__(self, db: Session):
        """
        Initialize OAuth service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.encryption_service = TokenEncryptionService()

        # Load OAuth credentials from environment
        self.client_id = os.getenv("GHL_CLIENT_ID")
        self.client_secret = os.getenv("GHL_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GHL_REDIRECT_URI")

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError(
                "Missing GHL OAuth credentials. Set GHL_CLIENT_ID, "
                "GHL_CLIENT_SECRET, and GHL_REDIRECT_URI environment variables."
            )

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for user to grant access

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL string
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "conversations.readonly conversations.write contacts.readonly locations.readonly"
        }

        if state:
            params["state"] = state

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.GHL_OAUTH_BASE_URL}/chooselocation?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dictionary with token data including location_id

        Raises:
            ValueError: If token exchange fails
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.GHL_OAUTH_BASE_URL}/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                response.raise_for_status()
                token_data = response.json()

                # Store tokens in database
                location_id = token_data.get("locationId")
                if not location_id:
                    raise ValueError("No locationId in token response")

                await self._store_tokens(location_id, token_data)

                return token_data

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Token exchange failed: status={e.response.status_code}, body={e.response.text}"
                )
                raise ValueError("Token exchange failed. Check server logs for details.")
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Token exchange error: {str(e)}", exc_info=True)
                raise ValueError("Token exchange error. Check server logs for details.")

    async def refresh_token(self, location_id: str) -> Dict:
        """
        Refresh an expired access token

        Args:
            location_id: GHL location identifier

        Returns:
            Dictionary with new token data

        Raises:
            ValueError: If refresh fails
        """
        # Get existing token from database
        token_record = self.db.query(GHLOAuthToken).filter(
            GHLOAuthToken.ghl_location_id == location_id
        ).first()

        if not token_record:
            raise ValueError(f"No OAuth token found for location {location_id}")

        # Decrypt refresh token
        refresh_token = self.encryption_service.decrypt(token_record.refresh_token_encrypted)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.GHL_OAUTH_BASE_URL}/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                response.raise_for_status()
                token_data = response.json()

                # Update tokens in database
                await self._store_tokens(location_id, token_data)

                return token_data

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Token refresh failed: location={location_id}, status={e.response.status_code}, body={e.response.text}"
                )
                raise ValueError("Token refresh failed. Check server logs for details.")
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Token refresh error: location={location_id}, {str(e)}", exc_info=True)
                raise ValueError("Token refresh error. Check server logs for details.")

    async def get_valid_access_token(self, location_id: str) -> str:
        """
        Get a valid access token, automatically refreshing if expired

        Args:
            location_id: GHL location identifier

        Returns:
            Valid decrypted access token

        Raises:
            ValueError: If token cannot be retrieved or refreshed
        """
        token_record = self.db.query(GHLOAuthToken).filter(
            GHLOAuthToken.ghl_location_id == location_id
        ).first()

        if not token_record:
            raise ValueError(f"No OAuth token found for location {location_id}")

        # Check if token is expired
        if token_record.is_expired():
            # Refresh the token
            await self.refresh_token(location_id)

            # Reload token record
            self.db.refresh(token_record)

        # Decrypt and return access token
        return self.encryption_service.decrypt(token_record.access_token_encrypted)

    async def _store_tokens(self, location_id: str, token_data: Dict) -> None:
        """
        Store or update encrypted tokens in database

        Args:
            location_id: GHL location identifier
            token_data: OAuth token response data
        """
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        scope = token_data.get("scope", "")

        if not access_token or not refresh_token:
            raise ValueError("Missing access_token or refresh_token in response")

        # Encrypt tokens
        access_token_encrypted = self.encryption_service.encrypt(access_token)
        refresh_token_encrypted = self.encryption_service.encrypt(refresh_token)

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Check if token record exists
        token_record = self.db.query(GHLOAuthToken).filter(
            GHLOAuthToken.ghl_location_id == location_id
        ).first()

        if token_record:
            # Update existing record
            token_record.access_token_encrypted = access_token_encrypted
            token_record.refresh_token_encrypted = refresh_token_encrypted
            token_record.expires_at = expires_at
            token_record.scope = scope
            token_record.raw_response = token_data
        else:
            # Create new record
            token_record = GHLOAuthToken(
                ghl_location_id=location_id,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                expires_at=expires_at,
                scope=scope,
                raw_response=token_data
            )
            self.db.add(token_record)

        self.db.commit()

    async def revoke_token(self, location_id: str) -> bool:
        """
        Revoke OAuth token and remove from database

        Args:
            location_id: GHL location identifier

        Returns:
            True if revoked successfully
        """
        token_record = self.db.query(GHLOAuthToken).filter(
            GHLOAuthToken.ghl_location_id == location_id
        ).first()

        if token_record:
            self.db.delete(token_record)
            self.db.commit()
            return True

        return False
