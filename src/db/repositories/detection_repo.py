"""Repository for :class:`DetectionEvent` CRUD operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.detection import DetectionEvent


class DetectionRepository:
    """Encapsulates all database access for :class:`DetectionEvent`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    # Create                                                              #
    # ------------------------------------------------------------------ #
    async def create(
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
    ) -> DetectionEvent:
        """Persist a single detection event and return it.

        Args:
            camera_id: Identifier of the source camera.
            detection_type: Category such as ``mask``, ``emotion``, ``object``.
            label: Specific label, e.g. ``no_mask``, ``happy``, ``person``.
            confidence: Model confidence in ``[0, 1]``.
            bbox: Optional bounding-box dict ``{x, y, w, h}``.
            track_id: Optional object-tracking ID.
            snapshot_path: Optional path to a saved frame snapshot.
            metadata: Optional extra metadata dict.

        Returns:
            The newly created :class:`DetectionEvent`.
        """
        event = DetectionEvent(
            camera_id=camera_id,
            detection_type=detection_type,
            label=label,
            confidence=confidence,
            bbox=bbox,
            track_id=track_id,
            snapshot_path=snapshot_path,
            metadata_extra=metadata,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def create_batch(
        self, events: list[dict[str, Any]]
    ) -> list[DetectionEvent]:
        """Persist multiple detection events in a single flush.

        Each dict in *events* should contain keys matching the constructor
        keyword arguments of :meth:`create` (``camera_id``, ``detection_type``,
        ``label``, ``confidence``, and optionally ``bbox``, ``track_id``,
        ``snapshot_path``, ``metadata``).

        Returns:
            A list of the newly created :class:`DetectionEvent` instances.
        """
        models: list[DetectionEvent] = []
        for data in events:
            model = DetectionEvent(
                camera_id=data["camera_id"],
                detection_type=data["detection_type"],
                label=data["label"],
                confidence=data["confidence"],
                bbox=data.get("bbox"),
                track_id=data.get("track_id"),
                snapshot_path=data.get("snapshot_path"),
                metadata_extra=data.get("metadata"),
            )
            models.append(model)
        self._session.add_all(models)
        await self._session.flush()
        return models

    # ------------------------------------------------------------------ #
    # Read                                                                #
    # ------------------------------------------------------------------ #
    async def get_by_id(self, event_id: int) -> DetectionEvent | None:
        """Return a single event by primary key, or ``None``."""
        return await self._session.get(DetectionEvent, event_id)

    async def get_by_camera(
        self,
        camera_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DetectionEvent]:
        """Return events for *camera_id* ordered by ``detected_at`` descending."""
        stmt = (
            select(DetectionEvent)
            .where(DetectionEvent.camera_id == camera_id)
            .order_by(DetectionEvent.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
        *,
        camera_id: str | None = None,
    ) -> list[DetectionEvent]:
        """Return events within ``[start, end]``, optionally filtered by camera."""
        stmt = select(DetectionEvent).where(
            DetectionEvent.detected_at >= start,
            DetectionEvent.detected_at <= end,
        )
        if camera_id is not None:
            stmt = stmt.where(DetectionEvent.camera_id == camera_id)
        stmt = stmt.order_by(DetectionEvent.detected_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(
        self,
        camera_id: str,
        detection_type: str,
        start: datetime,
        end: datetime,
    ) -> int:
        """Count events matching *camera_id* and *detection_type* in a time window."""
        stmt = (
            select(func.count())
            .select_from(DetectionEvent)
            .where(
                DetectionEvent.camera_id == camera_id,
                DetectionEvent.detection_type == detection_type,
                DetectionEvent.detected_at >= start,
                DetectionEvent.detected_at <= end,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_latest(
        self,
        camera_id: str,
        *,
        limit: int = 10,
    ) -> list[DetectionEvent]:
        """Return the most recent *limit* events for a camera."""
        stmt = (
            select(DetectionEvent)
            .where(DetectionEvent.camera_id == camera_id)
            .order_by(DetectionEvent.detected_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Delete                                                              #
    # ------------------------------------------------------------------ #
    async def delete_older_than(self, days: int) -> int:
        """Delete events older than *days* and return the count removed."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        stmt = (
            delete(DetectionEvent)
            .where(DetectionEvent.detected_at < cutoff)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
