# backend/tests/unit/test_pr2_webhooks.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


def _make_client():
    """TestClient para os endpoints de webhook sem DB real."""
    from src.main import app, get_db
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=False), app


class TestWebhookBodySizeGuard:
    """GHL-21: payloads >1MB devem retornar 413."""

    def test_oversized_body_returns_413(self):
        """Body maior que 1MB → HTTP 413."""
        client, app = _make_client()
        # 1MB + 1 byte
        oversized_body = b"x" * (1_000_001)
        resp = client.post(
            "/webhooks/ghl/messages",
            content=oversized_body,
            headers={"X-GHL-Signature": "anysig", "Content-Type": "application/json"},
        )
        app.dependency_overrides.clear()
        assert resp.status_code == 413, f"Expected 413, got {resp.status_code}"

    def test_body_at_limit_is_not_rejected(self):
        """Body exatamente 1MB não é rejeitado pelo guard."""
        client, app = _make_client()
        body_at_limit = b"x" * 1_000_000
        resp = client.post(
            "/webhooks/ghl/messages",
            content=body_at_limit,
            headers={"X-GHL-Signature": "anysig", "Content-Type": "application/json"},
        )
        app.dependency_overrides.clear()
        # Will fail sig validation (401) but NOT 413
        assert resp.status_code != 413, f"Got unexpected 413 for body at exact limit"


class TestWebhookSignatureWarning:
    """GHL-26: falha de assinatura deve emitir logger.warning com IP."""

    def test_invalid_signature_logs_warning_with_ip(self):
        """Assinatura inválida → logger.warning chamado com client IP."""
        from src.main import app, get_db
        import json

        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db

        client = TestClient(app, raise_server_exceptions=False)

        with patch("src.api.ghl_webhooks.logger") as mock_logger:
            payload = json.dumps({"type": "MessageDelivered", "messageId": "m1"}).encode()
            resp = client.post(
                "/webhooks/ghl/messages",
                content=payload,
                headers={
                    "X-GHL-Signature": "invalid_sig",
                    "Content-Type": "application/json"
                },
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 401
        # Warning must have been called at least once
        assert mock_logger.warning.called, "Expected logger.warning to be called on sig failure"
        # Check the call args
        warning_call = mock_logger.warning.call_args
        # Verify message contains signature-related keyword
        assert any(
            "sig" in str(a).lower() or "auth" in str(a).lower() or "invalid" in str(a).lower()
            for a in mock_logger.warning.call_args_list
        ), f"Warning did not mention signature failure: {mock_logger.warning.call_args_list}"
        # Verify extra dict has client_ip
        assert warning_call.kwargs.get("extra", {}).get("client_ip") is not None, (
            "Expected extra={'client_ip': ...} in logger.warning call"
        )


class TestWebhookPayloadSchema:
    """GHL-13: WebhookPayload Pydantic valida campos obrigatórios."""

    def test_missing_location_id_returns_422(self):
        """Payload sem locationId → HTTP 422 (schema validation)."""
        from src.main import app, get_db
        import json

        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)

        with patch("src.api.ghl_webhooks.GHLWebhookHandler") as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.validate_signature.return_value = True
            from unittest.mock import AsyncMock
            mock_handler.process_webhook = AsyncMock(
                return_value={"status": "processed", "webhook_id": "wh_1"}
            )
            mock_handler_cls.return_value = mock_handler

            payload = json.dumps({
                "type": "MessageDelivered",
                # locationId missing
                "messageId": "m1"
            }).encode()
            resp = client.post(
                "/webhooks/ghl/messages",
                content=payload,
                headers={"X-GHL-Signature": "fake", "Content-Type": "application/json"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_valid_payload_is_accepted(self):
        """Payload com campos obrigatórios passa pela validação de schema."""
        from src.main import app, get_db
        import json

        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)

        with patch("src.api.ghl_webhooks.GHLWebhookHandler") as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.validate_signature.return_value = True
            from unittest.mock import AsyncMock
            mock_handler.process_webhook = AsyncMock(
                return_value={"status": "processed", "webhook_id": "wh_1"}
            )
            mock_handler_cls.return_value = mock_handler

            payload = json.dumps({
                "type": "MessageDelivered",
                "locationId": "loc_abc",
                "messageId": "m1",
            }).encode()
            resp = client.post(
                "/webhooks/ghl/messages",
                content=payload,
                headers={"X-GHL-Signature": "fake", "Content-Type": "application/json"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code in (200, 201), f"Expected 200, got {resp.status_code}: {resp.text}"


class TestWebhookCleanupJob:
    """GHL-10: job APScheduler deleta processed_webhooks mais velhos que 30 dias."""

    def test_cleanup_job_is_registered(self):
        """O job 'cleanup_old_webhooks' está registrado no scheduler após startup."""
        from src.main import scheduler

        jobs = [j.id for j in scheduler.scheduler.get_jobs()]
        assert "cleanup_old_webhooks" in jobs, (
            f"Expected 'cleanup_old_webhooks' job in scheduler, found: {jobs}"
        )

    def test_cleanup_job_runs_with_interval_trigger(self):
        """O job de cleanup usa IntervalTrigger (não DateTrigger)."""
        from src.main import scheduler
        from apscheduler.triggers.interval import IntervalTrigger

        for job in scheduler.scheduler.get_jobs():
            if job.id == "cleanup_old_webhooks":
                assert isinstance(job.trigger, IntervalTrigger), (
                    f"Expected IntervalTrigger, got {type(job.trigger)}"
                )
                return
        pytest.fail("cleanup_old_webhooks job not found")
