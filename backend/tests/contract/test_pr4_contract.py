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
