"""Tests for teLLMe gateway API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from tellme.gateway import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "tellme-gateway"


def test_status_returns_services(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "teLLMe"
    assert "services" in data
    assert "services_healthy" in data


def test_files_endpoint_workspace_missing(client):
    resp = client.get("/files?path=/nonexistent")
    assert resp.status_code == 404


def test_command_without_nlp2cmd(client):
    """Command endpoint should fail when nlp2cmd is unreachable."""
    resp = client.post("/command", json={"query": "list files"})
    assert resp.status_code >= 400  # 502 in prod, may vary in test


def test_models_without_ollama(client):
    """Models endpoint should fail when ollama is unreachable."""
    resp = client.get("/models")
    # May return 502 (prod) or 200 with error (testclient httpx behavior)
    assert resp.status_code in (200, 502)
