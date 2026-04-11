"""
GHL Conversations Service
Handles WhatsApp message sending through GoHighLevel Conversations API
"""
import asyncio
import os
import httpx
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class TokenBucket:
    """
    Token bucket algorithm for rate limiting
    Allows 120 requests per minute (2 requests per second)
    """

    def __init__(self, capacity: int = 120, refill_rate: float = 2.0):
        """
        Initialize token bucket

        Args:
            capacity: Maximum number of tokens (requests) in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def wait_time(self) -> float:
        """Calculate wait time until next token is available"""
        if self.tokens >= 1:
            return 0.0

        return (1 - self.tokens) / self.refill_rate


class GHLConversationsService:
    """
    Service for managing WhatsApp conversations through GoHighLevel

    Features:
    - Send text and media messages
    - Rate limiting (120 req/min)
    - Automatic retry with exponential backoff
    - Conversation management
    """

    API_BASE_URL = "https://services.leadconnectorhq.com"
    API_VERSION = os.getenv("GHL_API_VERSION", "2021-07-28")

    def __init__(self, db: Session):
        """
        Initialize conversations service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        # Check if using private token or OAuth
        self.private_token = os.getenv("GHL_PRIVATE_TOKEN")
        self.use_private_token = bool(self.private_token)

        if not self.use_private_token:
            # Only import OAuth service if not using private token
            from src.services.ghl_oauth_service import GHLOAuthService
            self.oauth_service = GHLOAuthService(db)

        self.rate_limiter = TokenBucket(capacity=120, refill_rate=2.0)

    async def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded"""
        if not self.rate_limiter.consume():
            wait_time = self.rate_limiter.wait_time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.rate_limiter.consume()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_message(
        self,
        location_id: str,
        contact_id: str,
        message_text: str,
        media_url: Optional[str] = None
    ) -> Dict:
        """
        Send a WhatsApp message through GHL

        Args:
            location_id: GHL location identifier
            contact_id: GHL contact identifier (not phone number)
            message_text: Message text content
            media_url: Optional media URL for image/video/document

        Returns:
            Dictionary with message details (messageId, conversationId, status)

        Raises:
            ValueError: If parameters are invalid
            RateLimitExceeded: If rate limit is exceeded
            httpx.HTTPStatusError: If API request fails
        """
        # Validate inputs - message_text OR media_url is required
        if not location_id or not contact_id:
            raise ValueError("location_id and contact_id are required")

        if not message_text and not media_url:
            raise ValueError("Either message_text or media_url must be provided")

        # Apply rate limiting
        await self._wait_for_rate_limit()

        # Get access token (private token or OAuth)
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        # Prepare request payload
        payload = {
            'type': 'WhatsApp',  # GHL-06: was "SMS"
            'contactId': contact_id,  # GHL contact ID (not phone number)
            'message': message_text or ''  # Empty string if only media
        }

        if media_url:
            payload["attachments"] = [media_url]  # Array of URL strings, not objects

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.API_BASE_URL}/conversations/messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Version": self.API_VERSION,
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()
                result = response.json()

                return {
                    "messageId": result.get("id"),
                    "conversationId": result.get("conversationId"),
                    "contactId": result.get("contactId"),
                    "status": "sent",
                    "sentAt": datetime.utcnow().isoformat()
                }

            except httpx.HTTPStatusError as e:
                # Log detailed error information
                error_body = e.response.text if hasattr(e.response, 'text') else 'No response body'
                logger.error(f'❌ GHL API Error: Status {e.response.status_code}, URL: {e.request.url}, Body: {error_body}')

                if e.response.status_code == 401 and not self.use_private_token:
                    # GHL-08: token expired at runtime → force refresh, then re-raise for @retry
                    logger.warning(f'Token expired for location {location_id}, forcing refresh')
                    await self.oauth_service.refresh_token(location_id)
                elif e.response.status_code == 429:
                    raise RateLimitExceeded('GHL API rate limit exceeded')
                raise

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_conversation(self, location_id: str, conversation_id: str) -> Dict:
        """
        Get conversation details from GHL

        Args:
            location_id: GHL location identifier
            conversation_id: GHL conversation identifier

        Returns:
            Dictionary with conversation details
        """
        await self._wait_for_rate_limit()

        # Get access token (private token or OAuth)
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/conversations/{conversation_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Version": self.API_VERSION
                }
            )

            response.raise_for_status()
            return response.json()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def list_conversations(
        self,
        location_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        List conversations for a location

        Args:
            location_id: GHL location identifier
            limit: Maximum number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversation dictionaries
        """
        await self._wait_for_rate_limit()

        # Get access token (private token or OAuth)
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/conversations",
                params={
                    "locationId": location_id,
                    "limit": limit,
                    "offset": offset
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Version": self.API_VERSION
                }
            )

            response.raise_for_status()
            result = response.json()
            return result.get("conversations", [])

    async def get_message_status(
        self,
        location_id: str,
        message_id: str
    ) -> Dict:
        """
        Get status of a specific message

        Args:
            location_id: GHL location identifier
            message_id: GHL message identifier

        Returns:
            Dictionary with message status details
        """
        await self._wait_for_rate_limit()

        # Get access token (private token or OAuth)
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/conversations/messages/{message_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Version": self.API_VERSION
                }
            )

            response.raise_for_status()
            return response.json()
