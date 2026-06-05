"""Detection-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates with confidence."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = Field(ge=0.0, le=1.0)


class DetectionResult(BaseModel):
    """Single detection result from a frame."""
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    track_id: int | None = None
    detection_type: str  # 'object', 'mask', 'emotion'
    metadata: dict[str, Any] | None = None


class FrameDetectionResponse(BaseModel):
    """All detections from a single frame."""
    camera_id: str
    frame_number: int
    timestamp: datetime
    detections: list[DetectionResult]
    processing_time_ms: float
    fps: float


class DetectionEventCreate(BaseModel):
    """Schema for creating a detection event in the database."""
    camera_id: str
    detection_type: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: dict[str, float] | None = None
    track_id: int | None = None
    snapshot_path: str | None = None
    metadata: dict[str, Any] | None = None


class DetectionEventResponse(DetectionEventCreate):
    """Detection event as returned from the database."""
    id: int
    detected_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list[Any]
    total: int
    page: int
    page_size: int
