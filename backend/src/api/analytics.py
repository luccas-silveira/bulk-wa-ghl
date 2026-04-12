"""
Analytics API Endpoints
Provides dashboard analytics and metrics for campaigns and messages
"""
import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional

from src.database import get_db
from src.services import analytics_service
from src.limiter import limiter

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

# In-process TTL cache: key → (timestamp, payload). Unbounded by design
# for single-tenant, low-cardinality use (ghl_user_id + days). If user count
# grows significantly, replace with cachetools.TTLCache(maxsize=..., ttl=...).
_dashboard_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 30.0


@router.get("/dashboard", response_model=dict)
@limiter.limit("60/minute")
async def get_dashboard(
    request: Request,
    ghl_user_id: Optional[str] = Query(None, description="Filter metrics by GoHighLevel user ID"),
    days: int = Query(30, ge=1, le=365, description="Time range in days (1-365)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard metrics with real-time campaign and delivery data.

    Returns 504 if analytics queries exceed 5 seconds.
    Caches responses for 30 seconds. Use X-Cache-Bypass: true to force re-query.
    """
    bypass = request.headers.get("X-Cache-Bypass", "").lower() == "true"
    cache_key = f"{ghl_user_id}:{days}"

    if not bypass and cache_key in _dashboard_cache:
        cached_at, cached_payload = _dashboard_cache[cache_key]
        if time.monotonic() - cached_at < _CACHE_TTL_SECONDS:
            return cached_payload

    async def _gather_all():
        # Sequential awaits share one AsyncSession — asyncio.gather() with
        # a shared session would risk re-entrancy issues on the same connection.
        campaign_metrics = await analytics_service.get_campaign_metrics(
            db=db, ghl_user_id=ghl_user_id, days=days
        )
        delivery_metrics = await analytics_service.get_delivery_metrics(
            db=db, ghl_user_id=ghl_user_id, days=days
        )
        recent_campaigns = await analytics_service.get_recent_campaigns(
            db=db, ghl_user_id=ghl_user_id, days=days, limit=5
        )
        top_performing_campaigns = await analytics_service.get_top_campaigns(
            db=db, ghl_user_id=ghl_user_id, days=days, limit=10
        )
        timeline = await analytics_service.get_delivery_timeline(
            db=db, ghl_user_id=ghl_user_id, days=days
        )
        return campaign_metrics, delivery_metrics, recent_campaigns, top_performing_campaigns, timeline

    try:
        (
            campaign_metrics,
            delivery_metrics,
            recent_campaigns,
            top_performing_campaigns,
            timeline,
        ) = await asyncio.wait_for(_gather_all(), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Analytics query timeout — try a shorter date range"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Database error", "message": f"Failed to query metrics: {str(e)}"}
        )

    time_range = f"Últimos {days} dias"
    if ghl_user_id:
        filter_info = f"Dados filtrados para usuário: {ghl_user_id}"
    else:
        filter_info = "Dados agregados de todos os usuários"

    payload = {
        "campaign_metrics": campaign_metrics,
        "delivery_metrics": delivery_metrics,
        "recent_campaigns": recent_campaigns,
        "top_performing_campaigns": top_performing_campaigns,
        "timeline": timeline,
        "time_range": time_range,
        "filter_info": filter_info,
    }

    _dashboard_cache[cache_key] = (time.monotonic(), payload)
    return payload
