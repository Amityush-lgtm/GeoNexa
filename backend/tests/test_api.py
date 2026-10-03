"""
Integration tests for FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns offline readiness status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "warning", "error", "healthy", "degraded", "unhealthy"]
    assert "checks" in data
    assert "offline_mode" in data


def test_query_router_endpoint():
    """Verify natural-language query routing."""
    response = client.post(
        "/api/query",
        json={"text": "what has changed between these observations"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "confidence" in data


def test_archive_stats_endpoint():
    """Verify archive stats endpoint returns structure."""
    response = client.get("/api/archive/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_tiles" in data
    assert "total_scenes" in data
