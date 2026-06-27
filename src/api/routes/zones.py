"""Zone management REST API — CRUD for detection zones."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.detection.zone_detector import ZoneDetector

router = APIRouter(prefix="/zones", tags=["zones"])

# Shared zone detector instance
_zone_detector = ZoneDetector()


def get_zone_detector() -> ZoneDetector:
    """Return the singleton ZoneDetector instance."""
    return _zone_detector


# ── Pydantic schemas ──────────────────────────────────────────────────────

class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    camera_id: str = Field(..., min_length=1)
    polygon: list[list[int]] = Field(..., min_length=3, description="Polygon vertices [[x,y], ...]")
    zone_type: str = Field("exclusion", pattern=r"^(exclusion|monitoring|counting)$")
    is_active: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    polygon: list[list[int]] | None = None
    zone_type: str | None = None
    is_active: bool | None = None


class ZoneResponse(BaseModel):
    id: str
    name: str
    camera_id: str
    polygon: list[list[int]]
    zone_type: str
    is_active: bool


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ZoneResponse])
async def list_zones(camera_id: str | None = None) -> list[dict[str, Any]]:
    """List all zones, optionally filtered by camera_id."""
    zones = _zone_detector.get_zones(camera_id)
    return [
        {
            "id": z.id,
            "name": z.name,
            "camera_id": z.camera_id,
            "polygon": z.polygon,
            "zone_type": z.zone_type,
            "is_active": z.is_active,
        }
        for z in zones
    ]


@router.post("", response_model=ZoneResponse, status_code=201)
async def create_zone(body: ZoneCreate) -> dict[str, Any]:
    """Create a new detection zone."""
    zone_data = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "camera_id": body.camera_id,
        "polygon": body.polygon,
        "zone_type": body.zone_type,
        "is_active": body.is_active,
    }
    zone = _zone_detector.add_zone(zone_data)
    return {
        "id": zone.id,
        "name": zone.name,
        "camera_id": zone.camera_id,
        "polygon": zone.polygon,
        "zone_type": zone.zone_type,
        "is_active": zone.is_active,
    }


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: str, body: ZoneUpdate) -> dict[str, Any]:
    """Update an existing zone."""
    zones = _zone_detector.get_zones()
    target = next((z for z in zones if z.id == zone_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Zone not found")

    if body.name is not None:
        target.name = body.name
    if body.polygon is not None:
        target.polygon = body.polygon
    if body.zone_type is not None:
        target.zone_type = body.zone_type
    if body.is_active is not None:
        target.is_active = body.is_active

    return {
        "id": target.id,
        "name": target.name,
        "camera_id": target.camera_id,
        "polygon": target.polygon,
        "zone_type": target.zone_type,
        "is_active": target.is_active,
    }


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(zone_id: str) -> None:
    """Delete a zone by ID."""
    if not _zone_detector.remove_zone(zone_id):
        raise HTTPException(status_code=404, detail="Zone not found")
