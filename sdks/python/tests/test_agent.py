"""Tests for Agent class."""

from unittest.mock import AsyncMock

import pytest

from amplifier_sdk.agent import Agent, run
from amplifier_sdk.models import AgentInfo, RunResponse, Usage


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create mock client."""
    client = AsyncMock()
    client.create_agent = AsyncMock(return_value="ag_test123")
    client.run = AsyncMock(
        return_value=RunResponse(
            content="Hello!",
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
            turn_count=1,
        )
    )
    client.get_agent = AsyncMock(
        return_value=AgentInfo(
            agent_id="ag_test123",
            created_at="2024-01-01T00:00:00Z",
            status="ready",
            instructions="Be helpful.",
            provider="anthropic",
            tools=["bash"],
            message_count=2,
        )
    )
    client.get_messages = AsyncMock(
        return_value=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
    )
    client.clear_messages = AsyncMock()
    client.delete_agent = AsyncMock()
    client.close = AsyncMock()
    return client


class TestAgentCreate:
    """Tests for Agent.create factory method."""

    @pytest.mark.asyncio
    async def test_create_agent(self, mock_client: AsyncMock) -> None:
        """Agent.create creates agent on server."""
        agent = await Agent.create(
            mock_client,
            instructions="Be helpful.",
            provider="anthropic",
        )

        mock_client.create_agent.assert_called_once()
        assert agent.agent_id == "ag_test123"
        assert agent.instructions == "Be helpful."
        assert agent.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_create_with_tools(self, mock_client: AsyncMock) -> None:
        """Agent.create accepts tools."""
        agent = await Agent.create(
            mock_client,
            instructions="Be helpful.",
            tools=["bash", "filesystem"],
        )

        assert agent.tools == ["bash", "filesystem"]

    @pytest.mark.asyncio
    async def test_create_with_model(self, mock_client: AsyncMock) -> None:
        """Agent.create accepts model."""
        agent = await Agent.create(
            mock_client,
            instructions="Be helpful.",
            model="claude-sonnet-4-20250514",
        )

        assert agent.model == "claude-sonnet-4-20250514"


class TestAgentRun:
    """Tests for Agent.run method."""

    @pytest.mark.asyncio
    async def test_run_calls_client(self, mock_client: AsyncMock) -> None:
        """Run calls client.run with agent_id."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        response = await agent.run("Hello!")

        mock_client.run.assert_called_once_with("ag_test123", "Hello!", 10)
        assert response.content == "Hello!"

    @pytest.mark.asyncio
    async def test_run_with_max_turns(self, mock_client: AsyncMock) -> None:
        """Run accepts max_turns parameter."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        await agent.run("Work hard", max_turns=20)

        mock_client.run.assert_called_with("ag_test123", "Work hard", 20)

    @pytest.mark.asyncio
    async def test_run_after_delete_raises(self, mock_client: AsyncMock) -> None:
        """Run raises error after agent deleted."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")
        await agent.delete()

        with pytest.raises(RuntimeError, match="has been deleted"):
            await agent.run("Hello!")


class TestAgentInfo:
    """Tests for Agent info methods."""

    @pytest.mark.asyncio
    async def test_get_info(self, mock_client: AsyncMock) -> None:
        """get_info returns agent information."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        info = await agent.get_info()

        mock_client.get_agent.assert_called_with("ag_test123")
        assert info.agent_id == "ag_test123"
        assert info.status == "ready"

    @pytest.mark.asyncio
    async def test_get_messages(self, mock_client: AsyncMock) -> None:
        """get_messages returns conversation history."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        messages = await agent.get_messages()

        mock_client.get_messages.assert_called_with("ag_test123")
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_clear_messages(self, mock_client: AsyncMock) -> None:
        """clear_messages calls client."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        await agent.clear_messages()

        mock_client.clear_messages.assert_called_with("ag_test123")


class TestAgentDelete:
    """Tests for Agent.delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_client(self, mock_client: AsyncMock) -> None:
        """Delete calls client.delete_agent."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        await agent.delete()

        mock_client.delete_agent.assert_called_once_with("ag_test123")

    @pytest.mark.asyncio
    async def test_delete_twice_is_noop(self, mock_client: AsyncMock) -> None:
        """Delete twice only calls client once."""
        agent = await Agent.create(mock_client, instructions="Be helpful.")

        await agent.delete()
        await agent.delete()

        # Only called once
        mock_client.delete_agent.assert_called_once()


class TestAgentContextManager:
    """Tests for Agent as context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_deletes_on_exit(
        self, mock_client: AsyncMock
    ) -> None:
        """Context manager deletes agent on exit."""
        async with await Agent.create(mock_client, instructions="Be helpful.") as agent:
            assert agent.agent_id == "ag_test123"

        mock_client.delete_agent.assert_called_once()


class TestRunFunction:
    """Tests for one-shot run function."""

    @pytest.mark.asyncio
    async def test_run_function(self) -> None:
        """run() creates client and calls run_once."""
        # This test would need to mock the client creation
        # For now, we just test the function exists
        assert callable(run)
