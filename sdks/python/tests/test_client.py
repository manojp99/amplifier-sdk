"""Tests for AmplifierClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from amplifier_sdk.client import AmplifierClient


@pytest.fixture
def client() -> AmplifierClient:
    """Create test client."""
    return AmplifierClient(
        base_url="http://localhost:8080",
        api_key="test-api-key",
    )


class TestClientInit:
    """Tests for client initialization."""

    def test_default_base_url(self) -> None:
        """Default base URL is localhost:8080."""
        client = AmplifierClient()
        assert client.base_url == "http://localhost:8080"

    def test_custom_base_url(self) -> None:
        """Custom base URL is used."""
        client = AmplifierClient(base_url="http://custom:9000")
        assert client.base_url == "http://custom:9000"

    def test_strips_trailing_slash(self) -> None:
        """Trailing slash is stripped from base URL."""
        client = AmplifierClient(base_url="http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"

    def test_api_key_stored(self) -> None:
        """API key is stored."""
        client = AmplifierClient(api_key="secret")
        assert client.api_key == "secret"


class TestHeaders:
    """Tests for request headers."""

    def test_content_type_always_set(self) -> None:
        """Content-Type header is always set."""
        client = AmplifierClient()
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_auth_header_when_api_key(self) -> None:
        """Authorization header set when API key provided."""
        client = AmplifierClient(api_key="secret")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer secret"

    def test_no_auth_header_without_api_key(self) -> None:
        """No Authorization header when no API key."""
        client = AmplifierClient()
        headers = client._get_headers()
        assert "Authorization" not in headers


@pytest.mark.asyncio
class TestHealth:
    """Tests for health endpoint."""

    async def test_health_request(self, client: AmplifierClient) -> None:
        """Health makes GET request to /health."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.1.0"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            result = await client.health()

            mock_http_client.get.assert_called_once_with("/health")
            assert result["status"] == "ok"


@pytest.mark.asyncio
class TestCreateAgent:
    """Tests for create_agent method."""

    async def test_create_agent_minimal(self, client: AmplifierClient) -> None:
        """Create agent with minimal parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"agent_id": "agent-123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            agent_id = await client.create_agent(instructions="Be helpful.")

            assert agent_id == "agent-123"
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert call_args[0][0] == "/agents"
            assert call_args[1]["json"]["instructions"] == "Be helpful."

    async def test_create_agent_with_tools(self, client: AmplifierClient) -> None:
        """Create agent with tools."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"agent_id": "agent-456"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            await client.create_agent(
                instructions="Be helpful.",
                tools=["bash", "filesystem"],
            )

            call_args = mock_http_client.post.call_args
            assert call_args[1]["json"]["tools"] == ["bash", "filesystem"]


@pytest.mark.asyncio
class TestRun:
    """Tests for run method."""

    async def test_run_returns_response(self, client: AmplifierClient) -> None:
        """Run returns RunResponse."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "Hello!",
            "tool_calls": [],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            result = await client.run("agent-123", "Hi there!")

            assert result.content == "Hello!"
            assert result.usage.input_tokens == 10
            mock_http_client.post.assert_called_once_with(
                "/agents/agent-123/run",
                json={"prompt": "Hi there!"},
            )


@pytest.mark.asyncio
class TestDeleteAgent:
    """Tests for delete_agent method."""

    async def test_delete_agent(self, client: AmplifierClient) -> None:
        """Delete agent makes DELETE request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.delete = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            await client.delete_agent("agent-123")

            mock_http_client.delete.assert_called_once_with("/agents/agent-123")


@pytest.mark.asyncio
class TestRecipes:
    """Tests for recipe methods."""

    async def test_execute_recipe(self, client: AmplifierClient) -> None:
        """Execute recipe returns execution_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"execution_id": "exec-123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            result = await client.execute_recipe(recipe_yaml="name: test\nsteps: []")

            assert result == "exec-123"

    async def test_approve_gate(self, client: AmplifierClient) -> None:
        """Approve gate makes POST request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            await client.approve_gate("exec-123", "review-gate")

            mock_http_client.post.assert_called_once_with(
                "/recipes/exec-123/approve",
                json={"step_id": "review-gate"},
            )
