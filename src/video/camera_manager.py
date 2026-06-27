"""
Multi-camera pipeline manager.

Manages concurrent VideoStream + PipelineProcessor instances per camera,
supporting start/stop/list operations for dynamic camera management.

Usage::

    manager = CameraManager()
    manager.start_camera("cam-1", source=0, event_logger=logger)
    stream = manager.get_processor("cam-1")
    manager.stop_camera("cam-1")
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.detection.object_detector import ObjectDetector
from src.detection.mask_detector import MaskDetector
from src.pipeline.processor import PipelineProcessor
from src.video.stream import VideoStream

logger = structlog.get_logger(__name__)


@dataclass
class CameraState:
    """State of a running camera pipeline."""
    camera_id: str
    source: int | str
    name: str
    stream: VideoStream
    processor: PipelineProcessor
    is_running: bool = True


class CameraManager:
    """Manages multiple concurrent camera pipelines.

    Thread-safe singleton for starting, stopping, and querying camera pipelines.
    """

    def __init__(self) -> None:
        self._cameras: dict[str, CameraState] = {}
        self._lock = threading.Lock()
        self._shared_detector: ObjectDetector | None = None
        self._shared_mask_detector: MaskDetector | None = None

    def _get_detector(self) -> ObjectDetector:
        """Lazy-initialize shared object detector (YOLO model loaded once)."""
        if self._shared_detector is None:
            self._shared_detector = ObjectDetector()
        return self._shared_detector

    def _get_mask_detector(self) -> MaskDetector:
        """Lazy-initialize shared mask detector."""
        if self._shared_mask_detector is None:
            self._shared_mask_detector = MaskDetector()
        return self._shared_mask_detector

    def start_camera(
        self,
        camera_id: str,
        source: int | str = 0,
        name: str = "",
        event_logger: Any = None,
    ) -> CameraState:
        """Start a new camera pipeline.

        Args:
            camera_id: Unique identifier for this camera.
            source: OpenCV video source (0 for webcam, RTSP URL, file path).
            name: Human-readable name.
            event_logger: Optional EventLogger for DB persistence.

        Returns:
            The new CameraState.

        Raises:
            RuntimeError: If camera is already running or source fails to open.
        """
        with self._lock:
            if camera_id in self._cameras:
                existing = self._cameras[camera_id]
                if existing.is_running:
                    logger.warning("camera_already_running", camera_id=camera_id)
                    return existing

            try:
                stream = VideoStream(source=source, name=name or camera_id)
                stream.start()

                processor = PipelineProcessor(
                    detector=self._get_detector(),
                    mask_detector=self._get_mask_detector(),
                    event_logger=event_logger,
                    camera_id=camera_id,
                )

                state = CameraState(
                    camera_id=camera_id,
                    source=source,
                    name=name or camera_id,
                    stream=stream,
                    processor=processor,
                    is_running=True,
                )
                self._cameras[camera_id] = state

                logger.info(
                    "camera_started",
                    camera_id=camera_id,
                    source=str(source),
                    name=state.name,
                )
                return state

            except Exception:
                logger.exception("camera_start_failed", camera_id=camera_id, source=str(source))
                raise

    def stop_camera(self, camera_id: str) -> bool:
        """Stop a running camera pipeline.

        Returns:
            True if camera was stopped, False if not found.
        """
        with self._lock:
            state = self._cameras.get(camera_id)
            if not state:
                return False

            try:
                state.stream.stop()
                state.is_running = False
                logger.info("camera_stopped", camera_id=camera_id)
            except Exception:
                logger.exception("camera_stop_error", camera_id=camera_id)

            del self._cameras[camera_id]
            return True

    def get_camera(self, camera_id: str) -> CameraState | None:
        """Get camera state by ID."""
        with self._lock:
            return self._cameras.get(camera_id)

    def get_processor(self, camera_id: str) -> PipelineProcessor | None:
        """Get the PipelineProcessor for a specific camera."""
        state = self.get_camera(camera_id)
        return state.processor if state else None

    def get_stream(self, camera_id: str) -> VideoStream | None:
        """Get the VideoStream for a specific camera."""
        state = self.get_camera(camera_id)
        return state.stream if state else None

    def list_active(self) -> list[dict[str, Any]]:
        """Return info about all active cameras."""
        with self._lock:
            return [
                {
                    "camera_id": s.camera_id,
                    "source": str(s.source),
                    "name": s.name,
                    "is_running": s.is_running,
                    "fps": s.stream.fps,
                    "width": s.stream.width,
                    "height": s.stream.height,
                }
                for s in self._cameras.values()
                if s.is_running
            ]

    def stop_all(self) -> int:
        """Stop all running cameras. Returns count of cameras stopped."""
        with self._lock:
            camera_ids = list(self._cameras.keys())

        count = 0
        for cid in camera_ids:
            if self.stop_camera(cid):
                count += 1
        return count

    @property
    def active_count(self) -> int:
        """Number of currently active cameras."""
        with self._lock:
            return sum(1 for s in self._cameras.values() if s.is_running)
