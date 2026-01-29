"""Request models for the Amplifier Server API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for creating an agent."""

    instructions: str = Field(..., description="System prompt for the agent")
    provider: str = Field(..., description="LLM provider: anthropic, openai, azure")
    model: str | None = Field(None, description="Model name (uses provider default if omitted)")
    tools: list[str] = Field(default_factory=list, description="Tool names to enable")
    orchestrator: str = Field("basic", description="Execution strategy")
    context_manager: str = Field("simple", description="Memory management strategy")
    hooks: list[str] = Field(default_factory=list, description="Lifecycle hooks to enable")
    config: dict = Field(default_factory=dict, description="Additional configuration")


class RunRequest(BaseModel):
    """Request to run a prompt on an agent."""

    prompt: str = Field(..., description="The user prompt to execute")
    max_turns: int = Field(10, description="Maximum number of agent turns")


class OneOffRunRequest(BaseModel):
    """Request for one-off execution without persistent agent."""

    prompt: str = Field(..., description="The user prompt to execute")
    instructions: str = Field("You are a helpful assistant.", description="System prompt")
    provider: str = Field(..., description="LLM provider")
    model: str | None = Field(None, description="Model name")
    tools: list[str] = Field(default_factory=list, description="Tools to enable")
    max_turns: int = Field(10, description="Maximum number of agent turns")
