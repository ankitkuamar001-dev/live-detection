"""Tests for settings API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient):
    """GET /api/v1/settings should return runtime config."""
    response = await client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "confidence_threshold" in data or "model_name" in data


@pytest.mark.asyncio
async def test_system_info(client: AsyncClient):
    """GET /api/v1/system/info should return hardware data."""
    response = await client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "platform" in data
    assert "cpu_count" in data


@pytest.mark.asyncio
async def test_system_models(client: AsyncClient):
    """GET /api/v1/system/models should return model statuses."""
    response = await client.get("/api/v1/system/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
