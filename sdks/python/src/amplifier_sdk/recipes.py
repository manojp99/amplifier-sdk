"""Recipe management and execution.

Provides types and utilities for building, managing, and executing
multi-step AI agent workflows (recipes).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

# =============================================================================
# Recipe Types
# =============================================================================


@dataclass
class RecursionConfig:
    """Recursion protection configuration."""

    max_depth: int | None = None
    """Maximum recipe invocation depth"""

    max_agents: int | None = None
    """Maximum total agent spawns across all depths"""


@dataclass
class RateLimitingConfig:
    """Rate limiting configuration."""

    max_calls_per_minute: int | None = None
    """Maximum LLM calls per minute"""

    on_limit: Literal["fail", "queue"] | None = None
    """Whether to fail or queue when limit reached"""


@dataclass
class RecipeStep:
    """Recipe step definition."""

    id: str
    """Unique step identifier"""

    agent: str | None = None
    """Agent to execute this step (e.g., "foundation:zen-architect")"""

    mode: str | None = None
    """Agent mode (e.g., "ANALYZE", "ARCHITECT", "REVIEW")"""

    prompt: str | None = None
    """Prompt template for the agent (supports {{variable}} interpolation)"""

    type: Literal["agent", "bash"] = "agent"
    """Step type: agent (default) or bash"""

    command: str | None = None
    """Bash command to execute (when type="bash")"""

    output: str | None = None
    """Variable name to store step output"""

    timeout: int | None = None
    """Step timeout in seconds"""

    on_error: Literal["fail", "continue", "retry"] | None = None
    """Error handling strategy"""

    max_retries: int | None = None
    """Maximum retry attempts (when on_error="retry")"""

    requires_approval: bool = False
    """Whether this step requires human approval before executing"""

    approval_prompt: str | None = None
    """Custom approval prompt text"""

    conditions: list[dict[str, Any]] | None = None
    """Conditions that must be met for step to execute"""

    foreach: dict[str, Any] | None = None
    """Steps to execute in a loop"""


@dataclass
class RecipeDefinition:
    """Recipe definition."""

    name: str
    """Unique recipe name"""

    description: str
    """Human-readable description"""

    version: str
    """Semantic version (e.g., "1.0.0")"""

    steps: list[RecipeStep]
    """Workflow steps"""

    author: str | None = None
    """Recipe author"""

    created: str | None = None
    """Creation timestamp (ISO8601)"""

    updated: str | None = None
    """Last update timestamp (ISO8601)"""

    tags: list[str] = field(default_factory=list)
    """Categorization tags"""

    context: dict[str, Any] = field(default_factory=dict)
    """Initial context variables"""

    recursion: RecursionConfig | None = None
    """Recursion protection settings"""

    rate_limiting: RateLimitingConfig | None = None
    """Rate limiting settings"""


@dataclass
class RecipeSession:
    """Recipe execution session info."""

    session_id: str
    """Session identifier"""

    recipe_name: str
    """Recipe name being executed"""

    started: str
    """Execution start time"""

    current_step_index: int
    """Current step index"""

    completed_steps: list[str]
    """List of completed step IDs"""

    status: Literal["running", "completed", "failed", "awaiting_approval"] | None = None
    """Execution status"""

    error: str | None = None
    """Error message if failed"""


@dataclass
class RecipeStepEvent:
    """Recipe step progress event."""

    step_id: str
    """Step identifier"""

    status: Literal["started", "completed", "failed", "skipped"]
    """Step status"""

    output: Any = None
    """Step output (if available)"""

    error: str | None = None
    """Error message (if failed)"""

    duration: float | None = None
    """Execution duration in seconds"""


@dataclass
class RecipeApprovalGate:
    """Recipe approval gate."""

    session_id: str
    """Session identifier"""

    stage_name: str
    """Stage/step name requiring approval"""

    prompt: str
    """Approval prompt text"""

    context: dict[str, Any] | None = None
    """Context information for the approval decision"""


# =============================================================================
# Fluent Recipe Builder
# =============================================================================


class StepBuilder:
    """Fluent builder for recipe steps."""

    def __init__(self, step_id: str) -> None:
        """Initialize step builder.

        Args:
            step_id: Unique step identifier
        """
        self._step = RecipeStep(id=step_id)

    def agent(self, name: str) -> StepBuilder:
        """Set the agent to execute this step."""
        self._step.agent = name
        self._step.type = "agent"
        return self

    def mode(self, mode: str) -> StepBuilder:
        """Set agent mode."""
        self._step.mode = mode
        return self

    def prompt(self, text: str) -> StepBuilder:
        """Set the prompt template."""
        self._step.prompt = text
        return self

    def bash(self, command: str) -> StepBuilder:
        """Execute a bash command instead of an agent."""
        self._step.type = "bash"
        self._step.command = command
        return self

    def output(self, var_name: str) -> StepBuilder:
        """Store step output in a variable."""
        self._step.output = var_name
        return self

    def timeout(self, seconds: int) -> StepBuilder:
        """Set step timeout in seconds."""
        self._step.timeout = seconds
        return self

    def on_error(
        self, strategy: Literal["fail", "continue", "retry"], max_retries: int | None = None
    ) -> StepBuilder:
        """Configure error handling."""
        self._step.on_error = strategy
        if max_retries is not None:
            self._step.max_retries = max_retries
        return self

    def requires_approval(self, prompt: str | None = None) -> StepBuilder:
        """Require human approval before executing this step."""
        self._step.requires_approval = True
        if prompt:
            self._step.approval_prompt = prompt
        return self

    def when(
        self,
        variable: str,
        operator: Literal["equals", "not_equals", "contains", "matches"],
        value: Any,
    ) -> StepBuilder:
        """Add execution condition."""
        if self._step.conditions is None:
            self._step.conditions = []
        self._step.conditions.append({"variable": variable, "operator": operator, "value": value})
        return self

    def build(self) -> RecipeStep:
        """Build the step definition."""
        return self._step


class RecipeBuilder:
    """Fluent builder for creating recipes programmatically.

    Example:
        ```python
        recipe = RecipeBuilder("code-review")
            .description("Automated code review workflow")
            .version("1.0.0")
            .context({"severity": "high"})
            .step("analyze", lambda s: (
                s.agent("foundation:zen-architect")
                 .prompt("Analyze {{file_path}} for issues")
            ))
            .build()
        ```
    """

    def __init__(self, name: str) -> None:
        """Initialize recipe builder.

        Args:
            name: Unique recipe name
        """
        self._recipe = RecipeDefinition(name=name, description="", version="1.0.0", steps=[])

    def description(self, text: str) -> RecipeBuilder:
        """Set recipe description."""
        self._recipe.description = text
        return self

    def version(self, version: str) -> RecipeBuilder:
        """Set recipe version (semantic versioning)."""
        self._recipe.version = version
        return self

    def author(self, author: str) -> RecipeBuilder:
        """Set recipe author."""
        self._recipe.author = author
        return self

    def tags(self, *tags: str) -> RecipeBuilder:
        """Add tags for categorization."""
        self._recipe.tags = list(tags)
        return self

    def context(self, ctx: dict[str, Any]) -> RecipeBuilder:
        """Set initial context variables."""
        self._recipe.context.update(ctx)
        return self

    def recursion(self, config: RecursionConfig) -> RecipeBuilder:
        """Configure recursion protection."""
        self._recipe.recursion = config
        return self

    def rate_limiting(self, config: RateLimitingConfig) -> RecipeBuilder:
        """Configure rate limiting."""
        self._recipe.rate_limiting = config
        return self

    def step(self, step_id: str, configure: Callable[[StepBuilder], None]) -> RecipeBuilder:
        """Add a step to the recipe.

        Args:
            step_id: Step identifier
            configure: Function to configure the step

        Example:
            ```python
            .step("analyze", lambda s: (
                s.agent("foundation:zen-architect")
                 .prompt("Analyze the code")
                 .timeout(300)
            ))
            ```
        """
        builder = StepBuilder(step_id)
        configure(builder)
        self._recipe.steps.append(builder.build())
        return self

    def build(self) -> RecipeDefinition:
        """Build the final recipe definition."""
        if not self._recipe.description:
            raise ValueError("Recipe description is required")
        if not self._recipe.steps:
            raise ValueError("Recipe must have at least one step")
        return self._recipe


# =============================================================================
# Recipe Execution Monitor
# =============================================================================


RecipeEventHandler = Callable[[RecipeStepEvent], None]
ApprovalGateHandler = Callable[[RecipeApprovalGate], bool]


class RecipeExecution:
    """Recipe execution monitor.

    Provides event-based monitoring of recipe execution progress.
    """

    def __init__(self, client: Any, session_id: str, recipe_name: str) -> None:
        """Initialize recipe execution monitor.

        Args:
            client: AmplifierClient instance
            session_id: Session ID for this recipe execution
            recipe_name: Name of the recipe being executed
        """
        self._client = client
        self._session_id = session_id
        self._recipe_name = recipe_name
        self._step_handlers: dict[str, list[RecipeEventHandler]] = {}
        self._approval_handlers: list[ApprovalGateHandler] = []
        self._current_step: str | None = None
        self._steps: dict[str, RecipeStepEvent] = {}
        self._pending_approval: RecipeApprovalGate | None = None

    @property
    def id(self) -> str:
        """Get the session ID for this recipe execution."""
        return self._session_id

    @property
    def recipe(self) -> str:
        """Get the recipe name being executed."""
        return self._recipe_name

    def on(
        self,
        event: Literal["step.started", "step.completed", "step.failed", "step.skipped"],
        handler: RecipeEventHandler,
    ) -> RecipeExecution:
        """Register a handler for step events.

        Example:
            ```python
            execution.on("step.started", lambda step: print(f"Starting: {step.step_id}"))
            execution.on("step.completed", lambda step: print(f"Output: {step.output}"))
            ```
        """
        if event not in self._step_handlers:
            self._step_handlers[event] = []
        self._step_handlers[event].append(handler)
        return self

    def off(
        self,
        event: Literal["step.started", "step.completed", "step.failed", "step.skipped"],
        handler: RecipeEventHandler,
    ) -> RecipeExecution:
        """Remove an event handler."""
        if event in self._step_handlers:
            try:
                self._step_handlers[event].remove(handler)
            except ValueError:
                pass
        return self

    def on_approval(self, handler: ApprovalGateHandler) -> RecipeExecution:
        """Register handler for approval gates.

        Example:
            ```python
            def ask_user(gate: RecipeApprovalGate) -> bool:
                return input(f"{gate.prompt} (y/n): ").lower() == "y"

            execution.on_approval(ask_user)
            ```
        """
        self._approval_handlers.append(handler)
        return self

    def get_current_step(self) -> str | None:
        """Get the current step being executed."""
        return self._current_step

    def get_completed_steps(self) -> list[RecipeStepEvent]:
        """Get completed steps."""
        return [s for s in self._steps.values() if s.status == "completed"]

    def get_steps(self) -> list[RecipeStepEvent]:
        """Get all step events."""
        return list(self._steps.values())

    def handle_event(self, event: Any) -> None:
        """Internal: Handle incoming events from the stream."""
        # Parse recipe-specific events from the stream
        if event.type == "tool.call" and event.data.get("tool") == "recipes":
            operation = event.data.get("arguments", {}).get("operation")

            if operation == "execute":
                # Recipe execution started
                self._emit_step_event(RecipeStepEvent(step_id="recipe-start", status="started"))

        if event.type == "tool.result" and event.data.get("tool") == "recipes":
            result = event.data.get("result", {})

            # Check for step completion events
            if result.get("step_id"):
                step_event = RecipeStepEvent(
                    step_id=result["step_id"],
                    status=result.get("status", "completed"),
                    output=result.get("output"),
                    error=result.get("error"),
                    duration=result.get("duration"),
                )

                self._steps[result["step_id"]] = step_event
                self._current_step = result["step_id"]
                self._emit_step_event(step_event)

        # Handle approval requests
        if event.type == "approval.required":
            gate = RecipeApprovalGate(
                session_id=self._session_id,
                stage_name=event.data.get("stage", "unknown"),
                prompt=event.data.get("prompt", ""),
                context=event.data.get("context"),
            )

            # Note: handle_event is synchronous, approval handling happens separately
            # Store gate for later processing
            self._pending_approval = gate

    def handle_error(self, error: Exception) -> None:
        """Internal: Handle errors."""
        self._emit_step_event(
            RecipeStepEvent(step_id="recipe-error", status="failed", error=str(error))
        )

    def _emit_step_event(self, event: RecipeStepEvent) -> None:
        """Emit step event to registered handlers."""
        event_type = f"step.{event.status}"
        handlers = self._step_handlers.get(event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in recipe event handler: {e}")

    def process_pending_approvals(self) -> None:
        """Process any pending approval gates.

        This should be called periodically by the client to handle approval gates.
        Since handle_event is synchronous, we store gates and process them separately.
        """
        if not self._pending_approval:
            return

        gate = self._pending_approval
        self._pending_approval = None

        if not self._approval_handlers:
            print(f"Recipe approval required but no handler registered: {gate.prompt}")
            return

        # Call first approval handler (synchronous)
        handler = self._approval_handlers[0]
        approved = handler(gate)

        # Note: Actual approval response would be sent by the client asynchronously
        # Store the decision for the client to act on
        self._approval_decision = (gate.stage_name, approved)
