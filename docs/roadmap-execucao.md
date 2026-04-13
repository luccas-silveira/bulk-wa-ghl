# Roadmap de Execução — wpp-disp

**Propósito:** rastreamento operacional do [plano mestre](plano-implementacao-mestre.md).
**Fonte da verdade descritiva:** `plano-implementacao-mestre.md` contém descrição detalhada de cada item (arquivo, linha, ação específica, critérios de conclusão). Este documento só rastreia status e serve como painel executável.
**Última atualização:** 2026-04-12 (Runbook criado — 168/172 itens; **Fase 2: 52/52 COMPLETA** ✅; Fase 3: 6/7 itens concluídos)
**Branch ativa:** `004-campaign-management`

---

## Convenção de status

- `[ ]` Não iniciado
- `[~]` Em andamento ou parcial (com nota explicando o que falta)
- `[!]` Bloqueado (com nota explicando o bloqueio)
- `[x]` Concluído e verificado

## Visão geral

| Fase | Objetivo | EPICs incluídos | Itens | Concluídos |
|------|----------|-----------------|------:|-----------:|
| **0** — Bloqueadores de produção | Sistema deployável, seguro, timezone correto, secrets validados, pool controlado, dashboard sem dados fake | EPIC-01, 02, 03, 04, 05 (críticos/altos), 06 (validadores), 11 (ANA-01/02/03) | 41 | 41 |
| **1** — Estabilidade e segurança | State machine, webhooks idempotentes, telefone E.164, router frontend, UI crítica, infra de deploy, observabilidade | EPIC-05 (resto), 06 (resto), 07, 08, 09, 12, 13 (críticos), 14 (críticos/altos), 15, 17 | 73 | 66 |
| **2** — Qualidade e performance | N+1 eliminados, analytics real com timeline, UI completa, SSL endurecido | EPIC-10, 11 (resto), 13 (resto), 14 (resto), 16 | 52 | 52 |
| **Fora de fase** | EPIC-18 Opção B (remoção WAHA) + RAIZ-09 (endpoint createCampaign) | EPIC-18, RAIZ-09 | 6 | 6 |
| **Total** | | | **172** | **168** |

**Notas sobre contagem:**
- **Fase 3 (Polish e Backlog)** não aparece como linha separada: os itens de severidade Baixa que o plano mestre consolida em Fase 3 aqui ficam dentro de seus EPICs originais nas Fases 1 e 2, para evitar duplicação.
- **WAHA-04** aparece em duas linhas (EPIC-01 e EPIC-18) porque o plano mestre original também lista o item em ambos os EPICs. É o mesmo item físico (deletar o arquivo SQL), já concluído, por isso os dois checkboxes estão marcados.
- **GHL-26** aparece em duas linhas (EPIC-08 e EPIC-17) pela mesma razão — é uma referência cruzada intencional do plano mestre.
- Contagem de itens **únicos**: 170. Contagem de checkboxes no arquivo: 172 (170 + 2 duplicações intencionais).

## Próximo passo recomendado

**Fase 0 concluída (41/41). Fase 1 concluída (66/66). Fase 2 concluída (52/52).** Todos os EPICs concluídos. **Fase 3 em andamento: 6/7 itens concluídos.** Runbook de operações criado em `docs/runbook.md` (deploy, rollback, backup/restore, migrations, resposta a incidentes). Resta apenas **Lighthouse > 90** (auditoria — requer app em execução).

**Atenção ao risco R01** (plano mestre, linha 866): ao rodar `alembic upgrade head` em banco já populado (staging/produção), usar `alembic stamp eb03c3cc8781` antes de `alembic upgrade head` para não re-executar o schema inicial. Em banco vazio, rodar `alembic upgrade head` diretamente (aplica os dois revisions em sequência).

## Decisões estratégicas

| # | Decisão | Status | Bloqueia |
|---|---------|--------|----------|
| DECISAO-01 | Futuro WAHA | ✅ Resolvida 2026-04-10 (Opção B — remover) | — |
| DECISAO-02 | Sidebar no Layout (integrar ou deletar) | ✅ Resolvida 2026-04-10 (Opção B — deletar Sidebar.tsx e useNavigation) | FRONT-03 (EPIC-12) |
| DECISAO-03 | Soft delete vs cascade | ✅ Resolvida 2026-04-10 (Opção A — soft delete com `deleted_at` + RESTRICT) | PERS-15, PERS-16 (EPIC-06) |
| DECISAO-04 | Mensagens standalone (feature real ou lixo) | ✅ Resolvida 2026-04-10 (Opção B — `campaign_id` NOT NULL, feature removida) | PERS-09 (EPIC-06) |
| DECISAO-05 | AsyncSession completo vs mitigação por batch | ✅ Resolvida 2026-04-10 (Opção A — migração completa AsyncSession + asyncpg) | PERS-25 (EPIC-05) |
| DECISAO-06 | Política de retenção de backups | ✅ Resolvida 2026-04-10 (Opção B — manter últimos 10 backups por quantidade) | INFRA-14 (EPIC-15) |
| DECISAO-07 | Rate limiting agora ou diferir | ✅ Resolvida 2026-04-10 (Opção A — implementar agora, GHL + API FastAPI) | CAMP-19 (EPIC-17) |
| DECISAO-08 | Error reporting externo (Sentry) | ✅ Resolvida 2026-04-10 (Opção A — integrar Sentry no frontend e backend) | FRONT-17 (EPIC-13) |
| DECISAO-09 | Read/write replica PostgreSQL | ✅ Resolvida 2026-04-10 (Opção B — diferir; retomar quando monitoramento indicar gargalo real) | Performance futura |

