"""Camera ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.engine import Base, TimestampMixin, UUIDMixin


class Camera(UUIDMixin, TimestampMixin, Base):
    """A camera source registered in the system."""

    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # rtsp, http, file
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<Camera(id={self.id!r}, name={self.name!r}, "
            f"source_type={self.source_type!r}, active={self.is_active})>"
        )
