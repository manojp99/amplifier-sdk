"""Tests for recipes API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from amplifier_server.core.recipe_manager import (
    RecipeExecution,
    RecipeStatus,
    StepResult,
    StepStatus,
)
from amplifier_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    return TestClient(app)


def create_mock_execution(
    execution_id: str = "test-execution-id",
    recipe_name: str = "test-recipe",
    status: RecipeStatus = RecipeStatus.COMPLETED,
    current_step: str | None = None,
    steps: list[StepResult] | None = None,
    error: str | None = None,
) -> RecipeExecution:
    """Create a mock RecipeExecution object."""
    return RecipeExecution(
        execution_id=execution_id,
        recipe_name=recipe_name,
        status=status,
        created_at=datetime.utcnow(),
        current_step=current_step,
        steps=steps
        or [
            StepResult(step_id="step1", status=StepStatus.COMPLETED, content="Done"),
        ],
        error=error,
    )


@pytest.fixture
def mock_recipe_manager() -> MagicMock:
    """Mock recipe manager with proper async methods."""
    manager = MagicMock()

    # Async methods need AsyncMock
    manager.execute_recipe = AsyncMock(return_value="test-execution-id")
    manager.approve_gate = AsyncMock(return_value=True)
    manager.deny_gate = AsyncMock(return_value=True)

    # Sync methods use MagicMock - return proper RecipeExecution object
    manager.get_execution = MagicMock(return_value=create_mock_execution())
    manager.list_executions = MagicMock(return_value=["test-execution-id"])
    manager.active_count = 0

    return manager


class TestExecuteRecipe:
    """Tests for POST /recipes/execute endpoint."""

    def test_execute_recipe_with_yaml(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Execute recipe with inline YAML."""
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/execute",
                json={
                    "recipe_yaml": "name: test\nsteps:\n  - id: step1\n    prompt: Hello",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "execution_id" in data
            assert data["execution_id"] == "test-execution-id"

    def test_execute_recipe_with_path(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Execute recipe with file path."""
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/execute",
                json={
                    "recipe_path": "/path/to/recipe.yaml",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == "test-execution-id"

    def test_execute_recipe_with_context(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Execute recipe with context variables."""
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/execute",
                json={
                    "recipe_yaml": "name: test\nsteps:\n  - id: step1\n    prompt: Hello {{name}}",
                    "context": {"name": "World"},
                },
            )
            assert response.status_code == 200
            mock_recipe_manager.execute_recipe.assert_called_once()


class TestGetRecipeExecution:
    """Tests for GET /recipes/{execution_id} endpoint."""

    def test_get_execution_success(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Get execution returns status."""
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.get("/recipes/test-execution-id")
            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == "test-execution-id"
            assert data["status"] == "completed"

    def test_get_execution_not_found(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Get non-existent execution returns 404."""
        mock_recipe_manager.get_execution = MagicMock(return_value=None)
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.get("/recipes/nonexistent")
            assert response.status_code == 404


class TestApproveGate:
    """Tests for POST /recipes/{execution_id}/approve endpoint."""

    def test_approve_gate_success(self, client: TestClient, mock_recipe_manager: MagicMock) -> None:
        """Approve gate succeeds."""
        # Set execution to waiting approval state
        mock_recipe_manager.get_execution = MagicMock(
            return_value=create_mock_execution(
                status=RecipeStatus.WAITING_APPROVAL,
                current_step="review-gate",
            )
        )
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/test-execution-id/approve",
                json={"step_id": "review-gate"},
            )
            assert response.status_code == 200
            mock_recipe_manager.approve_gate.assert_called_once_with(
                "test-execution-id", "review-gate"
            )

    def test_approve_gate_not_waiting(
        self, client: TestClient, mock_recipe_manager: MagicMock
    ) -> None:
        """Approve gate fails if not waiting approval."""
        # Execution is completed, not waiting
        mock_recipe_manager.get_execution = MagicMock(
            return_value=create_mock_execution(status=RecipeStatus.COMPLETED)
        )
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/test-execution-id/approve",
                json={"step_id": "review-gate"},
            )
            assert response.status_code == 400


class TestDenyGate:
    """Tests for POST /recipes/{execution_id}/deny endpoint."""

    def test_deny_gate_success(self, client: TestClient, mock_recipe_manager: MagicMock) -> None:
        """Deny gate succeeds."""
        # Set execution to waiting approval state
        mock_recipe_manager.get_execution = MagicMock(
            return_value=create_mock_execution(
                status=RecipeStatus.WAITING_APPROVAL,
                current_step="review-gate",
            )
        )
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/test-execution-id/deny",
                json={"step_id": "review-gate", "reason": "Needs revision"},
            )
            assert response.status_code == 200
            mock_recipe_manager.deny_gate.assert_called_once()

    def test_deny_gate_not_found(self, client: TestClient, mock_recipe_manager: MagicMock) -> None:
        """Deny gate fails if execution not found."""
        mock_recipe_manager.get_execution = MagicMock(return_value=None)
        with patch(
            "amplifier_server.api.recipes.get_recipe_manager",
            return_value=mock_recipe_manager,
        ):
            response = client.post(
                "/recipes/nonexistent/deny",
                json={"step_id": "review-gate"},
            )
            assert response.status_code == 404
