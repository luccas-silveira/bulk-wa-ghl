# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is this project?

Bulk WhatsApp messaging platform integrated with GoHighLevel (GHL). Manages campaigns that distribute messages across multiple GHL users (round-robin), supports immediate and scheduled sends, pause/resume, and real-time analytics.

## Architecture

**Backend** (Python 3.12 / FastAPI 0.104) — `backend/src/`
- Entry point: `main.py` (uvicorn, port 8000)
- Routers: `api/` — campaign, GHL, analytics endpoints
- Services: `services/` — business logic (CampaignExecutor, CampaignScheduler, CampaignManagement, GHLConversations, GHLOAuth, TokenEncryption, Analytics)
- Models: `models/` — SQLAlchemy 2.0 models (Campaign, Message, GHLLocation, GHLOAuthToken, GHLConversation, GHLUser, ProcessedWebhook)
- Database: PostgreSQL 16 (Alembic configured in `backend/alembic/`, but no revisions committed yet — see "Database migrations" below)

**Messaging provider:** GoHighLevel (GHL) only. WAHA (WhatsApp HTTP API) is not supported — endpoints, types, and references have been removed. If WAHA support is ever needed again, it will require introducing a provider abstraction layer (`MessageProvider` interface) and refactoring `CampaignExecutorService` to consume it.

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
pytest                                        # All tests
pytest tests/unit                             # Unit tests only (pure logic, no I/O)
pytest tests/integration                      # Integration tests (services + real DB)
pytest tests/contract                         # FastAPI route contract tests
pytest tests/unit/test_file.py::test_name     # Single test
```

### Database migrations (from `backend/`)

Alembic is configured in `backend/alembic/` with autogenerate wired to `src.database.Base` (see `backend/alembic/env.py`), but `versions/` is empty — no revisions have been committed. The current schema was created manually and there is no versioned migration yet. To introduce versioned migrations, generate the first revision:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Note: `backend/run_migration.py` is a legacy raw-SQL runner that targeted the now-deleted `backend/migrations/` directory. It is dead code — ignore it.

### Docker
```bash
docker-compose up -d            # Start dev stack (postgres + backend + frontend)
docker-compose logs -f backend  # Follow backend logs
./deploy.sh production          # Production deployment
```

## Key patterns

- **Campaign execution**: Background tasks via `asyncio.create_task()`. Campaigns can be immediate or scheduled (APScheduler). Multi-user campaigns distribute contacts round-robin. `CampaignExecutorService.SPEED_DELAYS` uses `slow=420s`, `medium=240s`, `fast=60s` between contacts — when testing real execution, use a small contact list or the run will take hours.
- **Campaign status lifecycle**: `Campaign.status` is a plain `String(50)` (declared in `backend/src/models/campaign.py:37`, not an enum), default `draft`. Valid values: `draft`, `scheduled`, `executing`, `paused`, `completed`, `failed`, `cancelled`. Transitions observed in code: `draft → scheduled|executing|failed`; `executing → paused|completed|failed`; `paused → executing`; `scheduled → cancelled|failed`. Terminal states: `completed`, `failed`, `cancelled`.
- **Campaign endpoints split across two routers**: the modern router `/api/v1/campaigns` in `backend/src/api/campaign_management.py` handles list, details, logs, stats, pause/resume, and delete — this is what the frontend uses for read/management. **Creation still goes through the legacy inline `POST /campaigns` in `backend/src/main.py:200`** (consumed by `frontend/src/main.tsx:52`). Other inline endpoints in `main.py` (`GET /campaigns/{id}`, `GET /campaigns/scheduled`, `DELETE /campaigns/{id}/schedule`) are superseded by the router and not consumed by the frontend. `POST /campaigns/{id}/execute` in `main.py:465` is a 400 stub — do not use.
- **GHL OAuth**: Tokens encrypted with Fernet (`GHL_TOKEN_ENCRYPTION_KEY`) and stored in `ghl_oauth_tokens` table.
- **Observability**: Structured JSON logging with `X-Request-ID` propagation. Prometheus metrics at `/metrics` (toggle `ENABLE_METRICS`).
- **API docs**: FastAPI auto-generates Swagger at `http://localhost:8000/docs`.

## Supporting docs

The `docs/` folder contains domain context and historical decisions: `plano-implementacao-mestre.md` (master implementation plan), `roadmap-execucao.md` (live execution tracker with per-item status for all 18 EPICs — consult this first to see what's next and what's already done), `code-review-campaign-module.md`, and audit documents per subsystem (`auditoria-integracao-ghl.md`, `auditoria-persistencia-dados.md`, `auditoria-analytics-metricas.md`, `auditoria-frontend-ui.md`, `auditoria-infraestrutura-deploy.md`, and `auditoria-integracao-waha.md` — the last one is historical; WAHA is no longer supported). Read these for background on *why* something was built a certain way.

## Environment variables

- **Required at boot** (startup fails without it): `DATABASE_URL`
- **Required for any GHL functionality**: `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, `GHL_REDIRECT_URI`, `GHL_TOKEN_ENCRYPTION_KEY`
- **Optional**: `GHL_WEBHOOK_SECRET`, `GHL_PRIVATE_TOKEN`, `CORS_ORIGINS`, `ENABLE_METRICS`, `METRICS_TOKEN`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `LOG_LEVEL`, `DEBUG`
- **Frontend**: `VITE_API_URL` (defaults to `http://localhost:8000`)
