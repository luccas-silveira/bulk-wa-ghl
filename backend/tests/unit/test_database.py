"""
Unit tests for database.py async session factory.
Uses aiosqlite (in-memory) — no real PostgreSQL required.
"""
import pytest
import os
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    """get_db() deve retornar um AsyncSession."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    import importlib
    import src.database as db_module
    importlib.reload(db_module)

    gen = db_module.get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    try:
        await gen.aclose()
    except StopAsyncIteration:
        pass


def test_async_url_conversion():
    """_async_url deve converter todos os prefixos postgresql://."""
    import src.database as db_module
    assert db_module._async_url("postgresql://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"
    assert db_module._async_url("postgres://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"
    assert db_module._async_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"
