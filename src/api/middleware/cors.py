"""CORS middleware setup.

Configures Cross-Origin Resource Sharing so the browser-based
dashboard and external integrations can reach the API.
"""

from __future__ import annotations

from fastapi import FastAPI


def setup_cors(app: FastAPI, origins: list[str] | None = None) -> None:
    """Attach CORS middleware to the FastAPI application.

    Args:
        app: The FastAPI application instance.
        origins: Allowed origin patterns.  Defaults to ``["*"]`` (allow all).
    """
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
