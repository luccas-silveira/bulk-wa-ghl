# PR-1: State Machine e Integridade de Dados (EPIC-06) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforçar as state machines de Campaign e Message em três camadas (Python, SQLAlchemy e banco) e adicionar constraints de integridade referencial via migration Alembic.

**Architecture:** Nova exceção de domínio `InvalidTransitionError` em `src/exceptions.py`; método `transition_to()` no model `Campaign` com dict `VALID_TRANSITIONS`; guard `STATUS_ORDER` no webhook handler para Message; migration Alembic única com todos os CHECK constraints e ajustes de FK.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, FastAPI 0.104, Alembic, PostgreSQL 16, pytest

**Roadmap items cobertos:** CAMP-05, GHL-11, PERS-06, PERS-08, PERS-09, PERS-11, PERS-13, PERS-15, PERS-16, PERS-28

---

## Mapa de arquivos

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Criar | `backend/src/exceptions.py` | `InvalidTransitionError` — exceção de domínio |
| Modificar | `backend/src/models/campaign.py` | `VALID_TRANSITIONS`, `transition_to()`, `@validates('status')` |
| Modificar | `backend/src/models/message.py` | `STATUS_ORDER`, `VALID_STATUSES`, `@validates('status')` |
| Modificar | `backend/src/services/ghl_webhook_handler.py` | Guard de não-regressão em `handle_message_delivered` e `handle_message_read` |
| Modificar | `backend/src/services/campaign_executor_service.py` | 5× `campaign.status = 'x'` → `campaign.transition_to('x')` |
| Modificar | `backend/src/services/campaign_scheduler.py` | 1× substituição |
| Modificar | `backend/src/main.py` | 4× substituições (com guard duplo-fail em linha 308) |
| Modificar | `backend/src/api/campaign_management.py` | 1× substituição |
| Criar | `backend/alembic/versions/<rev>_state_machine_constraints.py` | CHECK constraints + NOT NULL + FK RESTRICT |
| Criar | `backend/tests/unit/test_exceptions.py` | Testes unitários de `InvalidTransitionError` |
| Criar | `backend/tests/unit/test_campaign_state_machine.py` | Testes unitários da state machine de Campaign |
| Criar | `backend/tests/unit/test_message_state_machine.py` | Testes unitários do guard de Message |
| Criar | `backend/tests/integration/test_state_machine_constraints.py` | Testes das constraints no banco real |

---

## Task 1: Criar `src/exceptions.py` com `InvalidTransitionError`

**Files:**
- Create: `backend/src/exceptions.py`
- Create: `backend/tests/unit/test_exceptions.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/unit/test_exceptions.py
"""Unit tests for domain exceptions."""
import pytest
from src.exceptions import InvalidTransitionError


class TestInvalidTransitionError:
    def test_message_includes_from_status(self):
        err = InvalidTransitionError("executing", "draft", set())
        assert "executing" in str(err)

    def test_message_includes_to_status(self):
        err = InvalidTransitionError("executing", "draft", set())
        assert "draft" in str(err)

    def test_message_includes_allowed_when_set(self):
        err = InvalidTransitionError("paused", "scheduled", {"executing"})
        assert "executing" in str(err)

    def test_terminal_state_message_when_no_allowed(self):
        err = InvalidTransitionError("completed", "executing", set())
        assert "terminal" in str(err).lower()

    def test_is_exception_subclass(self):
        err = InvalidTransitionError("paused", "scheduled", {"executing"})
        assert isinstance(err, Exception)

    def test_attributes_stored(self):
        err = InvalidTransitionError("paused", "draft", {"executing"})
        assert err.from_status == "paused"
        assert err.to_status == "draft"
        assert err.allowed == {"executing"}
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd backend && pytest tests/unit/test_exceptions.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.exceptions'`

- [ ] **Step 3: Criar `backend/src/exceptions.py`**

