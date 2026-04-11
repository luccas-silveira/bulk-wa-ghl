"""
Application configuration with startup validation.
Import this module early in main.py to fail fast on missing config.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    """Get a required environment variable or raise on startup."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set")
    return value


# Database
DATABASE_URL = _require_env("DATABASE_URL")

# GHL Integration
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID", "")
GHL_ENABLED = bool(GHL_CLIENT_ID)

if GHL_ENABLED:
    GHL_CLIENT_SECRET = _require_env("GHL_CLIENT_SECRET")
    GHL_REDIRECT_URI = _require_env("GHL_REDIRECT_URI")
    GHL_TOKEN_ENCRYPTION_KEY = _require_env("GHL_TOKEN_ENCRYPTION_KEY")
    GHL_WEBHOOK_SECRET = _require_env("GHL_WEBHOOK_SECRET")
else:
    GHL_CLIENT_SECRET = ""
    GHL_REDIRECT_URI = ""
    GHL_TOKEN_ENCRYPTION_KEY = ""
    GHL_WEBHOOK_SECRET = ""

GHL_PRIVATE_TOKEN = os.getenv("GHL_PRIVATE_TOKEN", "")

# Application
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

_cors_env = os.getenv("CORS_ORIGINS")
if not DEBUG and not _cors_env:
    raise RuntimeError(
        "Required environment variable 'CORS_ORIGINS' must be set when DEBUG=False"
    )
CORS_ORIGINS = [
    o.strip()
    for o in (_cors_env or "http://localhost:3001,http://localhost:3000").split(",")
    if o.strip()
]

ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

# Database pool
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))

# GHL API
GHL_API_VERSION = os.getenv("GHL_API_VERSION", "2021-07-28")
