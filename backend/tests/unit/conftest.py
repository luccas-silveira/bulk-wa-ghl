# backend/tests/unit/conftest.py
"""
Minimal conftest for unit tests.
Sets DATABASE_URL before src.config is imported so the module can be loaded
at collection time. Individual tests override vars via monkeypatch + reload.
"""
import os

# Provide a dummy DATABASE_URL so src.config can be imported without error.
# Tests that call importlib.reload(src.config) will override this via monkeypatch.
os.environ.setdefault("DATABASE_URL", "postgresql://unit_test:unit_test@localhost/unit_test")
