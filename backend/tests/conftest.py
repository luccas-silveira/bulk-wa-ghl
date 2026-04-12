"""
Pytest configuration and fixtures for test suite — AsyncSession + aiosqlite
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

# Set test environment variables before importing app
from cryptography.fernet import Fernet as _Fernet
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("GHL_CLIENT_ID", "test_client_id")
os.environ.setdefault("GHL_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("GHL_REDIRECT_URI", "http://localhost:8000/ghl/oauth/callback")
os.environ.setdefault("GHL_TOKEN_ENCRYPTION_KEY", _Fernet.generate_key().decode())
os.environ.setdefault("GHL_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3001")

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import Base, get_db
from src.main import app

# Import test fixtures
from tests.fixtures import (
    sample_ghl_locations,
    sample_campaign,
    sample_messages,
    mock_ghl_api_response,
    executing_campaign,
    paused_campaign,
    completed_campaign,
    draft_campaign,
    sample_campaign_with_messages,
)

# In-memory async SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingAsyncSession = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Fresh async database session per test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = TestingAsyncSession()
    try:
        yield session
    finally:
        await session.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def override_get_db(db_session):
    """Override the get_db dependency to use test async database."""
    async def _override_get_db():
        yield db_session
    return _override_get_db


@pytest_asyncio.fixture(scope="function")
async def async_client(override_get_db):
    """Async HTTP client for testing FastAPI endpoints."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()
