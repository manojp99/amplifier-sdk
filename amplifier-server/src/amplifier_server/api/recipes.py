"""Recipe API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import verify_api_key
from ..core.recipe_manager import (
    RecipeExecution,
    RecipeStatus,
    get_recipe_manager,
)
from ..models import (
    ApproveGateRequest,
    DenyGateRequest,
    ExecuteRecipeRequest,
    RecipeExecutionResponse,
    RecipeStepResult,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _to_response(execution: RecipeExecution) -> RecipeExecutionResponse:
    """Convert execution to response model."""
    return RecipeExecutionResponse(
        execution_id=execution.execution_id,
        status=execution.status.value,
        current_step=execution.current_step,
        steps=[
            RecipeStepResult(
                step_id=s.step_id,
                status=s.status.value,
                content=s.content,
                error=s.error,
            )
            for s in execution.steps
        ],
        error=execution.error,
    )


@router.post("/execute", response_model=RecipeExecutionResponse)
async def execute_recipe(
    request: ExecuteRecipeRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> RecipeExecutionResponse:
    """Execute a recipe.

    Starts recipe execution and returns immediately with an execution ID.
    Use GET /recipes/{execution_id} to poll for status updates.

    Either recipe_path or recipe_yaml must be provided.
    """
    manager = get_recipe_manager()

    if not request.recipe_path and not request.recipe_yaml:
        raise HTTPException(
            status_code=400,
            detail="Either recipe_path or recipe_yaml must be provided",
        )

    try:
        execution_id = await manager.execute_recipe(
            recipe_path=request.recipe_path,
            recipe_yaml=request.recipe_yaml,
            context=request.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recipe: {e}") from e

    execution = manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=500, detail="Failed to create execution")

    return _to_response(execution)


@router.get("/{execution_id}", response_model=RecipeExecutionResponse)
async def get_execution(
    execution_id: str,
    _api_key: str | None = Depends(verify_api_key),
) -> RecipeExecutionResponse:
    """Get recipe execution status.

    Returns the current status of a recipe execution including
    step progress and any errors.
    """
    manager = get_recipe_manager()
    execution = manager.get_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return _to_response(execution)


@router.post("/{execution_id}/approve")
async def approve_gate(
    execution_id: str,
    request: ApproveGateRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """Approve a recipe gate.

    Approves a gate step that is waiting for approval,
    allowing the recipe to continue execution.
    """
    manager = get_recipe_manager()

    execution = manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    if execution.status != RecipeStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Execution is not waiting for approval (status: {execution.status.value})",
        )

    approved = await manager.approve_gate(execution_id, request.step_id)
    if not approved:
        raise HTTPException(
            status_code=400,
            detail=f"Step not found or not waiting for approval: {request.step_id}",
        )

    return {"approved": True, "execution_id": execution_id, "step_id": request.step_id}


@router.post("/{execution_id}/deny")
async def deny_gate(
    execution_id: str,
    request: DenyGateRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """Deny a recipe gate.

    Denies a gate step that is waiting for approval,
    causing the recipe execution to fail.
    """
    manager = get_recipe_manager()

    execution = manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    if execution.status != RecipeStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Execution is not waiting for approval (status: {execution.status.value})",
        )

    denied = await manager.deny_gate(execution_id, request.step_id, request.reason)
    if not denied:
        raise HTTPException(
            status_code=400,
            detail=f"Step not found or not waiting for approval: {request.step_id}",
        )

    return {
        "denied": True,
        "execution_id": execution_id,
        "step_id": request.step_id,
        "reason": request.reason,
    }


@router.delete("/{execution_id}")
async def cancel_execution(
    execution_id: str,
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """Cancel a recipe execution.

    Cancels a running or waiting recipe execution.
    """
    manager = get_recipe_manager()

    execution = manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    if execution.status not in (RecipeStatus.RUNNING, RecipeStatus.WAITING_APPROVAL):
        raise HTTPException(
            status_code=400,
            detail=f"Execution cannot be cancelled (status: {execution.status.value})",
        )

    cancelled = await manager.cancel_execution(execution_id)
    if not cancelled:
        raise HTTPException(status_code=500, detail="Failed to cancel execution")

    return {"cancelled": True, "execution_id": execution_id}


@router.get("")
async def list_executions(
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """List all recipe executions.

    Returns a list of execution IDs and summary statistics.
    """
    manager = get_recipe_manager()

    return {
        "executions": manager.list_executions(),
        "active_count": manager.active_count,
    }