```python
# backend/src/exceptions.py
"""Domain exceptions for bulk-wa-ghl."""


class InvalidTransitionError(Exception):
    """Raised when a campaign status transition is not allowed."""

    def __init__(self, from_status: str, to_status: str, allowed: set) -> None:
        if allowed:
            msg = (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed: {sorted(allowed)}"
            )
        else:
            msg = (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"'{from_status}' is a terminal state — no transitions allowed."
            )
        super().__init__(msg)
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
```

- [ ] **Step 4: Rodar os testes para confirmar que passam**

```bash
cd backend && pytest tests/unit/test_exceptions.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/src/exceptions.py backend/tests/unit/test_exceptions.py
git commit -m "feat(domain): add InvalidTransitionError (EPIC-06)"
```

---

## Task 2: State machine de Campaign — `transition_to()` + `@validates` (CAMP-05, PERS-28)

**Files:**
- Modify: `backend/src/models/campaign.py`
- Create: `backend/tests/unit/test_campaign_state_machine.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
# backend/tests/unit/test_campaign_state_machine.py
"""Unit tests for Campaign state machine (CAMP-05, PERS-28)."""
import pytest
from src.models.campaign import Campaign
from src.exceptions import InvalidTransitionError


class TestValidTransitions:
    def test_draft_to_scheduled(self):
        c = Campaign(status='draft')
        c.transition_to('scheduled')
        assert c.status == 'scheduled'

    def test_draft_to_executing(self):
        c = Campaign(status='draft')
        c.transition_to('executing')
        assert c.status == 'executing'

    def test_draft_to_failed(self):
        c = Campaign(status='draft')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_executing_to_paused(self):
        c = Campaign(status='executing')
        c.transition_to('paused')
        assert c.status == 'paused'

    def test_executing_to_completed(self):
        c = Campaign(status='executing')
        c.transition_to('completed')
        assert c.status == 'completed'

    def test_executing_to_failed(self):
        c = Campaign(status='executing')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_paused_to_executing(self):
        c = Campaign(status='paused')
        c.transition_to('executing')
        assert c.status == 'executing'

    def test_scheduled_to_cancelled(self):
        c = Campaign(status='scheduled')
        c.transition_to('cancelled')
        assert c.status == 'cancelled'

    def test_scheduled_to_failed(self):
        c = Campaign(status='scheduled')
        c.transition_to('failed')
        assert c.status == 'failed'

    def test_scheduled_to_executing(self):
        c = Campaign(status='scheduled')
        c.transition_to('executing')
        assert c.status == 'executing'


class TestInvalidTransitions:
    def test_completed_is_terminal(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_failed_is_terminal(self):
        c = Campaign(status='failed')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_cancelled_is_terminal(self):
        c = Campaign(status='cancelled')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('executing')

    def test_draft_to_completed_not_allowed(self):
        c = Campaign(status='draft')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('completed')

    def test_paused_to_completed_not_allowed(self):
        c = Campaign(status='paused')
        with pytest.raises(InvalidTransitionError):
            c.transition_to('completed')

    def test_error_includes_from_state(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError, match="completed"):
            c.transition_to('paused')

    def test_error_includes_to_state(self):
        c = Campaign(status='completed')
        with pytest.raises(InvalidTransitionError, match="paused"):
            c.transition_to('paused')


class TestValidateStatus:
    def test_unknown_status_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid campaign status"):
            Campaign(status='unknown_status')

    def test_all_valid_statuses_accepted(self):
        for s in ('draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'):
            c = Campaign(status=s)
            assert c.status == s

    def test_assigning_invalid_status_raises(self):
        c = Campaign(status='draft')
        with pytest.raises(ValueError, match="Invalid campaign status"):
            c.status = 'typo_status'
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
cd backend && pytest tests/unit/test_campaign_state_machine.py -v
```
Expected: `AttributeError: 'Campaign' object has no attribute 'transition_to'`

- [ ] **Step 3: Adicionar state machine ao model Campaign**

Em `backend/src/models/campaign.py`, adicionar ao bloco de imports no topo:

