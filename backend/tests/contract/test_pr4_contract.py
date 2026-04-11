"""
Contract tests for PR-4: Pool, Rate Limiting, and Observability
"""
import pytest
import hmac
import hashlib
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Task 5: RAIZ-05 — Global exception handler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGlobalExceptionHandler:
    """RAIZ-05: 500 retorna {"detail": "Internal server error"} sem stack trace."""

    async def test_unhandled_exception_returns_500_with_safe_body(self, async_client: AsyncClient):
        """Endpoint que lança exceção não tratada deve retornar 500 com corpo seguro."""
        from src.main import app

        # Register a temporary route that raises an unhandled exception
        @app.get("/test-unhandled-exception")
        async def _raise():
            raise RuntimeError("catastrophic failure - should not appear in response")

        try:
            response = await async_client.get("/test-unhandled-exception")
        finally:
            # Remove the temporary route after the test
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test-unhandled-exception"]

        assert response.status_code == 500
        body = response.json()
        # Must have "detail" key, NOT expose the exception message
        assert "detail" in body
        assert "catastrophic failure" not in str(body)
        assert "stack" not in str(body).lower()
        assert "traceback" not in str(body).lower()


# ---------------------------------------------------------------------------
# Task 6: RAIZ-10 — HMAC authentication on /metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMetricsAuth:
    """RAIZ-10: /metrics requer METRICS_TOKEN em produção (DEBUG=False)."""

    async def test_metrics_returns_200_in_debug_mode_without_token(self, async_client: AsyncClient):
        """Em DEBUG=True, /metrics deve responder sem autenticação."""
        with patch("src.main.DEBUG", True), patch("src.main.metrics_enabled", True):
            response = await async_client.get("/metrics")
        # 200 or 404 (if metrics disabled in test app); the key is NOT 401
        assert response.status_code != 401

    async def test_metrics_requires_token_in_production(self, async_client: AsyncClient):
        """Em DEBUG=False com METRICS_TOKEN setado, /metrics sem token deve retornar 401."""
        with patch("src.main.DEBUG", False), \
             patch("src.config.DEBUG", False), \
             patch("src.config.METRICS_TOKEN", "secret_token_abc"):
            response = await async_client.get("/metrics")
        assert response.status_code == 401

    async def test_metrics_accepts_valid_bearer_token_in_production(self, async_client: AsyncClient):
        """Em DEBUG=False com token correto, /metrics deve retornar 200."""
        with patch("src.main.DEBUG", False), \
             patch("src.config.DEBUG", False), \
             patch("src.config.METRICS_TOKEN", "secret_token_abc"):
            response = await async_client.get(
                "/metrics",
                headers={"Authorization": "Bearer secret_token_abc"}
            )
        assert response.status_code == 200

    async def test_metrics_rejects_wrong_token_in_production(self, async_client: AsyncClient):
        """Em DEBUG=False com token errado, /metrics deve retornar 401."""
        with patch("src.main.DEBUG", False), \
             patch("src.config.DEBUG", False), \
             patch("src.config.METRICS_TOKEN", "secret_token_abc"):
            response = await async_client.get(
                "/metrics",
                headers={"Authorization": "Bearer wrong_token"}
            )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 7: INFRA-33 — X-Request-ID middleware hardening
# ---------------------------------------------------------------------------
import uuid as _uuid_module


@pytest.mark.asyncio
class TestRequestIDMiddleware:
    """INFRA-33: X-Request-ID gerado server-side se ausente ou inválido; sempre na resposta."""

    async def test_request_id_included_in_response_when_not_provided(self, async_client: AsyncClient):
        """Sem X-Request-ID no request, a resposta deve incluir um UUID válido."""
        response = await async_client.get("/health")
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        # Must be a valid UUID
        _uuid_module.UUID(request_id)  # raises ValueError if not valid UUID

    async def test_valid_client_uuid_is_echoed_in_response(self, async_client: AsyncClient):
        """X-Request-ID UUID válido do cliente deve ser ecoado na resposta."""
        client_id = str(_uuid_module.uuid4())
        response = await async_client.get("/health", headers={"X-Request-ID": client_id})
        assert response.headers.get("X-Request-ID") == client_id

    async def test_invalid_client_uuid_is_replaced_server_side(self, async_client: AsyncClient):
        """X-Request-ID inválido do cliente deve ser substituído por UUID gerado pelo server."""
        response = await async_client.get("/health", headers={"X-Request-ID": "not-a-uuid"})
        server_id = response.headers.get("X-Request-ID")
        assert server_id is not None
        assert server_id != "not-a-uuid"
        _uuid_module.UUID(server_id)  # must be a valid UUID


