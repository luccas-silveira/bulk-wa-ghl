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