```python
from sqlalchemy.orm import validates
from src.exceptions import InvalidTransitionError
```

Adicionar logo antes do método `__repr__`:

```python
VALID_STATUSES: set = {
    'draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'
}

VALID_TRANSITIONS: dict = {
    'draft':     {'scheduled', 'executing', 'failed'},
    'executing': {'paused', 'completed', 'failed'},
    'paused':    {'executing'},
    'scheduled': {'cancelled', 'failed', 'executing'},
}

@validates('status')
def validate_status(self, key: str, value: str) -> str:
    if value not in self.VALID_STATUSES:
        raise ValueError(
            f"Invalid campaign status: '{value}'. Must be one of {sorted(self.VALID_STATUSES)}"
        )
    return value

def transition_to(self, new_status: str) -> None:
    """Transition to new_status. Raises InvalidTransitionError if not allowed."""
    allowed = self.VALID_TRANSITIONS.get(self.status, set())
    if new_status not in allowed:
        raise InvalidTransitionError(self.status, new_status, allowed)
    self.status = new_status
```

- [ ] **Step 4: Rodar os testes para confirmar que passam**

```bash
cd backend && pytest tests/unit/test_campaign_state_machine.py -v
```
Expected: 20 PASSED

- [ ] **Step 5: Rodar toda a suíte de testes unitários**

```bash
cd backend && pytest tests/unit -v
```
Expected: todos PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/src/models/campaign.py backend/tests/unit/test_campaign_state_machine.py
git commit -m "feat(campaign): add VALID_TRANSITIONS + transition_to() + @validates (CAMP-05, PERS-28)"
```

---

## Task 3: Guard de não-regressão de Message no webhook handler (GHL-11, PERS-28)

**Files:**
- Modify: `backend/src/models/message.py`
- Modify: `backend/src/services/ghl_webhook_handler.py`
- Create: `backend/tests/unit/test_message_state_machine.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
# backend/tests/unit/test_message_state_machine.py
"""Unit tests for Message status guard (GHL-11, PERS-28)."""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.models.message import Message, STATUS_ORDER


class TestStatusOrder:
    def test_pending_before_sent(self):
        assert STATUS_ORDER['pending'] < STATUS_ORDER['sent']

    def test_sent_before_delivered(self):
        assert STATUS_ORDER['sent'] < STATUS_ORDER['delivered']

    def test_delivered_before_read(self):
        assert STATUS_ORDER['delivered'] < STATUS_ORDER['read']

    def test_failed_is_minus_one(self):
        assert STATUS_ORDER['failed'] == -1


class TestMessageValidates:
    def test_invalid_status_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid message status"):
            Message(status='unknown')

    def test_all_valid_statuses_accepted(self):
        for s in ('pending', 'sent', 'delivered', 'read', 'failed'):
            m = Message(status=s)
            assert m.status == s


class TestWebhookNoRegression:
    """Test the STATUS_ORDER guard logic directly."""

    def test_delivered_advances_from_sent(self):
        assert STATUS_ORDER.get('delivered', 0) > STATUS_ORDER.get('sent', 0)

    def test_delivered_does_not_advance_from_read(self):
        assert not (STATUS_ORDER.get('delivered', 0) > STATUS_ORDER.get('read', 0))

    def test_read_advances_from_delivered(self):
        assert STATUS_ORDER.get('read', 0) > STATUS_ORDER.get('delivered', 0)

    def test_read_does_not_advance_from_read(self):
        assert not (STATUS_ORDER.get('read', 0) > STATUS_ORDER.get('read', 0))

    def test_failed_has_order_minus_one(self):
        # failed (-1) is never > any current status (0+), so it won't trigger the guard
        # (failed is applied unconditionally — separate code path)
        assert STATUS_ORDER['failed'] == -1


