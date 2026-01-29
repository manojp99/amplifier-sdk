"""HTTP client for Amplifier server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from amplifier_sdk.models import AgentConfig, AgentInfo, RunResponse, StreamEvent


class AmplifierClient:
    """HTTP client for communicating with Amplifier server.

    Example:
        ```python
        async with AmplifierClient() as client:
            # Create agent
            agent_id = await client.create_agent(
                AgentConfig(
                    instructions="You are helpful.",
                    provider="anthropic",
                    tools=["bash"]
                )
            )

            # Run prompt
            response = await client.run(agent_id, "Hello!")
            print(response.content)

            # Stream response
            async for event in client.stream(agent_id, "Write a poem"):
                if event.text:
                    print(event.text, end="", flush=True)

            # Cleanup
            await client.delete_agent(agent_id)
        ```
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        """Initialize client.

        Args:
            base_url: Server URL (default: http://localhost:8000)
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AmplifierClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # Health
    async def health(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health status dict with version info
        """
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()

    # Modules
    async def list_modules(self) -> dict[str, list[str]]:
        """List available modules.

        Returns:
            Dict mapping category to list of module names
        """
        client = await self._get_client()
        response = await client.get("/modules")
        response.raise_for_status()
        return response.json()

    # Agents
    async def create_agent(self, config: AgentConfig) -> str:
        """Create a new agent.

        Args:
            config: Agent configuration

        Returns:
            Agent ID
        """
        client = await self._get_client()
        response = await client.post("/agents", json=config.to_dict())
        response.raise_for_status()
        return response.json()["agent_id"]

    async def get_agent(self, agent_id: str) -> AgentInfo:
        """Get agent info.

        Args:
            agent_id: Agent ID

        Returns:
            Agent information
        """
        client = await self._get_client()
        response = await client.get(f"/agents/{agent_id}")
        response.raise_for_status()
        return AgentInfo.from_dict(response.json())

    async def list_agents(self) -> list[str]:
        """List all agent IDs.

        Returns:
            List of agent IDs
        """
        client = await self._get_client()
        response = await client.get("/agents")
        response.raise_for_status()
        return response.json()["agents"]

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.

        Args:
            agent_id: Agent ID to delete
        """
        client = await self._get_client()
        response = await client.delete(f"/agents/{agent_id}")
        response.raise_for_status()

    # Execution
    async def run(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> RunResponse:
        """Run a prompt and get response.

        Args:
            agent_id: Agent ID
            prompt: User prompt
            max_turns: Maximum agent turns

        Returns:
            RunResponse with content and tool calls
        """
        client = await self._get_client()
        response = await client.post(
            f"/agents/{agent_id}/run",
            json={"prompt": prompt, "max_turns": max_turns},
        )
        response.raise_for_status()
        return RunResponse.from_dict(response.json())

    async def stream(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a prompt response.

        Args:
            agent_id: Agent ID
            prompt: User prompt
            max_turns: Maximum agent turns

        Yields:
            StreamEvent for each server-sent event
        """
        client = await self._get_client()
        async with client.stream(
            "POST",
            f"/agents/{agent_id}/stream",
            json={"prompt": prompt, "max_turns": max_turns},
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            event_type = "message"
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            yield StreamEvent(event=event_type, data=data)
                        except json.JSONDecodeError:
                            continue

    # Messages
    async def get_messages(self, agent_id: str) -> list[dict[str, Any]]:
        """Get conversation messages for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of messages
        """
        client = await self._get_client()
        response = await client.get(f"/agents/{agent_id}/messages")
        response.raise_for_status()
        return response.json()["messages"]

    async def clear_messages(self, agent_id: str) -> None:
        """Clear conversation messages for an agent.

        Args:
            agent_id: Agent ID
        """
        client = await self._get_client()
        response = await client.delete(f"/agents/{agent_id}/messages")
        response.raise_for_status()

    # One-off execution
    async def run_once(
        self,
        prompt: str,
        instructions: str = "You are a helpful assistant.",
        provider: str = "anthropic",
        model: str | None = None,
        tools: list[str] | None = None,
        max_turns: int = 10,
    ) -> RunResponse:
        """Run a one-off prompt without persistent agent.

        Args:
            prompt: User prompt
            instructions: System instructions
            provider: LLM provider
            model: Model name (optional)
            tools: List of tools (optional)
            max_turns: Maximum agent turns

        Returns:
            RunResponse with content and tool calls
        """
        client = await self._get_client()
        payload: dict[str, Any] = {
            "prompt": prompt,
            "instructions": instructions,
            "provider": provider,
            "max_turns": max_turns,
        }
        if model:
            payload["model"] = model
        if tools:
            payload["tools"] = tools

        response = await client.post("/run", json=payload)
        response.raise_for_status()
        return RunResponse.from_dict(response.json())
