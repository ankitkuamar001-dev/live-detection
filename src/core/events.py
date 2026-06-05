"""
Application lifecycle management.

Provides the FastAPI ``lifespan`` async context manager that handles
startup and shutdown of shared resources (DB, Redis, logging, etc.).
"""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.core.config import get_settings
from src.core.logging import get_logger, setup_logging
from src.db.engine import create_db_engine, create_session_factory

logger = get_logger(__name__)

# Global startup timestamp for uptime tracking
_start_time: float = 0.0


def get_uptime() -> float:
    """Return seconds since application startup."""
    return time.monotonic() - _start_time


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage the full application lifecycle.

    **Startup**:
        1. Load settings from YAML + env vars.
        2. Setup structured logging.
        3. Create DB engine & session factory.
        4. Ensure storage directories exist.
        5. Log startup banner.

    **Shutdown**:
        1. Dispose DB engine.
        2. Log shutdown message.
    """
    global _start_time
    _start_time = time.monotonic()

    # ── 1. Settings ──────────────────────────────────────────────────────
    settings = get_settings()
    app.state.settings = settings

    # ── 2. Logging ───────────────────────────────────────────────────────
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)

    # ── 3. Database ──────────────────────────────────────────────────────
    try:
        engine = create_db_engine(
            database_url=settings.database.url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            echo=settings.database.echo,
        )
        session_factory = create_session_factory(engine)
        app.state.db_engine = engine
        app.state.session_factory = session_factory
        logger.info("database_connected", url=settings.database.url.split("@")[-1])
    except Exception:
        logger.exception("database_connection_failed")
        # Allow app to start without DB in development
        app.state.db_engine = None
        app.state.session_factory = None

    # ── 4. Storage directories ───────────────────────────────────────────
    for dir_path in (settings.storage.snapshot_dir, settings.storage.video_clip_dir):
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # ── 5. Placeholder state for later phases ────────────────────────────
    app.state.model_registry = None  # Phase 3
    app.state.stream_manager = None  # Phase 2

    # ── 6. Startup banner ────────────────────────────────────────────────
    _log_startup_banner(settings)

    # ── YIELD — application runs ─────────────────────────────────────────
    yield

    # ── SHUTDOWN ─────────────────────────────────────────────────────────
    if app.state.db_engine is not None:
        await app.state.db_engine.dispose()
        logger.info("database_disconnected")

    logger.info(
        "application_shutdown",
        uptime_seconds=round(get_uptime(), 1),
    )


def _log_startup_banner(settings: object) -> None:
    """Log a startup banner with system information."""
    try:
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()
    except Exception:
        cpu_count = -1

    gpu_info = "N/A"
    try:
        from src.utils.gpu import get_gpu_info, is_gpu_available

        if is_gpu_available():
            info = get_gpu_info()
            gpu_info = info.get("name", "Available")
    except ImportError:
        pass

    logger.info(
        "application_startup",
        app=getattr(settings, "app_name", "Live Detection System"),
        version=getattr(settings, "app_version", "1.0.0"),
        python=sys.version.split()[0],
        platform=platform.platform(),
        cpu_count=cpu_count,
        gpu=gpu_info,
        debug=getattr(settings, "debug", False),
    )
