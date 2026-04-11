"""
FastAPI Backend - WhatsApp Campaign Management with GoHighLevel Integration
Complete API with GHL OAuth, Conversations, and Webhooks
"""

from fastapi import FastAPI, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import time
import uuid

# Import database
from src.database import get_db, SessionLocal, engine

# Import models
from src.models.campaign import Campaign
from src.models.message import Message

# Import schemas
from src.schemas.campaign import CampaignCreateRequest

# Import services
from src.services.campaign_executor_service import CampaignExecutorService
from src.services.campaign_scheduler import CampaignScheduler
from src.logging_config import (
    http_method_ctx_var,
    request_path_ctx_var,
    request_id_ctx_var,
    setup_logging,
)
from src.metrics import api_request_errors, api_request_latency, scheduler_jobs_gauge
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from src.config import CORS_ORIGINS, ENABLE_METRICS, GHL_ENABLED, DEBUG

# Import GHL API routers
from src.api.ghl_locations import router as ghl_locations_router
from src.api.ghl_oauth import router as ghl_oauth_router
from src.api.ghl_messages import router as ghl_messages_router
from src.api.ghl_webhooks import router as ghl_webhooks_router
from src.api.ghl_users import router as ghl_users_router
from src.api import analytics
from src.api import campaign_management

setup_logging()

# Initialize Campaign Scheduler (before lifespan to ensure it's available)
scheduler = CampaignScheduler()

# GHL-10: pre-register cleanup job so it is visible to get_jobs() before lifespan runs
from apscheduler.triggers.interval import IntervalTrigger as _IntervalTrigger
from sqlalchemy import text as _sql_text


async def _cleanup_old_webhooks():
    """Delete processed_webhooks older than 30 days (GHL-10)."""
    db_session = SessionLocal()
    try:
        result = db_session.execute(
            _sql_text(
                "DELETE FROM processed_webhooks "
                "WHERE processed_at < now() - interval '30 days'"
            )
        )
        db_session.commit()
        logging.getLogger(__name__).info(
            f"Cleaned up {result.rowcount} old processed webhooks"
        )
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Webhook cleanup job failed: {e}", exc_info=True
        )
        db_session.rollback()
    finally:
        db_session.close()


scheduler.scheduler.add_job(
    _cleanup_old_webhooks,
    trigger=_IntervalTrigger(days=1),
    id="cleanup_old_webhooks",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    if DEBUG:
        logger.warning(
            "DEBUG mode is enabled — SQL queries will be logged. "
            "Disable DEBUG in production."
        )
    scheduler.start()
    logger.info("Application started with Campaign Scheduler")

    # GHL-10: ensure cleanup job is registered (replace_existing=True is idempotent)
    scheduler.scheduler.add_job(
        _cleanup_old_webhooks,
        trigger=_IntervalTrigger(days=1),
        id="cleanup_old_webhooks",
        replace_existing=True,
    )
    logger.info("Registered webhook cleanup job (runs every 24h)")

    yield
    scheduler.shutdown()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="WhatsApp Campaign Management API",
    description="API with GoHighLevel integration for WhatsApp messaging",
    version="0.2.0",
    lifespan=lifespan
)

logger = logging.getLogger(__name__)

metrics_enabled = ENABLE_METRICS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Register GHL API routers only when GHL is configured
if GHL_ENABLED:
    app.include_router(ghl_locations_router)
    app.include_router(ghl_oauth_router)
    app.include_router(ghl_messages_router)
    app.include_router(ghl_webhooks_router)
    app.include_router(ghl_users_router)

# Always registered
app.include_router(analytics.router)
app.include_router(campaign_management.router)


# Observability middleware
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_token = request_id_ctx_var.set(request_id)
    path_token = request_path_ctx_var.set(request.url.path)
    method_token = http_method_ctx_var.set(request.method)

    start_time = time.perf_counter()
    response: Response

    try:
        response = await call_next(request)
        return response
    except Exception:
        api_request_errors.labels(method=request.method, path=request.url.path, status="500").inc()
        logger.exception("Unhandled exception during request")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )
    finally:
        duration = time.perf_counter() - start_time
        api_request_latency.labels(method=request.method, path=request.url.path).observe(duration)

        if 'response' in locals() and response.status_code >= 400:
            api_request_errors.labels(
                method=request.method,
                path=request.url.path,
                status=str(response.status_code)
            ).inc()

        scheduler_jobs_gauge.set(len(scheduler.scheduler.get_jobs()))

        request_id_ctx_var.reset(request_token)
        request_path_ctx_var.reset(path_token)
        http_method_ctx_var.reset(method_token)






