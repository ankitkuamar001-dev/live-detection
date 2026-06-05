"""AlertLog ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.engine import Base, TimestampMixin


class AlertLog(TimestampMixin, Base):
    """An alert raised by the detection pipeline and dispatched via a channel."""

    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    camera_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    detection_event_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("detection_events.id"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<AlertLog(id={self.id}, camera={self.camera_id!r}, "
            f"type={self.alert_type!r}, status={self.status!r})>"
        )
