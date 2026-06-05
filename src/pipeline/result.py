from pydantic import BaseModel
from typing import List, Optional

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class ObjectDetectionResult(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None
    mask_status: Optional[str] = None  # with_mask, without_mask, mask_weared_incorrect
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None

class FrameInferenceResult(BaseModel):
    camera_id: str
    timestamp: float
    detections: List[ObjectDetectionResult]
    latency_ms: float
