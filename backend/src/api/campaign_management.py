"""
Campaign Management API Endpoints
Provides campaign listing, details, logs, statistics, pause/resume, and deletion
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Response, status as http_status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.database import get_db
from src.services.campaign_management_service import CampaignManagementService

router = APIRouter(prefix="/api/v1/campaigns", tags=["Campaign Management"])


@router.get("", response_model=dict)
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by campaign status"),
    ghl_user_id: Optional[str] = Query(None, description="Filter by GHL user ID"),
    ghl_location_id: Optional[str] = Query(None, description="Filter by GHL location ID"),
    from_date: Optional[datetime] = Query(None, description="Filter campaigns created after this date"),
    to_date: Optional[datetime] = Query(None, description="Filter campaigns created before this date"),
    limit: int = Query(20, ge=1, le=100, description="Number of campaigns to return"),
    offset: int = Query(0, ge=0, description="Number of campaigns to skip"),
    db: Session = Depends(get_db)
):
    """
    List campaigns with filtering and pagination

    Query Parameters:
    - status: Filter by campaign status (draft, scheduled, executing, paused, completed, failed, cancelled)
    - ghl_user_id: Filter by GHL user ID
    - ghl_location_id: Filter by GHL location ID
    - from_date: Filter campaigns created after this date (ISO 8601)
    - to_date: Filter campaigns created before this date (ISO 8601)
    - limit: Number of campaigns to return (1-100, default: 20)
    - offset: Number of campaigns to skip (default: 0)

    Returns:
        List of campaigns with message statistics
    """
    try:
        service = CampaignManagementService(db)

        filters = {}
        if status:
            filters['status'] = status
        if ghl_user_id:
            filters['ghl_user_id'] = ghl_user_id
        if ghl_location_id:
            filters['ghl_location_id'] = ghl_location_id
        if from_date:
            filters['from_date'] = from_date
        if to_date:
            filters['to_date'] = to_date

        campaigns = service.list_campaigns(filters=filters, limit=limit, offset=offset)

        return {
            "campaigns": campaigns,
            "count": len(campaigns),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to list campaigns: {str(e)}"
            }
        )


@router.get("/{campaign_id}/details", response_model=dict)
async def get_campaign_details(
    campaign_id: int = Path(..., description="Campaign ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed campaign information including statistics and timeline

    Path Parameters:
    - campaign_id: Campaign ID

    Returns:
        Campaign details with statistics, timeline, and recent messages
    """
    try:
        service = CampaignManagementService(db)
        details = service.get_campaign_details(campaign_id)
        return details

    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": "Not found", "message": str(e)})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to get campaign details: {str(e)}"
            }
        )


@router.patch("/{campaign_id}/pause", response_model=dict)
async def pause_campaign(
    campaign_id: int = Path(..., description="Campaign ID"),
    db: Session = Depends(get_db)
):
    """
    Pause an executing campaign

    Path Parameters:
    - campaign_id: Campaign ID

    Returns:
        Success message and updated campaign data
    """
    try:
        # Get campaign with row-level lock to prevent race conditions
        from src.models.campaign import Campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).with_for_update().first()

        if not campaign:
            raise HTTPException(status_code=404, detail={"error": "Not found", "message": f"Campaign with id {campaign_id} not found"})

        # Validate status
        if campaign.status != 'executing':
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid operation",
                    "message": f"Cannot pause campaign with status '{campaign.status}'. Only executing campaigns can be paused."
                }
            )

        # Update status
        campaign.status = 'paused'
        campaign.paused_at = datetime.now()
        db.commit()
        db.refresh(campaign)

        return {
            "message": "Campaign paused successfully",
            "campaign": campaign.to_dict()
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to pause campaign: {str(e)}"
            }
        )


