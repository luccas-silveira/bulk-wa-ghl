# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is this project?

Bulk WhatsApp messaging platform integrated with GoHighLevel (GHL). Manages campaigns that distribute messages across multiple GHL users (round-robin), supports immediate and scheduled sends, pause/resume, and real-time analytics.

## Architecture

**Backend** (Python 3.12 / FastAPI 0.104) — `backend/src/`
- Entry point: `main.py` (uvicorn, port 8000)
- Routers: `api/` — campaign, GHL, analytics endpoints
- Services: `services/` — business logic (CampaignExecutor, CampaignScheduler, CampaignManagement, GHLConversations, GHLOAuth, TokenEncryption, Analytics, GHLContacts, GHLUsers, GHLWebhookHandler)
- Models: `models/` — SQLAlchemy 2.0 models (Campaign, Message, GHLLocation, GHLOAuthToken, GHLConversation, GHLUser, ProcessedWebhook)
- Database: PostgreSQL 16 (Alembic configured in `backend/alembic/`; initial revision `eb03c3cc8781_initial_schema` committed — see "Database migrations" below)
- **Note:** The DB layer currently uses synchronous SQLAlchemy sessions. A planned migration to full `AsyncSession` + `asyncpg` (PERS-25) is tracked in the roadmap but not yet implemented — do not assume async session support exists.

**Messaging provider:** GoHighLevel (GHL) only. WAHA (WhatsApp HTTP API) is not supported — endpoints, types, and references have been removed. If WAHA support is ever needed again, it will require introducing a provider abstraction layer (`MessageProvider` interface) and refactoring `CampaignExecutorService` to consume it.

**Frontend** (React 18.2 / TypeScript 5.2 / Vite 5.0) — `frontend/src/`
- Routing: `react-router-dom v6` — `BrowserRouter + Routes + Route` in `main.tsx`; all navigation via `useNavigate()`
- State: TanStack Query 5.90 for server state
- Styling: Tailwind CSS 3.4
- Charts: Chart.js 4.5 + react-chartjs-2
- Animations: framer-motion
- CSV parsing: papaparse (contact list upload in campaign wizard)
- Phone validation: libphonenumber-js (mirrors backend `phonenumbers` lib; used in campaign wizard)
- Key areas: `components/dashboard/`, `components/campaign/`, `components/ui/`, `pages/`, `hooks/`, `services/`
- API client: `services/api-client.ts` uses `VITE_API_URL` env var; `vite.config.ts` proxies `/api → localhost:8000` in dev

**Infrastructure**: Docker Compose (dev + prod), Nginx reverse proxy (prod), deployment via `deploy.sh`

## Commands

