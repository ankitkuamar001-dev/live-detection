"""
Analytics aggregation service.

Runs as a background asyncio task, periodically aggregating raw detection events
into hourly summaries stored in ``analytics_hourly``.

Usage::

    aggregator = AnalyticsAggregator(session_factory)
    await aggregator.start()   # in lifespan startup
    await aggregator.stop()    # in lifespan shutdown
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models.analytics import AnalyticsHourly
from src.db.models.detection import DetectionEvent

logger = structlog.get_logger(__name__)


class AnalyticsAggregator:
    """Background service that rolls up detection events into hourly buckets."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        interval_seconds: int = 300,  # run every 5 minutes
    ) -> None:
        self._session_factory = session_factory
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background aggregation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="analytics-aggregator")
        logger.info("analytics_aggregator_started", interval=self._interval)

    async def stop(self) -> None:
        """Stop the aggregation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("analytics_aggregator_stopped")

    async def _loop(self) -> None:
        """Periodic aggregation loop."""
        # Initial delay to let events accumulate
        await asyncio.sleep(30)
        while self._running:
            try:
                await self._aggregate_last_hours(hours=2)
            except Exception:
                logger.exception("analytics_aggregation_error")
            await asyncio.sleep(self._interval)

    async def _aggregate_last_hours(self, hours: int = 2) -> None:
        """Aggregate detection events for the last N hours into hourly buckets."""
        now = datetime.now(tz=timezone.utc)
        # Truncate to current hour
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        start_hour = current_hour - timedelta(hours=hours)

        async with self._session_factory() as session:
            async with session.begin():
                # Get distinct camera_ids with events in range
                camera_stmt = (
                    select(DetectionEvent.camera_id)
                    .where(DetectionEvent.detected_at >= start_hour)
                    .distinct()
                )
                result = await session.execute(camera_stmt)
                camera_ids = [row[0] for row in result.all()]

                if not camera_ids:
                    return

                for camera_id in camera_ids:
                    for h in range(hours + 1):
                        hour_start = start_hour + timedelta(hours=h)
                        hour_end = hour_start + timedelta(hours=1)

                        await self._aggregate_hour(
                            session, camera_id, hour_start, hour_end
                        )

        logger.debug(
            "analytics_aggregated",
            cameras=len(camera_ids),
            hours_covered=hours,
        )

    async def _aggregate_hour(
        self,
        session: AsyncSession,
        camera_id: str,
        hour_start: datetime,
        hour_end: datetime,
    ) -> None:
        """Compute and upsert a single hourly aggregation bucket."""
        base_filter = [
            DetectionEvent.camera_id == camera_id,
            DetectionEvent.detected_at >= hour_start,
            DetectionEvent.detected_at < hour_end,
        ]

        # Total detections
        total_stmt = select(func.count()).select_from(DetectionEvent).where(*base_filter)
        total_result = await session.execute(total_stmt)
        total = total_result.scalar_one()

        if total == 0:
            return

        # Mask counts
        mask_stmt = (
            select(DetectionEvent.label, func.count())
            .where(*base_filter, DetectionEvent.detection_type == "mask")
            .group_by(DetectionEvent.label)
        )
        mask_result = await session.execute(mask_stmt)
        mask_counts = dict(mask_result.all())

        # Emotion distribution
        emotion_stmt = (
            select(DetectionEvent.label, func.count())
            .where(*base_filter, DetectionEvent.detection_type == "emotion")
            .group_by(DetectionEvent.label)
        )
        emotion_result = await session.execute(emotion_stmt)
        emotion_dist = dict(emotion_result.all())

        # Object counts
        object_stmt = (
            select(DetectionEvent.label, func.count())
            .where(*base_filter, DetectionEvent.detection_type == "object")
            .group_by(DetectionEvent.label)
        )
        object_result = await session.execute(object_stmt)
        object_counts = dict(object_result.all())

        # Check if row exists
        existing_stmt = select(AnalyticsHourly).where(
            AnalyticsHourly.camera_id == camera_id,
            AnalyticsHourly.hour == hour_start,
        )
        existing_result = await session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.total_detections = total
            existing.mask_count = mask_counts.get("with_mask", 0)
            existing.no_mask_count = mask_counts.get("without_mask", 0)
            existing.incorrect_mask_count = mask_counts.get("incorrect_mask", 0)
            existing.emotion_distribution = emotion_dist if emotion_dist else None
            existing.object_counts = object_counts if object_counts else None
        else:
            row = AnalyticsHourly(
                camera_id=camera_id,
                hour=hour_start,
                total_detections=total,
                mask_count=mask_counts.get("with_mask", 0),
                no_mask_count=mask_counts.get("without_mask", 0),
                incorrect_mask_count=mask_counts.get("incorrect_mask", 0),
                emotion_distribution=emotion_dist if emotion_dist else None,
                object_counts=object_counts if object_counts else None,
            )
            session.add(row)