@app.get("/")
async def root():
    """Endpoint principal"""
    return {
        "message": "WhatsApp Campaign Management API",
        "version": "0.1.0",
        "status": "healthy",
        "provider": "GoHighLevel"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with database connectivity verification
    Returns 200 OK if healthy, 503 if database is unreachable
    """
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

    return {
        "status": "healthy",
        "database": db_status,
        "service": "wpp-disp-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if metrics_enabled:

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        """Expose Prometheus metrics for scraping. Protected by optional METRICS_TOKEN."""
        from src.config import METRICS_TOKEN
        if METRICS_TOKEN:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {METRICS_TOKEN}":
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ===== DASHBOARD API (NOW USES REAL DATA FROM ANALYTICS ROUTER) =====
# The dashboard endpoint is now handled by src/api/analytics.py
# It uses the analytics_service to provide real-time metrics from the database

# ===== CAMPAIGN CREATION (COM EXECUÇÃO REAL) =====

@app.post("/campaigns")
async def create_campaign(
    campaign_data: CampaignCreateRequest,
    db: Session = Depends(get_db)
):
    """
    POST /campaigns - Create and optionally execute a campaign via GHL.
    Validates input with Pydantic schema. Returns 422 for invalid data.
    """
    logger.info("Campaign creation request received")

    # Extract validated data
    ghl_location_id = campaign_data.ghl_location_id
    name = campaign_data.name
    ghl_user_id = campaign_data.ghl_user_id
    ghl_user_ids = campaign_data.ghl_user_ids
    sending_speed = campaign_data.sending_speed
    schedule_type = campaign_data.schedule_type
    scheduled_time = campaign_data.scheduled_time
    messages = [m.model_dump() for m in campaign_data.messages]
    csv_data = [c.model_dump() for c in campaign_data.audience_criteria.csv_data]

    # WAHA-12: validate ghl_location_id exists
    from src.models.ghl_location import GHLLocation
    location = db.query(GHLLocation).filter_by(ghl_location_id=ghl_location_id).first()
    if not location:
        return JSONResponse(
            status_code=422,
            content={"detail": f"GHL location '{ghl_location_id}' not found. Register the location first."}
        )

    # GHL-22: validate each ghl_user_id exists in ghl_users
    from src.models.ghl_user import GHLUser
    user_ids_to_validate = ghl_user_ids or ([ghl_user_id] if ghl_user_id else [])
    if not user_ids_to_validate:
        return JSONResponse(
            status_code=422,
            content={"detail": "At least one GHL user ID must be provided (ghl_user_ids or ghl_user_id)."}
        )
    for uid in user_ids_to_validate:
        user = db.query(GHLUser).filter_by(ghl_user_id=uid).first()
        if not user:
            return JSONResponse(
                status_code=422,
                content={"detail": f"GHL user '{uid}' not found in ghl_users table."}
            )

    logger.info(f"Campaign data: schedule_type={schedule_type}, contacts={len(csv_data)}, messages={len(messages)}")

    # Parse scheduled_time if provided
    parsed_scheduled_time = None
    if scheduled_time:
        try:
            parsed_scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        except Exception as e:
            logger.error(f"Failed to parse scheduled_time: {scheduled_time}, error: {e}")

    # Criar campanha no banco
    campaign = Campaign(
        name=name,
        status='draft',
        ghl_location_id=ghl_location_id,
        ghl_user_id=ghl_user_id,
        sending_speed=sending_speed,
        schedule_type=schedule_type,
        scheduled_time=parsed_scheduled_time
    )

    # Set multiple users if provided (otherwise fallback to single user)
    if ghl_user_ids and isinstance(ghl_user_ids, list) and len(ghl_user_ids) > 0:
        campaign.set_user_ids_list(ghl_user_ids)
        logger.info(f"📋 Multiple users set: {ghl_user_ids}")
    elif ghl_user_id:
        campaign.set_user_ids_list([ghl_user_id])
        logger.info(f"📋 Single user set: {ghl_user_id}")

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    campaign_id = campaign.id
    logger.info(f"Campaign {campaign_id} created: '{name}' with {len(csv_data)} recipients")

    # Resposta da campanha criada
    campaign_response = {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "ghl_location_id": campaign.ghl_location_id,
        "ghl_user_id": campaign.ghl_user_id,
        "sending_speed": campaign.sending_speed,
        "schedule_type": campaign.schedule_type,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "estimated_recipients": len(csv_data)
    }

    # Se for execução imediata, executar em background
    # Se for agendada, agendar no scheduler
    logger.info(f"Execution mode: schedule_type={schedule_type}, contacts={len(csv_data)}")

    # Persist contacts and messages in the campaign record for resume/scheduled support
    campaign.contacts_data = csv_data
    campaign.messages_template = messages
    db.commit()

    if schedule_type == 'immediate' and len(csv_data) > 0:
        logger.info(f"Starting background execution for campaign {campaign_id}")

        # Executar campanha em background com nova sessão de banco
        async def execute_campaign_background():
            """Execute campaign in background with independent DB session"""
            db_session = SessionLocal()
            try:
                executor = CampaignExecutorService(db_session)

                result = await executor.execute_campaign(
                    campaign_id=campaign_id,
                    contacts=csv_data,
                    messages_template=messages
                )

                logger.info(f"Campaign {campaign_id} completed: {result}")

            except Exception as e:
                logger.error(f"Error executing campaign {campaign_id}: {str(e)}", exc_info=True)
            finally:
                db_session.close()

        # Criar task independente (não bloqueia a resposta)
        asyncio.create_task(execute_campaign_background())

    elif schedule_type == 'scheduled' and parsed_scheduled_time and len(csv_data) > 0:
        # Schedule campaign for future execution
        logger.info(f"Scheduling campaign {campaign_id} for {parsed_scheduled_time}")

        try:
            scheduler.schedule_campaign(
                campaign_id=campaign_id,
                scheduled_time=parsed_scheduled_time,
                csv_data=csv_data,
                messages=messages
            )

            # Update status to 'scheduled'
            campaign.transition_to('scheduled')
            db.commit()

            logger.info(f"Campaign {campaign_id} scheduled successfully")

        except Exception as e:
            logger.error(f"Failed to schedule campaign {campaign_id}: {str(e)}")
            campaign.transition_to('failed')
            db.commit()

    return JSONResponse(status_code=201, content=campaign_response)


# ===== CAMPAIGN STATUS AND CONTROL =====

@app.get("/campaigns/scheduled")
async def list_scheduled_campaigns(db: Session = Depends(get_db)):
    """
    GET /campaigns/scheduled - List all scheduled campaigns
    """
    try:
        campaigns = db.query(Campaign).filter(
            Campaign.status == 'scheduled',
            Campaign.scheduled_time > datetime.now(timezone.utc)
        ).all()

        # Get scheduler jobs
        scheduled_jobs = scheduler.get_scheduled_jobs()
        job_map = {job['campaign_id']: job for job in scheduled_jobs}

        result = []
        for campaign in campaigns:
            campaign_dict = campaign.to_dict()
            job_info = job_map.get(campaign.id, {})
            campaign_dict['next_run_time'] = job_info.get('scheduled_time')
            result.append(campaign_dict)

        return JSONResponse(content={
            "campaigns": result,
            "total": len(result)
        })

    except Exception as e:
        logger.error(f"Failed to list scheduled campaigns: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list campaigns: {str(e)}"}
        )


@app.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    GET /campaigns/{id} - Obter detalhes e status da campanha
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        return JSONResponse(
            status_code=404,
            content={"error": "Campaign not found"}
        )

    return JSONResponse(content=campaign.to_dict())


@app.get("/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: int, db: Session = Depends(get_db)):
    """
    GET /campaigns/{id}/status - Status de execução em tempo real
    """
    executor = CampaignExecutorService(db)

    try:
        status_data = await executor.get_campaign_status(campaign_id)
        return JSONResponse(content=status_data)
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )


@app.get("/campaigns/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    GET /campaigns/{id}/messages - Listar mensagens enviadas
    """
    executor = CampaignExecutorService(db)

    try:
        messages = await executor.get_campaign_messages(campaign_id, limit, offset)
        return JSONResponse(content={"messages": messages, "limit": limit, "offset": offset})
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )


