"""Camera management API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter(tags=["Cameras"])

# ── In-memory camera store ──────────────────────────────────────────────

_cameras: dict[str, dict] = {}


def _init_default_cameras() -> None:
    """Seed with a default webcam entry."""
    if not _cameras:
        cam_id = str(uuid.uuid4())
        _cameras[cam_id] = {
            "id": cam_id,
            "name": "Built-in Webcam",
            "source_url": "0",
            "source_type": "webcam",
            "is_active": True,
            "status": "online",
            "fps": 30,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


_init_default_cameras()


# ── Schemas ─────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_url: str = Field(..., min_length=1)
    source_type: str = Field("webcam", pattern=r"^(webcam|rtsp|ip|file)$")


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    source_url: Optional[str] = None
    source_type: Optional[str] = Field(None, pattern=r"^(webcam|rtsp|ip|file)$")
    is_active: Optional[bool] = None


class CameraResponse(BaseModel):
    id: str
    name: str
    source_url: str
    source_type: str
    is_active: bool
    status: str = "online"
    fps: Optional[int] = None
    created_at: str


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras():
    """List all configured cameras."""
    return list(_cameras.values())


@router.post("/cameras", response_model=CameraResponse, status_code=201)
async def add_camera(camera: CameraCreate):
    """Add a new camera source."""
    cam_id = str(uuid.uuid4())
    entry = {
        "id": cam_id,
        "name": camera.name,
        "source_url": camera.source_url,
        "source_type": camera.source_type,
        "is_active": True,
        "status": "offline",
        "fps": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _cameras[cam_id] = entry
    logger.info("camera_added", camera_id=cam_id, name=camera.name)
    return entry


@router.get("/cameras/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str):
    """Get a single camera by ID."""
    if camera_id not in _cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _cameras[camera_id]


@router.put("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: str, update: CameraUpdate):
    """Update camera configuration."""
    if camera_id not in _cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam = _cameras[camera_id]
    if update.name is not None:
        cam["name"] = update.name
    if update.source_url is not None:
        cam["source_url"] = update.source_url
    if update.source_type is not None:
        cam["source_type"] = update.source_type
    if update.is_active is not None:
        cam["is_active"] = update.is_active
    logger.info("camera_updated", camera_id=camera_id)
    return cam


@router.delete("/cameras/{camera_id}", status_code=204)
async def delete_camera(camera_id: str):
    """Remove a camera."""
    if camera_id not in _cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    del _cameras[camera_id]
    logger.info("camera_deleted", camera_id=camera_id)


@router.get("/cameras/{camera_id}/status")
async def camera_status(camera_id: str):
    """Check camera health / connection status."""
    if camera_id not in _cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam = _cameras[camera_id]
    return {
        "id": cam["id"],
        "name": cam["name"],
        "status": cam["status"],
        "is_active": cam["is_active"],
    }
