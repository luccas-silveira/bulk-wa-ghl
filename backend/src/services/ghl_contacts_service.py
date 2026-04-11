"""
GHL Contacts Service
Handles contact management in GoHighLevel
"""
import os
import httpx
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import time
from dotenv import load_dotenv
from src.schemas.campaign import normalize_phone

load_dotenv()
logger = logging.getLogger(__name__)


class GHLContactsService:
    """
    Service for managing contacts in GoHighLevel

    Features:
    - Search contacts by phone number
    - Create new contacts
    - Get or create contact (search first, create if not found)
    - Rate limiting and retry logic
    """

    API_BASE_URL = "https://services.leadconnectorhq.com"
    API_VERSION = "2021-07-28"

    def __init__(self, db: Session):
        """
        Initialize contacts service

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

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_contact_by_phone(
        self,
        location_id: str,
        phone: str
    ) -> Optional[Dict]:
        """
        Search for a contact by phone number in GHL

        Args:
            location_id: GHL location identifier
            phone: Phone number to search (any format; normalized to E.164 before query)

        Returns:
            Contact dictionary if found, None otherwise
        """
        # Normalizar número para E.164 antes de buscar no GHL
        phone = normalize_phone(phone)

        # Get access token
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Search contacts by phone
                response = await client.get(
                    f"{self.API_BASE_URL}/contacts/",
                    params={
                        "locationId": location_id,
                        "query": phone
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Version": self.API_VERSION
                    }
                )

                response.raise_for_status()
                result = response.json()

                # Check if any contacts were found
                contacts = result.get("contacts", [])
                if contacts:
                    logger.info(f"✅ Contact found for phone {phone}: {contacts[0].get('id')}")
                    return contacts[0]

                logger.info(f"ℹ️  No contact found for phone {phone}")
                return None

            except httpx.HTTPStatusError as e:
                error_body = e.response.text if hasattr(e.response, 'text') else 'No response body'
                logger.error(f"❌ GHL Contacts Search Error: Status {e.response.status_code}, Body: {error_body}")
                raise

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def update_contact(
        self,
        contact_id: str,
        location_id: str,
        assigned_to: Optional[str] = None
    ) -> Dict:
        """
        Update contact in GHL (e.g., assign to user)

        Args:
            contact_id: GHL contact ID
            location_id: GHL location identifier
            assigned_to: User ID to assign contact to

        Returns:
            Updated contact dictionary
        """
        # Get access token
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        # Prepare update data
        update_data = {}
        if assigned_to:
            update_data["assignedTo"] = assigned_to

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.put(
                    f"{self.API_BASE_URL}/contacts/{contact_id}",
                    json=update_data,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Version": self.API_VERSION,
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()
                result = response.json()

                contact = result.get("contact", result)
                logger.info(f"🔄 Contact updated {contact_id}: assigned to {assigned_to}")
                return contact

            except httpx.HTTPStatusError as e:
                error_body = e.response.text if hasattr(e.response, 'text') else 'No response body'
                logger.error(f"❌ GHL Contact Update Error: Status {e.response.status_code}, Body: {error_body}")
                raise

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_contact(
        self,
        location_id: str,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Dict:
        """
        Create a new contact in GHL

        Args:
            location_id: GHL location identifier
            phone: Phone number (E.164 format)
            name: Contact name (optional)
            email: Contact email (optional)
            assigned_to: User ID to assign contact to (optional)

        Returns:
            Created contact dictionary with id
        """
        # Get access token
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        # Prepare contact data
        contact_data = {
            "locationId": location_id,
            "phone": phone
        }

        if name:
            # Split name into first and last name
            name_parts = name.strip().split(maxsplit=1)
            contact_data["firstName"] = name_parts[0]
            if len(name_parts) > 1:
                contact_data["lastName"] = name_parts[1]

        if email:
            contact_data["email"] = email

        if assigned_to:
            contact_data["assignedTo"] = assigned_to

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.API_BASE_URL}/contacts/",
                    json=contact_data,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Version": self.API_VERSION,
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()
                result = response.json()

                contact = result.get("contact", result)
                logger.info(f"➕ Contact created for phone {phone}: {contact.get('id')}")
                return contact

            except httpx.HTTPStatusError as e:
                error_body = e.response.text if hasattr(e.response, 'text') else 'No response body'
                logger.error(f"❌ GHL Contact Creation Error: Status {e.response.status_code}, Body: {error_body}")
                raise

    async def get_or_create_contact(
        self,
        location_id: str,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Dict:
        """
        Get existing contact or create new one, and assign to user if provided

        Args:
            location_id: GHL location identifier
            phone: Phone number (E.164 format)
            name: Contact name (optional)
            email: Contact email (optional)
            assigned_to: User ID to assign contact to (optional)

        Returns:
            Contact dictionary with id
        """
        # First, try to find existing contact
        contact = await self.search_contact_by_phone(location_id, phone)

        if contact:
            # Contact exists, update assignment if needed
            if assigned_to:
                contact = await self.update_contact(
                    contact_id=contact.get('id'),
                    location_id=location_id,
                    assigned_to=assigned_to
                )
            return contact

        # Contact not found, create new one with assignment
        contact = await self.create_contact(location_id, phone, name, email, assigned_to)
        return contact
