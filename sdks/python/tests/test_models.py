"""Tests for SDK data models."""


from amplifier_sdk.models import (
    AgentConfig,
    RecipeExecution,
    RecipeStatus,
    RunResponse,
    StreamEvent,
)


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_create_minimal(self) -> None:
        """Create with just instructions."""
        config = AgentConfig(instructions="You are helpful.")
        assert config.instructions == "You are helpful."
        assert config.tools == []
        assert config.provider == "anthropic"
        assert config.model is None

    def test_create_with_all_fields(self) -> None:
        """Create with all fields."""
        config = AgentConfig(
            instructions="You are helpful.",
            tools=["bash", "filesystem"],
            provider="openai",
            model="gpt-4o",
            bundle="my-bundle",
        )
        assert config.instructions == "You are helpful."
        assert config.tools == ["bash", "filesystem"]
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.bundle == "my-bundle"


class TestRunResponse:
    """Tests for RunResponse model."""

    def test_from_dict_minimal(self) -> None:
        """Create from minimal dict."""
        response = RunResponse.from_dict({"content": "Hello!"})
        assert response.content == "Hello!"
        assert response.tool_calls == []
        assert response.usage.input_tokens == 0
        assert response.usage.output_tokens == 0

    def test_from_dict_with_tool_calls(self) -> None:
        """Create with tool calls."""
        response = RunResponse.from_dict(
            {
                "content": "I'll run that command.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "name": "bash",
                        "arguments": {"command": "ls -la"},
                        "result": "file1.txt\nfile2.txt",
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "stop_reason": "tool_use",
            }
        )
        assert response.content == "I'll run that command."
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.tool_calls[0].arguments == {"command": "ls -la"}
        assert response.usage.input_tokens == 100
        assert response.stop_reason == "tool_use"


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_content_property(self) -> None:
        """Content property extracts from data."""
        event = StreamEvent(event="delta", data={"content": "Hello"})
        assert event.content == "Hello"

    def test_content_empty_when_missing(self) -> None:
        """Content is empty string when not present."""
        event = StreamEvent(event="start", data={})
        assert event.content == ""

    def test_is_done_for_done_event(self) -> None:
        """is_done true for done event."""
        event = StreamEvent(event="done", data={})
        assert event.is_done is True

    def test_is_done_for_error_event(self) -> None:
        """is_done true for error event."""
        event = StreamEvent(event="error", data={"error": "Something failed"})
        assert event.is_done is True

    def test_is_done_false_for_delta(self) -> None:
        """is_done false for delta event."""
        event = StreamEvent(event="delta", data={"content": "x"})
        assert event.is_done is False


class TestRecipeExecution:
    """Tests for RecipeExecution model."""

    def test_from_dict_completed(self) -> None:
        """Create from completed execution dict."""
        execution = RecipeExecution.from_dict(
            {
                "execution_id": "exec-123",
                "recipe_name": "code-review",
                "status": "completed",
                "steps": [
                    {
                        "step_id": "analyze",
                        "status": "completed",
                        "content": "Analysis done",
                    },
                    {
                        "step_id": "review",
                        "status": "completed",
                        "content": "Review done",
                    },
                ],
            }
        )
        assert execution.execution_id == "exec-123"
        assert execution.recipe_name == "code-review"
        assert execution.status == RecipeStatus.COMPLETED
        assert len(execution.steps) == 2

    def test_from_dict_with_error(self) -> None:
        """Create from failed execution dict."""
        execution = RecipeExecution.from_dict(
            {
                "execution_id": "exec-456",
                "recipe_name": "test-recipe",
                "status": "failed",
                "error": "Step failed: connection timeout",
            }
        )
        assert execution.status == RecipeStatus.FAILED
        assert execution.error == "Step failed: connection timeout"

    def test_from_dict_waiting_approval(self) -> None:
        """Create from waiting approval execution."""
        execution = RecipeExecution.from_dict(
            {
                "execution_id": "exec-789",
                "recipe_name": "deploy",
                "status": "waiting_approval",
                "current_step": "approval-gate",
            }
        )
        assert execution.status == RecipeStatus.WAITING_APPROVAL
        assert execution.current_step == "approval-gate"
