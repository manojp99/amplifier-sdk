"""Session manager for Amplifier agents - wraps amplifier-core directly."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from amplifier_server.core.config_translator import (
    translate_sub_agent_config,
    translate_to_mount_plan,
)
from amplifier_server.core.module_resolver import ServerModuleResolver


class AgentStatus(str, Enum):
    """Status of an agent."""

    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    DELETED = "deleted"


@dataclass
class ApprovalRequest:
    """A pending approval request."""

    approval_id: str
    agent_id: str
    tool: str
    action: str
    args: dict[str, Any]
    created_at: datetime
    timeout_at: datetime
    resolved: bool = False
    approved: bool | None = None
    reason: str | None = None


@dataclass
class SubAgentInfo:
    """Info about a spawned sub-agent."""

    agent_id: str
    parent_id: str
    agent_name: str
    created_at: datetime


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

    # Multi-agent support
    parent_id: str | None = None
    sub_agents: list[SubAgentInfo] = field(default_factory=list)

    # Approval support
    pending_approvals: list[ApprovalRequest] = field(default_factory=list)

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
        tools = self.sdk_config.get("tools", [])
        return [t if isinstance(t, str) else t.get("module", "") for t in tools]

    @property
    def orchestrator(self) -> str | None:
        """Get the agent's orchestrator."""
        orch = self.sdk_config.get("orchestrator", "basic")
        return orch if isinstance(orch, str) else orch.get("module", "basic")

    @property
    def context_manager(self) -> str | None:
        """Get the agent's context manager."""
        ctx = self.sdk_config.get("context_manager", "simple")
        return ctx if isinstance(ctx, str) else ctx.get("module", "simple")

    @property
    def hooks(self) -> list[str]:
        """Get the agent's hooks."""
        hooks = self.sdk_config.get("hooks", [])
        return [h if isinstance(h, str) else h.get("module", "") for h in hooks]

    @property
    def available_agents(self) -> list[str]:
        """Get available sub-agent names."""
        return list(self.sdk_config.get("agents", {}).keys())

    @property
    def has_approval_config(self) -> bool:
        """Check if agent has approval configuration."""
        return bool(self.sdk_config.get("approval"))


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
    4. Handles multi-agent orchestration
    5. Manages approval workflows
    """

    def __init__(self, resolver: ServerModuleResolver | None = None):
        """Initialize the session manager."""
        self.resolver = resolver or ServerModuleResolver()
        self.agents: dict[str, AgentState] = {}
        self._lock = asyncio.Lock()

    # =========================================================================
    # Agent CRUD
    # =========================================================================

    async def create_agent(self, sdk_config: dict[str, Any]) -> AgentState:
        """Create a new agent from SDK configuration."""
        agent_id = f"ag_{uuid.uuid4().hex[:12]}"
        mount_plan = translate_to_mount_plan(sdk_config)

        agent = AgentState(
            agent_id=agent_id,
            created_at=datetime.utcnow(),
            status=AgentStatus.READY,
            sdk_config=sdk_config,
            mount_plan=mount_plan,
        )

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
        """Delete an agent and cleanup its session."""
        async with self._lock:
            agent = self.agents.pop(agent_id, None)
            if agent is None:
                return False

            # Cleanup sub-agents
            for sub in agent.sub_agents:
                await self.delete_agent(sub.agent_id)

            # Cleanup session if exists
            if agent.session is not None:
                with contextlib.suppress(Exception):
                    await agent.session.cleanup()

            agent.status = AgentStatus.DELETED
            return True

    # =========================================================================
    # Multi-Agent Orchestration
    # =========================================================================

    async def spawn_agent(
        self,
        parent_id: str,
        agent_name: str,
        inherit_context: str = "none",
        inherit_context_turns: int = 5,
    ) -> AgentState | None:
        """
        Spawn a sub-agent from a parent agent.

        Args:
            parent_id: The parent agent's ID
            agent_name: Name of the sub-agent (from parent's agents config)
            inherit_context: Context inheritance mode (none, recent, all)
            inherit_context_turns: Number of turns for 'recent' mode

        Returns:
            The spawned agent state, or None if parent/agent_name not found
        """
        parent = self.agents.get(parent_id)
        if parent is None:
            return None

        # Get sub-agent config from parent
        agents_config = parent.sdk_config.get("agents", {})
        sub_agent_config = agents_config.get(agent_name)
        if sub_agent_config is None:
            return None

        # Convert to dict if needed
        if hasattr(sub_agent_config, "model_dump"):
            sub_agent_config = sub_agent_config.model_dump(exclude_none=True)

        # Translate config with parent inheritance
        mount_plan = translate_sub_agent_config(parent.sdk_config, sub_agent_config)

        # Create sub-agent
        agent_id = f"ag_{uuid.uuid4().hex[:12]}"
        sub_agent = AgentState(
            agent_id=agent_id,
            created_at=datetime.utcnow(),
            status=AgentStatus.READY,
            sdk_config={**sub_agent_config, "provider": parent.provider, "model": parent.model},
            mount_plan=mount_plan,
            parent_id=parent_id,
        )

        # Inherit context if requested
        if inherit_context == "recent":
            # Copy last N messages (excluding system)
            user_assistant_msgs = [m for m in parent.messages if m.get("role") != "system"]
            sub_agent.messages = user_assistant_msgs[-inherit_context_turns * 2 :]
        elif inherit_context == "all":
            sub_agent.messages = [m for m in parent.messages if m.get("role") != "system"]

        # Add system message for sub-agent
        if sub_agent_config.get("instructions"):
            sub_agent.messages.insert(
                0, {"role": "system", "content": sub_agent_config["instructions"]}
            )

        # Store sub-agent
        async with self._lock:
            self.agents[agent_id] = sub_agent
            parent.sub_agents.append(
                SubAgentInfo(
                    agent_id=agent_id,
                    parent_id=parent_id,
                    agent_name=agent_name,
                    created_at=datetime.utcnow(),
                )
            )

        return sub_agent

    async def list_sub_agents(self, parent_id: str) -> list[SubAgentInfo]:
        """List sub-agents for a parent agent."""
        parent = self.agents.get(parent_id)
        if parent is None:
            return []
        return parent.sub_agents

    # =========================================================================
    # Approval System
    # =========================================================================

    async def create_approval_request(
        self,
        agent_id: str,
        tool: str,
        action: str,
        args: dict[str, Any],
        timeout_seconds: int = 300,
    ) -> ApprovalRequest | None:
        """Create a pending approval request."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return None

        now = datetime.utcnow()
        request = ApprovalRequest(
            approval_id=f"apr_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            tool=tool,
            action=action,
            args=args,
            created_at=now,
            timeout_at=now + timedelta(seconds=timeout_seconds),
        )

        agent.pending_approvals.append(request)
        agent.status = AgentStatus.WAITING_APPROVAL
        return request

    async def list_pending_approvals(self, agent_id: str) -> list[ApprovalRequest]:
        """List pending approval requests for an agent."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return []
        return [a for a in agent.pending_approvals if not a.resolved]

    async def respond_to_approval(
        self,
        agent_id: str,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
    ) -> ApprovalRequest | None:
        """Respond to an approval request."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return None

        for request in agent.pending_approvals:
            if request.approval_id == approval_id and not request.resolved:
                request.resolved = True
                request.approved = approved
                request.reason = reason

                # Update agent status if no more pending approvals
                if not any(not a.resolved for a in agent.pending_approvals):
                    agent.status = AgentStatus.READY

                return request

        return None

    # =========================================================================
    # Execution
    # =========================================================================

    async def run(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> dict[str, Any]:
        """Run a prompt on an agent (non-streaming)."""
        events = []
        async for event in self.stream(agent_id, prompt, max_turns):
            events.append(event)

        # Extract final result from events
        content = ""
        tool_calls = []
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        turn_count = 1
        sub_agents_spawned = []

        for event in events:
            if event.event == "content:delta":
                content += event.data.get("text", "")
            elif event.event == "tool:start":
                tool_calls.append(event.data)
            elif event.event == "agent:spawn":
                sub_agents_spawned.append(event.data.get("agent_name"))
            elif event.event == "done":
                content = event.data.get("content", content)
                turn_count = event.data.get("turn_count", turn_count)
            elif event.event == "session:end" and "usage" in event.data:
                usage = event.data["usage"]

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage,
            "turn_count": turn_count,
            "sub_agents_spawned": sub_agents_spawned,
        }

    async def stream(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
        event_filter: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream execution of a prompt on an agent with rich events."""
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

            # Emit session start
            yield StreamEvent(
                event="session:start",
                data={"session_id": agent.agent_id, "prompt": prompt[:100]},
            )

            # Emit prompt start
            yield StreamEvent(
                event="prompt:start",
                data={"prompt": prompt, "max_turns": max_turns},
            )

            # Add user message to context
            agent.messages.append({"role": "user", "content": prompt})

            # Execute with event streaming
            async for event in self._execute_with_events(agent, prompt, max_turns):
                # Filter events if requested
                if event_filter is None or event.event in event_filter:
                    yield event

            # Emit prompt complete
            yield StreamEvent(
                event="prompt:complete",
                data={"turns": 1},
            )

            agent.status = AgentStatus.READY

        except Exception as e:
            agent.status = AgentStatus.ERROR
            agent.error = str(e)
            yield StreamEvent(event="error", data={"message": str(e)})

    async def _initialize_session(self, agent: AgentState) -> None:
        """Initialize the Core session for an agent."""
        # Add system message with instructions
        if agent.sdk_config.get("instructions"):
            agent.messages.insert(
                0, {"role": "system", "content": agent.sdk_config["instructions"]}
            )

        # TODO: Replace with actual amplifier-core integration
        agent.session = MockSession(agent, self)

    async def _execute_with_events(
        self,
        agent: AgentState,
        prompt: str,
        max_turns: int,
    ) -> AsyncIterator[StreamEvent]:
        """Execute prompt and yield rich events."""
        if agent.session is None:
            yield StreamEvent(event="error", data={"message": "Session not initialized"})
            return

        # Content start
        yield StreamEvent(event="content:start", data={})

        # Execute (mock for now)
        result = await agent.session.execute(prompt)

        # Simulate content streaming
        content = result.get("content", "")
        chunk_size = 20
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            yield StreamEvent(event="content:delta", data={"text": chunk})
            await asyncio.sleep(0.01)

        # Content complete
        yield StreamEvent(event="content:complete", data={"full_content": content})

        # Tool calls
        for tool_call in result.get("tool_calls", []):
            yield StreamEvent(
                event="tool:start",
                data={"tool": tool_call["name"], "args": tool_call.get("input", {})},
            )
            yield StreamEvent(
                event="tool:result",
                data={"tool": tool_call["name"], "output": tool_call.get("output", "")},
            )

        # Sub-agent spawns
        for spawn in result.get("sub_agents_spawned", []):
            yield StreamEvent(event="agent:spawn", data=spawn)
            yield StreamEvent(event="agent:complete", data=spawn)

        # Session end with usage
        yield StreamEvent(
            event="session:end",
            data={
                "usage": result.get(
                    "usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                )
            },
        )

        # Store assistant response
        agent.messages.append({"role": "assistant", "content": content})

        # Done
        yield StreamEvent(
            event="done",
            data={"content": content, "turn_count": result.get("turn_count", 1)},
        )

    # =========================================================================
    # Messages
    # =========================================================================

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
    """Mock session for development/testing. Will be replaced with amplifier-core."""

    def __init__(self, agent: AgentState, manager: SessionManager):
        self.agent = agent
        self.manager = manager

    async def execute(self, prompt: str) -> dict[str, Any]:
        """Mock execution that returns a simple response."""
        return {
            "content": f"I received your message: '{prompt}'. "
            f"I'm an agent with provider '{self.agent.provider}' "
            f"and tools {self.agent.tools}. "
            f"Available sub-agents: {self.agent.available_agents}.",
            "tool_calls": [],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "turn_count": 1,
            "sub_agents_spawned": [],
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