@router.patch("/{campaign_id}/resume", response_model=dict)
async def resume_campaign(
    campaign_id: int = Path(..., description="Campaign ID"),
    db: Session = Depends(get_db)
):
    """
    Resume a paused campaign from where it left off.
    Re-executes only contacts that haven't been sent to yet.

    Path Parameters:
    - campaign_id: Campaign ID

    Returns:
        Success message and campaign execution results
    """
    try:
        # Get campaign
        from src.models.campaign import Campaign
        from src.services.campaign_executor_service import CampaignExecutorService

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            raise HTTPException(status_code=404, detail={"error": "Not found", "message": f"Campaign with id {campaign_id} not found"})

        # Validate status
        if campaign.status != 'paused':
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid operation",
                    "message": f"Cannot resume campaign with status '{campaign.status}'. Only paused campaigns can be resumed."
                }
            )

        # Use executor service to handle resume
        executor = CampaignExecutorService(db)
        result = await executor.resume_campaign(campaign_id)

        db.refresh(campaign)
        return {
            "message": "Campaign resumed successfully",
            "details": result,
            "campaign": campaign.to_dict()
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to resume campaign: {str(e)}"
            }
        )


@router.get("/{campaign_id}/logs", response_model=dict)
async def get_campaign_logs(
    campaign_id: int = Path(..., description="Campaign ID"),
    status: Optional[str] = Query(None, description="Filter by message status"),
    recipient: Optional[str] = Query(None, description="Filter by recipient phone (partial match)"),
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    db: Session = Depends(get_db)
):
    """
    Get campaign message logs with filtering and pagination

    Path Parameters:
    - campaign_id: Campaign ID

    Query Parameters:
    - status: Filter by message status (pending, sent, delivered, read, failed)
    - recipient: Filter by recipient phone (partial match)
    - limit: Number of messages to return (1-200, default: 50)
    - offset: Number of messages to skip (default: 0)

    Returns:
        List of campaign messages with metadata
    """
    try:
        service = CampaignManagementService(db)

        filters = {}
        if status:
            filters['status'] = status
        if recipient:
            filters['recipient'] = recipient

        messages = service.get_campaign_logs(campaign_id, filters=filters, limit=limit, offset=offset)

        return {
            "logs": messages,  # Changed from "messages" to "logs" to match spec
            "count": len(messages),
            "limit": limit,
            "offset": offset,
            "campaign_id": campaign_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": "Not found", "message": str(e)})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to get campaign logs: {str(e)}"
            }
        )


@router.delete("/{campaign_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int = Path(..., description="Campaign ID"),
    db: Session = Depends(get_db)
):
    """
    Delete a campaign and all its messages

    Path Parameters:
    - campaign_id: Campaign ID

    Note: Cannot delete campaigns with status 'executing' or 'scheduled'.
    Please pause or cancel them first.

    Returns:
        HTTP 204 No Content on success
    """
    try:
        service = CampaignManagementService(db)
        service.delete_campaign(campaign_id)

        return Response(status_code=http_status.HTTP_204_NO_CONTENT)

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail={"error": "Not found", "message": error_msg})
        else:
            raise HTTPException(status_code=400, detail={"error": "Invalid operation", "message": error_msg})

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to delete campaign: {str(e)}"
            }
        )


@router.get("/stats", response_model=dict)
async def get_campaign_statistics(
    ghl_user_id: Optional[str] = Query(None, description="Filter by GHL user ID"),
    ghl_location_id: Optional[str] = Query(None, description="Filter by GHL location ID"),
    from_date: Optional[datetime] = Query(None, description="Filter campaigns created after this date"),
    to_date: Optional[datetime] = Query(None, description="Filter campaigns created before this date"),
    db: Session = Depends(get_db)
):
    """
    Get aggregate campaign statistics

    Query Parameters:
    - ghl_user_id: Filter by GHL user ID
    - ghl_location_id: Filter by GHL location ID
    - from_date: Filter campaigns created after this date (ISO 8601)
    - to_date: Filter campaigns created before this date (ISO 8601)

    Returns:
        Campaign counts by status, delivery metrics, recent campaigns, and top performers
    """
    try:
        service = CampaignManagementService(db)

        filters = {}
        if ghl_user_id:
            filters['ghl_user_id'] = ghl_user_id
        if ghl_location_id:
            filters['ghl_location_id'] = ghl_location_id
        if from_date:
            filters['from_date'] = from_date
        if to_date:
            filters['to_date'] = to_date

        statistics = service.get_campaign_statistics(filters=filters)

        return statistics

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to get campaign statistics: {str(e)}"
            }
        )