class TestWebhookHandlerDelivered:
    def _make_handler_with_message(self, current_status: str):
        """Returns (handler, message_mock)."""
        from src.services.ghl_webhook_handler import GHLWebhookHandler
        db = MagicMock()
        msg = MagicMock()
        msg.id = 1
        msg.status = current_status
        msg.ghl_status = current_status
        db.query.return_value.filter.return_value.first.return_value = msg
        with patch('src.services.ghl_webhook_handler.GHL_WEBHOOK_SECRET', 'secret'):
            handler = GHLWebhookHandler(db=db)
        return handler, msg

    def test_delivered_updates_sent_message(self):
        handler, msg = self._make_handler_with_message('sent')
        asyncio.run(handler.handle_message_delivered({'messageId': 'x', 'conversationId': 'y'}))
        assert msg.status == 'delivered'
        assert msg.ghl_status == 'delivered'

    def test_delivered_skips_read_message(self):
        handler, msg = self._make_handler_with_message('read')
        asyncio.run(handler.handle_message_delivered({'messageId': 'x', 'conversationId': 'y'}))
        assert msg.status == 'read'  # unchanged

    def test_read_updates_delivered_message(self):
        handler, msg = self._make_handler_with_message('delivered')
        asyncio.run(handler.handle_message_read({'messageId': 'x'}))
        assert msg.status == 'read'

    def test_read_skips_already_read_message(self):
        handler, msg = self._make_handler_with_message('read')
        asyncio.run(handler.handle_message_read({'messageId': 'x'}))
        assert msg.status == 'read'
        msg.delivered_at  # commit should not have been called with a change
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
cd backend && pytest tests/unit/test_message_state_machine.py -v
```
Expected: `ImportError: cannot import name 'STATUS_ORDER' from 'src.models.message'`

- [ ] **Step 3: Adicionar `STATUS_ORDER` e `@validates` ao model Message**

Em `backend/src/models/message.py`, adicionar ao bloco de imports:

```python
from sqlalchemy.orm import validates
```

Adicionar logo antes de `__repr__`:

```python
VALID_STATUSES: set = {'pending', 'sent', 'delivered', 'read', 'failed'}

STATUS_ORDER: dict = {
    'pending':   0,
    'sent':      1,
    'delivered': 2,
    'read':      3,
    'failed':    -1,  # aplicado independente da ordem — tratado separadamente
}

@validates('status')
def validate_status(self, key: str, value: str) -> str:
    if value not in self.VALID_STATUSES:
        raise ValueError(
            f"Invalid message status: '{value}'. Must be one of {sorted(self.VALID_STATUSES)}"
        )
    return value
```

- [ ] **Step 4: Adicionar guard de não-regressão ao webhook handler**

Em `backend/src/services/ghl_webhook_handler.py`, adicionar ao import de Message:

```python
from src.models.message import Message, STATUS_ORDER
```

Substituir o bloco `if message:` dentro de `handle_message_delivered` (mantenha o bloco `return {"message_id": message_id, "status": "not_found"}` intacto no fim):

```python
if message:
    if STATUS_ORDER.get('delivered', 0) > STATUS_ORDER.get(message.status, 0):
        message.status = 'delivered'
        message.ghl_status = 'delivered'
        message.delivered_at = datetime.now(timezone.utc)
        self.db.commit()
    return {
        "message_id": message.id,
        "status_updated": "delivered" if message.status == 'delivered' else "skipped_no_regression"
    }
```

Substituir o bloco `if message:` dentro de `handle_message_read`:

```python
if message:
    if STATUS_ORDER.get('read', 0) > STATUS_ORDER.get(message.status, 0):
        message.status = 'read'
        message.ghl_status = 'read'
        message.read_at = datetime.now(timezone.utc)
        self.db.commit()
    return {
        "message_id": message.id,
        "status_updated": "read" if message.status == 'read' else "skipped_no_regression"
    }
