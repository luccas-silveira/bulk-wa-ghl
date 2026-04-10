# backend/tests/unit/test_config.py
"""
Unit tests for config.py startup validation (EPIC-03).
Uses importlib.reload() because config runs at module level.
"""
import importlib
import os
import pytest


def _reload_config(monkeypatch, env_overrides: dict):
    """Helper: patch env vars and reload config module."""
    import src.config as cfg

    # Ensure DATABASE_URL is always present (already required).
    # Default DEBUG=True so CORS validation doesn't fire in non-CORS tests.
    base = {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "DEBUG": "True",
    }
    base.update(env_overrides)

    # Remove all GHL vars from env first to start clean
    for key in ["GHL_CLIENT_ID", "GHL_CLIENT_SECRET", "GHL_REDIRECT_URI",
                "GHL_TOKEN_ENCRYPTION_KEY", "GHL_WEBHOOK_SECRET",
                "CORS_ORIGINS", "DEBUG"]:
        monkeypatch.delenv(key, raising=False)

    for key, value in base.items():
        monkeypatch.setenv(key, value)

    return importlib.reload(cfg)


class TestGHLEnabledFlag:
    def test_ghl_disabled_when_no_client_id(self, monkeypatch):
        cfg = _reload_config(monkeypatch, {})
        assert cfg.GHL_ENABLED is False

    def test_ghl_enabled_when_client_id_set(self, monkeypatch):
        cfg = _reload_config(monkeypatch, {
            "GHL_CLIENT_ID": "test_id",
            "GHL_CLIENT_SECRET": "test_secret",
            "GHL_REDIRECT_URI": "http://localhost/callback",
            "GHL_TOKEN_ENCRYPTION_KEY": "test_key_32bytes_padded_to_valid_",
            "GHL_WEBHOOK_SECRET": "test_webhook_secret",
        })
        assert cfg.GHL_ENABLED is True


class TestGHLRequiredCreds:
    def test_raises_when_client_id_set_but_no_client_secret(self, monkeypatch):
        with pytest.raises(RuntimeError, match="GHL_CLIENT_SECRET"):
            _reload_config(monkeypatch, {"GHL_CLIENT_ID": "test_id"})

    def test_raises_when_client_id_set_but_no_redirect_uri(self, monkeypatch):
        with pytest.raises(RuntimeError, match="GHL_REDIRECT_URI"):
            _reload_config(monkeypatch, {
                "GHL_CLIENT_ID": "test_id",
                "GHL_CLIENT_SECRET": "test_secret",
            })

    def test_raises_when_client_id_set_but_no_encryption_key(self, monkeypatch):
        with pytest.raises(RuntimeError, match="GHL_TOKEN_ENCRYPTION_KEY"):
            _reload_config(monkeypatch, {
                "GHL_CLIENT_ID": "test_id",
                "GHL_CLIENT_SECRET": "test_secret",
                "GHL_REDIRECT_URI": "http://localhost/callback",
            })

    def test_raises_when_client_id_set_but_no_webhook_secret(self, monkeypatch):
        with pytest.raises(RuntimeError, match="GHL_WEBHOOK_SECRET"):
            _reload_config(monkeypatch, {
                "GHL_CLIENT_ID": "test_id",
                "GHL_CLIENT_SECRET": "test_secret",
                "GHL_REDIRECT_URI": "http://localhost/callback",
                "GHL_TOKEN_ENCRYPTION_KEY": "test_key",
            })

    def test_no_error_when_ghl_not_configured(self, monkeypatch):
        # Should not raise even though GHL creds are absent
        cfg = _reload_config(monkeypatch, {})
        assert cfg.GHL_ENABLED is False
        assert cfg.GHL_TOKEN_ENCRYPTION_KEY == ""
        assert cfg.GHL_WEBHOOK_SECRET == ""


class TestCORSRequirement:
    def test_raises_when_debug_false_and_cors_not_set(self, monkeypatch):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            _reload_config(monkeypatch, {"DEBUG": "False"})

    def test_no_error_when_debug_true_and_cors_not_set(self, monkeypatch):
        # In dev mode, CORS_ORIGINS defaults to localhost
        cfg = _reload_config(monkeypatch, {"DEBUG": "True"})
        assert "http://localhost:3001" in cfg.CORS_ORIGINS

    def test_no_error_when_cors_explicitly_set(self, monkeypatch):
        cfg = _reload_config(monkeypatch, {
            "DEBUG": "False",
            "CORS_ORIGINS": "https://app.example.com",
        })
        assert "https://app.example.com" in cfg.CORS_ORIGINS
