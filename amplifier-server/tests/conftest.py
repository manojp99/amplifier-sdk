"""Test configuration and fixtures for server tests."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from amplifier_server.core.recipe_manager import RecipeManager
from amplifier_server.core.session_manager import SessionManager
from amplifier_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session_manager() -> MagicMock:
    """Mock session manager."""
    manager = MagicMock(spec=SessionManager)
    manager.create_session = AsyncMock(return_value="test-agent-id")
    manager.get_session = MagicMock(
        return_value=MagicMock(
            session_id="test-agent-id",
            config={"instructions": "test"},
        )
    )
    manager.list_sessions = MagicMock(
        return_value=[{"agent_id": "test-agent-id", "created_at": "2024-01-01T00:00:00Z"}]
    )
    manager.delete_session = AsyncMock()
    manager.execute = AsyncMock(
        return_value={
            "content": "Hello! How can I help?",
            "tool_calls": [],
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "stop_reason": "end_turn",
        }
    )
    return manager


@pytest.fixture
def mock_recipe_manager() -> MagicMock:
    """Mock recipe manager."""
    manager = MagicMock(spec=RecipeManager)
    manager.execute = AsyncMock(return_value="test-execution-id")
    manager.get_execution = MagicMock(
        return_value={
            "execution_id": "test-execution-id",
            "recipe_name": "test-recipe",
            "status": "completed",
            "steps": [],
        }
    )
    manager.approve_gate = AsyncMock()
    manager.deny_gate = AsyncMock()
    return manager
