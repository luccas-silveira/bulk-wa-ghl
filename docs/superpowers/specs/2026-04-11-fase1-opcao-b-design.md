# Design — Fase 1 Opção B

**Data:** 2026-04-11
**Branch:** `004-campaign-management`
**Escopo:** 9 EPICs / 66 itens da Fase 1 do roadmap, excluindo PERS-25 (AsyncSession — PR separado)

---

## Contexto

Fase 0 (41/41 itens) está completa. A Fase 1 endereça estabilidade e segurança do sistema:
state machine enforçada, webhooks schema-validados, normalização E.164, router real no frontend,
memory leaks corrigidos, logs sem PII, exceções não expostas ao cliente.

PERS-25 (AsyncSession + asyncpg) foi deliberadamente excluído desta fase por risco alto e por
requerer PR isolado. Enquanto não aterra, novos métodos de serviço devem continuar o padrão
síncrono existente para não misturar tipos de sessão.

---

## Estrutura de PRs

| PR | EPICs | Itens | Dependências |
|----|-------|------:|--------------|
| PR-1 | EPIC-06 (State Machine) | 10 | EPIC-01, EPIC-02 ✅ |
| PR-2 | EPIC-07 + EPIC-08 | 15 | PR-1 |
| PR-3 | EPIC-09 + EPIC-13 | 6 | EPIC-01 ✅ |
| PR-4 | EPIC-05 resto + EPIC-17 | 9 | EPIC-01 ✅ |
| PR-5 | EPIC-15 | 18 | EPIC-01, EPIC-03 ✅ |
| PR-6 | EPIC-14 + EPIC-12 | 15 | RAIZ-09 (a implementar), EPIC-09 |

PRs 3, 4 e 5 são independentes entre si — podem ser desenvolvidos em paralelo após PR-1.

---

## PR-1 — EPIC-06: State Machine e Integridade de Dados

### State machine de Campaign

**Implementação em três camadas:**

**1. Camada Python — `Campaign` model (`backend/src/models/campaign.py`)**

```python
VALID_TRANSITIONS = {
    'draft':     {'scheduled', 'executing', 'failed'},
    'executing': {'paused', 'completed', 'failed'},
    'paused':    {'executing'},
    'scheduled': {'cancelled', 'failed', 'executing'},
}

def transition_to(self, new_status: str) -> None:
    allowed = self.VALID_TRANSITIONS.get(self.status, set())
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition campaign {self.id} from '{self.status}' to '{new_status}'. "
            f"Allowed: {allowed or 'none (terminal state)'}"
        )
    self.status = new_status
```

`InvalidTransitionError` é uma exceção de domínio definida em `src/exceptions.py` (novo arquivo).
Estados terminais (`completed`, `failed`, `cancelled`) não aparecem como chaves em
`VALID_TRANSITIONS` — qualquer transição a partir deles lança o erro.

**2. Camada SQLAlchemy — `@validates`**

```python
VALID_STATUSES = {'draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'}

@validates('status')
def validate_status(self, key, value):
    if value not in self.VALID_STATUSES:
        raise ValueError(f"Invalid campaign status: '{value}'")
    return value
```

O `@validates` valida apenas o valor, não a transição. Inicializações diretas
(ex: `status='draft'` na criação) continuam funcionando sem precisar de transição prévia.

**3. Camada DB — migration Alembic**

```sql
ALTER TABLE campaigns
    ADD CONSTRAINT chk_campaign_status
    CHECK (status IN ('draft','scheduled','executing','paused','completed','failed','cancelled'));

ALTER TABLE campaigns
    ADD CONSTRAINT chk_campaign_paused_at
    CHECK (paused_at IS NULL OR status = 'paused');
```

`String(50)` permanece no model — evita `ALTER TYPE` de Enum PostgreSQL, que não é transacional.

**Migração de chamadas existentes:**
Todos os `campaign.status = 'x'` nos serviços são substituídos por `campaign.transition_to('x')`:
- `backend/src/services/campaign_executor_service.py` (~5 ocorrências)
- `backend/src/services/campaign_scheduler.py` (~2 ocorrências)
- `backend/src/api/campaign_management.py` (~2 ocorrências)
- `backend/src/main.py` (~3 ocorrências)

### State machine de Message (GHL-11)

Sem método `transition_to` explícito. A regra é guardada no webhook handler:
nunca regredir `message.status` (fonte única de verdade — ANA-02). Ordem: `pending < sent < delivered < read`.

```python
STATUS_ORDER = {'pending': 0, 'sent': 1, 'delivered': 2, 'read': 3, 'failed': -1}

if STATUS_ORDER.get(new_status, -1) > STATUS_ORDER.get(message.status, 0):
    message.status = new_status  # fonte única (ANA-02)
    message.ghl_status = new_status  # mantido para rastreabilidade GHL
```

`failed` pode ser atribuído independentemente da ordem.

Migration Alembic com CHECK constraint em `messages.status`:
```sql
ALTER TABLE messages
    ADD CONSTRAINT chk_message_status
    CHECK (status IN ('pending','sent','delivered','read','failed'));
```