---

## Fase 0 — Bloqueadores de produção

Critérios de saída (plano mestre, linha 568):
- `alembic upgrade head` em banco limpo cria todas as 7 tabelas
- App falha na startup sem `.env` válido
- Timezone UTC padronizado
- Secrets OAuth seguros
- Pool com timeout
- Background task com rollback
- Dashboard não mostra dados fake
- Validações de agendamento funcionando

### EPIC-01 — Alembic e Schema Baseline
**Dependências:** nenhuma (primeiro) • **Itens:** 4 • **Concluídos:** 4 • **Status:** ✅ Concluído (2026-04-10)

- [x] **INFRA-15 / PERS-01 (RAIZ-02)** — Gerar migration inicial com `alembic revision --autogenerate -m "initial_schema"` e testar em banco limpo (Médio)
- [x] **PERS-03** — Envolver `import src.models` em try/except com mensagem clara em `backend/alembic/env.py:14-15` (Baixo)
- [x] **INFRA-24** — Remover fallback hardcoded `postgresql://user:password@localhost...` em `backend/alembic/env.py:26` (Baixo)
- [x] **WAHA-04 / RAIZ-03** — Deletar `backend/migrations/001_waha_session_migration.sql` (Concluído — arquivo já deletado)

### EPIC-02 — Fundação de Timezone (RAIZ-01)
**Dependências:** EPIC-01 • **Itens:** 3 • **Concluídos:** 3 • **Status:** ✅ Concluído (2026-04-10)

- [x] **PERS-05** — Adicionar `timezone=True` em todos os 17 `TIMESTAMP` dos 7 models; migration `a8f3c2e7d1b9` com `USING col AT TIME ZONE 'UTC'` (Médio)
- [x] **CAMP-01** — Substituir `datetime.utcnow()` e `datetime.now()` por `datetime.now(timezone.utc)` em 10 arquivos backend — 13 ocorrências corrigidas (Médio)
- [x] **FRONT-23** — Instalar `date-fns` + `date-fns-tz`; usar `fromZonedTime`/`toZonedTime` em `CampaignWizard.tsx:478-485` com timezone do browser (Médio)

### EPIC-03 — Configuração, Secrets e Startup Validation
**Dependências:** nenhuma • **Itens:** 9 • **Concluídos:** 9 • **Status:** ✅ Concluído (2026-04-10)

- [x] **INFRA-19** — `_require_env()` para `GHL_TOKEN_ENCRYPTION_KEY` e `GHL_WEBHOOK_SECRET` quando GHL habilitado em `config.py:23-28` (Baixo)
- [x] **GHL-14** — Validar `GHL_WEBHOOK_SECRET` no startup em vez de on-demand em `ghl_webhook_handler.py:40-43` (Baixo)
- [x] **INFRA-06** — Validar env vars obrigatórias antes de iniciar serviços em `deploy.sh:31-39` (Baixo)
- [x] **INFRA-20** — Logar warning se `DEBUG=True` em produção; prevenir SQL echo (Baixo)
- [x] **INFRA-21** — Substituir CORS `allow_methods=["*"]` e `allow_headers=["*"]` por listas explícitas em `main.py:76-83` (Baixo)
- [x] **INFRA-23 / WAHA-16** — Exigir `CORS_ORIGINS` quando `DEBUG=False` em `config.py:33` (Baixo)
- [x] **WAHA-14** — Lógica condicional: se `GHL_CLIENT_ID` setado, exigir creds GHL; senão desabilitar endpoints GHL (Médio)
- [x] **INFRA-34** — Criar `scripts/init-db.sql` ou remover referência em `docker-compose.yml:14` (Baixo)
- [x] **INFRA-35** — Usar `${POSTGRES_PASSWORD:?...}` em vez de `${POSTGRES_PASSWORD:-wpp_disp_password}` em `docker-compose.yml:10` (Baixo)

### EPIC-04 — Segurança OAuth e Tokens
**Dependências:** EPIC-03 • **Itens:** 9 • **Concluídos:** 9 • **Status:** ✅ Concluído (2026-04-11)

- [x] **GHL-01** — `with_for_update()` na query do token antes de verificar expiração em `ghl_oauth_service.py` (Médio)
- [x] **GHL-02** — Filtrar `access_token`/`refresh_token` antes de armazenar em `raw_response` (Baixo)
- [x] **GHL-03** — CSRF state gerado pelo servidor com HMAC-SHA256, validado no callback em `api/ghl_oauth.py` (Médio)
- [x] **GHL-12** — Retornar apenas metadata (location_id, scope, expires_in), nunca tokens brutos (Baixo)
- [x] **GHL-16** — `@retry` com tenacity em `_call_token_endpoint` (network errors only, não 4xx) (Baixo)
- [x] **GHL-17** — Validar campos obrigatórios na resposta OAuth antes de armazenar (Baixo)
- [x] **GHL-18** — `timeout=10.0` no `httpx.AsyncClient()` em `_call_token_endpoint` (Baixo)
- [x] **GHL-20** — MultiFernet com chaves separadas por vírgula em `token_encryption_service.py` (Alto)
- [x] **GHL-23** — Logar detalhe internamente, retornar mensagem genérica ao cliente (Baixo)