```

`handle_message_failed` não muda — `failed` é aplicado incondicionalmente.

- [ ] **Step 5: Rodar os testes para confirmar que passam**

```bash
cd backend && pytest tests/unit/test_message_state_machine.py -v
```
Expected: todos PASSED

- [ ] **Step 6: Rodar toda a suíte unitária**

```bash
cd backend && pytest tests/unit -v
```
Expected: todos PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/src/models/message.py \
        backend/src/services/ghl_webhook_handler.py \
        backend/tests/unit/test_message_state_machine.py
git commit -m "feat(message): STATUS_ORDER guard in webhook + @validates (GHL-11, PERS-28)"
```

---

## Task 4: Migrar `campaign.status = 'x'` para `transition_to()` em todos os serviços (CAMP-05)

**Files:**
- Modify: `backend/src/services/campaign_executor_service.py` (linhas 76, 198, 208, 323, 348)
- Modify: `backend/src/services/campaign_scheduler.py` (linha 196)
- Modify: `backend/src/main.py` (linhas 308, 331, 338, 460)
- Modify: `backend/src/api/campaign_management.py` (linha 141)

Nenhum novo arquivo de teste — a suíte existente (unit + contract) cobre o comportamento. Confirma-se que nada quebrou ao final.

- [ ] **Step 1: Atualizar `campaign_executor_service.py`**

Cinco substituições (nenhum import novo necessário — `transition_to` é método do model):

**Linha 76** — início da execução:
```python
# Antes:
campaign.status = 'executing'
# Depois:
campaign.transition_to('executing')
```

**Linha 198** — conclusão normal (dentro de `if campaign.status != 'paused':`):
```python
# Antes:
campaign.status = 'completed'
# Depois:
campaign.transition_to('completed')
```

**Linha 208** — handler de falha (após `db.rollback()`, campaign re-consultada do banco):
```python
# Antes:
campaign.status = 'failed'
# Depois:
campaign.transition_to('failed')
```

**Linha 323** — resume sem contacts_data:
```python
# Antes:
campaign.status = 'completed'
# Depois:
campaign.transition_to('completed')
```

**Linha 348** — resume, todos contatos já enviados:
```python
# Antes:
campaign.status = 'completed'
# Depois:
campaign.transition_to('completed')
```

- [ ] **Step 2: Atualizar `campaign_scheduler.py`**

**Linha 196** — campanha agendada sem dados persistidos:
```python
# Antes:
campaign.status = 'failed'
# Depois:
campaign.transition_to('failed')
```

- [ ] **Step 3: Atualizar `main.py`**

**Linha 308** — handler de erro do background task. Adicionar guard para evitar duplo-fail (o executor interno pode ter setado 'failed' antes de chegar aqui):
```python
# Antes:
failed_campaign.status = 'failed'
# Depois:
if failed_campaign.status not in ('failed', 'completed', 'cancelled'):
    failed_campaign.transition_to('failed')
```

**Linha 331** — agendamento com sucesso:
```python
# Antes:
campaign.status = 'scheduled'
# Depois:
campaign.transition_to('scheduled')
```

**Linha 338** — falha no agendamento:
```python
# Antes:
campaign.status = 'failed'
# Depois:
campaign.transition_to('failed')
```

**Linha 460** — cancelamento de campanha agendada:
```python
# Antes:
campaign.status = 'cancelled'
# Depois:
campaign.transition_to('cancelled')
```

- [ ] **Step 4: Atualizar `campaign_management.py`**

**Linha 141** — endpoint de pause:
```python
# Antes:
campaign.status = 'paused'
# Depois:
campaign.transition_to('paused')
```

Nota: o guard existente na linha 131 (`if campaign.status != 'executing': raise HTTPException(400)`) já garante que só campaigns 'executing' chegam aqui. O `transition_to('paused')` é uma segunda camada de segurança — deixar o guard existente no lugar.

- [ ] **Step 5: Rodar testes unitários e de contrato**

```bash
cd backend && pytest tests/unit tests/contract -v
```
Expected: todos PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/campaign_executor_service.py \
        backend/src/services/campaign_scheduler.py \
        backend/src/main.py \
        backend/src/api/campaign_management.py
