"""Tests for alert rules API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alert_rules(client: AsyncClient):
    """GET /api/v1/alerts/rules should return default rules."""
    response = await client.get("/api/v1/alerts/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_create_alert_rule(client: AsyncClient):
    """POST /api/v1/alerts/rules should create a new rule."""
    response = await client.post("/api/v1/alerts/rules", json={
        "name": "Test Rule",
        "event_type": "no_mask",
        "channels": ["log"],
        "conditions": {},
        "cooldown_seconds": 30,
        "is_active": True,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Rule"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_alert_history(client: AsyncClient):
    """GET /api/v1/alerts/history should return a list."""
    response = await client.get("/api/v1/alerts/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
