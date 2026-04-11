"""
Analytics API Endpoints
Provides dashboard analytics and metrics for campaigns and messages
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    ghl_user_id: Optional[str] = Query(None, description="Filter metrics by GoHighLevel user ID"),
    days: int = Query(30, ge=1, le=365, description="Time range in days (1-365)"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics with real-time campaign and delivery data

    Query Parameters:
    - ghl_user_id: Optional filter by GHL user ID
    - days: Time range in days (default: 30, range: 1-365)

    Returns:
        Dashboard metrics including campaign stats, delivery metrics,
        recent campaigns, and top performing campaigns
    """

    # Validate days parameter
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid parameter",
                "message": "days must be between 1 and 365"
            }
        )

    try:
        # Get campaign metrics
        campaign_metrics = analytics_service.get_campaign_metrics(
            db=db,
            ghl_user_id=ghl_user_id,
            days=days
        )

        # Get delivery metrics
        delivery_metrics = analytics_service.get_delivery_metrics(
            db=db,
            ghl_user_id=ghl_user_id,
            days=days
        )

        # Get recent campaigns
        recent_campaigns = analytics_service.get_recent_campaigns(
            db=db,
            ghl_user_id=ghl_user_id,
            days=days,
            limit=5
        )

        # Get top performing campaigns
        top_performing_campaigns = analytics_service.get_top_campaigns(
            db=db,
            ghl_user_id=ghl_user_id,
            days=days,
            limit=10
        )

        # Get delivery timeline for charts
        timeline = analytics_service.get_delivery_timeline(
            db=db,
            ghl_user_id=ghl_user_id,
            days=days
        )

        # Build time range string
        time_range = f"Últimos {days} dias"

        # Build filter info string
        if ghl_user_id:
            filter_info = f"Dados filtrados para usuário: {ghl_user_id}"
        else:
            filter_info = "Dados agregados de todos os usuários"

        # Build response
        response = {
            "campaign_metrics": campaign_metrics,
            "delivery_metrics": delivery_metrics,
            "recent_campaigns": recent_campaigns,
            "top_performing_campaigns": top_performing_campaigns,
            "timeline": timeline,
            "time_range": time_range,
            "filter_info": filter_info
        }

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"Failed to query metrics: {str(e)}"
            }
        )
