"""Tests for Amplifier SDK client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_sdk import AgentConfig, AmplifierClient, RunResponse


class TestAmplifierClient:
    """Tests for AmplifierClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self) -> None:
        """Client initializes with default values."""
        client = AmplifierClient()
        assert client.base_url == "http://localhost:8000"
        assert client.api_key is None
        assert client.timeout == 300.0

    @pytest.mark.asyncio
    async def test_client_custom_url(self) -> None:
        """Client accepts custom base URL."""
        client = AmplifierClient(base_url="http://custom:9000/")
        assert client.base_url == "http://custom:9000"  # Trailing slash removed

    @pytest.mark.asyncio
    async def test_client_api_key(self) -> None:
        """Client accepts API key."""
        client = AmplifierClient(api_key="test-key")
        assert client.api_key == "test-key"
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Client works as async context manager."""
        async with AmplifierClient() as client:
            assert client is not None
        # Client should be closed after context

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Health check returns server status."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "ok", "version": "0.1.0"}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = AmplifierClient()
            client._client = mock_client
            result = await client.health()

            assert result["status"] == "ok"
            mock_client.get.assert_called_with("/health")

    @pytest.mark.asyncio
    async def test_create_agent(self) -> None:
        """Can create an agent."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"agent_id": "ag_test123"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = AmplifierClient()
            client._client = mock_client
            config = AgentConfig(
                instructions="Be helpful.",
                provider="anthropic",
                tools=["bash"],
            )
            agent_id = await client.create_agent(config)

            assert agent_id == "ag_test123"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_agents(self) -> None:
        """Can list agents."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"agents": ["ag_1", "ag_2"]}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = AmplifierClient()
            client._client = mock_client
            agents = await client.list_agents()

            assert agents == ["ag_1", "ag_2"]
            mock_client.get.assert_called_with("/agents")

    @pytest.mark.asyncio
    async def test_run_prompt(self) -> None:
        """Can run a prompt."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": "Hello!",
                "tool_calls": [],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                "turn_count": 1,
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = AmplifierClient()
            client._client = mock_client
            result = await client.run("ag_test", "Hello")

            assert isinstance(result, RunResponse)
            assert result.content == "Hello!"
            assert result.turn_count == 1

    @pytest.mark.asyncio
    async def test_delete_agent(self) -> None:
        """Can delete an agent."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"deleted": True}
            mock_response.raise_for_status = MagicMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = AmplifierClient()
            client._client = mock_client
            await client.delete_agent("ag_test")

            mock_client.delete.assert_called_with("/agents/ag_test")


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_config_to_dict(self) -> None:
        """Config converts to dict correctly."""
        config = AgentConfig(
            instructions="Be helpful.",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            tools=["bash"],
        )
        data = config.to_dict()

        assert data["instructions"] == "Be helpful."
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["tools"] == ["bash"]

    def test_config_defaults(self) -> None:
        """Config has correct defaults."""
        config = AgentConfig(instructions="Test", provider="anthropic")
        data = config.to_dict()

        assert data["orchestrator"] == "basic"
        assert data["context_manager"] == "simple"
        assert "model" not in data  # None values excluded


class TestRunResponse:
    """Tests for RunResponse model."""

    def test_from_dict(self) -> None:
        """RunResponse parses from dict."""
        data = {
            "content": "Hello!",
            "tool_calls": [{"id": "tc_1", "name": "bash", "input": {"command": "ls"}}],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            "turn_count": 2,
        }
        response = RunResponse.from_dict(data)

        assert response.content == "Hello!"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.usage.total_tokens == 15
        assert response.turn_count == 2
