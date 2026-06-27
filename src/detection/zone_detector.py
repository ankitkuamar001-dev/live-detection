"""
Zone-based intrusion detection engine.

Checks if detected object centroids fall within user-defined polygon zones
and fires alert events for restricted zone intrusions.

Usage::

    detector = ZoneDetector()
    detector.load_zones([
        {"id": "z1", "name": "Restricted Area", "polygon": [[x,y], ...], "zone_type": "exclusion"}
    ])
    violations = detector.check_detections(detections)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ZoneConfig:
    """Represents a single detection zone."""
    id: str
    name: str
    polygon: list[list[int]]  # [[x1,y1], [x2,y2], ...]
    zone_type: str = "exclusion"  # exclusion, monitoring, counting
    camera_id: str = ""
    is_active: bool = True

    @property
    def np_polygon(self) -> np.ndarray:
        """Return polygon as numpy array for cv2 operations."""
        return np.array(self.polygon, dtype=np.int32)


@dataclass
class ZoneViolation:
    """A detected violation of a zone boundary."""
    zone_id: str
    zone_name: str
    zone_type: str
    detection: dict[str, Any]
    centroid: tuple[int, int]


class ZoneDetector:
    """Checks detection centroids against configured polygon zones."""

    def __init__(self) -> None:
        self._zones: dict[str, ZoneConfig] = {}

    def load_zones(self, zones: list[dict[str, Any]]) -> None:
        """Load zone configurations from a list of dicts."""
        self._zones.clear()
        for z in zones:
            zone = ZoneConfig(
                id=z["id"],
                name=z["name"],
                polygon=z["polygon"],
                zone_type=z.get("zone_type", "exclusion"),
                camera_id=z.get("camera_id", ""),
                is_active=z.get("is_active", True),
            )
            self._zones[zone.id] = zone
        logger.info("zones_loaded", count=len(self._zones))

    def add_zone(self, zone_data: dict[str, Any]) -> ZoneConfig:
        """Add a single zone."""
        zone = ZoneConfig(
            id=zone_data["id"],
            name=zone_data["name"],
            polygon=zone_data["polygon"],
            zone_type=zone_data.get("zone_type", "exclusion"),
            camera_id=zone_data.get("camera_id", ""),
            is_active=zone_data.get("is_active", True),
        )
        self._zones[zone.id] = zone
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone by ID."""
        return self._zones.pop(zone_id, None) is not None

    def get_zones(self, camera_id: str | None = None) -> list[ZoneConfig]:
        """Return all zones, optionally filtered by camera_id."""
        zones = list(self._zones.values())
        if camera_id:
            zones = [z for z in zones if z.camera_id == camera_id]
        return zones

    def check_detections(
        self,
        detections: list[dict[str, Any]],
        camera_id: str = "",
    ) -> list[ZoneViolation]:
        """Check all detections against active zones for the given camera.

        Args:
            detections: List of detection dicts with ``bbox`` key [x1, y1, x2, y2].
            camera_id: Only check zones belonging to this camera.

        Returns:
            List of :class:`ZoneViolation` for any detected intrusions.
        """
        violations: list[ZoneViolation] = []
        active_zones = [
            z for z in self._zones.values()
            if z.is_active and (not camera_id or z.camera_id == camera_id)
        ]

        if not active_zones:
            return violations

        for det in detections:
            bbox = det.get("bbox")
            if not bbox or len(bbox) < 4:
                continue

            # Compute centroid
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            centroid = (cx, cy)

            for zone in active_zones:
                # cv2.pointPolygonTest returns > 0 if inside, 0 on edge, < 0 outside
                result = cv2.pointPolygonTest(zone.np_polygon, centroid, False)

                if result >= 0:  # Inside or on boundary
                    violations.append(ZoneViolation(
                        zone_id=zone.id,
                        zone_name=zone.name,
                        zone_type=zone.type if hasattr(zone, "type") else zone.zone_type,
                        detection=det,
                        centroid=centroid,
                    ))

        return violations

    def draw_zones(self, frame: np.ndarray, camera_id: str = "") -> np.ndarray:
        """Draw zone polygons on a frame for visualization.

        Args:
            frame: BGR image.
            camera_id: Only draw zones for this camera.

        Returns:
            Annotated frame with zone overlays.
        """
        annotated = frame.copy()
        active_zones = [
            z for z in self._zones.values()
            if z.is_active and (not camera_id or z.camera_id == camera_id)
        ]

        colors = {
            "exclusion": (0, 0, 255),     # Red
            "monitoring": (0, 255, 255),  # Yellow
            "counting": (255, 0, 0),      # Blue
        }

        for zone in active_zones:
            color = colors.get(zone.zone_type, (0, 255, 0))
            pts = zone.np_polygon

            # Semi-transparent fill
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)

            # Border
            cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=2)

            # Label
            text_pos = (pts[0][0], pts[0][1] - 10)
            cv2.putText(
                annotated, f"{zone.name} ({zone.zone_type})",
                text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
            )

        return annotated

    @property
    def zone_count(self) -> int:
        """Number of loaded zones."""
        return len(self._zones)