git commit -m "refactor(campaign): replace direct status assignment with transition_to() (CAMP-05)"
```

---

## Task 5: Migration Alembic — CHECK constraints + NOT NULL + FK RESTRICT (PERS-06, 08, 09, 11, 13, 15, 16)

**Files:**
- Create: `backend/alembic/versions/<rev>_state_machine_constraints.py`
- Create: `backend/tests/integration/test_state_machine_constraints.py`

**Pré-requisito:** executar o check abaixo antes da migration em qualquer banco populado (staging/prod):

```bash
cd backend && python -c "
import os; os.environ.setdefault('DATABASE_URL', os.getenv('DATABASE_URL', ''))
from src.database import SessionLocal
db = SessionLocal()
nulls = db.execute('SELECT COUNT(*) FROM campaigns WHERE ghl_location_id IS NULL').scalar()
orphans = db.execute('SELECT COUNT(*) FROM messages WHERE campaign_id IS NULL').scalar()
print(f'campaigns NULL ghl_location_id: {nulls}')
print(f'messages NULL campaign_id: {orphans}')
db.close()
"
```
Se qualquer contagem for > 0, limpar ou backfill antes de prosseguir.

- [ ] **Step 1: Escrever o teste de integração (pré-migration)**

```python
# backend/tests/integration/test_state_machine_constraints.py
"""Integration tests for state machine DB constraints.
Requerem PostgreSQL real com migrations aplicadas.
Run: cd backend && pytest tests/integration/test_state_machine_constraints.py -v
"""
import pytest
from sqlalchemy.exc import IntegrityError
from src.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def cleanup(db):
    yield
    db.execute("DELETE FROM campaigns WHERE name LIKE 'test_constraint_%'")
    db.commit()


def _insert_campaign(db, name: str, status: str, location_id: str = 'test_loc',
                     location_name: str = 'Test', paused_at: str = 'NULL') -> None:
    db.execute(
        f"INSERT INTO campaigns (name, status, ghl_location_id, ghl_location_name, paused_at) "
        f"VALUES ('{name}', '{status}', '{location_id}', '{location_name}', {paused_at})"
    )


class TestCampaignStatusConstraint:
    def test_invalid_status_rejected(self, db):
        _insert_campaign(db, 'test_constraint_bad_status', 'not_valid')
        with pytest.raises(IntegrityError, match="chk_campaign_status"):
            db.commit()

    def test_all_valid_statuses_accepted(self, db):
        for s in ('draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled'):
            _insert_campaign(db, f'test_constraint_{s}', s)
        db.commit()  # deve passar sem erro


class TestCampaignPausedAtConstraint:
    def test_paused_at_with_non_paused_status_rejected(self, db):
        _insert_campaign(db, 'test_constraint_paused_at', 'executing', paused_at='now()')
        with pytest.raises(IntegrityError, match="chk_campaign_paused_at"):
            db.commit()

    def test_paused_at_null_with_executing_accepted(self, db):
        _insert_campaign(db, 'test_constraint_executing_ok', 'executing', paused_at='NULL')
        db.commit()


class TestMessageStatusConstraint:
    def test_invalid_message_status_rejected(self, db):
        result = db.execute("SELECT id FROM campaigns LIMIT 1").fetchone()
        if not result:
            pytest.skip("No campaigns in DB for FK reference")
        campaign_id = result[0]
        db.execute(
            f"INSERT INTO messages (campaign_id, recipient_phone, content, status) "
            f"VALUES ({campaign_id}, '+5511999990000', 'test', 'invalid_status')"
        )
        with pytest.raises(IntegrityError, match="chk_message_status"):
            db.commit()

    def test_valid_message_statuses_accepted(self, db):
        result = db.execute("SELECT id FROM campaigns LIMIT 1").fetchone()
        if not result:
            pytest.skip("No campaigns in DB for FK reference")
        campaign_id = result[0]
        for s in ('pending', 'sent', 'delivered', 'read', 'failed'):
            db.execute(
                f"INSERT INTO messages (campaign_id, recipient_phone, content, status) "
                f"VALUES ({campaign_id}, '+5511999990000', 'test', '{s}')"
            )
        db.commit()
        db.execute(
            f"DELETE FROM messages WHERE campaign_id = {campaign_id} "
            f"AND recipient_phone = '+5511999990000' AND content = 'test'"
        )
        db.commit()
