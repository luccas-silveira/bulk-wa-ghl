"""
Unit tests for PR-4: Connection Pool, Batch Commits, and Observability
"""
import importlib
import os
import pytest
from unittest.mock import MagicMock, patch, call
import re


# ---------------------------------------------------------------------------
# Task 1: PERS-21 — Pool defaults
# ---------------------------------------------------------------------------

class TestPoolDefaults:
    """PERS-21: DB_POOL_SIZE default 20, DB_MAX_OVERFLOW default 40"""

    def _reload_config(self, monkeypatch, env_overrides=None):
        import src.config as cfg
        base = {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "DEBUG": "True",
        }
        if env_overrides:
            base.update(env_overrides)
        for key in ["DB_POOL_SIZE", "DB_MAX_OVERFLOW",
                    "GHL_CLIENT_ID", "CORS_ORIGINS"]:
            monkeypatch.delenv(key, raising=False)
        for k, v in base.items():
            monkeypatch.setenv(k, v)
        return importlib.reload(cfg)

    def test_pool_size_default_is_20(self, monkeypatch):
        """DB_POOL_SIZE deve ser 20 quando não definido."""
        cfg = self._reload_config(monkeypatch)
        assert cfg.DB_POOL_SIZE == 20

    def test_max_overflow_default_is_40(self, monkeypatch):
        """DB_MAX_OVERFLOW deve ser 40 quando não definido."""
        cfg = self._reload_config(monkeypatch)
        assert cfg.DB_MAX_OVERFLOW == 40

    def test_pool_size_overridable_via_env(self, monkeypatch):
        """DB_POOL_SIZE deve respeitar override via env."""
        cfg = self._reload_config(monkeypatch, {"DB_POOL_SIZE": "5"})
        assert cfg.DB_POOL_SIZE == 5

    def test_max_overflow_overridable_via_env(self, monkeypatch):
        """DB_MAX_OVERFLOW deve respeitar override via env."""
        cfg = self._reload_config(monkeypatch, {"DB_MAX_OVERFLOW": "10"})
        assert cfg.DB_MAX_OVERFLOW == 10


# ---------------------------------------------------------------------------
# Task 2: PERS-24 — Batch commits
# ---------------------------------------------------------------------------


class TestBatchCommits:
    """PERS-24: commit a cada BATCH_COMMIT_SIZE mensagens, não por mensagem individual."""

    def test_batch_commit_size_constant_exists(self):
        """CampaignExecutorService deve ter BATCH_COMMIT_SIZE = 10."""
        from src.services.campaign_executor_service import CampaignExecutorService
        assert hasattr(CampaignExecutorService, "BATCH_COMMIT_SIZE")
        assert CampaignExecutorService.BATCH_COMMIT_SIZE == 10

    def test_commit_called_once_per_batch_not_per_message(self):
        """Dado 10 mensagens enviadas com BATCH_COMMIT_SIZE=10, commit deve ser chamado 1 vez (não 10)."""
        import asyncio
        from unittest.mock import MagicMock, AsyncMock, patch
        from src.services.campaign_executor_service import CampaignExecutorService

        db = MagicMock()

        # Campaign mock
        campaign = MagicMock()
        campaign.id = 1
        campaign.name = "Test"
        campaign.status = "draft"
        campaign.sending_speed = "fast"
        campaign.ghl_location_id = "loc_1"
        campaign.get_user_ids_list.return_value = ["user_1"]

        # Simulate pause check: first call (with_for_update) returns the campaign,
        # subsequent pause-check calls also return campaign (not paused).
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = campaign
        db.query.return_value.filter.return_value.first.return_value = campaign

        svc = CampaignExecutorService(db)

        contacts = [{"phone_number": f"+5511{i:08d}", "name": f"Contact {i}"} for i in range(10)]
        messages_template = [{"text": "Hello"}]

        # Mock the sub-services so no real HTTP calls happen
        async def fake_get_or_create(location_id, phone, name, email, assigned_to):
            return {"id": f"contact_{phone}"}

        async def fake_send_message(location_id, contact_id, message_text, media_url):
            return {"messageId": "msg_1", "conversationId": "conv_1", "status": "sent"}

        svc.contacts_service.get_or_create_contact = fake_get_or_create
        svc.conversations_service.send_message = fake_send_message

        with patch("asyncio.sleep", new_callable=AsyncMock):
            asyncio.get_event_loop().run_until_complete(
                svc.execute_campaign(
                    campaign_id=1,
                    contacts=contacts,
                    messages_template=messages_template,
                )
            )

        # With 10 messages and BATCH_COMMIT_SIZE=10, internal per-message commits
        # should NOT have been called 10 times — only batch boundaries + final.
        # We count only the commits inside the message loop (not the final commit
        # in the `finally` block or the status-update commit at the start).
        # The simplest assertion: total commits must be < 10 + 2 (status + final).
        commit_call_count = db.commit.call_count
        # 10 individual commits would give ≥ 12 total; with batching: status_commit(1)
        # + batch_commit(1) + finally_commit(1) = 3 total.
        assert commit_call_count <= 5, (
            f"Expected ≤ 5 commits for 10 messages with batch_size=10, got {commit_call_count}"
        )