@app.delete("/campaigns/{campaign_id}/schedule")
async def cancel_scheduled_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    DELETE /campaigns/{id}/schedule - Cancel a scheduled campaign
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        return JSONResponse(
            status_code=404,
            content={"error": "Campaign not found"}
        )

    if campaign.status != 'scheduled':
        return JSONResponse(
            status_code=400,
            content={"error": f"Campaign is not scheduled (status: {campaign.status})"}
        )

    try:
        # Remove from scheduler
        scheduler.cancel_campaign(campaign_id)

        # Update status
        campaign.transition_to('cancelled')
        db.commit()

        return JSONResponse(content={
            "success": True,
            "message": f"Campaign {campaign_id} cancelled",
            "campaign_id": campaign_id
        })

    except Exception as e:
        logger.error(f"Failed to cancel campaign {campaign_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to cancel campaign: {str(e)}"}
        )


@app.post("/campaigns/{campaign_id}/execute")
async def execute_campaign_manually(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    POST /campaigns/{id}/execute - Executar campanha manualmente
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        return JSONResponse(
            status_code=404,
            content={"error": "Campaign not found"}
        )

    if campaign.status == 'executing':
        return JSONResponse(
            status_code=400,
            content={"error": "Campaign is already executing"}
        )

    if campaign.status == 'completed':
        return JSONResponse(
            status_code=400,
            content={"error": "Campaign already completed"}
        )

    # Get messages from database or reconstruct from stored data
    # For now, we'll need the original CSV data - this should be stored in the campaign
    return JSONResponse(
        status_code=400,
        content={"error": "Manual execution not yet fully implemented. Use POST /campaigns with immediate schedule_type."}
    )


# ===== DOCUMENTAÇÃO E STATUS =====

@app.get("/docs-status")
async def docs_status():
    """Status da implementação"""
    return {
        "provider": "GoHighLevel (GHL)",
        "endpoints": [
            "POST /api/v1/campaigns - Criar campanha",
            "GET /api/v1/campaigns - Listar campanhas",
            "GET /api/v1/analytics/dashboard - Dashboard de métricas",
            "GET /ghl/locations - Listar locations GHL",
            "GET /ghl/users - Listar usuários GHL",
            "POST /ghl/oauth/callback - Callback OAuth GHL",
            "POST /ghl/webhooks - Receber webhooks GHL",
            "GET /health - Health check",
            "GET /docs - Documentação Swagger"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)