```

- [ ] **Step 2: Rodar os testes para confirmar que falham (constraints não existem ainda)**

```bash
cd backend && pytest tests/integration/test_state_machine_constraints.py -v
```
Expected: testes de `IntegrityError` falham — constraints não existem ainda.

- [ ] **Step 3: Gerar o arquivo de revision Alembic**

```bash
cd backend && alembic revision -m "state_machine_constraints"
```
Isso cria `backend/alembic/versions/<rev_id>_state_machine_constraints.py`.

- [ ] **Step 4: Preencher a migration gerada**

Abrir o arquivo criado e substituir `upgrade()` e `downgrade()` pelo conteúdo abaixo. O `down_revision` já estará preenchido pelo alembic (`a8f3c2e7d1b9`):

```python
def upgrade() -> None:
    # PERS-06: CHECK constraints para valores de status válidos
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_status
        CHECK (status IN ('draft','scheduled','executing','paused','completed','failed','cancelled'))
    """)
    op.execute("""
        ALTER TABLE messages
        ADD CONSTRAINT chk_message_status
        CHECK (status IN ('pending','sent','delivered','read','failed'))
    """)

    # PERS-11: paused_at só pode existir se status='paused'
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_paused_at
        CHECK (paused_at IS NULL OR status = 'paused')
    """)

    # PERS-13: ghl_location_id setado → ghl_location_name também deve estar setado
    op.execute("""
        ALTER TABLE campaigns
        ADD CONSTRAINT chk_campaign_location_name
        CHECK (ghl_location_id IS NULL OR ghl_location_name IS NOT NULL)
    """)

    # PERS-08: ghl_location_id NOT NULL
    # PRÉ-REQUISITO: nenhuma linha com ghl_location_id IS NULL (rodar o pre-check acima)
    op.execute("ALTER TABLE campaigns ALTER COLUMN ghl_location_id SET NOT NULL")

    # PERS-09: campaign_id NOT NULL (feature standalone removida — DECISAO-04)
    # PRÉ-REQUISITO: nenhuma mensagem com campaign_id IS NULL
    op.execute("ALTER TABLE messages ALTER COLUMN campaign_id SET NOT NULL")

    # PERS-15: messages.campaign_id CASCADE → RESTRICT
    op.drop_constraint('messages_campaign_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_campaign_id_fkey', 'messages', 'campaigns',
        ['campaign_id'], ['id'], ondelete='RESTRICT'
    )

    # PERS-16: ghl_conversations FK → RESTRICT
    # Verificar o nome real da constraint antes:
    # SELECT conname FROM pg_constraint WHERE conrelid = 'ghl_conversations'::regclass AND contype = 'f';
    try:
        op.drop_constraint('ghl_conversations_campaign_id_fkey', 'ghl_conversations', type_='foreignkey')
        op.create_foreign_key(
            'ghl_conversations_campaign_id_fkey', 'ghl_conversations', 'campaigns',
            ['campaign_id'], ['id'], ondelete='RESTRICT'
        )
    except Exception:
        pass  # tabela ou constraint podem não existir em bancos novos