### Integridade referencial (PERS-06, PERS-08, PERS-09, PERS-11, PERS-13, PERS-15, PERS-16, PERS-28)

Todos via migration Alembic única no PR-1:

```sql
-- PERS-08: ghl_location_id NOT NULL após migration
ALTER TABLE campaigns ALTER COLUMN ghl_location_id SET NOT NULL;

-- PERS-09: campaign_id NOT NULL (feature standalone removida — DECISAO-04)
ALTER TABLE messages ALTER COLUMN campaign_id SET NOT NULL;

-- PERS-13: CHECK cruzada location_id / location_name
ALTER TABLE campaigns
    ADD CONSTRAINT chk_campaign_location_name
    CHECK (ghl_location_id IS NULL OR ghl_location_name IS NOT NULL);

-- PERS-15: CASCADE → RESTRICT em messages
ALTER TABLE messages
    DROP CONSTRAINT messages_campaign_id_fkey,
    ADD CONSTRAINT messages_campaign_id_fkey
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE RESTRICT;

-- PERS-16: RESTRICT em conversations
ALTER TABLE ghl_conversations
    DROP CONSTRAINT ghl_conversations_campaign_id_fkey,
    ADD CONSTRAINT ghl_conversations_campaign_id_fkey
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE RESTRICT;
```

`@validates` SQLAlchemy (PERS-28) adicionado nos models `Campaign`, `Message`,
`GHLConversation` para os campos `status` e campos enum — segunda linha de defesa.

---

## PR-2 — EPIC-07 + EPIC-08: Execução e Webhooks

### EPIC-07 — Correções de execução (11 itens)

Todos os itens são cirúrgicos. Arquivo e linha referenciados no roadmap:

- **CAMP-04** — Resume fix: `user_index = sent_count % len(user_ids)` em `campaign_executor_service.py:294-356`
- **CAMP-08** — `get_campaign_status` usa agregação SQL em vez de `.all()` + count Python
- **CAMP-09** — Schema de resposta do resume normalizado
- **CAMP-10** — Warning se `sending_speed` inválida; validar na criação
- **CAMP-12** — `RateLimitExceeded` caught separadamente; aguarda antes de retry
- **GHL-05** — Buscar/criar contato para obter `contact_id` antes de `send_message()`
- **GHL-06** — `type: "WhatsApp"` em vez de `"SMS"` em `ghl_conversations_service.py:167`
- **GHL-08** — Catch 401 separado → força refresh antes do retry
- **GHL-15** — `is_active=False` em users não retornados pela API
- **GHL-22** — Validar `assigned_to` contra `ghl_users`
- **WAHA-12** — Validar `ghl_location_id` existe antes de criar campanha

### EPIC-08 — Webhooks: segurança e idempotência (4 itens)

- **GHL-13** — Schema Pydantic `WebhookPayload` com campos obrigatórios em `api/ghl_webhooks.py`
- **GHL-10** — Job APScheduler: `DELETE FROM processed_webhooks WHERE processed_at < now() - interval '30 days'`; registrado no startup do `main.py`
- **GHL-21** — Guard `len(body) > 1_000_000` antes de processar; retorna 413
- **GHL-26** — `logger.warning` com `webhook_id` e IP em falha de validação de assinatura

---

## PR-3 — EPIC-09 + EPIC-13: E.164 e UI Críticos

### EPIC-09 — Normalização de telefone (4 itens)

**Backend:**
- Migration Alembic: CHECK constraint `phone ~ '^\+[1-9]\d{1,14}$'` em `campaigns.recipient_phone` (via `messages`) e nos demais models com campo de telefone
- `@field_validator('phone_number')` no `ContactData` em `schemas/campaign.py`: normaliza (não rejeita) — usa `phonenumbers` lib para parse + format E.164
- `ghl_contacts_service.py`: normalizar antes de buscar contato no GHL

**Frontend:**
- Instalar `libphonenumber-js`; substituir validação em `CampaignWizard.tsx:159-164` por normalização com fallback para o valor original se não parseable

### EPIC-13 — UI críticos (2 itens)

- **FRONT-08** — `ui/Toast.tsx`: substituir `setTimeout` IDs soltos por `useRef<Map<string, ReturnType<typeof setTimeout>>>` com cleanup no `useEffect`
- **FRONT-11** — `ui/Input.tsx`: `useId()` para gerar id estável; `htmlFor={id}` no label; `id={id}` no input

---

## PR-4 — EPIC-05 resto + EPIC-17: Pool e Observabilidade

### EPIC-05 resto (3 itens)

- **PERS-21** — `DB_POOL_SIZE` default → 20, `DB_MAX_OVERFLOW` default → 40 em `config.py`
- **PERS-24** — Batch commits em `campaign_executor_service.py`: commit a cada N mensagens (configurável, default 10) em vez de commit por mensagem — reduz contenção de pool
- **PERS-19** — Métricas `db_pool_size`, `db_pool_checkedout`, `db_pool_queue_size` expostas via `engine.pool.status()` em `metrics.py`

