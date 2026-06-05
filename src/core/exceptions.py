"""
Application exception hierarchy.

Every domain-specific error extends ``AppException`` so that
a single FastAPI exception handler can catch them all and return
a consistent JSON error envelope.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------
class AppException(Exception):
    """Base application exception with HTTP status code and optional details."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class ConfigurationError(AppException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Configuration error", **kwargs: Any) -> None:
        super().__init__(message, status_code=500, **kwargs)


# ---------------------------------------------------------------------------
# Model / Inference
# ---------------------------------------------------------------------------
class ModelLoadError(AppException):
    """Raised when an AI model fails to load."""

    def __init__(self, message: str = "Failed to load model", **kwargs: Any) -> None:
        super().__init__(message, status_code=503, **kwargs)


class ModelInferenceError(AppException):
    """Raised when model inference fails."""

    def __init__(self, message: str = "Model inference failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=500, **kwargs)


# ---------------------------------------------------------------------------
# Video / Camera
# ---------------------------------------------------------------------------
class VideoStreamError(AppException):
    """Raised when a video stream cannot be opened or drops unexpectedly."""

    def __init__(self, message: str = "Video stream error", **kwargs: Any) -> None:
        super().__init__(message, status_code=503, **kwargs)


class CameraNotFoundError(AppException):
    """Raised when a requested camera ID does not exist."""

    def __init__(self, message: str = "Camera not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class DatabaseError(AppException):
    """Raised on database connection or query failures."""

    def __init__(self, message: str = "Database error", **kwargs: Any) -> None:
        super().__init__(message, status_code=500, **kwargs)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
class AlertDeliveryError(AppException):
    """Raised when an alert fails to be delivered to a channel."""

    def __init__(self, message: str = "Alert delivery failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=502, **kwargs)


# ---------------------------------------------------------------------------
# Validation / Auth / General
# ---------------------------------------------------------------------------
class ValidationError(AppException):
    """Raised for request payload validation errors."""

    def __init__(self, message: str = "Validation error", **kwargs: Any) -> None:
        super().__init__(message, status_code=422, **kwargs)


class RateLimitExceededError(AppException):
    """Raised when a client exceeds the configured rate limit."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(message, status_code=429, **kwargs)


class AuthenticationError(AppException):
    """Raised for authentication failures."""

    def __init__(self, message: str = "Authentication required", **kwargs: Any) -> None:
        super().__init__(message, status_code=401, **kwargs)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


# ---------------------------------------------------------------------------
# FastAPI exception handler
# ---------------------------------------------------------------------------
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Global exception handler for :class:`AppException` and its subclasses.

    Returns a consistent JSON error envelope::

        {
            "error": {
                "type": "CameraNotFoundError",
                "message": "Camera cam_99 not found",
                "details": {}
            }
        }
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": type(exc).__name__,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
