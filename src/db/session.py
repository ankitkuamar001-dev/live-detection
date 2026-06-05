"""Async session dependency / context-manager helper."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`AsyncSession`, committing on success or rolling back on error.

    Typical usage with FastAPI::

        @app.get("/items")
        async def list_items(
            session: AsyncSession = Depends(get_session_dep),
        ) -> list[Item]:
            ...

    The caller is expected to *partially apply* or wrap this generator so
    that ``session_factory`` is already bound (e.g. via ``functools.partial``
    or a closure).

    Args:
        session_factory: An :class:`async_sessionmaker` instance.

    Yields:
        An open :class:`AsyncSession`.
    """
    session: AsyncSession = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
