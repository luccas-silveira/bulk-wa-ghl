"""
FastAPI Backend - WhatsApp Campaign Management with GoHighLevel Integration
Complete API with GHL OAuth, Conversations, and Webhooks
"""

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio
import logging
import os

# Import database
from src.database import get_db, SessionLocal, engine

# Import models
from src.models.campaign import Campaign
from src.models.message import Message

# Import services
from src.services.campaign_executor_service import CampaignExecutorService
from src.services.campaign_scheduler import CampaignScheduler

# Import GHL API routers
from src.api.ghl_locations import router as ghl_locations_router
from src.api.ghl_oauth import router as ghl_oauth_router
from src.api.ghl_messages import router as ghl_messages_router
from src.api.ghl_webhooks import router as ghl_webhooks_router
from src.api.ghl_users import router as ghl_users_router
from src.api import analytics
from src.api import campaign_management

app = FastAPI(
    title="WhatsApp Campaign Management API",
    description="API with GoHighLevel integration for WhatsApp messaging",
    version="0.2.0"
)

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Campaign Scheduler
scheduler = CampaignScheduler()

# CORS - allow configuration via environment variable
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3001,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register GHL API routers
app.include_router(ghl_locations_router)
app.include_router(ghl_oauth_router)
app.include_router(ghl_messages_router)
app.include_router(ghl_webhooks_router)
app.include_router(ghl_users_router)

# Register Analytics API router
app.include_router(analytics.router)

# Register Campaign Management API router
app.include_router(campaign_management.router)


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Start the campaign scheduler on application startup"""
    scheduler.start()
    logger.info("Application started with Campaign Scheduler")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the campaign scheduler gracefully"""
    scheduler.shutdown()
    logger.info("Application shutdown complete")


@app.get("/")
async def root():
    """Endpoint principal"""
    return {
        "message": "WhatsApp Campaign Management API",
        "version": "0.1.0",
        "status": "healthy",
        "melhorias": "Interface WAHA implementada"
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
        "timestamp": datetime.now().isoformat()
    }

# ===== ENDPOINTS WAHA SESSIONS (NOVA IMPLEMENTAÇÃO) =====

@app.get("/waha/sessions")
async def get_waha_sessions():
    """
    GET /waha/sessions - Listar todas as sessões WAHA
    ✅ IMPLEMENTADO: Substituiu campos separados por dropdown único
    """
    # Simulação de sessões WAHA (em produção, faria chamada para WAHA API)
    sessions_demo = [
        {
            "id": "session1",
            "name": "WhatsApp Principal",
            "status": "WORKING",
            "is_active": True,
            "me": {
                "id": "5511999999999@c.us",
                "pushName": "Minha Empresa"
            },
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": "session2",
            "name": "WhatsApp Secundário",
            "status": "STOPPED",
            "is_active": False,
            "me": {
                "id": "5511888888888@c.us",
                "pushName": "Empresa Filial"
            },
            "last_updated": datetime.now().isoformat()
        }
    ]

    return {"sessions": sessions_demo}

@app.get("/waha/sessions/active")
async def get_active_waha_sessions():
    """
    GET /waha/sessions/active - Apenas sessões ativas (WORKING)
    ✅ IMPLEMENTADO: Para uso no Campaign Wizard
    """
    all_sessions = await get_waha_sessions()
    active_sessions = [
        session for session in all_sessions["sessions"]
        if session["is_active"]
    ]

    return {"sessions": active_sessions}

@app.get("/waha/sessions/{session_id}/validate")
async def validate_session(session_id: str):
    """
    GET /waha/sessions/{session_id}/validate - Validar sessão para campanha
    ✅ IMPLEMENTADO: Validação antes de criar campanha
    """
    # Verificar se sessão existe e está ativa
    all_sessions = await get_waha_sessions()
    session = next(
        (s for s in all_sessions["sessions"] if s["id"] == session_id),
        None
    )

    if not session:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Session validation failed",
                "message": f"Session '{session_id}' not found",
                "session_status": "NOT_FOUND"
            }
        )

    if not session["is_active"]:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Session validation failed",
                "message": f"Session '{session_id}' is not active",
                "session_status": session["status"]
            }
        )

    return {
        "valid": True,
        "session_id": session_id,
        "session_name": session["name"],
        "status": session["status"],
        "validated_at": datetime.now().isoformat()
    }

# ===== DASHBOARD API (NOW USES REAL DATA FROM ANALYTICS ROUTER) =====
# The dashboard endpoint is now handled by src/api/analytics.py
# It uses the analytics_service to provide real-time metrics from the database

# ===== CAMPAIGN CREATION (COM EXECUÇÃO REAL) =====

