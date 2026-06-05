"""Database engine, base classes, and mixins for SQLAlchemy 2.0 async."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# --------------------------------------------------------------------------- #
# Naming convention for auto-generated constraint names                       #
# --------------------------------------------------------------------------- #
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# --------------------------------------------------------------------------- #
# Declarative base                                                            #
# --------------------------------------------------------------------------- #
class Base(DeclarativeBase):
    """Application-wide declarative base with a naming-convention-aware metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# --------------------------------------------------------------------------- #
# Mixins                                                                      #
# --------------------------------------------------------------------------- #
class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )


class UUIDMixin:
    """Adds a UUID-based ``id`` primary key (stored as a 36-char string)."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )


# --------------------------------------------------------------------------- #
# Engine & session helpers                                                    #
# --------------------------------------------------------------------------- #
def create_db_engine(
    database_url: str,
    *,
    pool_size: int = 20,
    max_overflow: int = 10,
    echo: bool = False,
) -> AsyncEngine:
    """Create an :class:`AsyncEngine` for *database_url*.

    Handles both PostgreSQL (``asyncpg``) and SQLite (``aiosqlite``) URLs
    transparently.

    Args:
        database_url: An async-compatible database URL, e.g.
            ``postgresql+asyncpg://user:pass@host/db`` or
            ``sqlite+aiosqlite:///path.db``.
        pool_size: Core pool size (PostgreSQL only).
        max_overflow: Max connections above *pool_size* (PostgreSQL only).
        echo: If ``True``, emit SQL to the default log handler.

    Returns:
        A configured :class:`AsyncEngine`.
    """
    kwargs: dict[str, Any] = {"echo": echo}

    if database_url.startswith("sqlite"):
        # SQLite doesn't support pool_size / max_overflow; use StaticPool
        # for single-connection async testing or NullPool for lightweight use.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
        kwargs["pool_pre_ping"] = True

    return create_async_engine(database_url, **kwargs)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return an :class:`async_sessionmaker` bound to *engine*.

    Sessions created by this factory have ``expire_on_commit=False`` so that
    ORM-loaded attributes remain accessible after a commit without requiring
    a refresh.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables defined on :data:`Base.metadata`.

    This is intended for development / testing bootstrapping.  In production,
    prefer Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
