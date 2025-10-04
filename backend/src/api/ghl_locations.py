"""
GHL Locations API Endpoints
Provides REST API for managing GHL locations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.models.ghl_location import GHLLocation
from src.models.ghl_oauth_token import GHLOAuthToken

router = APIRouter(prefix="/ghl/locations", tags=["GHL Locations"])


@router.get("", response_model=dict)
async def get_locations(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    whatsapp: Optional[bool] = Query(None, description="Filter by WhatsApp availability"),
    db: Session = Depends(get_db)
):
    """
    Get list of GHL locations

    Query Parameters:
    - active: Filter by is_active status
    - whatsapp: Filter by has_whatsapp status

    Returns:
        Dictionary with locations array
    """
    query = db.query(GHLLocation)

    # Apply filters
    if active is not None:
        query = query.filter(GHLLocation.is_active == active)

    if whatsapp is not None:
        query = query.filter(GHLLocation.has_whatsapp == whatsapp)

    locations = query.all()

    return {
        "locations": [loc.to_dict() for loc in locations]
    }


@router.get("/{location_id}", response_model=dict)
async def get_location_by_id(
    location_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific GHL location by ID

    Path Parameters:
    - location_id: GHL location identifier

    Returns:
        Location object

    Raises:
        404: If location not found
    """
    location = db.query(GHLLocation).filter(
        GHLLocation.ghl_location_id == location_id
    ).first()

    if not location:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    return location.to_dict()


@router.get("/{location_id}/validate", response_model=dict)
async def validate_location(
    location_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate a GHL location for WhatsApp messaging

    Checks:
    - Location exists
    - Location is active
    - Location has WhatsApp enabled
    - OAuth token exists and is valid

    Path Parameters:
    - location_id: GHL location identifier

    Returns:
        Validation result with details

    Raises:
        404: If location not found
    """
    location = db.query(GHLLocation).filter(
        GHLLocation.ghl_location_id == location_id
    ).first()

    if not location:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    # Check if location is active
    if not location.is_active:
        return {
            "valid": False,
            "location_id": location_id,
            "reason": "Location is not active",
            "whatsapp_status": location.whatsapp_status
        }

    # Check if location has WhatsApp
    if not location.has_whatsapp:
        return {
            "valid": False,
            "location_id": location_id,
            "reason": "Location does not have WhatsApp enabled",
            "whatsapp_status": location.whatsapp_status
        }

    # Check WhatsApp status
    if location.whatsapp_status != "active":
        return {
            "valid": False,
            "location_id": location_id,
            "reason": f"WhatsApp status is '{location.whatsapp_status}', expected 'active'",
            "whatsapp_status": location.whatsapp_status
        }

    # Check OAuth token
    oauth_token = db.query(GHLOAuthToken).filter(
        GHLOAuthToken.ghl_location_id == location_id
    ).first()

    if not oauth_token:
        return {
            "valid": False,
            "location_id": location_id,
            "reason": "No OAuth token found for this location",
            "whatsapp_status": location.whatsapp_status
        }

    # Check if token is expired
    if oauth_token.is_expired():
        return {
            "valid": False,
            "location_id": location_id,
            "reason": "OAuth token is expired",
            "whatsapp_status": location.whatsapp_status,
            "token_expires_at": oauth_token.expires_at.isoformat()
        }

    # All checks passed
    return {
        "valid": True,
        "location_id": location_id,
        "location_name": location.name,
        "whatsapp_status": location.whatsapp_status,
        "whatsapp_number": location.whatsapp_number,
        "token_expires_at": oauth_token.expires_at.isoformat()
    }