### EPIC-05 — Concorrência, Pool e Session Management (itens críticos/altos)
**Dependências:** EPIC-01 • **Itens:** 11 (dos 14 totais; 3 médios vão para Fase 1) • **Concluídos:** 11 • **Status:** ✅ Concluído (2026-04-12)

- [x] **PERS-20** — Adicionar `pool_timeout=30` ao `create_engine()` em `database.py:8-15` (Baixo)
- [x] **PERS-22** — Rollback no except do background task de `main.py:302-305`; setar `campaign.status='failed'`; commit (Baixo)
- [x] **PERS-23 / CAMP-13** — `db_session.rollback()` no except antes do close em `campaign_scheduler.py:158` (Baixo)
- [x] **PERS-25 (RAIZ-11)** — AsyncSession completo + asyncpg em `main.py` e `campaign_executor_service.py` (Alto)
  _Implementado em Fase 1. Confirmado por auditoria em 2026-04-12: database.py usa create_async_engine + asyncpg, todos os serviços usam AsyncSession._
- [x] **GHL-04** — `asyncio.Lock` no `TokenBucket` em `ghl_conversations_service.py:25-77`; `consume()` agora async (Baixo)
- [x] **CAMP-06** — `with_for_update()` no check de pausa dentro do loop em `campaign_executor_service.py:99` (Baixo)
- [x] **CAMP-07** — `.with_for_update()` na query do resume em `api/campaign_management.py:185` (Baixo)
- [x] **GHL-07** — Tratar duplicata do GHL API com try/catch + retry do search em `ghl_contacts_service.py:260-275` (Médio)
- [x] **GHL-09** — `webhook_id` já é PK (UNIQUE implícito); catch `IntegrityError` adicionado em `ghl_webhook_handler.py:106-115` (Médio)
- [x] **CAMP-11** — Separar rollback de status vs rollback de mensagens em `campaign_executor_service.py:201-212`; mensagens `pending` marcadas como `failed` (Médio)
- [x] **CAMP-14** — Commit único no final do loop em `_load_pending_campaigns` em `campaign_scheduler.py:195-196` (Baixo)

### EPIC-06 — Validadores de schedule (críticos de Fase 0)
**Dependências:** EPIC-01, EPIC-02 • **Itens:** 2 (dos 12 totais; 10 vão para Fase 1) • **Concluídos:** 2 • **Status:** ✅ Concluído (2026-04-11)

- [x] **CAMP-02** — `@field_validator` rejeitando `scheduled_time` no passado em `schemas/campaign.py` (Baixo)
- [x] **CAMP-03** — `@model_validator` exigindo `scheduled_time` quando `schedule_type='scheduled'` em `schemas/campaign.py` (Baixo)

### EPIC-11 — Analytics (críticos de Fase 0)
**Dependências:** EPIC-10 (idealmente) • **Itens:** 3 (dos 20 totais; 17 vão para Fase 2) • **Concluídos:** 3/3 • **Status:** ✅ Concluído 2026-04-11

- [x] **ANA-01 / ANA-10** — Adicionar campo `timeline` no endpoint `/api/v1/analytics/dashboard`; frontend consome (Alto)
- [x] **ANA-02** — Padronizar em `Message.status` como fonte única em `analytics_service.py` (Médio)
- [x] **ANA-03** — Incluir `pending` no denominador do cálculo de delivery rate em `analytics_service.py` (Baixo)

---

## Fase 1 — Estabilidade e segurança

Critérios de saída (plano mestre, linha 590):
- State machine enforced (campaign e message)
- Webhooks idempotentes e schema-validated
- Normalização E.164 em todas as camadas
- Router real no frontend com 404
- Memory leaks do Toast corrigidos
- Componentes UI acessíveis (WCAG 2.1 A)
- Logs sem PII
- Exceções não expostas ao cliente

### EPIC-05 — Resto (médios)
**Dependências:** EPIC-01 • **Itens:** 3 • **Concluídos:** 3 • **Status:** ✅ Concluído (2026-04-11)

- [x] **PERS-21** — Aumentar defaults: `pool_size=20, max_overflow=40` em `config.py:38-39` (Baixo)
- [x] **PERS-24 / CAMP-16** — Batch commits ou savepoints em vez de commit por mensagem em `campaign_executor_service.py:95-191` (Médio)
- [x] **PERS-19 / PERS-31** — Expor métricas `db_pool_size`, `db_pool_checkedout`, `db_pool_queue_size` em `metrics.py` (Médio)

### EPIC-06 — State Machine e Data Integrity (resto)
**Dependências:** EPIC-01, EPIC-02 • **Itens:** 10 • **Concluídos:** 10 • **Status:** ✅ Concluído (2026-04-11)

