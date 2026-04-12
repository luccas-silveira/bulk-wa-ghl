"""
Database configuration — AsyncSession + asyncpg
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.config import DATABASE_URL, DEBUG, DB_POOL_SIZE, DB_MAX_OVERFLOW


def _async_url(url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg:// for async driver."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url  # already has driver or is sqlite+aiosqlite (tests)


engine = create_async_engine(
    _async_url(DATABASE_URL),
    echo=DEBUG,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()

# Backward-compatibility alias — services still importing SessionLocal will
# receive the async factory. Full migration of those call-sites is in Task 2+.
SessionLocal = async_session_factory


async def get_db():
    """FastAPI dependency — yields an AsyncSession, auto-closed on exit."""
    async with async_session_factory() as session:
        yield session
