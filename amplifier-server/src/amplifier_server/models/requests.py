"""Request models for the Amplifier Server API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Module Configuration Models
# =============================================================================


class ProviderConfig(BaseModel):
    """Configuration for a provider module."""

    module: str = Field(..., description="Provider module name: anthropic, openai, azure, ollama")
    model: str | None = Field(None, description="Model name")
    priority: int = Field(1, description="Priority for fallback (lower = higher priority)")
    config: dict[str, Any] = Field(default_factory=dict, description="Provider-specific config")


class ToolConfig(BaseModel):
    """Configuration for a tool module."""

    module: str = Field(..., description="Tool module name or 'mcp' or 'custom'")
    server: str | None = Field(None, description="MCP server URI (for module='mcp')")
    path: str | None = Field(None, description="Path to custom tool (for module='custom')")
    config: dict[str, Any] = Field(default_factory=dict, description="Tool-specific config")


class OrchestratorConfig(BaseModel):
    """Configuration for an orchestrator module."""

    module: str = Field(
        "basic", description="Orchestrator: basic, agentic-loop, streaming, parallel"
    )
    config: dict[str, Any] = Field(default_factory=dict, description="Orchestrator config")


class ContextManagerConfig(BaseModel):
    """Configuration for a context manager module."""

    module: str = Field("simple", description="Context manager: simple, persistent")
    config: dict[str, Any] = Field(default_factory=dict, description="Context manager config")


class HookConfig(BaseModel):
    """Configuration for a hook module."""

    module: str = Field(..., description="Hook module: logging, redaction, approval, custom")
    path: str | None = Field(None, description="Path to custom hook (for module='custom')")
    config: dict[str, Any] = Field(default_factory=dict, description="Hook-specific config")


class ApprovalConfig(BaseModel):
    """Configuration for approval requirements."""

    tools: list[str] = Field(default_factory=list, description="Tools requiring approval")
    auto_approve: list[str] = Field(default_factory=list, description="Tools auto-approved")
    timeout: int = Field(300, description="Approval timeout in seconds")


class SubAgentConfig(BaseModel):
    """Configuration for a sub-agent that can be spawned."""

    instructions: str = Field(..., description="System prompt for the sub-agent")
    provider: str | None = Field(None, description="Provider (inherits from parent if omitted)")
    model: str | None = Field(None, description="Model (inherits from parent if omitted)")
    tools: list[str | ToolConfig] = Field(default_factory=list, description="Tools for sub-agent")
    config: dict[str, Any] = Field(default_factory=dict, description="Additional config")


# =============================================================================
# Agent Configuration
# =============================================================================


class AgentConfig(BaseModel):
    """Configuration for creating an agent - full module wiring support."""

    instructions: str = Field(..., description="System prompt for the agent")

    # Provider(s) - string for simple, list for multiple/fallback
    provider: str | None = Field(None, description="Simple: single provider name")
    providers: list[ProviderConfig] | None = Field(
        None, description="Advanced: multiple providers with config"
    )
    model: str | None = Field(None, description="Model name (for simple provider)")

    # Tools - strings for simple, configs for advanced
    tools: list[str | ToolConfig] = Field(default_factory=list, description="Tools to enable")

    # Orchestrator
    orchestrator: str | OrchestratorConfig = Field("basic", description="Execution strategy")

    # Context manager
    context_manager: str | ContextManagerConfig = Field("simple", description="Memory strategy")

    # Hooks
    hooks: list[str | HookConfig] = Field(default_factory=list, description="Lifecycle hooks")

    # Approval configuration
    approval: ApprovalConfig | None = Field(None, description="Approval requirements")

    # Sub-agents for multi-agent orchestration
    agents: dict[str, SubAgentConfig] = Field(default_factory=dict, description="Named sub-agents")

    # Additional config
    config: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


# =============================================================================
# Run Requests
# =============================================================================


class RunRequest(BaseModel):
    """Request to run a prompt on an agent."""

    prompt: str = Field(..., description="The user prompt to execute")
    max_turns: int = Field(10, description="Maximum number of agent turns")
    stream_events: list[str] | None = Field(
        None, description="Event types to stream (None = default set)"
    )


class OneOffRunRequest(BaseModel):
    """Request for one-off execution without persistent agent."""

    prompt: str = Field(..., description="The user prompt to execute")
    instructions: str = Field("You are a helpful assistant.", description="System prompt")
    provider: str = Field("anthropic", description="LLM provider")
    model: str | None = Field(None, description="Model name")
    tools: list[str | ToolConfig] = Field(default_factory=list, description="Tools to enable")
    max_turns: int = Field(10, description="Maximum number of agent turns")


# =============================================================================
# Multi-Agent Requests
# =============================================================================


class SpawnAgentRequest(BaseModel):
    """Request to spawn a sub-agent."""

    agent_name: str = Field(..., description="Name of the sub-agent (from agents config)")
    inherit_context: Literal["none", "recent", "all"] = Field(
        "none", description="Context inheritance mode"
    )
    inherit_context_turns: int = Field(5, description="Number of turns for 'recent' mode")
    prompt: str | None = Field(None, description="Initial prompt for sub-agent")


# =============================================================================
# Recipe Requests
# =============================================================================


class RecipeStepConfig(BaseModel):
    """Configuration for a recipe step."""

    id: str = Field(..., description="Unique step identifier")
    agent: str = Field(..., description="Agent name to execute this step")
    prompt: str = Field(..., description="Prompt template (supports {{}} interpolation)")
    requires_approval: bool = Field(False, description="Whether step requires human approval")
    condition: str | None = Field(None, description="Condition for execution (template)")
    config: dict[str, Any] = Field(default_factory=dict, description="Step-specific config")


class RecipeConfig(BaseModel):
    """Configuration for a recipe."""

    name: str = Field(..., description="Recipe name")
    description: str | None = Field(None, description="Recipe description")
    steps: list[RecipeStepConfig] = Field(..., description="Recipe steps")
    agents: dict[str, SubAgentConfig] = Field(default_factory=dict, description="Agent definitions")


class ExecuteRecipeRequest(BaseModel):
    """Request to execute a recipe."""

    # Either inline recipe or file path
    recipe: RecipeConfig | None = Field(None, description="Inline recipe definition")
    recipe_path: str | None = Field(None, description="Path to recipe YAML file")

    # Input variables
    input: dict[str, Any] = Field(default_factory=dict, description="Input variables for recipe")


class RecipeApprovalResponse(BaseModel):
    """Response to a recipe approval request."""

    approved: bool = Field(..., description="Whether approved")
    reason: str | None = Field(None, description="Reason for decision")


# =============================================================================
# Approval Requests
# =============================================================================


class ApprovalResponse(BaseModel):
    """Response to an approval request."""

    approved: bool = Field(..., description="Whether the action is approved")
    reason: str | None = Field(None, description="Optional reason for the decision")
