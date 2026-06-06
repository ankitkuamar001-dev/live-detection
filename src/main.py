"""
FastAPI application entry point.

Usage::

    # Development
    uvicorn src.main:app --reload

    # Console script
    live-detection
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from src.api.middleware.cors import setup_cors
from src.api.middleware.metrics import setup_metrics
from src.api.routes import config as config_routes
from src.api.routes import health
from src.api.routes import streams
from src.api.routes import inference
from src.api.routes import telemetry
from src.api.routes import cameras
from src.api.routes import recordings
from src.api.routes import alert_rules
from src.api.routes import settings as settings_routes
from src.core.config import get_settings
from src.core.events import lifespan
from src.core.exceptions import AppException, app_exception_handler


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title="Live Detection System",
        description=(
            "Real-Time Face Mask Detection + Emotion Recognition + Object Detection System. "
            "Provides live video analytics, multi-camera support, alerting, and historical dashboards."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ────────────────────────────────────────────────────────
    settings = get_settings()
    setup_cors(application, origins=settings.cors_origins)

    # ── Exception handlers ───────────────────────────────────────────────
    application.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]

    # ── API routers ──────────────────────────────────────────────────────
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(config_routes.router, prefix="/api/v1")
    application.include_router(streams.router, prefix="/api/v1/ws")
    application.include_router(telemetry.router, prefix="/api/v1/ws")
    application.include_router(inference.router, prefix="/api/v1")
    application.include_router(cameras.router, prefix="/api/v1")
    application.include_router(recordings.router, prefix="/api/v1")
    application.include_router(alert_rules.router, prefix="/api/v1")
    application.include_router(settings_routes.router, prefix="/api/v1")

    # ── Prometheus metrics ───────────────────────────────────────────────
    if settings.monitoring.prometheus_enabled:
        setup_metrics(application)

    return application


# Module-level app instance (used by uvicorn / gunicorn)
app = create_app()


def run() -> None:
    """Console script entry point (``live-detection`` command)."""
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=settings.server.workers if not settings.debug else 1,
    )
