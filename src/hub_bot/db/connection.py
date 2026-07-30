"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from hub_bot.db.models import Base
from hub_bot.settings import get_database_url

logger = logging.getLogger(__name__)

# Lazy initialization
_async_engine = None
AsyncSessionLocal = None


async def init_db() -> None:
    """Initialize database: create engine and session factory.

    Must be called once at application startup, before creating any sessions.
    """
    global _async_engine, AsyncSessionLocal

    database_url = get_database_url()
    logger.info("Initializing database: %s", database_url)

    _async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    AsyncSessionLocal = sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Verify connection
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database connection pool.

    Must be called once at application shutdown.
    """
    global _async_engine

    if _async_engine:
        await _async_engine.dispose()
        logger.info("Database connection closed")


@asynccontextmanager
async def get_session():
    """Get a database session for use with context manager.

    Usage:
        async with get_session() as session:
            await UserRepository.get_by_id(session, user_id)
    """
    if not AsyncSessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def ensure_db_directory() -> None:
    """Ensure SQLite data directory exists."""
    database_url = get_database_url()

    # Parse SQLite path from URL (sqlite+aiosqlite:///./data/hub.db)
    if "sqlite" in database_url:
        # Extract path: sqlite+aiosqlite:///./data/hub.db → ./data/hub.db
        path_str = database_url.split("///")[-1]
        db_path = Path(path_str)

        db_dir = db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Ensured SQLite directory exists: %s", db_dir)
