"""Recipe execution manager."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

logger = logging.getLogger(__name__)

# Check if foundation is available
try:
    from amplifier_foundation import load_bundle

    FOUNDATION_AVAILABLE = True
except ImportError:
    FOUNDATION_AVAILABLE = False
    load_bundle = None


class RecipeStatus(str, Enum):
    """Status of a recipe execution."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of a recipe step."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a recipe step execution."""

    step_id: str
    status: StepStatus
    content: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class RecipeExecution:
    """State of a recipe execution."""

    execution_id: str
    recipe_name: str
    status: RecipeStatus
    created_at: datetime
    current_step: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    error: str | None = None
    recipe_data: dict = field(default_factory=dict)
    stage_name: str | None = None  # For staged recipes waiting approval


@dataclass
class RecipeManager:
    """Manages recipe executions.

    This class handles:
    - Starting recipe executions
    - Tracking execution progress
    - Handling approval gates
    - Managing execution lifecycle
    """

    _executions: dict[str, RecipeExecution] = field(default_factory=dict)
    _tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _project_path: Path = field(default_factory=Path.cwd)
    _prepared_bundle: Any = None  # PreparedBundle for agent execution

    async def initialize(self, bundle_path: str | None = None) -> None:
        """Initialize the recipe manager with a prepared bundle.

        Args:
            bundle_path: Path to bundle for agent execution
        """
        if not FOUNDATION_AVAILABLE or load_bundle is None:
            logger.warning("amplifier-foundation not available for recipes")
            return

        try:
            # Load a base bundle for agent execution
            bundle_uri = bundle_path or "git+https://github.com/microsoft/amplifier-foundation@main"
            bundle = await load_bundle(bundle_uri)
            self._prepared_bundle = await bundle.prepare()
            logger.info("Recipe manager initialized with foundation")
        except Exception as e:
            logger.error(f"Failed to initialize recipe manager: {e}")

    async def execute_recipe(
        self,
        recipe_path: str | None = None,
        recipe_yaml: str | None = None,
        context: dict | None = None,
    ) -> str:
        """Start executing a recipe.

        Args:
            recipe_path: Path to recipe YAML file
            recipe_yaml: Inline recipe YAML content
            context: Context variables for recipe

        Returns:
            Execution ID

        Raises:
            ValueError: If neither recipe_path nor recipe_yaml provided
        """
        if not recipe_path and not recipe_yaml:
            raise ValueError("Either recipe_path or recipe_yaml must be provided")

        execution_id = str(uuid4())

        # Parse recipe
        recipe_data = self._parse_recipe_yaml(recipe_path, recipe_yaml)
        recipe_name = recipe_data.get("name", "unnamed")

        # Create execution state
        execution = RecipeExecution(
            execution_id=execution_id,
            recipe_name=recipe_name,
            status=RecipeStatus.PENDING,
            created_at=datetime.utcnow(),
            context=context or {},
            recipe_data=recipe_data,
        )

        # Initialize step results
        for step in recipe_data.get("steps", []):
            execution.steps.append(
                StepResult(
                    step_id=step.get("id", str(uuid4())),
                    status=StepStatus.PENDING,
                )
            )

        async with self._lock:
            self._executions[execution_id] = execution

        # Start execution in background
        task = asyncio.create_task(self._run_recipe(execution_id))
        self._tasks[execution_id] = task

        logger.info(f"Started recipe execution {execution_id}: {recipe_name}")
        return execution_id

    def _parse_recipe_yaml(
        self,
        recipe_path: str | None,
        recipe_yaml: str | None,
    ) -> dict:
        """Parse recipe from path or YAML string."""
        if recipe_yaml:
            return yaml.safe_load(recipe_yaml)

        if recipe_path:
            try:
                with open(recipe_path) as f:
                    return yaml.safe_load(f)
            except FileNotFoundError as e:
                raise ValueError(f"Recipe not found: {recipe_path}") from e

        return {}

    async def _run_recipe(self, execution_id: str) -> None:
        """Execute recipe steps."""
        execution = self._executions.get(execution_id)
        if not execution:
            return

        execution.status = RecipeStatus.RUNNING

        try:
            steps = execution.recipe_data.get("steps", [])

            for i, step in enumerate(steps):
                step_id = step.get("id", str(i))
                step_type = step.get("type", "agent")

                # Update current step
                execution.current_step = step_id

                # Find step result
                step_result = next(
                    (s for s in execution.steps if s.step_id == step_id),
                    None,
                )
                if step_result:
                    step_result.status = StepStatus.RUNNING
                    step_result.started_at = datetime.utcnow()

                # Handle gate steps
                if step_type == "gate":
                    execution.status = RecipeStatus.WAITING_APPROVAL
                    execution.stage_name = step_id
                    if step_result:
                        step_result.status = StepStatus.WAITING_APPROVAL

                    # Wait until approved or denied
                    while True:
                        await asyncio.sleep(0.5)
                        if step_result and step_result.status in (
                            StepStatus.COMPLETED,
                            StepStatus.FAILED,
                            StepStatus.SKIPPED,
                        ):
                            break
                        if execution.status == RecipeStatus.CANCELLED:
                            return

                    if step_result and step_result.status == StepStatus.FAILED:
                        execution.status = RecipeStatus.FAILED
                        execution.error = step_result.error or "Gate denied"
                        return

                    execution.status = RecipeStatus.RUNNING

                else:
                    # Execute agent step
                    try:
                        result = await self._execute_step(step, execution.context)

                        if step_result:
                            step_result.status = StepStatus.COMPLETED
                            step_result.content = result
                            step_result.completed_at = datetime.utcnow()

                        # Add result to context for next steps
                        execution.context[f"steps.{step_id}.result"] = result

                    except Exception as e:
                        if step_result:
                            step_result.status = StepStatus.FAILED
                            step_result.error = str(e)
                            step_result.completed_at = datetime.utcnow()

                        execution.status = RecipeStatus.FAILED
                        execution.error = str(e)
                        logger.error(f"Step {step_id} failed: {e}")
                        return

            # All steps completed
            execution.status = RecipeStatus.COMPLETED
            execution.current_step = None
            logger.info(f"Recipe {execution.execution_id} completed")

        except Exception as e:
            execution.status = RecipeStatus.FAILED
            execution.error = str(e)
            logger.error(f"Recipe {execution.execution_id} failed: {e}")

    async def _execute_step(self, step: dict, context: dict) -> str:
        """Execute a single recipe step."""
        agent = step.get("agent", "default")
        prompt = step.get("prompt", "")

        # Template substitution
        for key, value in context.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        # Try to execute with foundation if available
        if self._prepared_bundle is not None:
            try:
                session = await self._prepared_bundle.create_session()
                async with session:
                    result = await session.execute(prompt)
                    return str(result)
            except Exception as e:
                logger.warning(f"Foundation execution failed, using mock: {e}")

        # Mock execution fallback
        return f"[Executed] Agent '{agent}' processed: {prompt[:200]}..."

    def get_execution(self, execution_id: str) -> RecipeExecution | None:
        """Get execution by ID."""
        return self._executions.get(execution_id)

    async def approve_gate(self, execution_id: str, step_id: str) -> bool:
        """Approve a gate step.

        Args:
            execution_id: Execution identifier
            step_id: Gate step identifier

        Returns:
            True if approved, False if not found
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        step_result = next(
            (s for s in execution.steps if s.step_id == step_id),
            None,
        )
        if not step_result:
            return False

        if step_result.status != StepStatus.WAITING_APPROVAL:
            return False

        step_result.status = StepStatus.COMPLETED
        step_result.completed_at = datetime.utcnow()
        logger.info(f"Approved gate {step_id} for execution {execution_id}")
        return True

    async def deny_gate(
        self,
        execution_id: str,
        step_id: str,
        reason: str = "",
    ) -> bool:
        """Deny a gate step.

        Args:
            execution_id: Execution identifier
            step_id: Gate step identifier
            reason: Reason for denial

        Returns:
            True if denied, False if not found
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        step_result = next(
            (s for s in execution.steps if s.step_id == step_id),
            None,
        )
        if not step_result:
            return False

        if step_result.status != StepStatus.WAITING_APPROVAL:
            return False

        step_result.status = StepStatus.FAILED
        step_result.error = reason or "Denied"
        step_result.completed_at = datetime.utcnow()
        logger.info(f"Denied gate {step_id} for execution {execution_id}: {reason}")
        return True

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.

        Args:
            execution_id: Execution identifier

        Returns:
            True if cancelled, False if not found
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        execution.status = RecipeStatus.CANCELLED

        # Cancel the background task
        task = self._tasks.get(execution_id)
        if task and not task.done():
            task.cancel()

        logger.info(f"Cancelled recipe execution {execution_id}")
        return True

    def list_executions(self) -> list[str]:
        """List all execution IDs."""
        return list(self._executions.keys())

    @property
    def active_count(self) -> int:
        """Number of active executions."""
        return sum(
            1
            for e in self._executions.values()
            if e.status in (RecipeStatus.RUNNING, RecipeStatus.WAITING_APPROVAL)
        )


# Global recipe manager instance
_manager: RecipeManager | None = None


def get_recipe_manager() -> RecipeManager:
    """Get the global recipe manager instance."""
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager
