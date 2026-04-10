"""
Pytest configuration and fixtures for test suite
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Set test environment variables before importing app
# All GHL vars must be set before config.py runs (GHL_ENABLED = bool(GHL_CLIENT_ID))
from cryptography.fernet import Fernet as _Fernet
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("DEBUG", "True")  # allows CORS_ORIGINS to default in tests
os.environ.setdefault("GHL_CLIENT_ID", "test_client_id")
os.environ.setdefault("GHL_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("GHL_REDIRECT_URI", "http://localhost:8000/ghl/oauth/callback")
os.environ.setdefault("GHL_TOKEN_ENCRYPTION_KEY", _Fernet.generate_key().decode())
os.environ.setdefault("GHL_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3001")

# Import app and database
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
    sample_campaign_with_messages
)


# Create in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override the get_db dependency to use test database"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    return _override_get_db


@pytest_asyncio.fixture(scope="function")
async def async_client(override_get_db):
    """Create an async HTTP client for testing FastAPI endpoints"""
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
