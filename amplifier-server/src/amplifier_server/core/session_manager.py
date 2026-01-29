"""Session manager for Amplifier agents - wraps amplifier-core directly."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from amplifier_server.core.config_translator import translate_to_mount_plan
from amplifier_server.core.module_resolver import ServerModuleResolver


class AgentStatus(str, Enum):
    """Status of an agent."""

    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    DELETED = "deleted"


@dataclass
class AgentState:
    """State of an agent (wraps a Core session)."""

    agent_id: str
    created_at: datetime
    status: AgentStatus = AgentStatus.READY
    sdk_config: dict[str, Any] = field(default_factory=dict)
    mount_plan: dict[str, Any] = field(default_factory=dict)
    session: Any | None = None  # AmplifierSession from core
    messages: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def instructions(self) -> str | None:
        """Get the agent's instructions."""
        return self.sdk_config.get("instructions")

    @property
    def provider(self) -> str | None:
        """Get the agent's provider."""
        return self.sdk_config.get("provider")

    @property
    def model(self) -> str | None:
        """Get the agent's model."""
        return self.sdk_config.get("model")

    @property
    def tools(self) -> list[str]:
        """Get the agent's tools."""
        return self.sdk_config.get("tools", [])


@dataclass
class StreamEvent:
    """An event from streaming execution."""

    event: str
    data: dict[str, Any]