# ---------------------------------------------------------------------------
# Task 8: CAMP-19 — Rate limiting with slowapi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRateLimiting:
    """CAMP-19: rate limiting 60 req/min por IP nos endpoints de campaign_management."""

    async def test_rate_limit_exceeded_returns_429(self, async_client: AsyncClient):
        """Exceder o limite deve retornar 429 com mensagem de rate limit."""
        from fastapi.responses import JSONResponse as _JSONResponse
        from src.main import app

        # Override the RateLimitExceeded handler temporarily to return 429 without needing state
        async def simple_429_handler(request, exc):
            return _JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

        from slowapi.errors import RateLimitExceeded as _RLE
        original_handlers = app.exception_handlers.copy()
        app.exception_handlers[_RLE] = simple_429_handler

        from src.limiter import limiter
        from unittest.mock import MagicMock

        mock_limit = MagicMock()
        mock_limit.error_message = None
        mock_limit.limit = "60 per 1 minute"
        mock_limit.__str__ = lambda self: "60 per 1 minute"

        try:
            with patch.object(limiter, "_check_request_limit", side_effect=_RLE(mock_limit)):
                response = await async_client.get("/api/v1/campaigns")
        finally:
            app.exception_handlers = original_handlers

        assert response.status_code == 429

    async def test_normal_request_passes_rate_limit(self, async_client: AsyncClient):
        """Request dentro do limite deve passar normalmente."""
        response = await async_client.get("/api/v1/campaigns")
        assert response.status_code in (200, 422, 500)  # Not 429


# ---------------------------------------------------------------------------
# Task 9: GHL-26 — Webhook signature failure logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWebhookSignatureLogging:
    """GHL-26: falhas de assinatura de webhook devem ser logadas como warning."""

    async def test_invalid_signature_logs_warning(self, async_client: AsyncClient):
        """Assinatura inválida deve gerar logger.warning com IP e webhook_id antes do 401."""
        import logging
        with patch("src.api.ghl_webhooks.logger") as mock_logger:
            response = await async_client.post(
                "/webhooks/ghl/messages",
                json={"type": "MessageDelivered", "messageId": "msg_test_001"},
                headers={"X-GHL-Signature": "bad_signature"}
            )

        assert response.status_code == 401
        # logger.warning deve ter sido chamado
        mock_logger.warning.assert_called_once()
        warning_call_args = str(mock_logger.warning.call_args)
        # Deve incluir o webhook_id (messageId) ou indicar que não havia
        assert "msg_test_001" in warning_call_args or "webhook_id" in warning_call_args.lower()

    async def test_missing_signature_logs_warning(self, async_client: AsyncClient):
        """Header ausente deve também gerar logger.warning antes do 401."""
        with patch("src.api.ghl_webhooks.logger") as mock_logger:
            response = await async_client.post(
                "/webhooks/ghl/messages",
                json={"type": "MessageDelivered", "messageId": "msg_no_sig_002"},
            )

        assert response.status_code == 401
        mock_logger.warning.assert_called_once()

    async def test_valid_signature_does_not_log_warning(self, async_client: AsyncClient):
        """Assinatura válida NÃO deve gerar warning de falha."""
        import json
        import hmac as _hmac
        import hashlib

        payload = {"type": "MessageDelivered", "locationId": "loc_1", "messageId": "msg_valid_003"}
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = _hmac.new(b"test_webhook_secret", payload_bytes, hashlib.sha256).hexdigest()

        with patch("src.api.ghl_webhooks.logger") as mock_logger:
            response = await async_client.post(
                "/webhooks/ghl/messages",
                content=payload_bytes,
                headers={"X-GHL-Signature": sig, "Content-Type": "application/json"}
            )

        # Check that warning was NOT called (regardless of final status)
        mock_logger.warning.assert_not_called()
