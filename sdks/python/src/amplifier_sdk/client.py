"""HTTP client for Amplifier server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from amplifier_sdk.models import RecipeExecution, RunResponse, StreamEvent


class AmplifierClient:
    """HTTP client for communicating with Amplifier server.

    Example:
        ```python
        client = AmplifierClient()

        # Create agent
        agent_id = await client.create_agent(
            instructions="You are helpful.",
            tools=["bash"]
        )

        # Run prompt
        response = await client.run(agent_id, "Hello!")
        print(response.content)

        # Stream response
        async for event in client.stream(agent_id, "Write a poem"):
            print(event.content, end="")
        ```
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        """Initialize client.

        Args:
            base_url: Server URL (default: http://localhost:8080)
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
        """Check server health."""
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()

    # Agents
    async def create_agent(
        self,
        instructions: str,
        tools: list[str] | None = None,
        provider: str = "anthropic",
        model: str | None = None,
        bundle: str | None = None,
    ) -> str:
        """Create a new agent.

        Args:
            instructions: System instructions for the agent
            tools: List of tools to enable
            provider: LLM provider (default: anthropic)
            model: Model name (optional)
            bundle: Bundle path (optional)

        Returns:
            Agent ID
        """
        client = await self._get_client()
        payload: dict[str, Any] = {
            "instructions": instructions,
            "provider": provider,
        }
        if tools:
            payload["tools"] = tools
        if model:
            payload["model"] = model
        if bundle:
            payload["bundle"] = bundle

        response = await client.post("/agents", json=payload)
        response.raise_for_status()
        return response.json()["agent_id"]

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get agent info."""
        client = await self._get_client()
        response = await client.get(f"/agents/{agent_id}")
        response.raise_for_status()
        return response.json()

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all agents."""
        client = await self._get_client()
        response = await client.get("/agents")
        response.raise_for_status()
        return response.json()["agents"]

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        client = await self._get_client()
        response = await client.delete(f"/agents/{agent_id}")
        response.raise_for_status()

    async def run(self, agent_id: str, prompt: str) -> RunResponse:
        """Run a prompt and get response.

        Args:
            agent_id: Agent ID
            prompt: User prompt

        Returns:
            RunResponse with content and tool calls
        """
        client = await self._get_client()
        response = await client.post(
            f"/agents/{agent_id}/run",
            json={"prompt": prompt},
        )
        response.raise_for_status()
        return RunResponse.from_dict(response.json())

    async def stream(
        self,
        agent_id: str,
        prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a prompt response.

        Args:
            agent_id: Agent ID
            prompt: User prompt

        Yields:
            StreamEvent for each server-sent event
        """
        client = await self._get_client()
        async with client.stream(
            "POST",
            f"/agents/{agent_id}/stream",
            json={"prompt": prompt},
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        try:
                            data = json.loads(data_str)
                            yield StreamEvent(
                                event=data.get("event", "message"),
                                data=data,
                            )
                        except json.JSONDecodeError:
                            continue

    # Recipes
    async def execute_recipe(
        self,
        recipe_path: str | None = None,
        recipe_yaml: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Execute a recipe.

        Args:
            recipe_path: Path to recipe file
            recipe_yaml: Inline recipe YAML
            context: Context variables

        Returns:
            Execution ID
        """
        client = await self._get_client()
        payload: dict[str, Any] = {}
        if recipe_path:
            payload["recipe_path"] = recipe_path
        if recipe_yaml:
            payload["recipe_yaml"] = recipe_yaml
        if context:
            payload["context"] = context

        response = await client.post("/recipes/execute", json=payload)
        response.raise_for_status()
        return response.json()["execution_id"]

    async def get_recipe_execution(self, execution_id: str) -> RecipeExecution:
        """Get recipe execution status."""
        client = await self._get_client()
        response = await client.get(f"/recipes/{execution_id}")
        response.raise_for_status()
        return RecipeExecution.from_dict(response.json())

    async def approve_gate(self, execution_id: str, step_id: str) -> None:
        """Approve a recipe gate."""
        client = await self._get_client()
        response = await client.post(
            f"/recipes/{execution_id}/approve",
            json={"step_id": step_id},
        )
        response.raise_for_status()

    async def deny_gate(
        self,
        execution_id: str,
        step_id: str,
        reason: str = "",
    ) -> None:
        """Deny a recipe gate."""
        client = await self._get_client()
        response = await client.post(
            f"/recipes/{execution_id}/deny",
            json={"step_id": step_id, "reason": reason},
        )
        response.raise_for_status()
