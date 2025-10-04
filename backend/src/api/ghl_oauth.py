"""
GHL OAuth API Endpoints
Handles OAuth 2.0 authorization flow with GoHighLevel
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database import get_db
from src.services.ghl_oauth_service import GHLOAuthService
from src.models.ghl_location import GHLLocation

router = APIRouter(prefix="/ghl/oauth", tags=["GHL OAuth"])


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback"""
    code: str
    state: str | None = None


@router.get("/authorize")
async def oauth_authorize(
    state: str | None = Query(None, description="Optional state parameter for CSRF protection"),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth authorization flow

    Redirects user to GHL authorization page

    Query Parameters:
    - state: Optional CSRF protection token

    Returns:
        Redirect to GHL authorization URL
    """
    oauth_service = GHLOAuthService(db)
    auth_url = oauth_service.get_authorization_url(state=state)

    return RedirectResponse(url=auth_url)


@router.post("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from GHL"),
    state: str | None = Query(None, description="State parameter"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from GHL

    Exchanges authorization code for access token and stores it

    Query Parameters:
    - code: Authorization code from GHL
    - state: Optional state parameter

    Returns:
        Success message with location details

    Raises:
        400: If token exchange fails
    """
    oauth_service = GHLOAuthService(db)

    try:
        token_data = await oauth_service.exchange_code_for_token(code)

        location_id = token_data.get("locationId")

        # Try to get location details from GHL or create placeholder
        location = db.query(GHLLocation).filter(
            GHLLocation.ghl_location_id == location_id
        ).first()

        if not location:
            # Create placeholder location record
            # In production, you would fetch location details from GHL API
            location = GHLLocation(
                ghl_location_id=location_id,
                name=f"Location {location_id}",
                company_id=token_data.get("companyId", "unknown"),
                is_active=True,
                has_whatsapp=True,  # Assume true since user went through OAuth
                whatsapp_status="pending"
            )
            db.add(location)
            db.commit()
            db.refresh(location)

        return {
            "success": True,
            "message": "OAuth authorization successful",
            "location_id": location_id,
            "location_name": location.name,
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope")
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh/{location_id}")
async def refresh_oauth_token(
    location_id: str,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
