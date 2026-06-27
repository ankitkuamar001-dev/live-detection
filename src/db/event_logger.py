"""
Background event logger for persisting detection events to the database.

Batches events in-memory and flushes to the DB at configurable intervals,
avoiding per-frame DB writes which would bottleneck the pipeline.

Usage::

    logger = EventLogger(session_factory, batch_size=50, flush_interval=5.0)
    await logger.start()

    # From pipeline (thread-safe):
    logger.log_event(camera_id="cam-1", detection_type="mask", label="no_mask", ...)

    # On shutdown:
    await logger.stop()
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models.detection import DetectionEvent

logger = structlog.get_logger(__name__)


class EventLogger:
    """Thread-safe, async-flushing event logger.

    Detection pipeline threads call :meth:`log_event` to enqueue events.
    A background asyncio task periodically flushes the batch to the database.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._flush_interval = flush_interval

        self._queue: deque[dict[str, Any]] = deque()
        self._lock = Lock()
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._total_logged = 0
        self._total_flushed = 0

    # ── Public API ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the background flush loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._flush_loop(), name="event-logger-flush")
        logger.info(
            "event_logger_started",
            batch_size=self._batch_size,
            flush_interval=self._flush_interval,
        )

    async def stop(self) -> None:
        """Stop the flush loop and drain remaining events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush()
        logger.info(
            "event_logger_stopped",
            total_logged=self._total_logged,
            total_flushed=self._total_flushed,
        )

    def log_event(
        self,
        *,
        camera_id: str,
        detection_type: str,
        label: str,
        confidence: float,
        bbox: dict[str, Any] | None = None,
        track_id: int | None = None,
        snapshot_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Enqueue a detection event (thread-safe, non-blocking).

        Args:
            camera_id: Source camera identifier.
            detection_type: One of ``mask``, ``emotion``, ``object``.
            label: Specific label (e.g. ``no_mask``, ``happy``, ``person``).
            confidence: Model confidence score in ``[0, 1]``.
            bbox: Optional bounding box ``{x1, y1, x2, y2}``.
            track_id: Optional tracker-assigned ID.
            snapshot_path: Optional path to saved frame.
            metadata: Optional extra metadata dict.
        """
        event_data = {
            "camera_id": camera_id,
            "detection_type": detection_type,
            "label": label,
            "confidence": confidence,
            "bbox": bbox,
            "track_id": track_id,
            "snapshot_path": snapshot_path,
            "metadata": metadata,
            "detected_at": datetime.now(tz=timezone.utc),
        }

        with self._lock:
            self._queue.append(event_data)
            self._total_logged += 1

    @property
    def pending_count(self) -> int:
        """Number of events queued but not yet flushed."""
        with self._lock:
            return len(self._queue)

    @property
    def stats(self) -> dict[str, int]:
        """Return logger statistics."""
        return {
            "total_logged": self._total_logged,
            "total_flushed": self._total_flushed,
            "pending": self.pending_count,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    async def _flush_loop(self) -> None:
        """Background loop that flushes events at fixed intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("event_logger_flush_error")

    async def _flush(self) -> None:
        """Drain the queue and batch-insert into the database."""
        # Grab all pending events atomically
        with self._lock:
            if not self._queue:
                return
            batch = list(self._queue)
            self._queue.clear()

        if not batch:
            return

        t0 = time.monotonic()
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    models = [
                        DetectionEvent(
                            camera_id=e["camera_id"],
                            detection_type=e["detection_type"],
                            label=e["label"],
                            confidence=e["confidence"],
                            bbox=e.get("bbox"),
                            track_id=e.get("track_id"),
                            snapshot_path=e.get("snapshot_path"),
                            metadata_extra=e.get("metadata"),
                        )
                        for e in batch
                    ]
                    session.add_all(models)

            elapsed_ms = (time.monotonic() - t0) * 1000
            self._total_flushed += len(batch)
            logger.debug(
                "events_flushed",
                count=len(batch),
                elapsed_ms=round(elapsed_ms, 1),
                total_flushed=self._total_flushed,
            )
        except Exception:
            logger.exception("event_flush_db_error", batch_size=len(batch))
            # Re-enqueue failed events (front of queue for ordering)
            with self._lock:
                for e in reversed(batch):
                    self._queue.appendleft(e)
