"""
Health-check endpoints for liveness, readiness, and system information.
"""

from __future__ import annotations

import os
import platform
import sys
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ComponentStatus(BaseModel):
    name: str
    status: str  # "healthy" | "unhealthy" | "unavailable"
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    components: list[ComponentStatus]


class SystemInfoResponse(BaseModel):
    python_version: str
    platform: str
    cpu_count: int | None
    memory_total_gb: float | None
    memory_used_gb: float | None
    gpu_available: bool
    gpu_name: str | None
    uptime_seconds: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the service is alive.",
)
async def liveness() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        version="1.0.0",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Checks critical dependencies (database, models) and reports readiness.",
)
async def readiness(request: Request) -> ReadinessResponse:
    components: list[ComponentStatus] = []

    # Database check
    db_engine = getattr(request.app.state, "db_engine", None)
    if db_engine is not None:
        try:
            from sqlalchemy import text

            async with db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            components.append(ComponentStatus(name="database", status="healthy"))
        except Exception as exc:
            components.append(
                ComponentStatus(name="database", status="unhealthy", detail=str(exc))
            )
    else:
        components.append(
            ComponentStatus(name="database", status="unavailable", detail="No engine configured")
        )

    # Model registry check
    model_registry = getattr(request.app.state, "model_registry", None)
    if model_registry is not None:
        components.append(ComponentStatus(name="models", status="healthy"))
    else:
        components.append(
            ComponentStatus(name="models", status="unavailable", detail="Not loaded yet")
        )

    # Stream manager check
    stream_manager = getattr(request.app.state, "stream_manager", None)
    if stream_manager is not None:
        components.append(ComponentStatus(name="streams", status="healthy"))
    else:
        components.append(
            ComponentStatus(name="streams", status="unavailable", detail="Not started yet")
        )

    overall = (
        "ready"
        if all(c.status == "healthy" for c in components if c.name == "database")
        else "not_ready"
    )
    return ReadinessResponse(status=overall, components=components)


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    summary="System information",
    description="Returns runtime information about the host and GPU.",
)
async def system_info() -> SystemInfoResponse:
    # Memory info
    mem_total: float | None = None
    mem_used: float | None = None
    try:
        import psutil

        vm = psutil.virtual_memory()
        mem_total = round(vm.total / (1024**3), 2)
        mem_used = round(vm.used / (1024**3), 2)
    except ImportError:
        pass

    # GPU info
    gpu_available = False
    gpu_name: str | None = None
    try:
        from src.utils.gpu import get_gpu_info, is_gpu_available

        gpu_available = is_gpu_available()
        if gpu_available:
            gpu_name = get_gpu_info().get("name")
    except Exception:
        pass

    # Uptime
    uptime = 0.0
    try:
        from src.core.events import get_uptime

        uptime = round(get_uptime(), 1)
    except Exception:
        pass

    return SystemInfoResponse(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        cpu_count=os.cpu_count(),
        memory_total_gb=mem_total,
        memory_used_gb=mem_used,
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        uptime_seconds=uptime,
    )
