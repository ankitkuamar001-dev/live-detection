"""Recordings management API routes."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(tags=["Recordings"])

RECORDINGS_DIR = Path("data/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


# ── Schemas ─────────────────────────────────────────────────────────────

class RecordingItem(BaseModel):
    filename: str
    size_bytes: int
    size_display: str
    created_at: str
    duration: str | None = None


class RecordingStatsResponse(BaseModel):
    total_count: int
    total_size_bytes: int
    total_size_display: str


def _format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _scan_recordings() -> list[dict]:
    """Scan the recordings directory for video files."""
    recordings = []
    if not RECORDINGS_DIR.exists():
        return recordings
    for f in sorted(RECORDINGS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix.lower() in (".mp4", ".avi", ".mkv", ".mov", ".webm"):
            stat = f.stat()
            recordings.append({
                "filename": f.name,
                "size_bytes": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "duration": None,
            })
    return recordings


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/recordings", response_model=list[RecordingItem])
async def list_recordings():
    """List all recorded video clips."""
    return _scan_recordings()


@router.get("/recordings/stats", response_model=RecordingStatsResponse)
async def recording_stats():
    """Get storage usage statistics for recordings."""
    recordings = _scan_recordings()
    total_size = sum(r["size_bytes"] for r in recordings)
    return {
        "total_count": len(recordings),
        "total_size_bytes": total_size,
        "total_size_display": _format_size(total_size),
    }


@router.get("/recordings/{filename}")
async def get_recording(filename: str):
    """Stream / download a specific recording file."""
    filepath = RECORDINGS_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")
    return FileResponse(
        path=str(filepath),
        media_type="video/mp4",
        filename=filename,
    )


@router.delete("/recordings/{filename}", status_code=204)
async def delete_recording(filename: str):
    """Delete a recording file."""
    filepath = RECORDINGS_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")
    os.remove(filepath)
    logger.info("recording_deleted", filename=filename)