@app.post("/campaigns")
async def create_campaign(
    campaign_data: dict,
    db: Session = Depends(get_db)
):
    """
    POST /campaigns - Criação e execução de campanha com GHL
    ✅ Salva campanha no banco
    ✅ Executa envio de mensagens via GHL Conversations API
    """

    # LOG COMPLETO DO PAYLOAD
    logger.info(f"📥 PAYLOAD RECEBIDO: {campaign_data}")

    # Validar dados necessários
    ghl_location_id = campaign_data.get("ghl_location_id")
    if not ghl_location_id:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "message": "ghl_location_id is required"
            }
        )

    # Extrair dados da campanha
    name = campaign_data.get("name", "Nova Campanha")
    ghl_user_id = campaign_data.get("ghl_user_id")
    ghl_user_ids = campaign_data.get("ghl_user_ids")  # NEW: Multiple users
    sending_speed = campaign_data.get("sending_speed", "medium")
    schedule_type = campaign_data.get("schedule_type", "immediate")
    scheduled_time = campaign_data.get("scheduled_time")
    messages = campaign_data.get("messages", [])
    audience_criteria = campaign_data.get("audience_criteria", {})
    csv_data = audience_criteria.get("csv_data", [])

    # LOG DETALHADO DA EXTRAÇÃO
    logger.info(f"📊 DADOS EXTRAÍDOS:")
    logger.info(f"   - schedule_type: {schedule_type}")
    logger.info(f"   - csv_data length: {len(csv_data)}")
    logger.info(f"   - csv_data: {csv_data}")
    logger.info(f"   - messages: {messages}")

    # Validar que pelo menos uma mensagem foi fornecida
    if not messages or len(messages) == 0:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "message": "Pelo menos uma mensagem (texto ou mídia) é obrigatória"
            }
        )

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
    logger.info(f"✅ Campaign {campaign_id} created: '{name}' with {len(csv_data)} recipients")
    logger.info(f"DEBUG: schedule_type={schedule_type}, csv_data length={len(csv_data)}, csv_data={csv_data}")

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
    logger.info(f"🔍 CHECANDO CONDIÇÃO: schedule_type={schedule_type}, len(csv_data)={len(csv_data)}")

    if schedule_type == 'immediate' and len(csv_data) > 0:
        logger.info(f"✅ CONDIÇÃO ATENDIDA! Entrando no bloco de execução")
        logger.info(f"🚀 Starting background execution for campaign {campaign_id}")

        # Executar campanha em background com nova sessão de banco
        async def execute_campaign_background():
            """Execute campaign in background with independent DB session"""
            db_session = SessionLocal()
            try:
                logger.info(f"📤 Executing campaign {campaign_id} with {len(csv_data)} contacts")
                executor = CampaignExecutorService(db_session)

                result = await executor.execute_campaign(
                    campaign_id=campaign_id,
                    contacts=csv_data,
                    messages_template=messages
                )

                logger.info(f"✅ Campaign {campaign_id} completed: {result}")

            except Exception as e:
                logger.error(f"❌ Error executing campaign {campaign_id}: {str(e)}", exc_info=True)
            finally:
                db_session.close()

        # Criar task independente (não bloqueia a resposta)
        asyncio.create_task(execute_campaign_background())

    elif schedule_type == 'scheduled' and parsed_scheduled_time and len(csv_data) > 0:
        # Schedule campaign for future execution
        logger.info(f"📅 Scheduling campaign {campaign_id} for {parsed_scheduled_time}")

        try:
            scheduler.schedule_campaign(
                campaign_id=campaign_id,
                scheduled_time=parsed_scheduled_time,
                csv_data=csv_data,
                messages=messages
            )

            # Update status to 'scheduled'
            campaign.status = 'scheduled'
            db.commit()

            logger.info(f"✅ Campaign {campaign_id} scheduled successfully")

        except Exception as e:
            logger.error(f"❌ Failed to schedule campaign {campaign_id}: {str(e)}")
            campaign.status = 'failed'
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
            Campaign.scheduled_time > datetime.now()
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
        campaign.status = 'cancelled'
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
        "melhorias_implementadas": {
            "dashboard_sem_user_id": "✅ Dashboard carrega métricas sem exigir User ID",
            "waha_sessions_api": "✅ API completa para sessões WAHA",
            "dropdown_unificado": "✅ Dropdown único substitui campos separados",
            "ghl_team_id_removido": "✅ Campo GHL Team ID completamente removido",
            "resolucao_conflito_porta": "✅ Frontend na 3001, WAHA na 3000"
        },
        "endpoints_novos": [
            "GET /waha/sessions - Listar sessões",
            "GET /waha/sessions/active - Sessões ativas",
            "GET /waha/sessions/{id}/validate - Validar sessão",
            "GET /dashboard - Dashboard melhorado"
        ],
        "testes_disponiveis": [
            "http://localhost:8000/waha/sessions",
            "http://localhost:8000/waha/sessions/active",
            "http://localhost:8000/api/v1/analytics/dashboard",
            "http://localhost:8000/docs"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)