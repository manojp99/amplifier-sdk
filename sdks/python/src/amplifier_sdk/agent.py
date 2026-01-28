"""High-level Agent API for Amplifier SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from amplifier_sdk.client import AmplifierClient
from amplifier_sdk.models import AgentConfig, RunResponse, StreamEvent


class Agent:
    """High-level agent interface for Amplifier.

    Example:
        ```python
        # Simple usage
        agent = Agent(instructions="You help with code.")
        response = await agent.run("Hello!")
        print(response.content)

        # With tools
        agent = Agent(
            instructions="You are a coding assistant.",
            tools=["filesystem", "bash"],
            provider="anthropic",
            model="claude-sonnet-4-20250514"
        )

        # Streaming
        async for event in agent.stream("Write a poem"):
            print(event.content, end="")

        # Multi-turn conversation
        await agent.run("Remember my name is Alice")
        await agent.run("What's my name?")  # Remembers context

        # Clean up when done
        await agent.delete()
        ```
    """

    def __init__(
        self,
        instructions: str,
        tools: list[str] | None = None,
        provider: str = "anthropic",
        model: str | None = None,
        bundle: str | None = None,
        base_url: str = "http://localhost:8080",
        api_key: str | None = None,
    ) -> None:
        """Create an agent.

        Args:
            instructions: System instructions for the agent
            tools: List of tools to enable (e.g., ["filesystem", "bash"])
            provider: LLM provider (default: anthropic)
            model: Model name (optional, uses provider default)
            bundle: Bundle path for advanced configuration (optional)
            base_url: Server URL (default: http://localhost:8080)
            api_key: API key for authentication (optional)
        """
        self.config = AgentConfig(
            instructions=instructions,
            tools=tools or [],
            provider=provider,
            model=model,
            bundle=bundle,
        )
        self._client = AmplifierClient(base_url=base_url, api_key=api_key)
        self._agent_id: str | None = None

    @property
    def agent_id(self) -> str | None:
        """Get the agent ID (None if not yet created)."""
        return self._agent_id

    async def _ensure_created(self) -> str:
        """Ensure agent is created on server, return agent_id."""
        if self._agent_id is None:
            self._agent_id = await self._client.create_agent(
                instructions=self.config.instructions,
                tools=self.config.tools,
                provider=self.config.provider,
                model=self.config.model,
                bundle=self.config.bundle,
            )
        return self._agent_id

    async def run(self, prompt: str) -> RunResponse:
        """Run a prompt and get response.

        Args:
            prompt: User message

        Returns:
            RunResponse with content, tool_calls, and usage
        """
        agent_id = await self._ensure_created()
        return await self._client.run(agent_id, prompt)

    async def stream(self, prompt: str) -> AsyncIterator[StreamEvent]:
        """Stream a prompt response.

        Args:
            prompt: User message

        Yields:
            StreamEvent for each token/event
        """
        agent_id = await self._ensure_created()
        async for event in self._client.stream(agent_id, prompt):
            yield event

    async def delete(self) -> None:
        """Delete the agent from server."""
        if self._agent_id:
            await self._client.delete_agent(self._agent_id)
            self._agent_id = None

    async def close(self) -> None:
        """Close the client connection."""
        await self._client.close()

    async def __aenter__(self) -> Agent:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - deletes agent and closes client."""
        await self.delete()
        await self.close()


# Convenience function for one-shot usage
async def run(
    prompt: str,
    instructions: str = "You are a helpful assistant.",
    tools: list[str] | None = None,
    provider: str = "anthropic",
    base_url: str = "http://localhost:8080",
    api_key: str | None = None,
) -> RunResponse:
    """One-shot prompt execution.

    Creates an agent, runs the prompt, and cleans up.

    Example:
        ```python
        from amplifier_sdk import run

        response = await run("What is 2+2?")
        print(response.content)
        ```
    """
    async with Agent(
        instructions=instructions,
        tools=tools,
        provider=provider,
        base_url=base_url,
        api_key=api_key,
    ) as agent:
        return await agent.run(prompt)