# ---------------------------------------------------------------------------
# Task 3: PERS-19 — Pool metrics
# ---------------------------------------------------------------------------


class TestPoolMetrics:
    """PERS-19: métricas de pool expostas via Gauge do Prometheus."""

    def test_pool_gauges_exist_in_metrics_module(self):
        """db_pool_size, db_pool_checkedout, db_pool_queue_size devem existir em metrics.py."""
        from src import metrics
        assert hasattr(metrics, "db_pool_size_gauge")
        assert hasattr(metrics, "db_pool_checkedout_gauge")
        assert hasattr(metrics, "db_pool_queue_size_gauge")

    def test_update_pool_metrics_parses_status_string(self):
        """update_pool_metrics() deve parsear engine.pool.status() e atualizar os Gauges."""
        from src.metrics import update_pool_metrics, db_pool_size_gauge, db_pool_checkedout_gauge, db_pool_queue_size_gauge
        from unittest.mock import MagicMock

        fake_engine = MagicMock()
        fake_engine.pool.status.return_value = (
            "Pool size: 20  Connections in pool: 3 "
            "Current Overflow: 0 Current Checked out connections: 2"
        )

        update_pool_metrics(fake_engine)

        # Read gauge values via _value.get() — prometheus_client internal
        assert db_pool_size_gauge._value.get() == 20.0
        assert db_pool_checkedout_gauge._value.get() == 2.0
        assert db_pool_queue_size_gauge._value.get() == 3.0


# ---------------------------------------------------------------------------
# Task 4: RAIZ-04 — Phone masking filter
# ---------------------------------------------------------------------------


class TestPhoneMaskFilter:
    """RAIZ-04: PhoneMaskFilter mascara E.164 antes de emitir log."""

    def test_filter_class_exists(self):
        from src.logging_config import PhoneMaskFilter
        assert PhoneMaskFilter is not None

    def test_masks_e164_in_message(self):
        import logging
        from src.logging_config import PhoneMaskFilter

        f = PhoneMaskFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Processing +5511999999999 (João)", args=(), exc_info=None
        )
        result = f.filter(record)
        assert result is True
        assert "+5511999999999" not in record.getMessage()
        assert "+***" in record.getMessage()

    def test_masks_multiple_phones_in_one_message(self):
        import logging
        from src.logging_config import PhoneMaskFilter

        f = PhoneMaskFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Sending from +12025550100 to +5521988887777",
            args=(), exc_info=None
        )
        f.filter(record)
        assert "+12025550100" not in record.getMessage()
        assert "+5521988887777" not in record.getMessage()
        assert record.getMessage().count("+***") == 2

    def test_preserves_message_without_phone(self):
        import logging
        from src.logging_config import PhoneMaskFilter

        f = PhoneMaskFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Campaign 42 completed successfully", args=(), exc_info=None
        )
        original = record.getMessage()
        f.filter(record)
        assert record.getMessage() == original

    def test_filter_applied_to_root_handler(self):
        """PhoneMaskFilter deve estar instalado no handler do root logger após setup_logging()."""
        import logging
        from src.logging_config import setup_logging, PhoneMaskFilter
        setup_logging()
        root = logging.getLogger()
        all_filters = [f for h in root.handlers for f in h.filters]
        assert any(isinstance(f, PhoneMaskFilter) for f in all_filters)
