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
