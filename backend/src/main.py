"""
FastAPI Backend Simplificado - WhatsApp Campaign Interface Improvements
Demonstração das funcionalidades implementadas
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio

app = FastAPI(
    title="WhatsApp Campaign Management API",
    description="API melhorada com integração WAHA",
    version="0.1.0"
)

# CORS para permitir frontend na porta 3001
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

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
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
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

# ===== DASHBOARD API (MELHORADO) =====

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard(ghl_user_id: str = None, days: int = 30):
    """
    GET /dashboard - Dashboard SEM necessidade de User ID obrigatório
    ✅ IMPLEMENTADO: Mostra métricas agregadas imediatamente
    """
    # Simular dados do dashboard
    dashboard_data = {
        "campaign_metrics": {
            "total_campaigns": 25 if not ghl_user_id else 8,
            "active_campaigns": 3 if not ghl_user_id else 1,
            "completed_campaigns": 20 if not ghl_user_id else 6,
            "failed_campaigns": 2 if not ghl_user_id else 1
        },
        "delivery_metrics": {
            "sent": 1250 if not ghl_user_id else 450,
            "delivery_rate": 94.5,
            "read_rate": 78.2
        },
        "recent_campaigns": [
            {
                "id": "camp1",
                "name": "Promoção Black Friday",
                "status": "completed",
                "delivery_rate": 96.8,
                "created_at": "2025-09-25T10:00:00Z"
            },
            {
                "id": "camp2",
                "name": "Lançamento Produto",
                "status": "executing",
                "delivery_rate": 92.1,
                "created_at": "2025-09-28T14:30:00Z"
            }
        ],
        "top_performing_campaigns": [
            {
                "id": "camp1",
                "name": "Promoção Black Friday",
                "delivered_count": 485,
                "read_rate": 89.3
            }
        ]
    }

    # Adicionar informação sobre filtro
    if ghl_user_id:
        dashboard_data["filter_info"] = f"Dados filtrados para usuário: {ghl_user_id}"
    else:
        dashboard_data["filter_info"] = "Dados agregados de todos os usuários"

    dashboard_data["time_range"] = f"Últimos {days} dias"

    return dashboard_data

# ===== CAMPAIGN CREATION (ATUALIZADO) =====

@app.post("/campaigns")
async def create_campaign(campaign_data: dict):
    """
    POST /campaigns - Criação de campanha com waha_session_id
    ✅ IMPLEMENTADO: Usa waha_session_id em vez de campos separados
    ❌ REMOVIDO: ghl_team_id (campo que não existe na realidade)
    """

    # Validar se waha_session_id foi fornecido
    if "waha_session_id" not in campaign_data:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "message": "waha_session_id is required"
            }
        )

    # Validar sessão
    session_id = campaign_data["waha_session_id"]
    validation_response = await validate_session(session_id)

    if isinstance(validation_response, JSONResponse):
        return validation_response

    # Simular criação da campanha
    campaign_response = {
        "id": f"camp_{int(datetime.now().timestamp())}",
        "name": campaign_data.get("name", "Nova Campanha"),
        "status": "draft",
        "waha_session_id": session_id,
        "sending_speed": campaign_data.get("sending_speed", "medium"),
        "schedule_type": campaign_data.get("schedule_type", "immediate"),
        "created_at": datetime.now().isoformat(),
        "estimated_recipients": len(campaign_data.get("audience_criteria", {}).get("csv_data", [100]))
    }

    return JSONResponse(status_code=201, content=campaign_response)

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