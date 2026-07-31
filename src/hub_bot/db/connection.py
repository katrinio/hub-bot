"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from hub_bot.settings import get_database_url

logger = logging.getLogger(__name__)


class _SessionFactoryProxy:
    """Late-bound session factory exported for package compatibility."""

    def __init__(self) -> None:
        self._factory: sessionmaker[Any] | None = None

    def configure(self, factory: sessionmaker[Any]) -> None:
        self._factory = factory

    def __bool__(self) -> bool:
        return self._factory is not None

    def __call__(self) -> AsyncSession:
        if self._factory is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._factory()


class _DatabaseState:
    def __init__(self) -> None:
        self.async_engine = None
        self.session_factory = _SessionFactoryProxy()


_state = _DatabaseState()
AsyncSessionLocal = _state.session_factory


async def init_db() -> None:
    """Initialize database: create engine and session factory.

    Must be called once at application startup, before creating any sessions.
    """
    database_url = get_database_url()
    logger.info("Initializing database: %s", database_url)

    _state.async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    _state.session_factory.configure(sessionmaker(
        _state.async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    ))

    logger.info("Database engine initialized (schema managed by Alembic)")


async def close_db() -> None:
    """Close database connection pool.

    Must be called once at application shutdown.
    """
    if _state.async_engine:
        await _state.async_engine.dispose()
        logger.info("Database connection closed")


@asynccontextmanager
async def get_session():
    """Get a database session for use with context manager.

    Usage:
        async with get_session() as session:
            await UserRepository.get_by_id(session, user_id)
    """
    if not _state.session_factory:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = _state.session_factory()
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