- [x] **CAMP-05** — Adicionar `VALID_TRANSITIONS` + `transition_to()` method no model Campaign (Médio)
- [x] **GHL-11** — Implementar máquina de estados `sent → delivered → read` no webhook; não regredir (Médio)
- [x] **PERS-06** — Usar `SQLEnum` ou CHECK constraint em `status` columns (Médio)
- [x] **PERS-11** — CHECK constraint: `paused_at` consistente com `status='paused'` em `campaign.py:44` (Baixo)
- [x] **PERS-28** — Adicionar `@validates` SQLAlchemy para status e enums em todos os models (Médio)
- [x] **PERS-08** — Após migração, tornar `ghl_location_id` NOT NULL OU CHECK constraint cruzada (Médio)
- [x] **PERS-09** — Tornar `message.campaign_id` NOT NULL OU documentar feature standalone (Baixo)
  _Bloqueia decisão: DECISAO-04_
- [x] **PERS-13** — CHECK constraint cruzada: `ghl_location_id` setado → `ghl_location_name` setado em `campaign.py:48-57` (Baixo)
- [x] **PERS-15** — Reavaliar CASCADE em messages; considerar RESTRICT + soft-delete (Médio)
  _Bloqueia decisão: DECISAO-03_
- [x] **PERS-16** — RESTRICT em vez de CASCADE em conversations, ou cleanup explícito (Baixo)
  _Bloqueia decisão: DECISAO-03_

### EPIC-07 — Execução de Campanha (correções funcionais)
**Dependências:** EPIC-02, EPIC-05, EPIC-06 • **Itens:** 11 • **Concluídos:** 11 • **Status:** ✅ Concluído (2026-04-11)

- [x] **CAMP-04** — Calcular `user_index` inicial no resume: `sent_count % len(user_ids)` em `campaign_executor_service.py:294-356` (Baixo)
- [x] **CAMP-12** — Catch `RateLimitExceeded` separado; aguardar antes de retry em `campaign_executor_service.py:159` (Baixo)
- [x] **GHL-06** — Trocar `type: "SMS"` por `type: "WhatsApp"` em `ghl_conversations_service.py:167` (Baixo)
- [x] **GHL-05** — Buscar/criar contato para obter `contact_id` antes de `send_message()` em `api/ghl_messages.py:102` (Baixo)
- [x] **GHL-08** — Catch 401 separado que força refresh antes do retry em `ghl_conversations_service.py:198-205` (Baixo)
- [x] **GHL-15** — Marcar `is_active=False` em users da location não retornados pela API em `ghl_users_service.py:79-124` (Médio)
- [x] **GHL-22** — Validar `assigned_to` contra tabela `ghl_users` em `ghl_contacts_service.py:112-162` (Baixo)
- [x] **WAHA-12** — Validar `ghl_location_id` existe no banco antes de criar campanha em `main.py:291-420` (Baixo)
- [x] **CAMP-08** — Usar agregação SQL em `get_campaign_status` em vez de `.all()` + count Python (Baixo)
- [x] **CAMP-09** — Normalizar schema de resposta do resume em `campaign_executor_service.py:340` (Baixo)
- [x] **CAMP-10** — Logar warning se `sending_speed` inválida; validar na criação em `campaign_executor_service.py:80` (Baixo)

### EPIC-08 — Webhooks GHL: segurança e idempotência
**Dependências:** EPIC-03, EPIC-06 • **Itens:** 4 • **Concluídos:** 4 • **Status:** ✅ Concluído (2026-04-11)

- [x] **GHL-13** — Criar schema Pydantic `WebhookPayload` com campos obrigatórios em `api/ghl_webhooks.py:55-70` (Médio)
- [x] **GHL-10** — Job periódico deletando `processed_at < now() - 30 dias` em `models/processed_webhook.py:20-34` (Baixo)
- [x] **GHL-21** — Checar `len(body) > 1MB` antes de processar em `ghl_webhooks.py` (Baixo)
- [x] **GHL-26** — `logger.warning` em falha de validação de assinatura em `ghl_webhook_handler.py:45-67` (Baixo)

### EPIC-09 — Normalização e Validação de Telefone (RAIZ-08)
**Dependências:** EPIC-01 • **Itens:** 4 • **Concluídos:** 4 • **Status:** ✅ Concluído (2026-04-11)

- [x] **PERS-10** — CHECK constraint `phone ~ '^\+[1-9]\d{1,14}$'` via migration Alembic nos 4 models (Médio)
- [x] **CAMP-23 / FRONT-24** — Normalizar em vez de rejeitar; usar `libphonenumber-js` em `CampaignWizard.tsx:159-164` (Baixo)
- [x] **GHL-19** — Normalizar telefone antes de buscar contato no GHL em `ghl_contacts_service.py:54-105` (Médio)
- [x] **Backend Pydantic** — `@field_validator` no `ContactData.phone_number` em `schemas/campaign.py` (Baixo)

### EPIC-12 — Frontend: Router e Arquitetura SPA
**Dependências:** RAIZ-09 (createCampaign) • **Itens:** 7 • **Concluídos:** 7 • **Status:** ✅ Concluído (2026-04-11)

- [x] **FRONT-01** — Instalar `react-router-dom`; migrar para `<BrowserRouter>` + `<Routes>` em `main.tsx:26-125` (Alto)
- [x] **FRONT-02** — Criar componente `NotFound`; retornar em rota desconhecida em `main.tsx:116-117` (Baixo)
- [x] **FRONT-03** — Integrar Sidebar ou deletar `Sidebar.tsx`/`Layout.tsx` (Médio)
  _Bloqueia decisão: DECISAO-02_
