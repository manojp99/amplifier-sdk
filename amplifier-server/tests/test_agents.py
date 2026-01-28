"""Tests for agents API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from amplifier_server.core.session_manager import AgentState
from amplifier_server.main import app
from amplifier_server.models import RunResponse, Usage


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    return TestClient(app)


def create_mock_agent_state(
    agent_id: str = "test-agent-id",
    instructions: str = "You are helpful.",
    tools: list[str] | None = None,
    provider: str = "anthropic",
    model: str | None = None,
) -> AgentState:
    """Create a mock AgentState object."""
    return AgentState(
        agent_id=agent_id,
        created_at=datetime.utcnow(),
        instructions=instructions,
        tools=tools or [],
        provider=provider,
        model=model,
        session=None,
        prepared=None,
        message_count=0,
    )


@pytest.fixture
def mock_session_manager() -> MagicMock:
    """Mock session manager with proper async methods."""
    manager = MagicMock()

    # Async methods need AsyncMock
    manager.create_agent = AsyncMock(return_value="test-agent-id")
    manager.run = AsyncMock(
        return_value=RunResponse(
            content="Hello! How can I help?",
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=20),
        )
    )
    manager.delete_agent = AsyncMock(return_value=True)

    # Sync methods use MagicMock
    manager.get_agent = MagicMock(return_value=create_mock_agent_state())
    manager.list_agents = MagicMock(return_value=["test-agent-id"])
    manager.active_count = 1

    return manager


class TestCreateAgent:
    """Tests for POST /agents endpoint."""

    def test_create_agent_success(
        self, client: TestClient, mock_session_manager: MagicMock
    ) -> None:
        """Create agent returns agent_id."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.post(
                "/agents",
                json={
                    "instructions": "You are helpful.",
                    "provider": "anthropic",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "agent_id" in data
            assert data["agent_id"] == "test-agent-id"

    def test_create_agent_with_tools(
        self, client: TestClient, mock_session_manager: MagicMock
    ) -> None:
        """Create agent with tools."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.post(
                "/agents",
                json={
                    "instructions": "You are helpful.",
                    "tools": ["bash", "filesystem"],
                    "provider": "anthropic",
                },
            )
            assert response.status_code == 200
            mock_session_manager.create_agent.assert_called_once()

    def test_create_agent_missing_instructions(self, client: TestClient) -> None:
        """Create agent without instructions fails."""
        response = client.post(
            "/agents",
            json={"provider": "anthropic"},
        )
        assert response.status_code == 422  # Validation error


class TestGetAgent:
    """Tests for GET /agents/{agent_id} endpoint."""

    def test_get_agent_success(self, client: TestClient, mock_session_manager: MagicMock) -> None:
        """Get agent returns agent info."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.get("/agents/test-agent-id")
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == "test-agent-id"
            assert data["instructions"] == "You are helpful."
            assert data["provider"] == "anthropic"

    def test_get_agent_not_found(self, client: TestClient, mock_session_manager: MagicMock) -> None:
        """Get non-existent agent returns 404."""
        mock_session_manager.get_agent = MagicMock(return_value=None)
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.get("/agents/nonexistent")
            assert response.status_code == 404


class TestListAgents:
    """Tests for GET /agents endpoint."""

    def test_list_agents_success(self, client: TestClient, mock_session_manager: MagicMock) -> None:
        """List agents returns array."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.get("/agents")
            assert response.status_code == 200
            data = response.json()
            assert "agents" in data
            assert isinstance(data["agents"], list)
            assert "count" in data


class TestDeleteAgent:
    """Tests for DELETE /agents/{agent_id} endpoint."""

    def test_delete_agent_success(
        self, client: TestClient, mock_session_manager: MagicMock
    ) -> None:
        """Delete agent succeeds."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.delete("/agents/test-agent-id")
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            mock_session_manager.delete_agent.assert_called_once_with("test-agent-id")

    def test_delete_agent_not_found(
        self, client: TestClient, mock_session_manager: MagicMock
    ) -> None:
        """Delete non-existent agent returns 404."""
        mock_session_manager.delete_agent = AsyncMock(return_value=False)
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.delete("/agents/nonexistent")
            assert response.status_code == 404


class TestRunPrompt:
    """Tests for POST /agents/{agent_id}/run endpoint."""

    def test_run_prompt_success(self, client: TestClient, mock_session_manager: MagicMock) -> None:
        """Run prompt returns response."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.post(
                "/agents/test-agent-id/run",
                json={"prompt": "Hello!"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data["content"] == "Hello! How can I help?"

    def test_run_prompt_includes_usage(
        self, client: TestClient, mock_session_manager: MagicMock
    ) -> None:
        """Run prompt includes token usage."""
        with patch(
            "amplifier_server.api.agents.get_session_manager",
            return_value=mock_session_manager,
        ):
            response = client.post(
                "/agents/test-agent-id/run",
                json={"prompt": "Hello!"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "usage" in data
            assert data["usage"]["input_tokens"] == 10
            assert data["usage"]["output_tokens"] == 20

    def test_run_prompt_missing_prompt(self, client: TestClient) -> None:
        """Run without prompt fails."""
        response = client.post(
            "/agents/test-agent-id/run",
            json={},
        )
        assert response.status_code == 422