class SessionManager:
    """
    Manages agent sessions using amplifier-core directly.

    This is the core component that:
    1. Translates SDK config → Core mount plan
    2. Creates and manages AmplifierSession instances
    3. Bridges Core events → SSE stream
    """

    def __init__(self, resolver: ServerModuleResolver | None = None):
        """
        Initialize the session manager.

        Args:
            resolver: Module resolver for finding modules. Uses default if not provided.
        """
        self.resolver = resolver or ServerModuleResolver()
        self.agents: dict[str, AgentState] = {}
        self._lock = asyncio.Lock()

    async def create_agent(self, sdk_config: dict[str, Any]) -> AgentState:
        """
        Create a new agent from SDK configuration.

        Args:
            sdk_config: User-friendly configuration
                {
                    "instructions": "You are helpful",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-20250514",
                    "tools": ["bash", "filesystem"],
                }

        Returns:
            AgentState with the new agent
        """
        # Generate agent ID
        agent_id = f"ag_{uuid.uuid4().hex[:12]}"

        # Translate to mount plan
        mount_plan = translate_to_mount_plan(sdk_config)

        # Create agent state (session created lazily on first run)
        agent = AgentState(
            agent_id=agent_id,
            created_at=datetime.utcnow(),
            status=AgentStatus.READY,
            sdk_config=sdk_config,
            mount_plan=mount_plan,
        )

        # Store agent
        async with self._lock:
            self.agents[agent_id] = agent

        return agent

    async def get_agent(self, agent_id: str) -> AgentState | None:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    async def list_agents(self) -> list[str]:
        """List all agent IDs."""
        return list(self.agents.keys())

    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent and cleanup its session.

        Returns:
            True if agent was deleted, False if not found
        """
        async with self._lock:
            agent = self.agents.pop(agent_id, None)
            if agent is None:
                return False

            # Cleanup session if exists
            if agent.session is not None:
                with contextlib.suppress(Exception):
                    await agent.session.cleanup()

            agent.status = AgentStatus.DELETED
            return True

    async def run(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> dict[str, Any]:
        """
        Run a prompt on an agent (non-streaming).

        Args:
            agent_id: The agent ID
            prompt: User prompt
            max_turns: Maximum execution turns

        Returns:
            Result dict with content, tool_calls, usage, turn_count
        """
        # Collect all events from streaming
        events = []
        async for event in self.stream(agent_id, prompt, max_turns):
            events.append(event)

        # Extract final result from events
        content = ""
        tool_calls = []
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        turn_count = 1

        for event in events:
            if event.event == "content_delta":
                content += event.data.get("text", "")
            elif event.event == "tool_use":
                tool_calls.append(event.data)
            elif event.event == "done":
                content = event.data.get("content", content)
                turn_count = event.data.get("turn_count", turn_count)
            elif event.event == "message_end" and "usage" in event.data:
                usage = event.data["usage"]

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage,
            "turn_count": turn_count,
        }

    async def stream(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream execution of a prompt on an agent.

        Args:
            agent_id: The agent ID
            prompt: User prompt
            max_turns: Maximum execution turns

        Yields:
            StreamEvent objects with event type and data
        """
        agent = self.agents.get(agent_id)
        if agent is None:
            yield StreamEvent(event="error", data={"message": f"Agent not found: {agent_id}"})
            return

        if agent.status == AgentStatus.DELETED:
            yield StreamEvent(event="error", data={"message": "Agent has been deleted"})
            return

        # Mark as running
        agent.status = AgentStatus.RUNNING

        try:
            # Initialize session if needed
            if agent.session is None:
                await self._initialize_session(agent)

            # Add user message to context
            agent.messages.append({"role": "user", "content": prompt})

            # Execute with event streaming
            async for event in self._execute_with_events(agent, prompt, max_turns):
                yield event

            agent.status = AgentStatus.READY

        except Exception as e:
            agent.status = AgentStatus.ERROR
            agent.error = str(e)
            yield StreamEvent(event="error", data={"message": str(e)})

    async def _initialize_session(self, agent: AgentState) -> None:
        """
        Initialize the Core session for an agent.

        This is where we would import and use amplifier-core.
        For now, we use a mock implementation.
        """
        # TODO: Replace with actual amplifier-core integration
        # from amplifier_core import AmplifierSession
        # agent.session = AmplifierSession(agent.mount_plan)
        # agent.session.coordinator.mount("module-source-resolver", self.resolver)
        # await agent.session.initialize()

        # Add system message with instructions
        if agent.sdk_config.get("instructions"):
            agent.messages.insert(
                0, {"role": "system", "content": agent.sdk_config["instructions"]}
            )

        # Mock session for now
        agent.session = MockSession(agent)

    async def _execute_with_events(
        self,
        agent: AgentState,
        prompt: str,
        max_turns: int,
    ) -> AsyncIterator[StreamEvent]:
        """Execute prompt and yield events."""
        # Start message
        yield StreamEvent(event="message_start", data={"id": f"msg_{uuid.uuid4().hex[:8]}"})

        # TODO: Replace with actual Core execution that streams events
        # For now, mock the streaming behavior

        if agent.session is None:
            yield StreamEvent(event="error", data={"message": "Session not initialized"})
            return

        # Mock execution - in real implementation this would:
        # 1. Register hook to capture events
        # 2. Call session.execute(prompt)
        # 3. Yield events as they come from the hook

        result = await agent.session.execute(prompt)

        # Simulate content streaming
        content = result.get("content", "")
        chunk_size = 20
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            yield StreamEvent(event="content_delta", data={"text": chunk})
            await asyncio.sleep(0.01)  # Simulate streaming delay

        # Tool calls
        for tool_call in result.get("tool_calls", []):
            yield StreamEvent(event="tool_use", data=tool_call)
            yield StreamEvent(
                event="tool_result",
                data={"tool": tool_call["name"], "output": tool_call.get("output", "")},
            )

        # End message
        yield StreamEvent(
            event="message_end",
            data={
                "usage": result.get("usage", {"input_tokens": 0, "output_tokens": 0}),
            },
        )

        # Store assistant response
        agent.messages.append({"role": "assistant", "content": content})

        # Done
        yield StreamEvent(
            event="done",
            data={
                "content": content,
                "turn_count": result.get("turn_count", 1),
            },
        )

    async def get_messages(self, agent_id: str) -> list[dict[str, Any]]:
        """Get conversation messages for an agent."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return []
        return agent.messages

    async def clear_messages(self, agent_id: str) -> bool:
        """Clear conversation messages for an agent."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return False

        # Keep system message if present
        system_messages = [m for m in agent.messages if m.get("role") == "system"]
        agent.messages = system_messages
        return True

    @property
    def active_count(self) -> int:
        """Number of active agents."""
        return len(self.agents)


class MockSession:
    """
    Mock session for development/testing.

    This will be replaced with actual amplifier-core integration.
    """

    def __init__(self, agent: AgentState):
        self.agent = agent

    async def execute(self, prompt: str) -> dict[str, Any]:
        """Mock execution that returns a simple response."""
        # In real implementation, this calls the orchestrator
        return {
            "content": f"I received your message: '{prompt}'. "
            f"I'm an agent with provider '{self.agent.provider}' "
            f"and tools {self.agent.tools}.",
            "tool_calls": [],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "turn_count": 1,
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
