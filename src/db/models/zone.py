"""Zone ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.engine import Base, TimestampMixin, UUIDMixin


class Zone(UUIDMixin, TimestampMixin, Base):
    """A named polygon region within a camera's field of view."""

    __tablename__ = "zones"

    camera_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cameras.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    polygon: Mapped[list] = mapped_column(JSON, nullable=False)
    zone_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # exclusion, monitoring, counting
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<Zone(id={self.id!r}, camera={self.camera_id!r}, "
            f"name={self.name!r}, type={self.zone_type!r})>"
        )
