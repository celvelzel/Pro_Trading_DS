"""Async API and sync worker database sessions.

The API uses ``AsyncSession`` while Celery tasks use ``Session``.  Engines are
created lazily and this module never creates tables at import or application
startup; migrations are the only schema authority.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(RuntimeError):
    """Raised when a configured database URL cannot be used."""


def _default_sqlite_path() -> str:
    data_dir = Path(os.getenv("AGENT_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "agent.db")


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """Return the configured SQLAlchemy URL.

    Local development defaults to SQLite so the legacy app remains runnable.
    Docker/production should set ``DATABASE_URL`` to PostgreSQL.
    """

    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        return f"sqlite+aiosqlite:///{_default_sqlite_path()}"
    if value.startswith("postgres://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
    if value.startswith("sqlite:///") and "+aiosqlite" not in value:
        return value.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if not value.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite:///")):
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql://, postgresql+asyncpg://, or sqlite+aiosqlite:///"
        )
    return value


def _sync_url(async_url: str) -> str:
    if async_url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + async_url.removeprefix("postgresql+asyncpg://")
    if async_url.startswith("sqlite+aiosqlite:///"):
        return async_url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    raise DatabaseConfigurationError(f"Unsupported async database URL: {async_url}")


@lru_cache(maxsize=1)
def async_engine():
    return create_async_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def sync_engine():
    return create_engine(_sync_url(get_database_url()), pool_pre_ping=True)


async_session_factory = async_sessionmaker(async_engine(), expire_on_commit=False)
sync_session_factory = sessionmaker(bind=sync_engine(), expire_on_commit=False)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one request-scoped async session."""

    async with async_session_factory() as session:
        yield session


def get_sync_session() -> Iterator[Session]:
    """Worker/service helper yielding one transaction-scoped sync session."""

    with sync_session_factory() as session:
        yield session
