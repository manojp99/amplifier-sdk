"""Tests for SDK data models."""

from amplifier_sdk.models import (
    AgentConfig,
    AgentInfo,
    RunResponse,
    StreamEvent,
    ToolCall,
    Usage,
)


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_create_minimal(self) -> None:
        """Create with just instructions and provider."""
        config = AgentConfig(instructions="You are helpful.", provider="anthropic")
        assert config.instructions == "You are helpful."
        assert config.provider == "anthropic"
        assert config.tools == []
        assert config.model is None

    def test_create_with_all_fields(self) -> None:
        """Create with all fields."""
        config = AgentConfig(
            instructions="You are helpful.",
            provider="openai",
            model="gpt-4o",
            tools=["bash", "filesystem"],
            orchestrator="streaming",
            context_manager="persistent",
            hooks=["logging"],
            config={"key": "value"},
        )
        assert config.instructions == "You are helpful."
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.tools == ["bash", "filesystem"]
        assert config.orchestrator == "streaming"
        assert config.context_manager == "persistent"
        assert config.hooks == ["logging"]
        assert config.config == {"key": "value"}

    def test_to_dict(self) -> None:
        """Config converts to dict correctly."""
        config = AgentConfig(
            instructions="Test",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            tools=["bash"],
        )
        data = config.to_dict()

        assert data["instructions"] == "Test"
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["tools"] == ["bash"]

    def test_to_dict_excludes_none(self) -> None:
        """Config to_dict excludes None values."""
        config = AgentConfig(instructions="Test", provider="anthropic")
        data = config.to_dict()

        assert "model" not in data  # None values excluded


class TestToolCall:
    """Tests for ToolCall model."""

    def test_from_dict(self) -> None:
        """Create from dict."""
        data = {
            "id": "tc_123",
            "name": "bash",
            "input": {"command": "ls -la"},
            "output": "file1.txt\nfile2.txt",
        }
        tc = ToolCall.from_dict(data)

        assert tc.id == "tc_123"
        assert tc.name == "bash"
        assert tc.input == {"command": "ls -la"}
        assert tc.output == "file1.txt\nfile2.txt"

    def test_from_dict_minimal(self) -> None:
        """Create from minimal dict."""
        data = {"id": "tc_1", "name": "test", "input": {}}
        tc = ToolCall.from_dict(data)

        assert tc.id == "tc_1"
        assert tc.output is None


class TestUsage:
    """Tests for Usage model."""

    def test_from_dict(self) -> None:
        """Create from dict."""
        data = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        usage = Usage.from_dict(data)

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_from_dict_defaults(self) -> None:
        """Missing fields default to 0."""
        usage = Usage.from_dict({})

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0


class TestRunResponse:
    """Tests for RunResponse model."""

    def test_from_dict_minimal(self) -> None:
        """Create from minimal dict."""
        response = RunResponse.from_dict({"content": "Hello!"})
        assert response.content == "Hello!"
        assert response.tool_calls == []
        assert response.usage.input_tokens == 0
        assert response.turn_count == 1

    def test_from_dict_with_tool_calls(self) -> None:
        """Create with tool calls."""
        response = RunResponse.from_dict(
            {
                "content": "I'll run that command.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "name": "bash",
                        "input": {"command": "ls -la"},
                        "output": "file1.txt\nfile2.txt",
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                },
                "turn_count": 2,
            }
        )
        assert response.content == "I'll run that command."
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.tool_calls[0].input == {"command": "ls -la"}
        assert response.usage.input_tokens == 100
        assert response.turn_count == 2


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_text_property_content_delta(self) -> None:
        """Text property extracts from content_delta events."""
        event = StreamEvent(event="content_delta", data={"text": "Hello"})
        assert event.text == "Hello"

    def test_text_empty_for_other_events(self) -> None:
        """Text is empty string for non-content_delta events."""
        event = StreamEvent(event="start", data={"text": "Hello"})
        assert event.text == ""

    def test_tool_name_property(self) -> None:
        """Tool name extracted from tool_use events."""
        event = StreamEvent(event="tool_use", data={"tool": "bash"})
        assert event.tool_name == "bash"

    def test_tool_name_none_for_other_events(self) -> None:
        """Tool name is None for non-tool_use events."""
        event = StreamEvent(event="content_delta", data={"tool": "bash"})
        assert event.tool_name is None

    def test_is_done_for_done_event(self) -> None:
        """is_done true for done event."""
        event = StreamEvent(event="done", data={})
        assert event.is_done is True

    def test_is_done_false_for_delta(self) -> None:
        """is_done false for delta event."""
        event = StreamEvent(event="content_delta", data={"text": "x"})
        assert event.is_done is False

    def test_is_error_for_error_event(self) -> None:
        """is_error true for error event."""
        event = StreamEvent(event="error", data={"message": "Something failed"})
        assert event.is_error is True
        assert event.error_message == "Something failed"

    def test_is_error_false_for_other_events(self) -> None:
        """is_error false for non-error events."""
        event = StreamEvent(event="done", data={})
        assert event.is_error is False
        assert event.error_message is None


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_from_dict(self) -> None:
        """Create from dict."""
        data = {
            "agent_id": "ag_test123",
            "created_at": "2024-01-01T00:00:00Z",
            "status": "ready",
            "instructions": "Be helpful.",
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "tools": ["bash", "filesystem"],
            "message_count": 5,
        }
        info = AgentInfo.from_dict(data)

        assert info.agent_id == "ag_test123"
        assert info.status == "ready"
        assert info.instructions == "Be helpful."
        assert info.provider == "anthropic"
        assert info.tools == ["bash", "filesystem"]
        assert info.message_count == 5

    def test_from_dict_minimal(self) -> None:
        """Create from minimal dict."""
        data = {"agent_id": "ag_1", "created_at": "2024-01-01", "status": "ready"}
        info = AgentInfo.from_dict(data)

        assert info.agent_id == "ag_1"
        assert info.instructions is None
        assert info.tools == []
        assert info.message_count == 0
