"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /api/v1/health/ should return 200 with status ok."""
    response = await client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    """GET /api/v1/health/ready should return 200."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
