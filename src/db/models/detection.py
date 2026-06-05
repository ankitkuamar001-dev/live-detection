"""DetectionEvent ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.engine import Base, TimestampMixin


class DetectionEvent(TimestampMixin, Base):
    """A single detection event captured by a camera pipeline."""

    __tablename__ = "detection_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    camera_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    detection_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # mask, emotion, object
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    metadata_extra: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __table_args__ = (
        Index(
            "idx_camera_type_time",
            "camera_id",
            "detection_type",
            "detected_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DetectionEvent(id={self.id}, camera={self.camera_id!r}, "
            f"type={self.detection_type!r}, label={self.label!r}, "
            f"confidence={self.confidence:.2f})>"
        )
