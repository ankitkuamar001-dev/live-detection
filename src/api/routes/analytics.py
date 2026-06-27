"""
REST API for historical analytics.

Exposes hourly aggregations, daily roll-ups, summary stats, and raw event queries.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import create_db_engine, create_session_factory
from src.db.models.analytics import AnalyticsHourly
from src.db.models.detection import DetectionEvent
from src.core.config import get_settings

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_session_factory():
    """Get or create session factory from settings."""
    settings = get_settings()
    engine = create_db_engine(
        database_url=settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
    )
    return create_session_factory(engine)


_session_factory = None


def _sf():
    global _session_factory
    if _session_factory is None:
        _session_factory = _get_session_factory()
    return _session_factory


@router.get("/hourly")
async def get_hourly_analytics(
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
) -> list[dict[str, Any]]:
    """Return hourly aggregated analytics for the specified time range."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    stmt = (
        select(AnalyticsHourly)
        .where(AnalyticsHourly.hour >= cutoff)
        .order_by(AnalyticsHourly.hour.asc())
    )
    if camera_id:
        stmt = stmt.where(AnalyticsHourly.camera_id == camera_id)

    async with _sf()() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    return [
        {
            "id": row.id,
            "camera_id": row.camera_id,
            "hour": row.hour.isoformat() if row.hour else None,
            "total_detections": row.total_detections,
            "mask_count": row.mask_count,
            "no_mask_count": row.no_mask_count,
            "incorrect_mask_count": row.incorrect_mask_count,
            "emotion_distribution": row.emotion_distribution,
            "object_counts": row.object_counts,
            "avg_fps": row.avg_fps,
            "avg_inference_ms": row.avg_inference_ms,
        }
        for row in rows
    ]


@router.get("/daily")
async def get_daily_analytics(
    camera_id: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
) -> list[dict[str, Any]]:
    """Return daily roll-up of detection counts."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    async with _sf()() as session:
        # Aggregate hourly rows into daily buckets
        stmt = (
            select(AnalyticsHourly)
            .where(AnalyticsHourly.hour >= cutoff)
            .order_by(AnalyticsHourly.hour.asc())
        )
        if camera_id:
            stmt = stmt.where(AnalyticsHourly.camera_id == camera_id)

        result = await session.execute(stmt)
        rows = result.scalars().all()

    # Aggregate by date
    daily: dict[str, dict[str, Any]] = {}
    for row in rows:
        date_key = row.hour.strftime("%Y-%m-%d") if row.hour else "unknown"
        if date_key not in daily:
            daily[date_key] = {
                "date": date_key,
                "total_detections": 0,
                "mask_count": 0,
                "no_mask_count": 0,
                "incorrect_mask_count": 0,
                "emotions": {},
                "objects": {},
            }
        d = daily[date_key]
        d["total_detections"] += row.total_detections or 0
        d["mask_count"] += row.mask_count or 0
        d["no_mask_count"] += row.no_mask_count or 0
        d["incorrect_mask_count"] += row.incorrect_mask_count or 0
        if row.emotion_distribution:
            for k, v in row.emotion_distribution.items():
                d["emotions"][k] = d["emotions"].get(k, 0) + v
        if row.object_counts:
            for k, v in row.object_counts.items():
                d["objects"][k] = d["objects"].get(k, 0) + v

    return list(daily.values())


@router.get("/summary")
async def get_analytics_summary(
    hours: int = Query(24, ge=1, le=720),
) -> dict[str, Any]:
    """Return a high-level summary across all cameras."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    async with _sf()() as session:
        # Total events
        total_stmt = (
            select(func.count())
            .select_from(DetectionEvent)
            .where(DetectionEvent.detected_at >= cutoff)
        )
        total = (await session.execute(total_stmt)).scalar_one()

        # By type
        type_stmt = (
            select(DetectionEvent.detection_type, func.count())
            .where(DetectionEvent.detected_at >= cutoff)
            .group_by(DetectionEvent.detection_type)
        )
        by_type = dict((await session.execute(type_stmt)).all())

        # Mask breakdown
        mask_stmt = (
            select(DetectionEvent.label, func.count())
            .where(
                DetectionEvent.detected_at >= cutoff,
                DetectionEvent.detection_type == "mask",
            )
            .group_by(DetectionEvent.label)
        )
        mask_breakdown = dict((await session.execute(mask_stmt)).all())

        # Emotion breakdown
        emotion_stmt = (
            select(DetectionEvent.label, func.count())
            .where(
                DetectionEvent.detected_at >= cutoff,
                DetectionEvent.detection_type == "emotion",
            )
            .group_by(DetectionEvent.label)
        )
        emotion_breakdown = dict((await session.execute(emotion_stmt)).all())

        # Active cameras
        cam_stmt = (
            select(func.count(func.distinct(DetectionEvent.camera_id)))
            .where(DetectionEvent.detected_at >= cutoff)
        )
        active_cameras = (await session.execute(cam_stmt)).scalar_one()

    total_masks = sum(mask_breakdown.values()) if mask_breakdown else 0
    compliant = mask_breakdown.get("with_mask", 0)

    return {
        "period_hours": hours,
        "total_events": total,
        "by_type": by_type,
        "mask_breakdown": mask_breakdown,
        "mask_compliance_pct": round(compliant / total_masks * 100, 1) if total_masks > 0 else 0,
        "emotion_breakdown": emotion_breakdown,
        "active_cameras": active_cameras,
    }


@router.get("/events")
async def get_detection_events(
    camera_id: str | None = Query(None),
    detection_type: str | None = Query(None, description="mask, emotion, or object"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """Return raw detection events with optional filters."""
    async with _sf()() as session:
        stmt = (
            select(DetectionEvent)
            .order_by(DetectionEvent.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if camera_id:
            stmt = stmt.where(DetectionEvent.camera_id == camera_id)
        if detection_type:
            stmt = stmt.where(DetectionEvent.detection_type == detection_type)

        result = await session.execute(stmt)
        rows = result.scalars().all()

    return [
        {
            "id": row.id,
            "camera_id": row.camera_id,
            "detected_at": row.detected_at.isoformat() if row.detected_at else None,
            "detection_type": row.detection_type,
            "label": row.label,
            "confidence": round(row.confidence, 3),
            "bbox": row.bbox,
            "track_id": row.track_id,
            "snapshot_path": row.snapshot_path,
        }
        for row in rows
    ]