### EPIC-17 — Observabilidade (6 itens)

- **RAIZ-04** — `ContextFilter.filter()` em `logging_config.py`: regex para mascarar telefones E.164 (`\+\d{7,15}` → `+***`) antes de emitir log
- **RAIZ-05** — `@app.exception_handler(Exception)` em `main.py`: loga detalhes internamente, retorna `{"detail": "Internal server error"}` com status 500
- **RAIZ-10** — `/metrics`: `hmac.compare_digest` + `METRICS_TOKEN` obrigatório quando `DEBUG=False`
- **INFRA-33** — Middleware em `main.py`: gera `X-Request-ID` UUID server-side se não presente no request; valida formato UUID se header vier do cliente
- **CAMP-19** — Middleware `slowapi` em `main.py` e `api/campaign_management.py`: rate limiting por IP
- **GHL-26** — `logger.warning` em falha de assinatura (também cobre EPIC-08)

---

## PR-5 — EPIC-15: Infra, Deploy e Backup

18 itens todos em arquivos de infra. Sem impacto no código de aplicação.

### Dockerfiles e imagens
- `.dockerignore` na raiz e em `frontend/`: `.env*`, `.git`, `node_modules`, `__pycache__`, `tests/`
- `frontend/Dockerfile`: instrução `USER node` (não-root) após `EXPOSE`
- `backend/Dockerfile`: healthcheck `curl -sf http://localhost:8000/health || exit 1`
- `docker-compose*.yml`: `deploy.resources.limits` em todos os serviços; healthcheck no nginx

### deploy.sh
- Validar branch antes de `git pull`
- `df -h` check: abortar se menos de 1GB livre
- Falhar se string `YOUR_DOMAIN` ainda presente em `deploy.sh` ou `nginx/sites-available/`
- `alembic downgrade -1` antes de derrubar serviços no rollback
- Bloquear deploy se backup falhar

### Scripts de backup/migração
- `scripts/backup-db.sh`: criptografia com openssl (`-aes-256-cbc`); `gunzip -t` para verificar integridade; retenção dos últimos 10 backups (DECISAO-06)
- `scripts/migrate-db.sh`: chamar `backup-db.sh` antes de migrar; `timeout 300` no docker exec
- `scripts/health-check.sh`: `exit 1` se qualquer check falhar
- `/health` endpoint: verificar conectividade com DB e provider ativo (GHL)
- `start_projects.sh`: `pip install -r requirements.txt` em vez de lista hardcoded

---

## PR-6 — EPIC-14 + EPIC-12: Frontend Campanhas e Router

**Pré-requisito:** RAIZ-09 (migrar `POST /campaigns` para o router moderno) deve ser implementado como primeiro commit deste PR.

### RAIZ-09 — Migrar criação de campanha
Mover `POST /campaigns` de `main.py:204` para `api/campaign_management.py`. Atualizar `frontend/src/main.tsx:52` para apontar para `/api/v1/campaigns`.

### EPIC-12 — React Router (7 itens)
- Instalar `react-router-dom`; migrar `main.tsx:26-125` para `<BrowserRouter>` + `<Routes>` + `<Route>`
- Componente `<NotFound>` em rota `*`
- Deletar `Sidebar.tsx` e `Layout.tsx` (DECISAO-02)
- Substituir custom event `navigate` por `useNavigate()` hook
- `<ProtectedRoute>` stub preparado para futura auth
- `useSearchParams` para filtros de campanha na URL
- `vite.config.ts` com proxy `/api → localhost:8000` e alias `@/`

### EPIC-14 — Correções de Wizard e CampaignList (8 itens)
- Alinhar `audience_criteria` entre frontend e backend
- Guard `validMessages.length === 0` antes de submit
- Optional chaining em `campaign.message_stats?.total ?? 0`
- `setCsvParseError(null)` no path de sucesso do parse
- `beforeunload` handler quando form dirty
- Capturar e exibir erro do submit via Toast
- `invalidateQueries({ queryKey: [...], exact: true })`
- Componente `<MessageStatusBadge>` extraído de `CampaignDetails`

---

## Controle de progresso

- **Macro:** marcar `[x]` no `docs/roadmap-execucao.md` conforme cada item for concluído
- **Micro:** `tasks.md` gerado pelo writing-plans guia a execução de cada PR
- **Git:** mensagens de commit referenciam IDs do roadmap: `feat(campaign): add transition_to() (CAMP-05)`
- **Fluxo por PR:** `tasks.md → implementar → commit com ID → [x] no roadmap → PR`

---

## Itens excluídos desta fase

- **PERS-25** (AsyncSession + asyncpg): PR dedicado, alto risco
- **EPIC-10** (N+1 queries): Fase 2
- **EPIC-11 resto** (Analytics completo): Fase 2
- **EPIC-13 resto** (15 itens de UI): Fase 2/3
- **EPIC-14 resto** (8 itens de Wizard): Fase 2
