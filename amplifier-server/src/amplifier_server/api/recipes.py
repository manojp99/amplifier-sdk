"""Recipes API endpoints for multi-step workflow execution."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from amplifier_server.api.agents import get_session_manager
from amplifier_server.core.session_manager import SessionManager
from amplifier_server.models.requests import (
    ExecuteRecipeRequest,
    RecipeApprovalResponse,
    RecipeConfig,
)
from amplifier_server.models.responses import (
    RecipeExecution,
    RecipeListResponse,
    RecipeStepResult,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])

# In-memory storage for recipe executions
_recipe_executions: dict[str, RecipeExecutionState] = {}


class RecipeExecutionState:
    """State for a recipe execution."""

    def __init__(
        self,
        execution_id: str,
        recipe: RecipeConfig,
        input_vars: dict[str, Any],
    ):
        self.execution_id = execution_id
        self.recipe = recipe
        self.input = input_vars
        self.status = "pending"
        self.current_step: str | None = None
        self.steps: dict[str, RecipeStepResult] = {}
        self.output: dict[str, Any] = {}
        self.error: str | None = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Approval handling
        self.pending_approval: dict[str, Any] | None = None
        self.approval_event: asyncio.Event = asyncio.Event()

        # Initialize step results
        for step in recipe.steps:
            self.steps[step.id] = RecipeStepResult(
                step_id=step.id,
                agent=step.agent,
                status="pending",
            )

    def to_response(self) -> RecipeExecution:
        """Convert to response model."""
        return RecipeExecution(
            execution_id=self.execution_id,
            recipe_name=self.recipe.name,
            status=cast(Any, self.status),  # Status is validated at runtime
            current_step=self.current_step,
            steps=list(self.steps.values()),
            input=self.input,
            output=self.output,
            error=self.error,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
        )


def _interpolate_template(template: str, context: dict[str, Any]) -> str:
    """
    Interpolate {{variable}} patterns in a template.

    Supports:
    - {{input.field}} - Input variables
    - {{steps.step_id.result}} - Step results
    """
    import re

    def replace_var(match: re.Match[str]) -> str:
        var_path = match.group(1).strip()
        parts = var_path.split(".")

        current = context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return match.group(0)  # Keep original if not found

        return str(current) if current is not None else ""

    return re.sub(r"\{\{([^}]+)\}\}", replace_var, template)


async def _execute_recipe(
    state: RecipeExecutionState,
    manager: SessionManager,
) -> None:
    """Execute a recipe asynchronously."""
    state.status = "running"
    state.updated_at = datetime.utcnow()

    # Build context for template interpolation
    context: dict[str, Any] = {
        "input": state.input,
        "steps": {},
    }

    try:
        for step_config in state.recipe.steps:
            step_id = step_config.id
            state.current_step = step_id
            step_result = state.steps[step_id]

            # Check condition
            if step_config.condition:
                condition_result = _interpolate_template(step_config.condition, context)
                if condition_result.lower() in ("false", "0", ""):
                    step_result.status = "skipped"
                    context["steps"][step_id] = {"result": None, "skipped": True}
                    continue

            # Mark step as running
            step_result.status = "running"
            step_result.started_at = datetime.utcnow().isoformat()
            state.updated_at = datetime.utcnow()

            # Check for approval requirement
            if step_config.requires_approval:
                state.status = "waiting_approval"
                step_result.status = "waiting_approval"
                state.pending_approval = {
                    "step_id": step_id,
                    "agent": step_config.agent,
                    "prompt": _interpolate_template(step_config.prompt, context),
                }

                # Wait for approval
                await state.approval_event.wait()
                state.approval_event.clear()

                # Check if denied
                if state.status == "failed":
                    step_result.status = "failed"
                    step_result.error = "Approval denied"
                    break

                state.status = "running"

            # Interpolate prompt
            prompt = _interpolate_template(step_config.prompt, context)

            # Get or create agent for this step
            agent_name = step_config.agent
            agent_config = state.recipe.agents.get(agent_name)

            if agent_config:
                # Create temporary agent from recipe's agent config
                agent_dict = agent_config.model_dump(exclude_none=True)
                if "provider" not in agent_dict:
                    agent_dict["provider"] = "anthropic"  # Default
                agent = await manager.create_agent(agent_dict)
                agent_id = agent.agent_id
            else:
                # Create minimal agent
                step_instructions = (
                    f"You are executing step '{step_id}' of recipe '{state.recipe.name}'."
                )
                agent = await manager.create_agent(
                    {
                        "instructions": step_instructions,
                        "provider": "anthropic",
                        "tools": [],
                    }
                )
                agent_id = agent.agent_id

            try:
                # Execute step
                result = await manager.run(agent_id, prompt)
                content = result.get("content", "")

                step_result.status = "completed"
                step_result.content = content
                step_result.completed_at = datetime.utcnow().isoformat()

                # Store result in context for next steps
                context["steps"][step_id] = {
                    "result": content,
                    "completed": True,
                }

                # Store in output
                state.output[step_id] = content

            except Exception as e:
                step_result.status = "failed"
                step_result.error = str(e)
                state.status = "failed"
                state.error = f"Step '{step_id}' failed: {e}"
                break

            finally:
                # Cleanup temporary agent
                await manager.delete_agent(agent_id)

            state.updated_at = datetime.utcnow()

        # Mark as completed if no errors
        if state.status == "running":
            state.status = "completed"
            state.current_step = None

    except Exception as e:
        state.status = "failed"
        state.error = str(e)

    state.updated_at = datetime.utcnow()


@router.post("", response_model=RecipeExecution)
async def execute_recipe(
    request: ExecuteRecipeRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> RecipeExecution:
    """Execute a recipe (starts async execution, returns immediately)."""
    # Get recipe config
    recipe: RecipeConfig | None = None

    if request.recipe:
        recipe = request.recipe
    elif request.recipe_path:
        # TODO: Load recipe from file path
        raise HTTPException(status_code=400, detail="Recipe file loading not yet implemented")
    else:
        raise HTTPException(status_code=400, detail="Either 'recipe' or 'recipe_path' is required")

    # Create execution state
    execution_id = f"rex_{uuid.uuid4().hex[:12]}"
    state = RecipeExecutionState(
        execution_id=execution_id,
        recipe=recipe,
        input_vars=request.input,
    )

    # Store execution
    _recipe_executions[execution_id] = state

    # Start async execution
    asyncio.create_task(_execute_recipe(state, manager))

    return state.to_response()


@router.get("/{execution_id}", response_model=RecipeExecution)
async def get_recipe_execution(execution_id: str) -> RecipeExecution:
    """Get the status of a recipe execution."""
    state = _recipe_executions.get(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Recipe execution not found: {execution_id}")
    return state.to_response()


@router.get("/{execution_id}/stream")
async def stream_recipe_execution(execution_id: str) -> EventSourceResponse:
    """Stream events from a recipe execution (SSE)."""
    state = _recipe_executions.get(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Recipe execution not found: {execution_id}")

    async def event_generator():
        last_status = None
        last_step = None
        last_step_statuses: dict[str, str] = {}

        yield {
            "event": "recipe:start",
            "data": json.dumps({"execution_id": execution_id, "recipe_name": state.recipe.name}),
        }

        while True:
            # Check for status changes
            if state.status != last_status:
                last_status = state.status

                if state.status == "completed":
                    yield {
                        "event": "recipe:complete",
                        "data": json.dumps({"output": state.output}),
                    }
                    break
                elif state.status == "failed":
                    yield {
                        "event": "recipe:failed",
                        "data": json.dumps({"error": state.error}),
                    }
                    break
                elif state.status == "waiting_approval" and state.pending_approval:
                    yield {
                        "event": "approval:requested",
                        "data": json.dumps(state.pending_approval),
                    }

            # Check for step changes
            if state.current_step != last_step:
                if state.current_step:
                    yield {
                        "event": "step:start",
                        "data": json.dumps(
                            {
                                "step_id": state.current_step,
                                "agent": state.steps[state.current_step].agent,
                            }
                        ),
                    }
                last_step = state.current_step

            # Check for step status changes
            for step_id, step_result in state.steps.items():
                if (
                    step_id not in last_step_statuses
                    or last_step_statuses[step_id] != step_result.status
                ):
                    last_step_statuses[step_id] = step_result.status

                    if step_result.status == "completed":
                        yield {
                            "event": "step:complete",
                            "data": json.dumps(
                                {"step_id": step_id, "content": step_result.content}
                            ),
                        }
                    elif step_result.status == "failed":
                        yield {
                            "event": "step:failed",
                            "data": json.dumps({"step_id": step_id, "error": step_result.error}),
                        }
                    elif step_result.status == "skipped":
                        yield {
                            "event": "step:skipped",
                            "data": json.dumps({"step_id": step_id}),
                        }

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())


@router.post("/{execution_id}/approvals/{step_id}")
async def respond_to_recipe_approval(
    execution_id: str,
    step_id: str,
    response: RecipeApprovalResponse,
) -> dict:
    """Respond to a recipe step approval request."""
    state = _recipe_executions.get(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Recipe execution not found: {execution_id}")

    if state.pending_approval is None or state.pending_approval.get("step_id") != step_id:
        raise HTTPException(status_code=400, detail=f"No pending approval for step: {step_id}")

    if response.approved:
        state.status = "running"
    else:
        state.status = "failed"
        state.error = (
            f"Approval denied for step '{step_id}': {response.reason or 'No reason provided'}"
        )

    state.pending_approval = None
    state.approval_event.set()

    return {
        "execution_id": execution_id,
        "step_id": step_id,
        "approved": response.approved,
        "reason": response.reason,
    }


@router.get("", response_model=RecipeListResponse)
async def list_recipe_executions() -> RecipeListResponse:
    """List all recipe executions."""
    return RecipeListResponse(
        executions=[state.to_response() for state in _recipe_executions.values()],
        count=len(_recipe_executions),
    )


@router.delete("/{execution_id}")
async def cancel_recipe_execution(execution_id: str) -> dict:
    """Cancel a recipe execution."""
    state = _recipe_executions.get(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Recipe execution not found: {execution_id}")

    if state.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400, detail=f"Recipe execution already finished: {state.status}"
        )

    state.status = "cancelled"
    state.error = "Cancelled by user"
    state.updated_at = datetime.utcnow()

    # Release any pending approval wait
    state.approval_event.set()

    return {"execution_id": execution_id, "status": "cancelled"}