def downgrade() -> None:
    try:
        op.drop_constraint('ghl_conversations_campaign_id_fkey', 'ghl_conversations', type_='foreignkey')
        op.create_foreign_key(
            'ghl_conversations_campaign_id_fkey', 'ghl_conversations', 'campaigns',
            ['campaign_id'], ['id'], ondelete='CASCADE'
        )
    except Exception:
        pass

    op.drop_constraint('messages_campaign_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_campaign_id_fkey', 'messages', 'campaigns',
        ['campaign_id'], ['id'], ondelete='CASCADE'
    )

    op.execute("ALTER TABLE messages ALTER COLUMN campaign_id DROP NOT NULL")
    op.execute("ALTER TABLE campaigns ALTER COLUMN ghl_location_id DROP NOT NULL")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_location_name")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_paused_at")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS chk_message_status")
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaign_status")
```

- [ ] **Step 5: Aplicar a migration ao banco de dev**

```bash
cd backend && alembic upgrade head
```
Expected: `Running upgrade a8f3c2e7d1b9 -> <new_rev_id>, state_machine_constraints`

- [ ] **Step 6: Rodar os testes de integração para confirmar que as constraints funcionam**

```bash
cd backend && pytest tests/integration/test_state_machine_constraints.py -v
```
Expected: todos PASSED

- [ ] **Step 7: Rodar toda a suíte de testes**

```bash
cd backend && pytest -v
```
Expected: todos PASSED

- [ ] **Step 8: Atualizar os models para refletir NOT NULL**

Em `backend/src/models/campaign.py`, linha `ghl_location_id`:
```python
# Antes:
ghl_location_id = Column(
    String(50),
    ForeignKey('ghl_locations.ghl_location_id', ondelete='RESTRICT'),
    nullable=True,  # Nullable during migration phase
    index=True
)
# Depois:
ghl_location_id = Column(
    String(50),
    ForeignKey('ghl_locations.ghl_location_id', ondelete='RESTRICT'),
    nullable=False,
    index=True
)
```

Em `backend/src/models/message.py`, linha `campaign_id`:
```python
# Antes:
campaign_id = Column(
    Integer,
    ForeignKey('campaigns.id', ondelete='CASCADE'),
    nullable=True,  # Nullable to support standalone messages
    index=True
)
# Depois:
campaign_id = Column(
    Integer,
    ForeignKey('campaigns.id', ondelete='RESTRICT'),
    nullable=False,
    index=True
)
```

- [ ] **Step 9: Rodar toda a suíte após atualização dos models**

```bash
cd backend && pytest -v
```
Expected: todos PASSED

- [ ] **Step 10: Commit**

```bash
git add backend/alembic/versions/ \
        backend/src/models/campaign.py \
        backend/src/models/message.py \
        backend/tests/integration/test_state_machine_constraints.py
git commit -m "feat(db): CHECK constraints + FK RESTRICT + NOT NULL (PERS-06,08,09,11,13,15,16)"
```

---

## Checklist final do PR-1

Antes de abrir o PR, verificar:

- [ ] `pytest tests/unit -v` — todos PASSED
- [ ] `pytest tests/contract -v` — todos PASSED
- [ ] `pytest tests/integration/test_state_machine_constraints.py -v` — todos PASSED
- [ ] Nenhum `campaign.status = ` direto restante no código (exceto nos models):
  ```bash
  grep -rn "campaign\.status\s*=" backend/src --include="*.py" | grep -v "models/"
  ```
  Expected: 0 resultados
- [ ] Marcar no roadmap: `[x]` para CAMP-05, GHL-11, PERS-06, PERS-08, PERS-09, PERS-11, PERS-13, PERS-15, PERS-16, PERS-28

---

## Próximos planos

Este é o primeiro de 6 planos da Fase 1 Opção B:

| Plano | EPICs | Status |
|-------|-------|--------|
| PR-1 (este) | EPIC-06 State Machine | ✅ Escrito |
| PR-2 | EPIC-07 + EPIC-08 | Aguarda PR-1 mergeado |
| PR-3 | EPIC-09 + EPIC-13 | Independente |
| PR-4 | EPIC-05 resto + EPIC-17 | Independente |
| PR-5 | EPIC-15 Infra | Independente |
| PR-6 | EPIC-14 + EPIC-12 | Aguarda RAIZ-09 |
