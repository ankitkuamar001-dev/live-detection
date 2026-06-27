"""Tests for cameras API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_cameras(client: AsyncClient):
    """GET /api/v1/cameras should return a list with default webcam."""
    response = await client.get("/api/v1/cameras")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Default webcam should exist
    assert any(c["name"] == "Default Webcam" for c in data)


@pytest.mark.asyncio
async def test_create_camera(client: AsyncClient):
    """POST /api/v1/cameras should create a new camera."""
    response = await client.post("/api/v1/cameras", json={
        "name": "Test Camera",
        "source": "rtsp://test.local/stream",
        "source_type": "rtsp",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Camera"
    assert data["source_type"] == "rtsp"
    assert "id" in data


@pytest.mark.asyncio
async def test_delete_camera(client: AsyncClient):
    """POST then DELETE a camera."""
    # Create
    create_resp = await client.post("/api/v1/cameras", json={
        "name": "Temp Camera",
        "source": "0",
        "source_type": "webcam",
    })
    assert create_resp.status_code == 201
    cam_id = create_resp.json()["id"]

    # Delete
    delete_resp = await client.delete(f"/api/v1/cameras/{cam_id}")
    assert delete_resp.status_code == 204
