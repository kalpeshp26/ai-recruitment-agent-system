"""
--- FILE: backend/database/db.py ---

Async SQLAlchemy engine and session factory. Provides `get_db` FastAPI
dependency and `init_db` helper to create tables at startup when using
SQLite for local development.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings
from shared.db.database import Base


_engine: AsyncEngine | None = None
_async_sessionmaker: async_sessionmaker | None = None


def _detect_db_is_sqlite(url: str) -> bool:
    """Return True if DATABASE_URL refers to SQLite."""
    return url.startswith("sqlite") or "aiosqlite" in url


def get_engine() -> AsyncEngine:
    """Create or return the global async engine.

    The engine is created lazily on first call using `settings.DATABASE_URL`.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.SQLALCHEMY_ECHO,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Create or return the global async sessionmaker."""
    global _async_sessionmaker
    if _async_sessionmaker is None:
        _async_sessionmaker = async_sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _async_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async SQLAlchemy session.

    Usage in routers:
        async def handler(db: AsyncSession = Depends(get_db)):
            async with db.begin():
                ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database schema for development environments.

    For SQLite (local dev) this will create tables using SQLAlchemy's
    metadata. For production (PostgreSQL) migrations are expected and
    this function performs no destructive actions.
    """
    engine = get_engine()
    # Only auto-create tables for SQLite/dev to avoid interfering with migrations.
    if _detect_db_is_sqlite(settings.DATABASE_URL):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


__all__ = ["get_engine", "get_session_factory", "get_db", "init_db"]
