"""
Runtime configuration endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Request

from src.core.config import PROJECT_ROOT

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/", summary="Current configuration (non-sensitive)")
async def get_config(request: Request) -> dict[str, Any]:
    """Return the current runtime configuration with secrets redacted."""
    settings = request.app.state.settings
    cfg = {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "server": settings.server.model_dump(),
        "models": {
            "device": settings.models.device,
            "object_detection": settings.models.object_detection.model_dump(),
            "mask_detection": settings.models.mask_detection.model_dump(),
            "emotion_recognition": settings.models.emotion_recognition.model_dump(),
        },
        "tracking": settings.tracking.model_dump(),
        "video": settings.video.model_dump(),
        "alerts": settings.alerts.model_dump(),
        "storage": settings.storage.model_dump(),
        "monitoring": settings.monitoring.model_dump(),
    }
    return cfg


@router.get("/cameras", summary="Camera configurations")
async def get_cameras() -> dict[str, Any]:
    """Load and return camera definitions from cameras.yaml."""
    cameras_path = PROJECT_ROOT / "configs" / "cameras.yaml"
    if not cameras_path.exists():
        return {"cameras": []}
    with open(cameras_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data
