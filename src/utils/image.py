"""Image processing utilities built on OpenCV and NumPy.

Provides helpers for decoding, encoding, resizing, cropping, and
annotating video frames in the detection pipeline.
"""

from __future__ import annotations

import logging
from typing import Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Codec helpers ──────────────────────────────────────────────────────


def decode_image(data: bytes) -> np.ndarray:
    """Decode raw bytes (JPEG/PNG/etc.) into a BGR ``np.ndarray``.

    Args:
        data: Raw image bytes.

    Returns:
        Decoded image as a NumPy array in BGR colour order.

    Raises:
        ValueError: If the image cannot be decoded.
    """
    buf = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image from the provided bytes")
    return frame


def encode_image(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode a BGR frame to JPEG bytes.

    Args:
        frame: Image array in BGR colour order.
        quality: JPEG quality (0–100).

    Returns:
        JPEG-encoded bytes.

    Raises:
        ValueError: If encoding fails.
    """
    params = [cv2.IMWRITE_JPEG_QUALITY, max(0, min(quality, 100))]
    success, buf = cv2.imencode(".jpg", frame, params)
    if not success:
        raise ValueError("Failed to encode image to JPEG")
    return buf.tobytes()


# ── Geometry helpers ───────────────────────────────────────────────────


def resize_frame(frame: np.ndarray, width: int) -> np.ndarray:
    """Resize *frame* to the given *width* while preserving aspect ratio.

    Args:
        frame: Source image.
        width: Target width in pixels.

    Returns:
        Resized image.
    """
    h, w = frame.shape[:2]
    if w == width:
        return frame
    ratio = width / w
    new_h = int(h * ratio)
    interpolation = cv2.INTER_AREA if ratio < 1 else cv2.INTER_LINEAR
    return cv2.resize(frame, (width, new_h), interpolation=interpolation)


def crop_region(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> np.ndarray:
    """Extract a rectangular region of interest with bounds checking.

    Args:
        frame: Source image.
        bbox: ``(x1, y1, x2, y2)`` pixel coordinates.

    Returns:
        Cropped sub-image.  If the bounding box is entirely outside the
        frame the original frame is returned.
    """
    h, w = frame.shape[:2]
    x1 = max(0, min(bbox[0], w))
    y1 = max(0, min(bbox[1], h))
    x2 = max(0, min(bbox[2], w))
    y2 = max(0, min(bbox[3], h))

    if x2 <= x1 or y2 <= y1:
        logger.warning("Invalid crop region %s for frame %dx%d – returning full frame", bbox, w, h)
        return frame

    return frame[y1:y2, x1:x2].copy()


# ── Drawing / annotation helpers ──────────────────────────────────────


def draw_bbox(
    frame: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    label: str = "",
    color: tuple[int, int, int] = (0, 255, 0),
    confidence: float | None = None,
    thickness: int = 2,
) -> np.ndarray:
    """Draw a bounding box with an optional label and confidence score.

    Args:
        frame: Image to annotate (modified **in-place** and returned).
        x1, y1, x2, y2: Box corners in pixel coordinates.
        label: Class name to display above the box.
        color: BGR colour tuple.
        confidence: If provided, appended to the label as a percentage.
        thickness: Line thickness in pixels.

    Returns:
        The annotated frame (same object as *frame*).
    """
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    if label or confidence is not None:
        text = label
        if confidence is not None:
            pct = f"{confidence * 100:.0f}%"
            text = f"{label} {pct}" if label else pct

        frame = draw_text(frame, text, (x1, y1 - 8), color=color)

    return frame


def draw_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int] = (0, 255, 0),
    scale: float = 0.6,
    thickness: int = 1,
    bg_color: tuple[int, int, int] | None = (0, 0, 0),
    padding: int = 4,
) -> np.ndarray:
    """Draw *text* on *frame* with a filled background rectangle.

    Args:
        frame: Image to annotate (modified **in-place** and returned).
        text: String to render.
        position: ``(x, y)`` of the text baseline origin.
        color: Text colour (BGR).
        scale: Font scale factor.
        thickness: Text stroke thickness.
        bg_color: Background rectangle colour.  ``None`` to skip.
        padding: Pixels of padding around the text within the background.

    Returns:
        The annotated frame.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = position

    if bg_color is not None:
        cv2.rectangle(
            frame,
            (x - padding, y - th - padding - baseline),
            (x + tw + padding, y + padding),
            bg_color,
            cv2.FILLED,
        )

    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)
    return frame
