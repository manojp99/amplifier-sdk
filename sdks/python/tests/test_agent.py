"""Tests for Agent class."""

import pytest
from unittest.mock import AsyncMock, patch

from amplifier_sdk.agent import Agent, run
from amplifier_sdk.models import RunResponse, Usage


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create mock client."""
    client = AsyncMock()
    client.create_agent = AsyncMock(return_value="agent-123")
    client.run = AsyncMock(
        return_value=RunResponse(
            content="Hello!",
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5),
        )
    )
    client.delete_agent = AsyncMock()
    client.close = AsyncMock()
    return client


class TestAgentInit:
    """Tests for Agent initialization."""

    def test_creates_with_instructions(self) -> None:
        """Agent stores instructions."""
        agent = Agent(instructions="Be helpful.")
        assert agent.config.instructions == "Be helpful."

    def test_default_provider(self) -> None:
        """Default provider is anthropic."""
        agent = Agent(instructions="Be helpful.")
        assert agent.config.provider == "anthropic"

    def test_custom_provider(self) -> None:
        """Custom provider is used."""
        agent = Agent(instructions="Be helpful.", provider="openai")
        assert agent.config.provider == "openai"

    def test_with_tools(self) -> None:
        """Tools are stored."""
        agent = Agent(instructions="Be helpful.", tools=["bash", "filesystem"])
        assert agent.config.tools == ["bash", "filesystem"]

    def test_agent_id_initially_none(self) -> None:
        """Agent ID is None before first call."""
        agent = Agent(instructions="Be helpful.")
        assert agent.agent_id is None


@pytest.mark.asyncio
class TestAgentRun:
    """Tests for Agent.run method."""

    async def test_run_creates_agent_on_first_call(
        self, mock_client: AsyncMock
    ) -> None:
        """First run creates agent on server."""
        agent = Agent(instructions="Be helpful.")
        agent._client = mock_client

        await agent.run("Hello!")

        mock_client.create_agent.assert_called_once()
        assert agent.agent_id == "agent-123"

    async def test_run_reuses_agent_id(self, mock_client: AsyncMock) -> None:
        """Subsequent runs reuse agent_id."""
        agent = Agent(instructions="Be helpful.")
        agent._client = mock_client

        await agent.run("Hello!")
        await agent.run("How are you?")

        # create_agent only called once
        mock_client.create_agent.assert_called_once()
        # run called twice
        assert mock_client.run.call_count == 2

    async def test_run_returns_response(self, mock_client: AsyncMock) -> None:
        """Run returns RunResponse."""
        agent = Agent(instructions="Be helpful.")
        agent._client = mock_client

        response = await agent.run("Hello!")

        assert response.content == "Hello!"
        assert response.usage.input_tokens == 10


@pytest.mark.asyncio
class TestAgentDelete:
    """Tests for Agent.delete method."""

    async def test_delete_calls_client(self, mock_client: AsyncMock) -> None:
        """Delete calls client.delete_agent."""
        agent = Agent(instructions="Be helpful.")
        agent._client = mock_client
        agent._agent_id = "agent-123"

        await agent.delete()

        mock_client.delete_agent.assert_called_once_with("agent-123")
        assert agent.agent_id is None

    async def test_delete_noop_when_not_created(self, mock_client: AsyncMock) -> None:
        """Delete does nothing if agent not created."""
        agent = Agent(instructions="Be helpful.")
        agent._client = mock_client

        await agent.delete()

        mock_client.delete_agent.assert_not_called()


@pytest.mark.asyncio
class TestAgentContextManager:
    """Tests for Agent as context manager."""

    async def test_context_manager_deletes_on_exit(
        self, mock_client: AsyncMock
    ) -> None:
        """Context manager deletes agent on exit."""
        async with Agent(instructions="Be helpful.") as agent:
            agent._client = mock_client
            agent._agent_id = "agent-123"

        mock_client.delete_agent.assert_called_once()
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
class TestRunFunction:
    """Tests for one-shot run function."""

    async def test_run_creates_and_deletes(self) -> None:
        """run() creates agent, runs, and deletes."""
        mock_response = RunResponse(
            content="42",
            tool_calls=[],
            usage=Usage(input_tokens=5, output_tokens=2),
        )

        with patch("amplifier_sdk.agent.AmplifierClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.create_agent = AsyncMock(return_value="temp-agent")
            mock_instance.run = AsyncMock(return_value=mock_response)
            mock_instance.delete_agent = AsyncMock()
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            response = await run("What is 2+2?")

            assert response.content == "42"
            mock_instance.create_agent.assert_called_once()
            mock_instance.run.assert_called_once()
            mock_instance.delete_agent.assert_called_once()
