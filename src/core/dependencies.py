"""
FastAPI dependency injection functions.

All dependencies pull shared state from ``request.app.state`` which is
populated during the lifespan startup phase.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings

# Optional API key header
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_settings(request: Request) -> Settings:
    """Return the cached application settings."""
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.

    Commits on success, rolls back on exception, and always closes.
    """
    session_factory = request.app.state.session_factory
    if session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_model_registry(request: Request) -> Any:
    """
    Return the model registry (loaded during Phase 3).

    Returns ``None`` if models are not yet loaded.
    """
    return getattr(request.app.state, "model_registry", None)


async def get_stream_manager(request: Request) -> Any:
    """
    Return the stream manager (loaded during Phase 2).

    Returns ``None`` if the stream manager is not yet initialised.
    """
    return getattr(request.app.state, "stream_manager", None)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> bool:
    """
    Validate the ``X-API-Key`` header if an API key is configured.

    If no API key is set in the application settings, all requests are allowed.
    """
    settings: Settings = request.app.state.settings
    if settings.api_key is None:
        # No key configured — allow all requests
        return True
    if api_key is None or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
