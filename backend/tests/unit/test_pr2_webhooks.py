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