- [x] **FRONT-06** — Substituir custom event `navigate` por router hook (resolvido com FRONT-01)
- [x] **FRONT-07** — Implementar `<ProtectedRoute>` quando auth existir em `main.tsx:73-119` (Médio)
- [x] **FRONT-31** — `useSearchParams` para filtros na URL em `CampaignList.tsx:21-30` (Baixo)
- [x] **FRONT-35** — Criar `vite.config.ts` com proxy + aliases (Baixo)

### EPIC-13 — Componentes UI (críticos de Fase 1)
**Dependências:** nenhuma • **Itens:** 2 (dos 17 totais; 15 vão para Fase 2/3) • **Concluídos:** 2 • **Status:** ✅ Concluído (2026-04-11)

- [x] **FRONT-08** — Armazenar timeout IDs em `useRef(Map)` e limpar no cleanup em `ui/Toast.tsx:40-56,101` (Médio)
- [x] **FRONT-11** — `useId()` + `htmlFor` + `id` em `ui/Input.tsx:84-87,97` (Baixo)

### EPIC-14 — Wizard e Campanhas (críticos/altos)
**Dependências:** RAIZ-09, EPIC-02, EPIC-09 • **Itens:** 8 (dos 16 totais; 8 médios/baixos vão para Fase 2) • **Concluídos:** 8 • **Status:** ✅ Concluído (2026-04-11)

- [x] **FRONT-21** — Alinhar payload `audience_criteria` entre frontend e backend em `CampaignWizard.tsx:236-258` (Baixo)
- [x] **CAMP-20** — Validar `validMessages.length === 0` antes de enviar em `CampaignWizard.tsx:243-257` (Baixo)
- [x] **CAMP-22 / FRONT-P22** — Optional chaining: `campaign.message_stats?.total ?? 0` em `CampaignList.tsx:200-204` (Baixo)
- [x] **CAMP-24** — `setCsvParseError(null)` no path de sucesso em `CampaignWizard.tsx:173-175` (Baixo)
- [x] **CAMP-25 / FRONT-32** — Criar `MessageStatusBadge` separado em `CampaignDetails.tsx:264` (Baixo)
- [x] **FRONT-22** — `beforeunload` handler quando form dirty em `CampaignWizard.tsx` (Baixo)
- [x] **FRONT-25** — Capturar erro no catch e exibir via Toast ou estado local em `CampaignWizard.tsx:261-264` (Baixo)
- [x] **FRONT-29** — `invalidateQueries({ queryKey: [...], exact: true })` em `CampaignList.tsx:53,61,69` (Baixo)

### EPIC-15 — Infra: Deploy, Backup, Health Check
**Dependências:** EPIC-01, EPIC-03 • **Itens:** 18 • **Concluídos:** 18 • **Status:** ✅ Concluído (2026-04-11)

- [x] **INFRA-01** — Criar `.dockerignore` com `.env*`, `.git`, `node_modules`, `__pycache__`, `tests/` (Baixo)
- [x] **INFRA-07** — Bloquear deploy em produção se backup falhar em `deploy.sh:56-59` (Baixo)
- [x] **INFRA-12** — Criptografar backups com openssl ou GPG em `scripts/backup-db.sh` (Baixo)
- [x] **INFRA-17** — Chamar `./scripts/backup-db.sh` no início de `scripts/migrate-db.sh` (Baixo)
- [x] **INFRA-08** — Tentar `alembic downgrade -1` antes de derrubar serviços em `deploy.sh:81-89` (Médio)
- [x] **INFRA-09** — Validar branch antes de `git pull` em `deploy.sh:63-66` (Baixo)
- [x] **INFRA-10** — Checar `df` antes de iniciar em `deploy.sh` (Baixo)
- [x] **INFRA-11** — Falhar se `YOUR_DOMAIN` não substituído em `deploy.sh` + `nginx/sites-available/` (Baixo)
- [x] **INFRA-18** — `timeout 300` no docker exec em `scripts/migrate-db.sh:20-21` (Baixo)
- [x] **INFRA-13** — `gunzip -t` para verificar integridade em `scripts/backup-db.sh` (Baixo)
- [x] **INFRA-14** — Retenção escalonada em `scripts/backup-db.sh:44-47` (Baixo)
  _Bloqueia decisão: DECISAO-06_
- [x] **INFRA-29** — `exit 1` se qualquer check falhar em `scripts/health-check.sh` (Baixo)
- [x] **INFRA-30 / WAHA-11** — `/health` verifica conectividade com provider ativo em `main.py:152-179` (Médio)
- [x] **INFRA-31** — `pip install -r requirements.txt` em vez de lista hardcoded em `start_projects.sh:20` (Baixo)
- [x] **INFRA-02** — USER não-root após EXPOSE em `frontend/Dockerfile` (Baixo)
- [x] **INFRA-03** — `curl -sf http://localhost:8000/health` em `backend/Dockerfile:49-51` (Baixo)
- [x] **INFRA-04** — `deploy.resources.limits` em todos serviços em `docker-compose*.yml` (Baixo)
- [x] **INFRA-05** — Healthcheck no serviço nginx em `docker-compose.prod.yml:49-70` (Baixo)

### EPIC-17 — Observabilidade: Métricas, Logs e /metrics
**Dependências:** nenhuma • **Itens:** 6 • **Concluídos:** 6 • **Status:** ✅ Concluído (2026-04-11)

