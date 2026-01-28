"""Data models for Amplifier SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RecipeStatus(str, Enum):
    """Status of a recipe execution."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for creating an agent."""

    instructions: str
    tools: list[str] = field(default_factory=list)
    provider: str = "anthropic"
    model: str | None = None
    bundle: str | None = None


@dataclass
class ToolCall:
    """A tool call made by the agent."""

    id: str
    name: str
    arguments: dict[str, Any]
    result: str | None = None


@dataclass
class Usage:
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class RunResponse:
    """Response from running a prompt."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    stop_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> RunResponse:
        """Create from API response dict."""
        tool_calls = [
            ToolCall(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
                result=tc.get("result"),
            )
            for tc in data.get("tool_calls", [])
        ]
        usage_data = data.get("usage", {})
        usage = Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        )
        return cls(
            content=data.get("content", ""),
            tool_calls=tool_calls,
            usage=usage,
            stop_reason=data.get("stop_reason"),
        )


@dataclass
class StreamEvent:
    """A streaming event from the server."""

    event: str
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def content(self) -> str:
        """Get content from delta events."""
        return self.data.get("content", "")

    @property
    def is_done(self) -> bool:
        """Check if this is the final event."""
        return self.event in ("done", "error")


@dataclass
class StepResult:
    """Result of a recipe step."""

    step_id: str
    status: str
    content: str | None = None
    error: str | None = None


@dataclass
class RecipeExecution:
    """State of a recipe execution."""

    execution_id: str
    recipe_name: str
    status: RecipeStatus
    current_step: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    error: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> RecipeExecution:
        """Create from API response dict."""
        steps = [
            StepResult(
                step_id=s.get("step_id", ""),
                status=s.get("status", ""),
                content=s.get("content"),
                error=s.get("error"),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            execution_id=data.get("execution_id", ""),
            recipe_name=data.get("recipe_name", ""),
            status=RecipeStatus(data.get("status", "pending")),
            current_step=data.get("current_step"),
            steps=steps,
            error=data.get("error"),
        )
