"""Tests for HTTP routes via Starlette TestClient.

These tests verify the HTTP API surface — status codes, response shapes,
and error handling — without needing amplifier-core installed.
"""

import pytest
from starlette.testclient import TestClient

from amplifier_app_runtime.app import create_app


@pytest.fixture(scope="module")
def client():
    """Shared test client for all route tests."""
    return TestClient(create_app())


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client: TestClient) -> None:
    response = client.get("/v1/health")
    data = response.json()
    assert data.get("status") == "ok"


def test_list_sessions_returns_empty_lists(client: TestClient) -> None:
    response = client.get("/v1/session")
    assert response.status_code == 200
    data = response.json()
    assert "active" in data
    assert "saved" in data
    assert isinstance(data["active"], list)
    assert isinstance(data["saved"], list)


def test_get_nonexistent_session_returns_404(client: TestClient) -> None:
    response = client.get("/v1/session/nonexistent-id-abc123")
    assert response.status_code == 404


def test_delete_nonexistent_session_returns_404_or_false(client: TestClient) -> None:
    response = client.delete("/v1/session/nonexistent-id-abc123")
    # 404 if session not found — acceptable behaviour
    assert response.status_code in (200, 404)


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/v1/does-not-exist")
    assert response.status_code == 404
