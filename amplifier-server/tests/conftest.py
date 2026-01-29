"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from amplifier_server.api.agents import set_session_manager
from amplifier_server.core.session_manager import SessionManager
from amplifier_server.main import create_app


@pytest.fixture
def session_manager() -> SessionManager:
    """Create a fresh session manager for testing."""
    return SessionManager()


@pytest.fixture
def client(session_manager: SessionManager) -> TestClient:
    """Create test client with injected session manager."""
    set_session_manager(session_manager)
    app = create_app()
    return TestClient(app)
