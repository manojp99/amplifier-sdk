"""Response models for the Amplifier Server API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ToolCall(BaseModel):
    """A tool call made by the agent."""

    id: str
    name: str
    input: dict[str, Any]
    output: str | None = None


class AgentResponse(BaseModel):
    """Response after creating or getting an agent."""

    agent_id: str
    created_at: str
    status: str = "ready"
    instructions: str | None = None
    provider: str | None = None
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    message_count: int = 0


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    agents: list[str]
    count: int


class RunResponse(BaseModel):
    """Response from running a prompt."""

    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    turn_count: int = 1


class StreamEvent(BaseModel):
    """A streaming event."""

    event: Literal[
        "message_start",
        "content_delta",
        "tool_use",
        "tool_result",
        "message_end",
        "error",
        "done",
    ]
    data: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    core_version: str | None = None


class ModulesResponse(BaseModel):
    """Available modules response."""

    providers: list[str]
    tools: list[str]
    orchestrators: list[str]
    context_managers: list[str]
    hooks: list[str]


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    deleted: bool


class MessagesResponse(BaseModel):
    """Response for getting conversation messages."""

    messages: list[dict[str, Any]]


class ClearResponse(BaseModel):
    """Response for clearing conversation."""

    cleared: bool
