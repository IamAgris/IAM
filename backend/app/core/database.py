"""Database configuration - SQLAlchemy async engine and session.

Engine creation is lazy: importing the app for OpenAPI/schema generation must not
require a DBAPI driver (which may be blocked by host application-control policies).
"""

from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Build database URL if not explicitly provided
if settings.database_url:
    DATABASE_URL = settings.database_url
else:
    DATABASE_URL = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

# Base class for models (defined before engine so metadata is always importable)
Base = declarative_base()

_engine = None
_AsyncSessionLocal = None


def get_engine() -> Any:
    """Lazily create the async engine (avoids DBAPI import at module import)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=settings.app_debug,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> Any:
    """Lazily create the session factory."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


# Backwards-compatible module attributes (lazy proxies)
class _LazyEngine:
    def __getattr__(self, name: Any) -> Any:
        return getattr(get_engine(), name)

    def begin(self) -> Any:
        return get_engine().begin()

    def dispose(self) -> Any:
        return get_engine().dispose()


engine = _LazyEngine()


class _LazySessionLocal:
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return get_session_factory()(*args, **kwargs)


AsyncSessionLocal = _LazySessionLocal()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    async with get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()
