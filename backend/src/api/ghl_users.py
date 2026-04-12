"""
GHL Users API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.database import get_db
from src.services.ghl_users_service import GHLUsersService

router = APIRouter(prefix="/ghl", tags=["GHL Users"])


@router.get("/users")
async def get_users_by_location(
    location_id: str = Query(..., description="GHL Location ID"),
    sync: bool = Query(False, description="Sync from GHL API before returning"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get users for a GHL location

    Args:
        location_id: GHL location ID
        sync: If True, fetch fresh data from GHL API first
        db: Database session

    Returns:
        List of users
    """
    try:
        service = GHLUsersService(db)

        if sync:
            # Fetch fresh data from GHL API and sync to database
            users = await service.sync_users_for_location(location_id)
        else:
            # Get from database, but if empty, fetch from API once
            users = await service.get_users_by_location(location_id, active_only=True)
            if not users:
                users = await service.sync_users_for_location(location_id)

        return {
            "users": [user.to_dict() for user in users],
            "location_id": location_id,
            "count": len(users)
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.post("/users/sync/{location_id}")
async def sync_users(
    location_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually sync users from GHL API for a location

    Args:
        location_id: GHL location ID
        db: Database session

    Returns:
        Synced users
    """
    try:
        service = GHLUsersService(db)
        users = await service.sync_users_for_location(location_id)

        return {
            "message": f"Successfully synced {len(users)} users",
            "users": [user.to_dict() for user in users],
            "location_id": location_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync users: {str(e)}")
