"""
GHL Users Service
Handles fetching users from GoHighLevel API
"""
import os
import httpx
import logging
from typing import ClassVar, List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv
from src.models.ghl_user import GHLUser

load_dotenv()

logger = logging.getLogger(__name__)


class GHLUsersService:
    """Service for managing GHL users"""

    BASE_URL = "https://services.leadconnectorhq.com"
    _http_client: ClassVar[Optional[httpx.AsyncClient]] = None

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._http_client is None or cls._http_client.is_closed:
            cls._http_client = httpx.AsyncClient(timeout=10.0)
        return cls._http_client

    @classmethod
    async def close_client(cls) -> None:
        if cls._http_client and not cls._http_client.is_closed:
            await cls._http_client.aclose()
            cls._http_client = None

    def __init__(self, db: AsyncSession):
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
    async def fetch_users_from_api(self, location_id: str) -> List[Dict]:
        """
        Fetch users from GHL API for a specific location

        Args:
            location_id: GHL location ID

        Returns:
            List of user dictionaries from GHL API
        """
        # Get access token (private token or OAuth)
        if self.use_private_token:
            access_token = self.private_token
        else:
            access_token = await self.oauth_service.get_valid_access_token(location_id)

        if not access_token:
            raise ValueError(f"No valid access token for location {location_id}")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

        client = self._get_client()
        # GHL Users API endpoint
        response = await client.get(
            f"{self.BASE_URL}/users/",
            headers=headers,
            params={"locationId": location_id},
        )

        response.raise_for_status()
        data = response.json()

        # GHL returns users in "users" array
        return data.get("users", [])

    async def sync_users_for_location(self, location_id: str) -> List[GHLUser]:
        """
        Fetch users from GHL API and sync to database.
        Users returned by API → is_active=True (upsert).
        Users in DB but NOT returned by API → is_active=False (GHL-15).

        Args:
            location_id: GHL location ID

        Returns:
            List of GHLUser models
        """
        users_data = await self.fetch_users_from_api(location_id)

        synced_users = []
        api_user_ids = set()

        for user_data in users_data:
            ghl_user_id = user_data.get('id')
            if not ghl_user_id:
                logger.warning("GHL API returned user without 'id', skipping: %s", user_data)
                continue
            api_user_ids.add(ghl_user_id)

            ex_result = await self.db.execute(
                select(GHLUser).where(GHLUser.ghl_user_id == ghl_user_id)
            )
            existing_user = ex_result.scalar_one_or_none()

            if existing_user:
                existing_user.name = user_data.get('name', '')
                existing_user.email = user_data.get('email')
                existing_user.phone = user_data.get('phone')
                existing_user.role = user_data.get('role')
                existing_user.is_active = True
                synced_users.append(existing_user)
            else:
                new_user = GHLUser(
                    ghl_user_id=ghl_user_id,
                    ghl_location_id=location_id,
                    name=user_data.get('name', ''),
                    email=user_data.get('email'),
                    phone=user_data.get('phone'),
                    role=user_data.get('role'),
                    is_active=True,
                )
                self.db.add(new_user)
                synced_users.append(new_user)

        # GHL-15: mark users removed from GHL as inactive
        if api_user_ids:
            await self.db.execute(
                update(GHLUser)
                .where(
                    GHLUser.ghl_location_id == location_id,
                    GHLUser.ghl_user_id.notin_(api_user_ids),
                )
                .values(is_active=False)
            )
        else:
            # API returned empty → mark ALL local users for this location inactive
            await self.db.execute(
                update(GHLUser)
                .where(GHLUser.ghl_location_id == location_id)
                .values(is_active=False)
            )

        await self.db.commit()
        return synced_users

    async def get_users_by_location(self, location_id: str, active_only: bool = True) -> List[GHLUser]:
        """
        Get users from database for a location

        Args:
            location_id: GHL location ID
            active_only: Only return active users

        Returns:
            List of GHLUser models
        """
        stmt = select(GHLUser).where(GHLUser.ghl_location_id == location_id)
        if active_only:
            stmt = stmt.where(GHLUser.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
