"""High-level Agent interface for Amplifier SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from amplifier_sdk.models import AgentConfig, AgentInfo, RunResponse, StreamEvent

if TYPE_CHECKING:
    from amplifier_sdk.client import AmplifierClient


class Agent:
    """High-level interface for interacting with an Amplifier agent.

    Example:
        ```python
        from amplifier_sdk import AmplifierClient, Agent

        async with AmplifierClient() as client:
            # Create agent with context manager for auto-cleanup
            async with Agent.create(
                client,
                instructions="You are a coding assistant.",
                provider="anthropic",
                tools=["bash", "filesystem"]
            ) as agent:
                # Run prompt
                response = await agent.run("Create a Python project")
                print(response.content)

                # Stream response
                async for event in agent.stream("Add a README"):
                    if event.text:
                        print(event.text, end="", flush=True)

                # Conversation continues automatically
                response = await agent.run("Now add tests")
        ```
    """

    def __init__(
        self,
        client: AmplifierClient,
        agent_id: str,
        config: AgentConfig,
    ) -> None:
        """Initialize agent.

        Note: Use Agent.create() instead of direct construction.

        Args:
            client: AmplifierClient instance
            agent_id: Agent ID from server
            config: Agent configuration
        """
        self._client = client
        self._agent_id = agent_id
        self._config = config
        self._deleted = False

    @property
    def agent_id(self) -> str:
        """Get the agent ID."""
        return self._agent_id

    @property
    def instructions(self) -> str:
        """Get the agent's instructions."""
        return self._config.instructions

    @property
    def provider(self) -> str | None:
        """Get the agent's provider."""
        return self._config.provider

    @property
    def model(self) -> str | None:
        """Get the agent's model."""
        return self._config.model

    @property
    def tools(self) -> list[Any]:
        """Get the agent's enabled tools (strings or ToolConfig objects)."""
        return list(self._config.tools)

    @classmethod
    async def create(
        cls,
        client: AmplifierClient,
        instructions: str,
        provider: str = "anthropic",
        model: str | None = None,
        tools: list[str] | None = None,
        orchestrator: str = "basic",
        context_manager: str = "simple",
        hooks: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Agent:
        """Create a new agent.

        Args:
            client: AmplifierClient instance
            instructions: System instructions for the agent
            provider: LLM provider (default: anthropic)
            model: Model name (optional, uses provider default)
            tools: List of tools to enable
            orchestrator: Execution strategy (default: basic)
            context_manager: Memory management (default: simple)
            hooks: Lifecycle hooks to enable
            config: Additional configuration

        Returns:
            Agent instance
        """
        agent_config = AgentConfig(
            instructions=instructions,
            provider=provider,
            model=model,
            tools=list(tools) if tools else [],
            orchestrator=orchestrator,
            context_manager=context_manager,
            hooks=list(hooks) if hooks else [],
            config=config or {},
        )

        agent_id = await client.create_agent(agent_config)
        return cls(client, agent_id, agent_config)

    async def run(self, prompt: str, max_turns: int = 10) -> RunResponse:
        """Run a prompt and get response.

        Args:
            prompt: User prompt
            max_turns: Maximum agent turns

        Returns:
            RunResponse with content and tool calls
        """
        self._check_deleted()
        return await self._client.run(self._agent_id, prompt, max_turns)

    async def stream(
        self,
        prompt: str,
        max_turns: int = 10,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a prompt response.

        Args:
            prompt: User prompt
            max_turns: Maximum agent turns

        Yields:
            StreamEvent for each server-sent event
        """
        self._check_deleted()
        async for event in self._client.stream(self._agent_id, prompt, max_turns):
            yield event

    async def get_info(self) -> AgentInfo:
        """Get current agent information.

        Returns:
            AgentInfo with status and message count
        """
        self._check_deleted()
        return await self._client.get_agent(self._agent_id)

    async def get_messages(self) -> list[dict[str, Any]]:
        """Get conversation messages.

        Returns:
            List of conversation messages
        """
        self._check_deleted()
        return await self._client.get_messages(self._agent_id)

    async def clear_messages(self) -> None:
        """Clear conversation history (keeps system message)."""
        self._check_deleted()
        await self._client.clear_messages(self._agent_id)

    async def delete(self) -> None:
        """Delete this agent and cleanup resources."""
        if not self._deleted:
            await self._client.delete_agent(self._agent_id)
            self._deleted = True

    def _check_deleted(self) -> None:
        """Raise error if agent has been deleted."""
        if self._deleted:
            raise RuntimeError(f"Agent {self._agent_id} has been deleted")

    async def __aenter__(self) -> Agent:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - auto-delete agent."""
        await self.delete()


# Convenience function for one-off execution
async def run(
    prompt: str,
    instructions: str = "You are a helpful assistant.",
    provider: str = "anthropic",
    model: str | None = None,
    tools: list[str] | None = None,
    base_url: str = "http://localhost:8000",
) -> RunResponse:
    """Run a one-off prompt without persistent agent.

    Convenience function for simple use cases.

    Example:
        ```python
        from amplifier_sdk import run

        response = await run(
            "What is 2 + 2?",
            provider="anthropic"
        )
        print(response.content)
        ```

    Args:
        prompt: User prompt
        instructions: System instructions
        provider: LLM provider
        model: Model name (optional)
        tools: List of tools (optional)
        base_url: Server URL

    Returns:
        RunResponse with content
    """
    from amplifier_sdk.client import AmplifierClient

    async with AmplifierClient(base_url=base_url) as client:
        return await client.run_once(
            prompt=prompt,
            instructions=instructions,
            provider=provider,
            model=model,
            tools=tools,
        )
