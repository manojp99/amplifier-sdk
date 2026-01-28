"""Response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A tool call made during execution."""

    id: str = Field(..., description="Unique tool call ID")
    name: str = Field(..., description="Tool name")
    input: dict = Field(default_factory=dict, description="Tool input parameters")
    output: str | None = Field(None, description="Tool output (if completed)")


class Usage(BaseModel):
    """Token usage statistics."""

    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    total_tokens: int = Field(default=0, description="Total tokens")


class AgentResponse(BaseModel):
    """Response when creating an agent."""

    agent_id: str = Field(..., description="Unique agent identifier")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")


class RunResponse(BaseModel):
    """Response from running a prompt."""

    content: str = Field(..., description="Response content")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tool calls made")
    usage: Usage = Field(default_factory=lambda: Usage(), description="Token usage")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field("ok", description="Server status")
    version: str = Field(..., description="Server version")
    active_sessions: int = Field(0, description="Number of active sessions")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict | None = Field(None, description="Additional error details")


class RecipeStepResult(BaseModel):
    """Result of a recipe step."""

    step_id: str = Field(..., description="Step identifier")
    status: str = Field(..., description="Step status")
    content: str | None = Field(None, description="Step output content")
    error: str | None = Field(None, description="Error message if failed")


class RecipeExecutionResponse(BaseModel):
    """Response for recipe execution."""

    execution_id: str = Field(..., description="Unique execution identifier")
    status: str = Field(..., description="Execution status")
    current_step: str | None = Field(None, description="Currently executing step")
    steps: list[RecipeStepResult] = Field(default_factory=list, description="Step results")
    error: str | None = Field(None, description="Error message if failed")
