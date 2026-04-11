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
