"""Shared async database infrastructure for all petclinic services.

Provides:
- ``Base`` — SQLAlchemy 2.0 DeclarativeBase for model definitions
- ``create_engine`` — async engine factory
- ``create_session_factory`` — async session-maker factory
- ``get_db_dependency`` — FastAPI ``Depends()``-compatible session provider
"""

from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base.  Each service imports this and defines models on it."""


def create_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = False,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(database_url, echo=echo, pool_pre_ping=pool_pre_ping)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to *engine*."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_db_dependency(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Return an async-generator callable suitable for ``Depends(get_db)``."""

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _get_db
