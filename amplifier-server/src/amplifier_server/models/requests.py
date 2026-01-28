"""Request models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    instructions: str = Field(..., description="System prompt for the agent")
    tools: list[str] = Field(default_factory=list, description="List of tool names")
    provider: str | None = Field(None, description="LLM provider name")
    model: str | None = Field(None, description="Model name")
    bundle_path: str | None = Field(
        None, description="Path to bundle file (alternative to inline config)"
    )


class RunPromptRequest(BaseModel):
    """Request to run a prompt on an agent."""

    prompt: str = Field(..., description="User prompt to execute")
    max_turns: int = Field(10, description="Maximum turns for agentic loop")


class ExecuteRecipeRequest(BaseModel):
    """Request to execute a recipe."""

    recipe_path: str | None = Field(None, description="Path to recipe YAML file")
    recipe_yaml: str | None = Field(None, description="Inline recipe YAML content")
    context: dict = Field(default_factory=dict, description="Context variables for recipe")


class ApproveGateRequest(BaseModel):
    """Request to approve a recipe gate."""

    step_id: str = Field(..., description="ID of the gate step to approve")


class DenyGateRequest(BaseModel):
    """Request to deny a recipe gate."""

    step_id: str = Field(..., description="ID of the gate step to deny")
    reason: str = Field("", description="Reason for denial")
