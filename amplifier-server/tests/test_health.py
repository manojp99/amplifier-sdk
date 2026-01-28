"""Tests for health endpoint."""

import pytest
from fastapi.testclient import TestClient

from amplifier_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_includes_version(self, client: TestClient) -> None:
        """Health endpoint includes version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
