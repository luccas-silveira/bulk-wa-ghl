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
