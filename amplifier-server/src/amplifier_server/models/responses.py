"""Response models for the Amplifier Server API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Basic Response Models
# =============================================================================


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


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    core_version: str | None = None


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    deleted: bool


class ClearResponse(BaseModel):
    """Response for clearing conversation."""

    cleared: bool


# =============================================================================
# Agent Response Models
# =============================================================================


class AgentResponse(BaseModel):
    """Response after creating or getting an agent."""

    agent_id: str
    created_at: str
    status: str = "ready"
    instructions: str | None = None
    provider: str | None = None
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    orchestrator: str | None = None
    context_manager: str | None = None
    hooks: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)  # Available sub-agents
    message_count: int = 0
    has_approval_config: bool = False


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    agents: list[str]
    count: int


class MessagesResponse(BaseModel):
    """Response for getting conversation messages."""

    messages: list[dict[str, Any]]


# =============================================================================
# Run Response Models
# =============================================================================


class RunResponse(BaseModel):
    """Response from running a prompt."""

    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    turn_count: int = 1
    sub_agents_spawned: list[str] = Field(default_factory=list)


# =============================================================================
# Streaming Event Models
# =============================================================================


EventType = Literal[
    # Session lifecycle
    "session:start",
    "session:end",
    # Prompt lifecycle
    "prompt:start",
    "prompt:complete",
    # Content streaming
    "content:start",
    "content:delta",
    "content:complete",
    # Tool execution
    "tool:start",
    "tool:result",
    # Sub-agent delegation
    "agent:spawn",
    "agent:complete",
    # Approvals
    "approval:requested",
    "approval:granted",
    "approval:denied",
    "approval:timeout",
    # Errors
    "error",
    # Done
    "done",
]


class StreamEvent(BaseModel):
    """A streaming event with rich event taxonomy."""

    event: EventType
    data: dict[str, Any]


# =============================================================================
# Module Response Models
# =============================================================================


class ModulesResponse(BaseModel):
    """Available modules response."""

    providers: list[str]
    tools: list[str]
    orchestrators: list[str]
    context_managers: list[str]
    hooks: list[str]


# =============================================================================
# Multi-Agent Response Models
# =============================================================================


class SpawnResponse(BaseModel):
    """Response after spawning a sub-agent."""

    agent_id: str
    parent_id: str
    agent_name: str
    status: str = "ready"


class SubAgentListResponse(BaseModel):
    """Response for listing sub-agents."""

    sub_agents: list[dict[str, Any]]
    count: int


# =============================================================================
# Approval Response Models
# =============================================================================


class ApprovalRequest(BaseModel):
    """An approval request from the agent."""

    approval_id: str
    agent_id: str
    tool: str
    action: str
    args: dict[str, Any]
    created_at: str
    timeout_at: str


class ApprovalListResponse(BaseModel):
    """Response for listing pending approvals."""

    approvals: list[ApprovalRequest]
    count: int


# =============================================================================
# Recipe Response Models
# =============================================================================


class RecipeStepResult(BaseModel):
    """Result of a recipe step execution."""

    step_id: str
    agent: str
    status: Literal["pending", "running", "completed", "failed", "skipped", "waiting_approval"]
    content: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class RecipeExecution(BaseModel):
    """Status of a recipe execution."""

    execution_id: str
    recipe_name: str
    status: Literal["pending", "running", "waiting_approval", "completed", "failed", "cancelled"]
    current_step: str | None = None
    steps: list[RecipeStepResult] = Field(default_factory=list)
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str
    updated_at: str


class RecipeListResponse(BaseModel):
    """Response for listing recipe executions."""

    executions: list[RecipeExecution]
    count: int


# =============================================================================
# Recipe Streaming Events
# =============================================================================


RecipeEventType = Literal[
    "recipe:start",
    "recipe:complete",
    "recipe:failed",
    "step:start",
    "step:complete",
    "step:failed",
    "step:skipped",
    "approval:requested",
    "approval:granted",
    "approval:denied",
    "content:delta",
    "error",
]


class RecipeStreamEvent(BaseModel):
    """A streaming event for recipe execution."""

    event: RecipeEventType
    data: dict[str, Any]