- [x] **RAIZ-04 (CAMP-17 / GHL-24 / INFRA-32)** — Filtro de mascaramento E.164 no `ContextFilter.filter()` em `logging_config.py` (Médio)
- [x] **RAIZ-05 (CAMP-18 / ANA-21 / GHL-23)** — `@app.exception_handler(Exception)` genérico em `main.py` (Baixo)
- [x] **RAIZ-10 (ANA-08 / INFRA-22)** — `hmac.compare_digest` + token obrigatório em produção em `main.py:182-192` (Baixo)
- [x] **INFRA-33** — Gerar `X-Request-ID` server-side; validar UUID se preservar em `main.py:102` (Baixo)
- [x] **CAMP-19 / WAHA-17** — Middleware `slowapi` em `main.py`, `api/campaign_management.py` (Médio)
  _Bloqueia decisão: DECISAO-07_
- [x] **GHL-26** — `logger.warning` em falha de assinatura em `ghl_webhook_handler.py:45-67` (Baixo) _(também aparece em EPIC-08)_

---

## Fase 2 — Qualidade e performance

Critérios de saída (plano mestre, linha 612):
- Dashboard com 10k campanhas carrega em <3s
- Métricas Prometheus de negócios disponíveis
- Contrato API com timeline funcionando
- SSL Labs A+
- Frontend com optimistic updates

### EPIC-10 — Performance e N+1 Queries
**Dependências:** EPIC-01 • **Itens:** 8 • **Concluídos:** 8 • **Status:** ✅ Concluído (2026-04-12)

- [x] **ANA-04** — JOIN + GROUP BY em vez de loop em `analytics_service.py:150-175` (Médio)
- [x] **ANA-05** — JOIN + GROUP BY + `outerjoin` em `analytics_service.py:207-239` (Médio)
- [x] **ANA-07** — `db.query(Campaign.status, func.count()).group_by(...)` em `analytics_service.py:40-49` (Baixo)
- [x] **PERS-17** — Índices compostos `(status, ghl_location_id)`, `(status, created_at)` em `models/campaign.py:70-74` (Baixo)
- [x] **PERS-18** — Índice parcial em `status` para `pending`/`sent` em `models/message.py:62-69` (Baixo)
- [x] **ANA-27** — Cache in-process com TTL 30s em `api/analytics.py` (Médio)
- [x] **RAIZ-06 (CAMP-15 / GHL-27)** — `httpx.AsyncClient` singleton por serviço (Médio)
- [x] **ANA-17** — Timeout de 5s no endpoint; retornar 504 se exceder em `api/analytics.py:15-102` (Baixo)

### EPIC-11 — Analytics: Dados Reais e Contrato API (resto)
**Dependências:** EPIC-10 • **Itens:** 17 • **Concluídos:** 16 • **Status:** ✅ Concluído (2026-04-12)

- [x] **ANA-09** — Adicionar métricas de negócios em `metrics.py:1-24`: `messages_sent_total`, `campaign_delivery_rate`, etc. (Médio)
- [x] **ANA-06** — Normalizar path Prometheus: `/campaigns/{id}` em vez de `/campaigns/123` em `main.py:114,122,125-129` (Médio)
- [x] **ANA-11** — Validar formato de `delivery_rate` (decimal vs porcentagem) em `Dashboard.tsx:154-156` (Baixo)
- [x] **ANA-12** — Aumentar timeout para 7s em `Dashboard.tsx:46-47` (Baixo)
- [x] **ANA-13** — Adicionar timestamp `fetchedAt` + polling opcional em `Dashboard.tsx` (Baixo)
- [x] **ANA-14** — Prop `period` dinâmico em `MetricCard.tsx:127-129` (Baixo)
- [x] **ANA-15** — AbortController para cancelar requests anteriores em `Dashboard.tsx:73-78` (Baixo)
- [x] **ANA-16** — Validar schema da resposta antes de setar state em `Dashboard.tsx:59-62` (Baixo) — _implementado 2026-04-13: isDashboardMetrics type guard com verificação de campos leaf_
- [x] **ANA-18** — Propagar `timeRange` ou consolidar em uma chamada em `Dashboard.tsx` + `MessagingKpiPanel.tsx` (Médio)
- [x] **ANA-19** — `role="img"` + `aria-label` nos gráficos em `ChartComponents.tsx` (Médio)
- [x] **ANA-20** — Parsear body JSON do erro em `analytics-service.ts:19-28` (Baixo)
- [x] **ANA-22** — Remover validação manual redundante em `analytics.py:34-41` (Baixo) — _já estava resolvido: FastAPI Query(ge=1, le=365)_
- [x] **ANA-23** — Calcular change real a partir de dados históricos em `Dashboard.tsx:178-205` (Médio)
- [x] **ANA-24** — Util `formatNumber()` compartilhado em MetricCard, ChartComponents, Dashboard (Baixo)
- [x] **ANA-25 / FRONT-39** — Reduzir `staleTime` para 10-15s em `MessagingKpiPanel.tsx:55-59` (Baixo)
- [x] **ANA-26** — `.nullslast()` em `order_by(sent_at.desc())` em `campaign_management_service.py:180` (Baixo)
- [x] **ANA-28** — Tratar estado vazio separado de `!metrics` em `Dashboard.tsx:128-148` (Baixo)

