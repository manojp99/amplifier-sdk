"""HTTP client for Amplifier server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from amplifier_sdk.models import (
    AgentConfig,
    AgentInfo,
    ApprovalInfo,
    RecipeConfig,
    RecipeExecution,
    RunResponse,
    SpawnConfig,
    StreamEvent,
    SubAgentInfo,
)


class AmplifierClient:
    """HTTP client for communicating with Amplifier server.

    Example:
        ```python
        async with AmplifierClient() as client:
            # Create agent with full module wiring
            agent_id = await client.create_agent(
                AgentConfig(
                    instructions="You are helpful.",
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                    tools=["bash", "filesystem"],
                    orchestrator="streaming",
                    hooks=["logging"],
                    agents={
                        "researcher": {
                            "instructions": "You research topics.",
                            "tools": ["web_search"]
                        }
                    }
                )
            )

            # Run prompt
            response = await client.run(agent_id, "Hello!")
            print(response.content)

            # Spawn sub-agent
            sub_agent_id = await client.spawn_agent(
                agent_id,
                agent_name="researcher",
                prompt="Research Python async"
            )

            # Stream with rich events
            async for event in client.stream(agent_id, "Write a poem"):
                if event.event == "content:delta":
                    print(event.data.get("text", ""), end="", flush=True)
                elif event.event == "tool:start":
                    print(f"\\nUsing tool: {event.data.get('tool')}")

            # Execute recipe
            execution = await client.execute_recipe(
                recipe=RecipeConfig(
                    name="analysis",
                    steps=[
                        {"id": "step1", "agent": "analyzer", "prompt": "Analyze this"}
                    ]
                ),
                input={"topic": "AI"}
            )

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

    # =========================================================================
    # Health & Modules
    # =========================================================================

    async def health(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health status dict with version info
        """
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()

    async def list_modules(self) -> dict[str, list[str]]:
        """List available modules.

        Returns:
            Dict mapping category to list of module names
        """
        client = await self._get_client()
        response = await client.get("/modules")
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Agent CRUD
    # =========================================================================

    async def create_agent(self, config: AgentConfig) -> str:
        """Create a new agent with full module wiring support.

        Args:
            config: Agent configuration including providers, tools, orchestrator,
                   context manager, hooks, and sub-agent definitions

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
            Agent information including status and available sub-agents
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

    # =========================================================================
    # Execution
    # =========================================================================

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
            RunResponse with content, tool calls, and spawned sub-agents
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
        event_filter: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a prompt response with rich event taxonomy.

        Events include:
        - session:start/end - Session lifecycle
        - prompt:start/complete - Prompt processing
        - content:start/delta/complete - Content streaming
        - tool:start/result - Tool execution
        - agent:spawn/complete - Sub-agent spawning
        - approval:requested/responded - Human-in-loop
        - done - Execution complete

        Args:
            agent_id: Agent ID
            prompt: User prompt
            max_turns: Maximum agent turns
            event_filter: Optional list of event types to receive

        Yields:
            StreamEvent for each server-sent event
        """
        client = await self._get_client()
        payload: dict[str, Any] = {"prompt": prompt, "max_turns": max_turns}
        if event_filter:
            payload["stream_events"] = event_filter

        async with client.stream(
            "POST",
            f"/agents/{agent_id}/stream",
            json=payload,
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

    # =========================================================================
    # Multi-Agent Orchestration
    # =========================================================================

    async def spawn_agent(
        self,
        parent_id: str,
        agent_name: str,
        prompt: str | None = None,
        inherit_context: str = "none",
        inherit_context_turns: int = 5,
    ) -> str:
        """Spawn a sub-agent from a parent agent.

        Args:
            parent_id: Parent agent ID
            agent_name: Name of sub-agent (must be defined in parent's agents config)
            prompt: Optional initial prompt to run
            inherit_context: Context inheritance mode (none, recent, all)
            inherit_context_turns: Number of turns for 'recent' mode

        Returns:
            Sub-agent ID
        """
        client = await self._get_client()
        payload = SpawnConfig(
            agent_name=agent_name,
            prompt=prompt,
            inherit_context=inherit_context,
            inherit_context_turns=inherit_context_turns,
        ).to_dict()

        response = await client.post(f"/agents/{parent_id}/spawn", json=payload)
        response.raise_for_status()
        return response.json()["agent_id"]

    async def list_sub_agents(self, parent_id: str) -> list[SubAgentInfo]:
        """List sub-agents spawned by a parent agent.

        Args:
            parent_id: Parent agent ID

        Returns:
            List of sub-agent info
        """
        client = await self._get_client()
        response = await client.get(f"/agents/{parent_id}/sub-agents")
        response.raise_for_status()
        return [SubAgentInfo.from_dict(sa) for sa in response.json()["sub_agents"]]

    # =========================================================================
    # Approval System
    # =========================================================================

    async def list_pending_approvals(self, agent_id: str) -> list[ApprovalInfo]:
        """List pending approval requests for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of pending approval requests
        """
        client = await self._get_client()
        response = await client.get(f"/agents/{agent_id}/approvals")
        response.raise_for_status()
        return [ApprovalInfo.from_dict(a) for a in response.json()["approvals"]]

    async def approve(
        self,
        agent_id: str,
        approval_id: str,
        reason: str | None = None,
    ) -> None:
        """Approve a pending request.

        Args:
            agent_id: Agent ID
            approval_id: Approval request ID
            reason: Optional reason for approval
        """
        client = await self._get_client()
        response = await client.post(
            f"/agents/{agent_id}/approvals/{approval_id}",
            json={"approved": True, "reason": reason},
        )
        response.raise_for_status()

    async def deny(
        self,
        agent_id: str,
        approval_id: str,
        reason: str | None = None,
    ) -> None:
        """Deny a pending request.

        Args:
            agent_id: Agent ID
            approval_id: Approval request ID
            reason: Optional reason for denial
        """
        client = await self._get_client()
        response = await client.post(
            f"/agents/{agent_id}/approvals/{approval_id}",
            json={"approved": False, "reason": reason},
        )
        response.raise_for_status()

    # =========================================================================
    # Recipes (Multi-Step Workflows)
    # =========================================================================

    async def execute_recipe(
        self,
        recipe: RecipeConfig | None = None,
        recipe_path: str | None = None,
        input: dict[str, Any] | None = None,
    ) -> RecipeExecution:
        """Execute a recipe (multi-step workflow).

        Args:
            recipe: Recipe configuration (inline)
            recipe_path: Path to recipe YAML file
            input: Input variables for the recipe

        Returns:
            Recipe execution with ID and status
        """
        client = await self._get_client()
        payload: dict[str, Any] = {"input": input or {}}
        if recipe:
            payload["recipe"] = recipe.to_dict()
        elif recipe_path:
            payload["recipe_path"] = recipe_path
        else:
            raise ValueError("Either recipe or recipe_path is required")

        response = await client.post("/recipes", json=payload)
        response.raise_for_status()
        return RecipeExecution.from_dict(response.json())

    async def get_recipe_execution(self, execution_id: str) -> RecipeExecution:
        """Get recipe execution status.

        Args:
            execution_id: Recipe execution ID

        Returns:
            Recipe execution with current status
        """
        client = await self._get_client()
        response = await client.get(f"/recipes/{execution_id}")
        response.raise_for_status()
        return RecipeExecution.from_dict(response.json())

    async def stream_recipe(
        self,
        execution_id: str,
    ) -> AsyncIterator[StreamEvent]:
        """Stream events from a recipe execution.

        Events include:
        - recipe:start/complete/failed - Recipe lifecycle
        - step:start/complete/failed/skipped - Step lifecycle
        - approval:requested - Approval needed

        Args:
            execution_id: Recipe execution ID

        Yields:
            StreamEvent for each server-sent event
        """
        client = await self._get_client()
        async with client.stream(
            "GET",
            f"/recipes/{execution_id}/stream",
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

    async def approve_recipe_step(
        self,
        execution_id: str,
        step_id: str,
        reason: str | None = None,
    ) -> None:
        """Approve a recipe step.

        Args:
            execution_id: Recipe execution ID
            step_id: Step ID requiring approval
            reason: Optional reason for approval
        """
        client = await self._get_client()
        response = await client.post(
            f"/recipes/{execution_id}/approvals/{step_id}",
            json={"approved": True, "reason": reason},
        )
        response.raise_for_status()

    async def deny_recipe_step(
        self,
        execution_id: str,
        step_id: str,
        reason: str | None = None,
    ) -> None:
        """Deny a recipe step.

        Args:
            execution_id: Recipe execution ID
            step_id: Step ID requiring approval
            reason: Optional reason for denial
        """
        client = await self._get_client()
        response = await client.post(
            f"/recipes/{execution_id}/approvals/{step_id}",
            json={"approved": False, "reason": reason},
        )
        response.raise_for_status()

    async def list_recipe_executions(self) -> list[RecipeExecution]:
        """List all recipe executions.

        Returns:
            List of recipe executions
        """
        client = await self._get_client()
        response = await client.get("/recipes")
        response.raise_for_status()
        return [RecipeExecution.from_dict(e) for e in response.json()["executions"]]

    async def cancel_recipe(self, execution_id: str) -> None:
        """Cancel a recipe execution.

        Args:
            execution_id: Recipe execution ID
        """
        client = await self._get_client()
        response = await client.delete(f"/recipes/{execution_id}")
        response.raise_for_status()

    # =========================================================================
    # Messages
    # =========================================================================

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

    # =========================================================================
    # One-off Execution
    # =========================================================================

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
