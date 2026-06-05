"""AnalyticsHourly ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.engine import Base


class AnalyticsHourly(Base):
    """Pre-aggregated hourly detection statistics per camera."""

    __tablename__ = "analytics_hourly"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    camera_id: Mapped[str] = mapped_column(String(50), nullable=False)
    hour: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    total_detections: Mapped[int] = mapped_column(Integer, default=0)
    mask_count: Mapped[int] = mapped_column(Integer, default=0)
    no_mask_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_mask_count: Mapped[int] = mapped_column(Integer, default=0)
    emotion_distribution: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    object_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    avg_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_inference_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    __table_args__ = (
        UniqueConstraint("camera_id", "hour", name="uq_camera_hour"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalyticsHourly(id={self.id}, camera={self.camera_id!r}, "
            f"hour={self.hour!r}, detections={self.total_detections})>"
        )