### EPIC-13 — Componentes UI (resto)
**Dependências:** nenhuma • **Itens:** 15 • **Concluídos:** 14 • **Status:** ✅ Concluído 2026-04-12

- [x] **FRONT-09** — `role="region"` + `aria-label` no container; `role="alert"` nos toasts + close button `aria-label` em `ui/Toast.tsx` (Baixo)
- [x] **FRONT-10** — Limite máximo de 5 toasts visíveis (FIFO) com timer cleanup em `ui/Toast.tsx` (Baixo)
- [x] **FRONT-12** — Handler `onKeyDown` para Enter/Space quando `clickable=true` em `ui/Card.tsx` (Baixo)
- [x] **FRONT-13** — Warning em dev se children vazio e sem `aria-label` em `ui/Button.tsx` (Baixo)
- [x] **FRONT-14** — `aria-label="Remover"` no botão + `aria-hidden` no SVG em `ui/Badge.tsx` (Baixo)
- [x] **FRONT-15** — `aria-label` dinâmico + `aria-pressed` no password toggle em `ui/Input.tsx` (Baixo)
- [x] **FRONT-16** — Sentry `captureException` em `componentDidCatch` em `ErrorBoundary.tsx` (Médio)
- [x] **FRONT-17** — Listener global `unhandledrejection` + Sentry em `ErrorBoundary.tsx`; `initSentry()` em `main.tsx` (Médio)
- [x] **FRONT-18** — `React.isValidElement()` guard antes de `cloneElement` em `Button.tsx`, `Card.tsx`, `Input.tsx` (Baixo)
- [x] **FRONT-19** — Guard de controlled/uncontrolled em `ui/Input.tsx` (Baixo)
- [x] **FRONT-20** — ~~`onClick={onToggleCollapse}` no overlay mobile em `Sidebar.tsx`~~ **SKIPPED** — Sidebar.tsx deletado per DECISAO-02 (Baixo)
- [x] **FRONT-36** — `aria-label="Navegação principal"` em `Header.tsx` (Baixo)
- [x] **FRONT-37** — Skip link + `id="main-content"` em `Layout.tsx` (Baixo)
- [x] **FRONT-38** — `darkMode: 'class'` em `tailwind.config.js` (Baixo)
- [x] **FRONT-40** — `shadow-ghl-lg` em Toast, Card elevated, ErrorBoundary (Baixo)

### EPIC-14 — Wizard/Campanhas (resto)
**Dependências:** RAIZ-09, EPIC-02, EPIC-09 • **Itens:** 8 • **Concluídos:** 8 • **Status:** ✅ Concluído (2026-04-12)

- [x] **FRONT-26** — Só limpar errors após avançar com sucesso em `CampaignWizard.tsx:269-277` (Baixo)
- [x] **FRONT-27** — `useRef` + foco ao mudar step em `CampaignWizard.tsx:269-277` (Baixo)
- [x] **FRONT-28** — Salvar column mapping em localStorage em `CampaignWizard.tsx:47,98-126` (Baixo)
- [x] **FRONT-30** — Optimistic updates com `onMutate`/`onError` em `CampaignList.tsx:50-71` (Médio)
- [x] **FRONT-33** — `refetchInterval` se campanha em execução em `CampaignDetails.tsx:31-34` (Baixo)
- [x] **FRONT-34** — Modal pedindo nome da campanha para confirmar delete em `CampaignActions.tsx:87-120` (Médio)
- [x] **CAMP-26** — Adicionar spinner `Loader2` no botão submit em `CampaignWizard.tsx:231-265` (Baixo)
- [x] **CAMP-27** — `.filter()` antes do `.map()` na paginação em `CampaignList.tsx:278-292` (Baixo)

### EPIC-16 — Nginx, SSL e Headers de Segurança
**Dependências:** nenhuma • **Itens:** 4 • **Concluídos:** 4 • **Status:** ✅ Concluído (já implementado em EPIC-15/PR-5)

- [x] **INFRA-25** — `ssl_prefer_server_ciphers on` em `nginx/sites-available/wpp-disp.conf:34` (Baixo)
- [x] **INFRA-26** — CSP `connect-src` com domínios externos necessários em `nginx/nginx.conf:45` (Baixo)
- [x] **INFRA-27** — Headers de segurança explícitos no server block em `nginx/sites-available/wpp-disp.conf:38-46` (Baixo)
- [x] **INFRA-28** — Adicionar `ssl_stapling on` em `nginx/sites-available/wpp-disp.conf` (Baixo)

---

## Itens fora de fase

### EPIC-18 — WAHA: Decisão e Execução (CONCLUÍDO)
**Status:** ✅ **Concluído em 2026-04-10.** DECISAO-01 resolvida como Opção B (Remover). Todos os itens abaixo da Opção B foram aplicados.

**Opção B — Remover (executada):**
- [x] **WAHA-01** — Deletar endpoints WAHA de `main.py:196-228`
- [x] **WAHA-07** — Atualizar `/docs-status` removendo WAHA em `main.py:595-618`
- [x] **WAHA-04 / RAIZ-03** — Deletar `backend/migrations/001_waha_session_migration.sql`
- [x] **WAHA-10** — Remover tipos TypeScript deprecados em `frontend/src/types/api.ts:11-43`
- [x] **WAHA-15** — Documentar que WAHA não é suportado em `CLAUDE.md`

