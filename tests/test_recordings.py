"""Tests for recordings API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_recordings(client: AsyncClient):
    """GET /api/v1/recordings should return a list (possibly empty)."""
    response = await client.get("/api/v1/recordings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_recordings_stats(client: AsyncClient):
    """GET /api/v1/recordings/stats should return storage info."""
    response = await client.get("/api/v1/recordings/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "total_size_mb" in data
