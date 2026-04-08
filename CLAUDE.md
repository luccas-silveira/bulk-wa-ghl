# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is this project?

**wpp_disp** is a bulk WhatsApp messaging platform integrated with GoHighLevel (GHL). It allows creating and managing campaigns that send messages to contact lists via GHL's WhatsApp API, with multi-user round-robin distribution, scheduling, pause/resume, and real-time analytics.

## Architecture

**Backend** (Python 3.12 / FastAPI 0.104) — `backend/src/`
- Entry point: `main.py` (uvicorn, port 8000)
- Routers: `routers/` — campaign, GHL, analytics, WAHA endpoints
- Services: `services/` — business logic (CampaignExecutor, CampaignScheduler, CampaignManagement, GHLConversations, GHLOAuth, TokenEncryption, Analytics)
- Models: `models/` — SQLAlchemy 2.0 models (Campaign, Message, GHLLocation, GHLOAuthToken, GHLConversation, GHLUser, ProcessedWebhook)
- Database: PostgreSQL 16, migrations via Alembic (`backend/alembic/`)

**Frontend** (React 18.2 / TypeScript 5.2 / Vite 5.0) — `frontend/src/`
- State: TanStack Query 5.90 for server state
- Styling: Tailwind CSS 3.4
- Charts: Chart.js 4.5 + react-chartjs-2
- Key areas: `components/dashboard/`, `components/campaign/`, `components/ui/`, `pages/`, `hooks/`, `services/`
- API client: `services/api-client.ts` uses `VITE_API_URL` env var

**Infrastructure**: Docker Compose (dev + prod), Nginx reverse proxy (prod), deployment via `deploy.sh`

## Commands

### Frontend (run from `frontend/`)
```bash
npm run dev              # Vite dev server (port 3001)
npm run build            # Production build
npm test                 # Jest tests
npm test -- --testPathPattern=<pattern>  # Single test file
npm run test:coverage    # Coverage report
```

### Backend (run from `backend/`)
```bash
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
pytest                                    # All tests
pytest tests/test_file.py::test_name      # Single test
```

### Database migrations (from `backend/`)
```bash
alembic revision --autogenerate -m "description"   # Create migration
alembic upgrade head                                # Apply migrations
```

### Docker
```bash
docker-compose up -d            # Start dev stack (postgres + backend + frontend)
docker-compose logs -f backend  # Follow backend logs
./deploy.sh production          # Production deployment
```

## Key patterns

- **Campaign execution**: Background tasks via `asyncio.create_task()`. Campaigns can be immediate or scheduled (APScheduler). Multi-user campaigns distribute contacts round-robin.
- **GHL OAuth**: Tokens encrypted with Fernet (`GHL_TOKEN_ENCRYPTION_KEY`) and stored in `ghl_oauth_tokens` table.
- **Observability**: Structured JSON logging with `X-Request-ID` propagation. Prometheus metrics at `/metrics` (toggle `ENABLE_METRICS`).
- **API docs**: FastAPI auto-generates Swagger at `http://localhost:8000/docs`.

## Environment variables

Required: `DATABASE_URL`, `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, `GHL_REDIRECT_URI`, `GHL_TOKEN_ENCRYPTION_KEY`
Frontend: `VITE_API_URL` (defaults to `http://localhost:8000`)