**Opção A — Manter e implementar (NÃO executada):** WAHA-02, WAHA-03, WAHA-05, WAHA-06, WAHA-08, WAHA-13. Estes itens não serão trabalhados pois DECISAO-01 foi resolvida como Opção B.

**Independente da opção (NÃO executado):** WAHA-09 (mensagem genérica em validação de sessão em `main.py:252`). Como o endpoint foi deletado pela Opção B, este item perdeu relevância.

### RAIZ-09 — createCampaign ausente no service
**Status:** ✅ Concluído (2026-04-11) • **Severidade:** bloqueia EPIC-12 e EPIC-14

Este não é um EPIC por si, mas um problema raiz transversal listado no plano mestre. O frontend ainda chama `POST /campaigns` (endpoint inline legado em `main.py:200`) em vez de `/api/v1/campaigns`. Bloqueia o arranque do EPIC-12 e EPIC-14.

- [x] **RAIZ-09** — Implementar `campaignService.createCampaign()` no frontend e mover endpoint de criação para `/api/v1/campaigns` no backend
  - Backend: `backend/src/api/campaign_management.py` — adicionar endpoint de criação
  - Frontend: `frontend/src/services/campaign-service.ts` — adicionar `createCampaign()`
  - Frontend: `frontend/src/main.tsx:52` — trocar chamada para o novo service
  - Remover o `POST /campaigns` inline de `main.py:200-329` ou marcar deprecated

---

## Histórico de mudanças

| Data | Mudança | Fonte |
|------|---------|-------|
| 2026-04-10 | Documento criado a partir do `plano-implementacao-mestre.md`. WAHA EPIC-18 Opção B marcado como concluído (5 itens). ANA-01 marcado como parcial com nota sobre hacks. Status inicial de 12 itens verificado contra o código na branch `004-campaign-management`. | Revisão manual + verificação de código |
| 2026-04-10 | DECISAO-02 a DECISAO-09 resolvidas. EPIC-01 (Alembic Baseline) concluído: `alembic/env.py` corrigido (PERS-03, INFRA-24), migration `eb03c3cc8781_initial_schema` gerada e aplicada ao banco dev. Total: 9 itens concluídos. | Implementação direta |
| 2026-04-11 | Fase 1 concluída (66/66). 6 PRs mergeados em `004-campaign-management`: PR-1 (EPIC-06 State Machine), PR-2 (EPIC-07 Execução + EPIC-08 Webhooks), PR-3 (EPIC-09 E.164 + EPIC-13 UI críticos), PR-4 (EPIC-05 resto + EPIC-17 Observabilidade), PR-5 (EPIC-15 Infra/Deploy/Backup), PR-6 (EPIC-12 React Router + EPIC-14 Wizard + RAIZ-09). | PRs mergeados |
| 2026-04-12 | EPIC-13 concluído (14/15 — FRONT-20 dead, Sidebar deletado). 14 itens: Toast ARIA+FIFO, Card keyboard nav, Button/Badge/Input a11y, Sentry integration, shadow-ghl-lg, skip link, darkMode. Fase 2: 39/52. Total: 152/172. | Subagent-Driven Development |
| 2026-04-12 | EPIC-14 Fase 2 concluído (8/8). FRONT-26/27/28/30/33/34, CAMP-26/27: erro limpo ao voltar no wizard, foco no heading, localStorage para column mapping, spinner no submit, optimistic updates na CampaignList, refetchInterval condicional, modal de confirmação com nome da campanha. TypeScript fix: `Query<CampaignDetailsResponse>`. 83/83 testes passando. Fase 2: 47/52. Total: 160/172. | Subagent-Driven Development |
| 2026-04-12 | EPIC-16 marcado completo — todos os 4 itens (INFRA-25/26/27/28) já estavam implementados em EPIC-15/PR-5. Nenhum trabalho adicional necessário. Fase 2: 51/52 (só PERS-25 pendente). Total: 164/172. | Auditoria de código |
| 2026-04-12 | PERS-25 marcado completo — AsyncSession + asyncpg já implementados em Fase 1 (database.py, campaign_executor_service.py, campaign_scheduler.py, main.py). **Fase 2: 52/52 COMPLETA.** Total: 165/172. | Auditoria de código |
| 2026-04-12 | ANA-16 implementado — `isDashboardMetrics` type guard em `Dashboard.tsx` (verifica campos leaf `total_campaigns`, `active_campaigns`, `sent`, `delivery_rate`, `read_rate`); data tipada como `unknown` força narrowing antes de `setMetrics`. `/docs-status` atualizado para refletir `GHL_ENABLED` (campo `ghl_enabled` adicionado, endpoints GHL condicionais). 85/85 testes frontend, 99/99 backend. Total: 167/172. Fase 3: 5/7. | Subagent-Driven Development |
| 2026-04-12 | Runbook de operações criado em `docs/runbook.md` — cobre primeiro deploy, deploy de atualização, rollback (código + migration + restore), backup/restore com decrypt AES-256-CBC, migrações Alembic (incl. R01 stamp), health checks, operações de campanha (velocidades, estados, campanhas presas), resposta a incidentes (backend, DB, startup, campanha não inicia), rotinas periódicas e referência rápida de comandos. Total: 168/172. Fase 3: 6/7. | Documentação manual |
