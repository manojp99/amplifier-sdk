"""Tests for recipes API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from amplifier_server.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    return TestClient(app)


@pytest.fixture
def mock_recipe_manager() -> MagicMock:
    """Mock recipe manager."""
    manager = MagicMock()
    manager.execute = AsyncMock(return_value="test-execution-id")
    manager.get_execution = MagicMock(
        return_value={
            "execution_id": "test-execution-id",
            "recipe_name": "test-recipe",
            "status": "completed",
            "current_step": None,
            "steps": [
                {"step_id": "step1", "status": "completed", "content": "Done"},
            ],
            "error": None,
        }
    )
    manager.approve_gate = AsyncMock()
    manager.deny_gate = AsyncMock()
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
            mock_recipe_manager.execute.assert_called_once()


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


class TestDenyGate:
    """Tests for POST /recipes/{execution_id}/deny endpoint."""

    def test_deny_gate_success(self, client: TestClient, mock_recipe_manager: MagicMock) -> None:
        """Deny gate succeeds."""
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
