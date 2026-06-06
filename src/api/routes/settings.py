"""System settings and hardware info API routes."""

from __future__ import annotations

import platform
import os
import shutil
from typing import Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config import get_settings

logger = structlog.get_logger()

router = APIRouter(tags=["Settings"])

# ── Runtime overrides (in-memory) ───────────────────────────────────────

_runtime_overrides: dict = {}


# ── Schemas ─────────────────────────────────────────────────────────────

class RuntimeSettings(BaseModel):
    model_name: str
    confidence_threshold: float
    target_fps: int
    device: str
    debug: bool


class RuntimeSettingsUpdate(BaseModel):
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_fps: Optional[int] = Field(None, ge=1, le=120)


class SystemInfoResponse(BaseModel):
    platform: str
    python_version: str
    cpu_count: int
    total_ram_gb: float
    disk_total_gb: float
    disk_used_gb: float
    disk_usage_percent: float
    gpu_available: bool
    gpu_name: str | None = None


class ModelInfoItem(BaseModel):
    name: str
    type: str
    status: str  # loaded | error | not_found
    device: str
    size: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/settings", response_model=RuntimeSettings)
async def get_runtime_settings():
    """Get current runtime configuration."""
    settings = get_settings()
    return {
        "model_name": _runtime_overrides.get("model_name", settings.detection.model),
        "confidence_threshold": _runtime_overrides.get(
            "confidence_threshold", settings.detection.confidence_threshold
        ),
        "target_fps": _runtime_overrides.get("target_fps", 15),
        "device": settings.detection.device,
        "debug": settings.debug,
    }


@router.put("/settings", response_model=RuntimeSettings)
async def update_runtime_settings(update: RuntimeSettingsUpdate):
    """Update runtime settings (hot-reload without restart)."""
    if update.confidence_threshold is not None:
        _runtime_overrides["confidence_threshold"] = update.confidence_threshold
        logger.info("setting_updated", key="confidence_threshold", value=update.confidence_threshold)
    if update.target_fps is not None:
        _runtime_overrides["target_fps"] = update.target_fps
        logger.info("setting_updated", key="target_fps", value=update.target_fps)
    return await get_runtime_settings()


@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get system hardware information."""
    # RAM
    total_ram_gb = 0.0
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_ram_gb = round(mem.total / (1024 ** 3), 1)
    except ImportError:
        # Fallback for systems without psutil
        total_ram_gb = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3), 1) if hasattr(os, "sysconf") else 0.0

    # Disk
    disk = shutil.disk_usage("/")
    disk_total = round(disk.total / (1024 ** 3), 1)
    disk_used = round(disk.used / (1024 ** 3), 1)
    disk_pct = round((disk.used / disk.total) * 100, 1)

    # GPU
    gpu_available = False
    gpu_name = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_available = True
            gpu_name = "Apple Silicon (MPS)"
    except ImportError:
        pass

    return {
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "total_ram_gb": total_ram_gb,
        "disk_total_gb": disk_total,
        "disk_used_gb": disk_used,
        "disk_usage_percent": disk_pct,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
    }


@router.get("/system/models", response_model=list[ModelInfoItem])
async def get_loaded_models():
    """Get status of all loaded AI models."""
    models = []

    # YOLO object detector
    try:
        from src.detection.model_registry import ModelRegistry
        registry = ModelRegistry()
        models.append({
            "name": "YOLO11n",
            "type": "Object Detection",
            "status": "loaded",
            "device": "cpu",
            "size": "5.6 MB",
        })
    except Exception:
        models.append({
            "name": "YOLO11n",
            "type": "Object Detection",
            "status": "error",
            "device": "cpu",
            "size": None,
        })

    # Face Detector (MediaPipe)
    models.append({
        "name": "MediaPipe Face Detection",
        "type": "Face Detection",
        "status": "loaded",
        "device": "cpu",
        "size": "~2 MB",
    })

    # Emotion Recognizer (HSEmotion)
    models.append({
        "name": "EfficientNet-B0 (HSEmotion)",
        "type": "Emotion Recognition",
        "status": "loaded",
        "device": "cpu",
        "size": "~20 MB",
    })

    # Mask Detector
    mask_path = "models/yolo11n_mask.pt"
    models.append({
        "name": "YOLO11n Mask Detector",
        "type": "Face Mask Detection",
        "status": "loaded" if os.path.exists(mask_path) else "not_found",
        "device": "cpu",
        "size": None,
    })

    return models
