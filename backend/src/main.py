"""
FastAPI Backend - WhatsApp Campaign Management with GoHighLevel Integration
Complete API with GHL OAuth, Conversations, and Webhooks
"""

from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging
import hmac
import os
import time
import uuid
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import database
from src.database import get_db, engine, async_session_factory

# Import services
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
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

# Import GHL API routers
from src.api.ghl_locations import router as ghl_locations_router
from src.api.ghl_oauth import router as ghl_oauth_router
from src.api.ghl_messages import router as ghl_messages_router
from src.api.ghl_webhooks import router as ghl_webhooks_router
from src.api.ghl_users import router as ghl_users_router
from src.api import analytics
from src.api import campaign_management

setup_logging()

from src.limiter import limiter  # noqa: E402 — must be after setup_logging()

# Initialize Campaign Scheduler (before lifespan to ensure it's available)
scheduler = CampaignScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    if DEBUG:
        logger.warning(
            "DEBUG mode is enabled — SQL queries will be logged. "
            "Disable DEBUG in production."
        )
    await scheduler.start()
    logger.info("Application started with Campaign Scheduler")

    # GHL-10: ensure cleanup job is registered (replace_existing=True is idempotent)
    scheduler.scheduler.add_job(
        _cleanup_old_webhooks,
        trigger=IntervalTrigger(days=1),
        id="cleanup_old_webhooks",
        replace_existing=True,
    )
    logger.info("Registered webhook cleanup job (runs every 24h)")

    yield
    scheduler.shutdown()
    # Close persistent HTTP clients
    from src.services.ghl_conversations_service import GHLConversationsService
    from src.services.ghl_contacts_service import GHLContactsService
    from src.services.ghl_oauth_service import GHLOAuthService
    from src.services.ghl_users_service import GHLUsersService
    await GHLConversationsService.close_client()
    await GHLContactsService.close_client()
    await GHLOAuthService.close_client()
    await GHLUsersService.close_client()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="WhatsApp Campaign Management API",
    description="API with GoHighLevel integration for WhatsApp messaging",
    version="0.2.0",
    lifespan=lifespan
)

logger = logging.getLogger(__name__)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global fallback: log internally, return safe 500 to client."""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


async def _cleanup_old_webhooks():
    """Delete processed_webhooks older than 30 days (GHL-10)."""
    async with async_session_factory() as db_session:
        try:
            result = await db_session.execute(
                text("DELETE FROM processed_webhooks WHERE processed_at < now() - interval '30 days'")
            )
            await db_session.commit()
            logger.info(f"Cleaned up {result.rowcount} old processed webhooks")
        except Exception as e:
            logger.error(f"Webhook cleanup job failed: {e}", exc_info=True)
            await db_session.rollback()


# GHL-10: pre-register cleanup job so it is visible to get_jobs() before lifespan runs
scheduler.scheduler.add_job(
    _cleanup_old_webhooks,
    trigger=IntervalTrigger(days=1),
    id="cleanup_old_webhooks",
    replace_existing=True,
)

metrics_enabled = ENABLE_METRICS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Cache-Bypass"],
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
    # Validate or generate X-Request-ID
    client_request_id = request.headers.get("X-Request-ID")
    if client_request_id:
        try:
            uuid.UUID(client_request_id)
            request_id = client_request_id
        except ValueError:
            request_id = str(uuid.uuid4())
    else:
        request_id = str(uuid.uuid4())

    request_token = request_id_ctx_var.set(request_id)
    path_token = request_path_ctx_var.set(request.url.path)
    method_token = http_method_ctx_var.set(request.method)

    start_time = time.perf_counter()
    response: Response

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        api_request_errors.labels(method=request.method, path=request.url.path, status="500").inc()
        logger.exception("Unhandled exception during request")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={"X-Request-ID": request_id},
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
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint with database connectivity verification
    Returns 200 OK if healthy, 503 if database is unreachable
    """
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
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

    import src.config as _config
    return {
        "status": "healthy",
        "database": db_status,
        "ghl_enabled": _config.GHL_ENABLED,
        "service": "wpp-disp-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if metrics_enabled:

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        """Expose Prometheus metrics for scraping. Protected by METRICS_TOKEN in production."""
        from src.config import METRICS_TOKEN, DEBUG as _DEBUG
        if not _DEBUG and METRICS_TOKEN:
            auth_header = request.headers.get("Authorization", "")
            expected = f"Bearer {METRICS_TOKEN}"
            if not hmac.compare_digest(auth_header, expected):
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from src.metrics import update_pool_metrics
        update_pool_metrics(engine)
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ===== DASHBOARD API (NOW USES REAL DATA FROM ANALYTICS ROUTER) =====
# The dashboard endpoint is now handled by src/api/analytics.py
# It uses the analytics_service to provide real-time metrics from the database


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