"""
SQLAlchemy async database engine and session management.
Uses SQLite for development, PostgreSQL for production.
"""
import uuid
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL


if "sqlite" in DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"timeout": 30})
else:
    engine = create_async_engine(DATABASE_URL, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def generate_id() -> str:
    return str(uuid.uuid4())[:12]


def _quote_identifier(connection, identifier: str) -> str:
    return connection.dialect.identifier_preparer.quote(identifier)


def _sync_missing_columns(sync_connection) -> None:
    """Add any model columns that are missing from an existing table.

    This keeps older databases usable when the ORM model has evolved.
    """
    inspector = inspect(sync_connection)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            column_sql = f"{_quote_identifier(sync_connection, column.name)} {column.type.compile(dialect=sync_connection.dialect)}"
            alter_sql = f"ALTER TABLE {_quote_identifier(sync_connection, table.name)} ADD COLUMN {column_sql}"
            sync_connection.execute(text(alter_sql))


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables and reconcile missing columns on startup."""
    import shared.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sync_missing_columns)
    print("SUCCESS: Database tables created")

from contextlib import asynccontextmanager

@asynccontextmanager
async def db_session():
    """Context manager for database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Sync session for compatibility with existing code
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create sync engine for sync operations
sync_database_url = DATABASE_URL
if 'sqlite+aiosqlite' in sync_database_url:
    sync_database_url = sync_database_url.replace('sqlite+aiosqlite', 'sqlite')
elif '+asyncpg' in sync_database_url:
    sync_database_url = sync_database_url.replace('+asyncpg', '')

sync_engine = create_engine(sync_database_url, echo=False)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

from contextlib import contextmanager

@contextmanager
def db_session():
    """Sync context manager for database sessions."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_sync():
    """Compatibility generator for tests and sync code that expect a
    synchronous generator yielding a SQLAlchemy session.

    Many existing tests call `db_gen = get_db(); session = next(db_gen)` so
    we provide this thin wrapper around the `SyncSessionLocal` factory.
    Note: this is intentionally NOT named `get_db` so it doesn't override the
    async FastAPI dependency `get_db` used by endpoints.
    """
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()