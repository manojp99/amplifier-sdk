"""Data models for the Amplifier SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Agent Configuration Models
# =============================================================================


@dataclass
class ProviderConfig:
    """Configuration for a provider with priority and model settings."""

    module: str
    priority: int = 1
    model: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"module": self.module, "priority": self.priority}
        if self.model:
            result["model"] = self.model
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class ToolConfig:
    """Configuration for a tool with custom settings."""

    module: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"module": self.module}
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class HookConfig:
    """Configuration for a hook with custom settings."""

    module: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"module": self.module}
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class ApprovalConfig:
    """Configuration for approval requirements."""

    require_approval: list[str] = field(default_factory=list)
    auto_approve: list[str] = field(default_factory=list)
    timeout: int = 300

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "require_approval": self.require_approval,
            "auto_approve": self.auto_approve,
            "timeout": self.timeout,
        }


@dataclass
class SubAgentConfig:
    """Configuration for a sub-agent that can be spawned."""

    instructions: str
    provider: str | None = None
    model: str | None = None
    tools: list[str | ToolConfig] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"instructions": self.instructions}
        if self.provider:
            result["provider"] = self.provider
        if self.model:
            result["model"] = self.model
        if self.tools:
            result["tools"] = [
                t.to_dict() if isinstance(t, ToolConfig) else t for t in self.tools
            ]
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class AgentConfig:
    """Configuration for creating an agent with full module wiring support."""

    instructions: str
    provider: str | None = "anthropic"
    providers: list[ProviderConfig] | None = None
    model: str | None = None
    tools: list[str | ToolConfig] = field(default_factory=list)
    orchestrator: str = "basic"
    context_manager: str = "simple"
    hooks: list[str | HookConfig] = field(default_factory=list)
    approval: ApprovalConfig | None = None
    agents: dict[str, SubAgentConfig] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        result: dict[str, Any] = {
            "instructions": self.instructions,
            "orchestrator": self.orchestrator,
            "context_manager": self.context_manager,
        }
        if self.provider:
            result["provider"] = self.provider
        if self.providers:
            result["providers"] = [p.to_dict() for p in self.providers]
        if self.model:
            result["model"] = self.model
        if self.tools:
            result["tools"] = [
                t.to_dict() if isinstance(t, ToolConfig) else t for t in self.tools
            ]
        if self.hooks:
            result["hooks"] = [
                h.to_dict() if isinstance(h, HookConfig) else h for h in self.hooks
            ]
        if self.approval:
            result["approval"] = self.approval.to_dict()
        if self.agents:
            result["agents"] = {k: v.to_dict() for k, v in self.agents.items()}
        if self.config:
            result["config"] = self.config
        return result


# =============================================================================
# Spawn Configuration
# =============================================================================


@dataclass
class SpawnConfig:
    """Configuration for spawning a sub-agent."""

    agent_name: str
    prompt: str | None = None
    inherit_context: str = "none"
    inherit_context_turns: int = 5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "agent_name": self.agent_name,
            "inherit_context": self.inherit_context,
            "inherit_context_turns": self.inherit_context_turns,
        }
        if self.prompt:
            result["prompt"] = self.prompt
        return result


# =============================================================================
# Response Models
# =============================================================================


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
    sub_agents_spawned: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunResponse:
        """Create from dictionary."""
        return cls(
            content=data.get("content", ""),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            usage=Usage.from_dict(data.get("usage", {})),
            turn_count=data.get("turn_count", 1),
            sub_agents_spawned=data.get("sub_agents_spawned", []),
        )


@dataclass
class StreamEvent:
    """A streaming event from the server."""

    event: str
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Get text content from content:delta events."""
        if self.event in ("content_delta", "content:delta"):
            return self.data.get("text", "")
        return ""

    @property
    def tool_name(self) -> str | None:
        """Get tool name from tool:start events."""
        if self.event in ("tool_use", "tool:start"):
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
    orchestrator: str | None = None
    context_manager: str | None = None
    hooks: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    message_count: int = 0
    has_approval_config: bool = False

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
            orchestrator=data.get("orchestrator"),
            context_manager=data.get("context_manager"),
            hooks=data.get("hooks", []),
            agents=data.get("agents", []),
            message_count=data.get("message_count", 0),
            has_approval_config=data.get("has_approval_config", False),
        )


@dataclass
class SubAgentInfo:
    """Information about a spawned sub-agent."""

    agent_id: str
    parent_id: str
    agent_name: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubAgentInfo:
        """Create from dictionary."""
        return cls(
            agent_id=data.get("agent_id", ""),
            parent_id=data.get("parent_id", ""),
            agent_name=data.get("agent_name", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ApprovalInfo:
    """Information about a pending approval request."""

    approval_id: str
    agent_id: str
    tool: str
    action: str
    args: dict[str, Any]
    created_at: str
    timeout_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalInfo:
        """Create from dictionary."""
        return cls(
            approval_id=data.get("approval_id", ""),
            agent_id=data.get("agent_id", ""),
            tool=data.get("tool", ""),
            action=data.get("action", ""),
            args=data.get("args", {}),
            created_at=data.get("created_at", ""),
            timeout_at=data.get("timeout_at", ""),
        )


# =============================================================================
# Recipe Models
# =============================================================================


@dataclass
class RecipeStep:
    """A step in a recipe."""

    id: str
    agent: str
    prompt: str
    condition: str | None = None
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "agent": self.agent,
            "prompt": self.prompt,
        }
        if self.condition:
            result["condition"] = self.condition
        if self.requires_approval:
            result["requires_approval"] = self.requires_approval
        return result


@dataclass
class RecipeConfig:
    """Configuration for a recipe (multi-step workflow)."""

    name: str
    steps: list[RecipeStep] = field(default_factory=list)
    agents: dict[str, SubAgentConfig] = field(default_factory=dict)
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.agents:
            result["agents"] = {k: v.to_dict() for k, v in self.agents.items()}
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class RecipeStepResult:
    """Result of a recipe step execution."""

    step_id: str
    agent: str
    status: str
    content: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeStepResult:
        """Create from dictionary."""
        return cls(
            step_id=data.get("step_id", ""),
            agent=data.get("agent", ""),
            status=data.get("status", ""),
            content=data.get("content"),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class RecipeExecution:
    """Status of a recipe execution."""

    execution_id: str
    recipe_name: str
    status: str
    current_step: str | None = None
    steps: list[RecipeStepResult] = field(default_factory=list)
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeExecution:
        """Create from dictionary."""
        return cls(
            execution_id=data.get("execution_id", ""),
            recipe_name=data.get("recipe_name", ""),
            status=data.get("status", ""),
            current_step=data.get("current_step"),
            steps=[RecipeStepResult.from_dict(s) for s in data.get("steps", [])],
            input=data.get("input", {}),
            output=data.get("output", {}),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
