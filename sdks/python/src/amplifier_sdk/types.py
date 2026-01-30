"""Type definitions for Amplifier SDK.

These types mirror the amplifier-app-runtime protocol events and commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Event types from the server."""

    # Response events
    RESULT = "result"
    ERROR = "error"
    ACK = "ack"

    # Content streaming
    CONTENT_START = "content.start"
    CONTENT_DELTA = "content.delta"
    CONTENT_END = "content.end"

    # Thinking/reasoning
    THINKING_DELTA = "thinking.delta"
    THINKING_END = "thinking.end"

    # Tool execution
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    TOOL_ERROR = "tool.error"

    # Session lifecycle
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"

    # Approval flow
    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_RESOLVED = "approval.resolved"

    # Agent spawning
    AGENT_SPAWNED = "agent.spawned"
    AGENT_COMPLETED = "agent.completed"

    # Server events
    CONNECTED = "connected"
    PONG = "pong"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """An event from the server.

    Events are streamed during prompt execution and contain:
    - type: The event type (content.delta, tool.call, etc.)
    - data: Event-specific payload
    - correlation_id: Links to the originating command
    - sequence: Position in the stream
    - final: True if this is the last event
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    id: str = ""
    correlation_id: str | None = None
    sequence: int | None = None
    final: bool = False
    timestamp: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Create an Event from a dictionary."""
        return cls(
            type=data.get("type", ""),
            data=data.get("data", {}),
            id=data.get("id", ""),
            correlation_id=data.get("correlation_id"),
            sequence=data.get("sequence"),
            final=data.get("final", False),
            timestamp=data.get("timestamp", ""),
        )

    def is_error(self) -> bool:
        """Check if this is an error event."""
        return self.type == EventType.ERROR.value

    def is_final(self) -> bool:
        """Check if this is the final event."""
        return self.final


@dataclass
class SessionInfo:
    """Information about a session."""

    id: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    state: str = "ready"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionInfo:
        """Create a SessionInfo from a dictionary."""
        return cls(
            id=data.get("id") or data.get("session_id", ""),
            title=data.get("title", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            state=data.get("state", "ready"),
        )


@dataclass
class ToolCall:
    """A tool call made by the agent."""

    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any] = field(default_factory=dict)
    output: Any = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create a ToolCall from a dictionary."""
        return cls(
            tool_name=data.get("tool_name", ""),
            tool_call_id=data.get("tool_call_id", ""),
            arguments=data.get("arguments", {}),
            output=data.get("output"),
        )


@dataclass
class ApprovalRequest:
    """An approval request from the agent."""

    request_id: str
    prompt: str
    options: list[str] = field(default_factory=list)
    timeout: float = 300.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        """Create an ApprovalRequest from a dictionary."""
        return cls(
            request_id=data.get("request_id", ""),
            prompt=data.get("prompt", ""),
            options=data.get("options", []),
            timeout=data.get("timeout", 300.0),
        )


@dataclass
class PromptResponse:
    """Complete response from a synchronous prompt."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    session_id: str = ""
    stop_reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptResponse:
        """Create a PromptResponse from a dictionary."""
        return cls(
            content=data.get("content", ""),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            session_id=data.get("session_id", ""),
            stop_reason=data.get("stop_reason", ""),
        )


@dataclass
class ModuleConfig:
    """Configuration for a module (provider, tool, hook, etc.)."""

    module: str
    source: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"module": self.module}
        if self.source:
            result["source"] = self.source
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class AgentConfig:
    """Configuration for an agent within a bundle."""

    name: str
    description: str | None = None
    instructions: str | None = None
    tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.instructions:
            result["instructions"] = self.instructions
        if self.tools:
            result["tools"] = self.tools
        return result


@dataclass
class BundleDefinition:
    """Runtime bundle definition.

    Allows you to define a complete bundle configuration programmatically
    instead of referencing a pre-existing bundle by name.

    Example:
        bundle = BundleDefinition(
            name="my-agent",
            providers=[ModuleConfig(module="provider-anthropic")],
            tools=[
                ModuleConfig(module="tool-filesystem"),
                ModuleConfig(module="tool-web"),
            ],
            instructions="You are a helpful coding assistant.",
        )
        session = await client.create_session(bundle=bundle)
    """

    name: str
    version: str = "1.0.0"
    description: str | None = None
    providers: list[ModuleConfig] = field(default_factory=list)
    tools: list[ModuleConfig] = field(default_factory=list)
    hooks: list[ModuleConfig] = field(default_factory=list)
    orchestrator: ModuleConfig | None = None
    context: ModuleConfig | None = None
    agents: list[AgentConfig] = field(default_factory=list)
    instructions: str | None = None
    session: dict[str, Any] = field(default_factory=dict)
    includes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API request."""
        result: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
        }
        if self.description:
            result["description"] = self.description
        if self.providers:
            result["providers"] = [p.to_dict() for p in self.providers]
        if self.tools:
            result["tools"] = [t.to_dict() for t in self.tools]
        if self.hooks:
            result["hooks"] = [h.to_dict() for h in self.hooks]
        if self.orchestrator:
            result["orchestrator"] = self.orchestrator.to_dict()
        if self.context:
            result["context"] = self.context.to_dict()
        if self.agents:
            result["agents"] = [a.to_dict() for a in self.agents]
        if self.instructions:
            result["instructions"] = self.instructions
        if self.session:
            result["session"] = self.session
        if self.includes:
            result["includes"] = self.includes
        return result


@dataclass
class SessionConfig:
    """Configuration for creating a session.

    The bundle parameter can be either:
    - A string name referencing a pre-existing bundle (e.g., "foundation")
    - A BundleDefinition for runtime bundle creation

    Example with named bundle:
        config = SessionConfig(bundle="foundation")

    Example with runtime bundle:
        config = SessionConfig(
            bundle=BundleDefinition(
                name="my-agent",
                providers=[ModuleConfig(module="provider-anthropic")],
                tools=[ModuleConfig(module="tool-filesystem")],
            )
        )
    """

    bundle: str | BundleDefinition | None = None
    provider: str | None = None
    model: str | None = None
    working_directory: str | None = None
    behaviors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {}
        if self.bundle:
            if isinstance(self.bundle, str):
                result["bundle"] = self.bundle
            else:
                # Runtime bundle definition
                result["bundle_definition"] = self.bundle.to_dict()
        if self.provider:
            result["provider"] = self.provider
        if self.model:
            result["model"] = self.model
        if self.working_directory:
            result["working_directory"] = self.working_directory
        if self.behaviors:
            result["behaviors"] = self.behaviors
        return result