### Frontend (run from `frontend/`)
```bash
npm run dev              # Vite dev server (port 3001)
npm run build            # Production build
npx tsc --noEmit         # TypeScript check without build
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

Alembic is configured in `backend/alembic/` with autogenerate wired to `src.database.Base` (see `backend/alembic/env.py`). Two revisions are committed in `versions/`: `eb03c3cc8781_initial_schema` (baseline) and `a8f3c2e7d1b9` (timezone fixes). To apply or generate new revisions:

```bash
alembic upgrade head                              # Apply all pending migrations
alembic revision --autogenerate -m "description" # Generate new revision after model changes
```

**Safety for already-populated databases (staging/prod):** run `alembic stamp eb03c3cc8781` before `alembic upgrade head` to mark the baseline revision as applied without re-executing it. On a fresh empty database, run `alembic upgrade head` directly — it applies both revisions in sequence.

Note: `backend/run_migration.py` is a legacy raw-SQL runner that targeted the now-deleted `backend/migrations/` directory. It is dead code — ignore it.

### Docker
```bash
docker-compose up -d            # Start dev stack (postgres + backend + frontend)
docker-compose logs -f backend  # Follow backend logs
./deploy.sh production          # Production deployment
```

## Key patterns

### Campaign state machine

**Never assign `campaign.status` directly.** Use `campaign.transition_to(new_status)` — it enforces the state machine and raises `InvalidTransitionError` (defined in `backend/src/exceptions.py`) for illegal transitions.

Valid values: `draft`, `scheduled`, `executing`, `paused`, `completed`, `failed`, `cancelled`.  
Valid transitions: `draft → scheduled|executing|failed`; `executing → paused|completed|failed`; `paused → executing`; `scheduled → cancelled|failed|executing`. Terminal states (`completed`, `failed`, `cancelled`) have no outgoing transitions.

A SQLAlchemy `@validates('status')` guard in the model also rejects unknown values before they reach the DB.

### Campaign execution

Background tasks via `asyncio.create_task()`. Campaigns can be immediate or scheduled (APScheduler). Multi-user campaigns distribute contacts round-robin. `CampaignExecutorService.SPEED_DELAYS` uses `slow=420s`, `medium=240s`, `fast=60s` between contacts — when testing real execution, use a small contact list or the run will take hours.

### Campaign endpoints

All campaign operations live under `/api/v1/campaigns` in `backend/src/api/campaign_management.py`: `POST` (create), list, details, logs, stats, pause/resume, and delete. `main.py` contains no inline campaign handlers.

### Rate limiting

`backend/src/limiter.py` holds the `slowapi.Limiter` singleton (imported as `from src.limiter import limiter`). Decorate new endpoints with `@limiter.limit("60/minute")` and add `request: Request` as the first parameter. The singleton lives in its own module to avoid circular imports with `main.py`.

### Phone normalization (E.164)

`normalize_phone()` in `backend/src/schemas/campaign.py` normalizes phone numbers to E.164 format using the `phonenumbers` library. It normalizes (does not reject) unparseable numbers — the raw value is returned unchanged if parsing fails. Applied automatically via `@field_validator` on `ContactData.phone_number` and in `ghl_contacts_service.py` before GHL lookups.

### PII masking in logs

`ContextFilter` in `backend/src/logging_config.py` masks E.164 phone numbers (`+\d{7,15}` → `+***`) before log records are emitted. Do not log raw phone numbers anywhere — the filter is a second line of defense, not an invitation.

### X-Request-ID and middleware

`main.py` auto-generates a UUID `X-Request-ID` if the client does not send one, and validates UUID format if it does. The ID is propagated via `contextvars` so it appears in structured JSON logs. A global `@app.exception_handler(Exception)` returns `{"detail": "Internal server error"}` with status 500 for unhandled exceptions — internal details are only in logs.

### Frontend routing

`main.tsx` uses `BrowserRouter + Routes + Route`. All navigation is via `useNavigate()` — no `window.dispatchEvent` / custom events. Routes: `/` (Dashboard), `/campaigns` (list), `/campaigns/new` (Wizard), `/analytics`, `/settings`, `*` (NotFound). Each route wraps its element in `<ProtectedRoute>` (transparent stub, ready for future auth). `CampaignsPage` reads `?status=` via `useSearchParams` to pre-filter the campaign list.

### GHL OAuth

Tokens encrypted with Fernet (`GHL_TOKEN_ENCRYPTION_KEY`) and stored in `ghl_oauth_tokens` table. `GHL_WEBHOOK_SECRET` is validated at startup (not on-demand) — `ghl_webhook_handler.py` reads it from `src.config`, not from `os.getenv`.

### Observability

Structured JSON logging with `X-Request-ID` propagation. Prometheus metrics at `/metrics` (toggle `ENABLE_METRICS`, protected by `METRICS_TOKEN` when `DEBUG=False`). APScheduler job `_cleanup_old_webhooks` runs daily to purge `processed_webhooks` older than 30 days (registered in the `lifespan` in `main.py`). API docs at `http://localhost:8000/docs`.

## Supporting docs

The `docs/` folder contains domain context and historical decisions: `plano-implementacao-mestre.md` (master implementation plan), `roadmap-execucao.md` (live execution tracker with per-item status for all 18 EPICs — consult this first to see what's next and what's already done), `code-review-campaign-module.md`, and audit documents per subsystem (`auditoria-integracao-ghl.md`, `auditoria-persistencia-dados.md`, `auditoria-analytics-metricas.md`, `auditoria-frontend-ui.md`, `auditoria-infraestrutura-deploy.md`, and `auditoria-integracao-waha.md` — the last one is historical; WAHA is no longer supported). Read these for background on *why* something was built a certain way.

## Environment variables

- **Required at boot** (startup fails without it): `DATABASE_URL`
- **GHL integration** — controlled by `GHL_ENABLED = bool(GHL_CLIENT_ID)` (computed in `config.py`). Set `GHL_CLIENT_ID` to enable GHL; when set, these also become required at startup (via `_require_env()`): `GHL_CLIENT_SECRET`, `GHL_REDIRECT_URI`, `GHL_TOKEN_ENCRYPTION_KEY`, `GHL_WEBHOOK_SECRET`. When `GHL_ENABLED=False`, all GHL API routers are not registered (`main.py`).
- **Required in production** (`DEBUG=False`): `CORS_ORIGINS` — startup raises `RuntimeError` if not set. Defaults to `http://localhost:3001,http://localhost:3000` only when `DEBUG=True`.
- **Optional**: `GHL_PRIVATE_TOKEN`, `GHL_API_VERSION` (defaults to `2021-07-28`), `ENABLE_METRICS`, `METRICS_TOKEN`, `DB_POOL_SIZE` (default 20), `DB_MAX_OVERFLOW` (default 40), `LOG_LEVEL`, `DEBUG`
- **Frontend**: `VITE_API_URL` (defaults to `http://localhost:8000`)
