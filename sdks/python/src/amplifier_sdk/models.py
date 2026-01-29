"""Data models for the Amplifier SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for creating an agent."""

    instructions: str
    provider: str = "anthropic"
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    orchestrator: str = "basic"
    context_manager: str = "simple"
    hooks: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        result: dict[str, Any] = {
            "instructions": self.instructions,
            "provider": self.provider,
            "orchestrator": self.orchestrator,
            "context_manager": self.context_manager,
        }
        if self.model:
            result["model"] = self.model
        if self.tools:
            result["tools"] = self.tools
        if self.hooks:
            result["hooks"] = self.hooks
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class ToolCall:
    """A tool call made by the agent."""

    id: str
    name: str
    input: dict[str, Any]
    output: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            input=data.get("input", {}),
            output=data.get("output"),
        )


@dataclass
class Usage:
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Usage:
        """Create from dictionary."""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class RunResponse:
    """Response from running a prompt."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    turn_count: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunResponse:
        """Create from dictionary."""
        return cls(
            content=data.get("content", ""),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            usage=Usage.from_dict(data.get("usage", {})),
            turn_count=data.get("turn_count", 1),
        )


@dataclass
class StreamEvent:
    """A streaming event from the server."""

    event: str
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Get text content from content_delta events."""
        if self.event == "content_delta":
            return self.data.get("text", "")
        return ""

    @property
    def tool_name(self) -> str | None:
        """Get tool name from tool_use events."""
        if self.event == "tool_use":
            return self.data.get("tool")
        return None

    @property
    def is_done(self) -> bool:
        """Check if this is the final event."""
        return self.event == "done"

    @property
    def is_error(self) -> bool:
        """Check if this is an error event."""
        return self.event == "error"

    @property
    def error_message(self) -> str | None:
        """Get error message from error events."""
        if self.event == "error":
            return self.data.get("message")
        return None


@dataclass
class AgentInfo:
    """Information about an agent."""

    agent_id: str
    created_at: str
    status: str
    instructions: str | None = None
    provider: str | None = None
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    message_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentInfo:
        """Create from dictionary."""
        return cls(
            agent_id=data.get("agent_id", ""),
            created_at=data.get("created_at", ""),
            status=data.get("status", ""),
            instructions=data.get("instructions"),
            provider=data.get("provider"),
            model=data.get("model"),
            tools=data.get("tools", []),
            message_count=data.get("message_count", 0),
        )
