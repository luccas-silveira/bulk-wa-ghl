"""
GHL OAuth API Endpoints
Handles OAuth 2.0 authorization flow with GoHighLevel
"""
import secrets
import hmac as _hmac
import hashlib
import time
import json
import base64
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database import get_db
from src.services.ghl_oauth_service import GHLOAuthService
from src.models.ghl_location import GHLLocation
from src.config import GHL_CLIENT_SECRET

_STATE_TTL_SECONDS = 300  # 5 minutos


def _generate_oauth_state() -> str:
    """Generate a signed, time-limited CSRF state token (stateless, no DB required)."""
    payload = json.dumps({
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + _STATE_TTL_SECONDS,
    })
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = _hmac.new(GHL_CLIENT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_oauth_state(state) -> bool:
    """Verify state signature and expiration. Returns True only if valid."""
    if not state:
        return False
    try:
        payload_b64, sig = state.rsplit(".", 1)
        expected = _hmac.new(GHL_CLIENT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return False
        # Add padding back for urlsafe_b64decode
        padding = "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else ""
        payload = json.loads(base64.urlsafe_b64decode((payload_b64 + padding).encode()).decode())
        return int(payload["exp"]) > int(time.time())
    except Exception:
        return False


router = APIRouter(prefix="/ghl/oauth", tags=["GHL OAuth"])


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback"""
    code: str
    state: str | None = None


@router.get("/authorize")
async def oauth_authorize(db: AsyncSession = Depends(get_db)):
    """Initiate OAuth authorization flow. Generates CSRF state server-side."""
    state = _generate_oauth_state()
    oauth_service = GHLOAuthService(db)
    auth_url = oauth_service.get_authorization_url(state=state)
    return RedirectResponse(url=auth_url)


@router.post("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from GHL"),
    state: str | None = Query(None, description="CSRF state parameter"),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback. Validates CSRF state before processing."""
    if not state or not _verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or missing CSRF state parameter")

    oauth_service = GHLOAuthService(db)

    try:
        token_data = await oauth_service.exchange_code_for_token(code)

        location_id = token_data["location_id"]

        result = await db.execute(
            select(GHLLocation).where(GHLLocation.ghl_location_id == location_id)
        )
        location = result.scalar_one_or_none()

        if not location:
            location = GHLLocation(
                ghl_location_id=location_id,
                name=f"Location {location_id}",
                company_id=token_data["company_id"],
                is_active=True,
                has_whatsapp=True,
                whatsapp_status="pending"
            )
            db.add(location)
            await db.commit()
            await db.refresh(location)

        return {
            "success": True,
            "message": "OAuth authorization successful",
            "location_id": location_id,
            "location_name": location.name,
            "expires_in": token_data["expires_in"],
            "scope": token_data["scope"],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh/{location_id}")
async def refresh_oauth_token(
    location_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually refresh OAuth token for a location

    Path Parameters:
    - location_id: GHL location identifier

    Returns:
        Success message with new token details

    Raises:
        400: If token refresh fails
        404: If location or token not found
    """
    oauth_service = GHLOAuthService(db)

    try:
        token_data = await oauth_service.refresh_token(location_id)

        return {
            "success": True,
            "message": "Token refreshed successfully",
            "location_id": location_id,
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope")
        }

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/revoke/{location_id}")
async def revoke_oauth_token(
    location_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke OAuth token for a location

    Path Parameters:
    - location_id: GHL location identifier

    Returns:
        Success message

    Raises:
        404: If token not found
    """
    oauth_service = GHLOAuthService(db)

    success = await oauth_service.revoke_token(location_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No OAuth token found for location {location_id}"
        )

    return {
        "success": True,
        "message": f"OAuth token revoked for location {location_id}"
    }
