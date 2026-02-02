"""Tests for AmplifierClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplifier_sdk import AmplifierClient, Event, PromptResponse, SessionInfo


class TestAmplifierClient:
    """Test cases for AmplifierClient."""

    @pytest.fixture
    def client(self) -> AmplifierClient:
        """Create a test client."""
        return AmplifierClient(base_url="http://localhost:4096")

    @pytest.mark.asyncio
    async def test_ping_success(self, client: AmplifierClient) -> None:
        """Test successful ping."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await client.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, client: AmplifierClient) -> None:
        """Test ping failure."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.ping()
            assert result is False

    @pytest.mark.asyncio
    async def test_create_session(self, client: AmplifierClient) -> None:
        """Test session creation."""
        mock_response_data = {
            "id": "sess_123",
            "title": "Test Session",
            "created_at": "2024-01-01T00:00:00Z",
            "state": "ready",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            session = await client.create_session(bundle="foundation")

            assert session.id == "sess_123"
            assert session.title == "Test Session"
            assert session.state == "ready"

    @pytest.mark.asyncio
    async def test_delete_session(self, client: AmplifierClient) -> None:
        """Test session deletion."""
        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_delete.return_value = mock_response

            result = await client.delete_session("sess_123")
            assert result is True

    @pytest.mark.asyncio
    async def test_prompt_sync(self, client: AmplifierClient) -> None:
        """Test synchronous prompt."""
        mock_response_data = {
            "content": "Hello! How can I help?",
            "tool_calls": [],
            "session_id": "sess_123",
            "stop_reason": "end_turn",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            response = await client.prompt_sync("sess_123", "Hello!")

            assert response.content == "Hello! How can I help?"
            assert response.session_id == "sess_123"
            assert response.stop_reason == "end_turn"


class TestTypes:
    """Test cases for type definitions."""

    def test_event_from_dict(self) -> None:
        """Test Event.from_dict."""
        data = {
            "type": "content.delta",
            "data": {"delta": "Hello"},
            "id": "evt_123",
            "correlation_id": "cmd_456",
            "sequence": 0,
            "final": False,
        }

        event = Event.from_dict(data)

        assert event.type == "content.delta"
        assert event.data == {"delta": "Hello"}
        assert event.id == "evt_123"
        assert event.correlation_id == "cmd_456"
        assert event.sequence == 0
        assert event.final is False

    def test_event_is_error(self) -> None:
        """Test Event.is_error."""
        error_event = Event(type="error", data={"error": "Something failed"})
        content_event = Event(type="content.delta", data={"delta": "Hi"})

        assert error_event.is_error() is True
        assert content_event.is_error() is False

    def test_event_extracts_tool_call_id(self) -> None:
        """Test Event extracts tool_call_id from data."""
        data = {
            "type": "tool.call",
            "data": {
                "tool_name": "bash",
                "tool_call_id": "tc_abc123",
                "arguments": {"command": "ls"},
            },
        }

        event = Event.from_dict(data)

        assert event.type == "tool.call"
        assert event.tool_call_id == "tc_abc123"
        assert event.data["tool_name"] == "bash"

    def test_event_extracts_agent_id(self) -> None:
        """Test Event extracts agent_id from data."""
        data = {
            "type": "content.delta",
            "data": {
                "delta": "Hello from child",
                "agent_id": "agent_child_1",
            },
        }

        event = Event.from_dict(data)

        assert event.type == "content.delta"
        assert event.agent_id == "agent_child_1"
        assert event.data["delta"] == "Hello from child"

    def test_event_correlation_tool_call_to_result(self) -> None:
        """Test tool call and result correlation using tool_call_id."""
        call_data = {
            "type": "tool.call",
            "data": {
                "tool_name": "bash",
                "tool_call_id": "tc_123",
                "arguments": {"command": "pwd"},
            },
        }

        result_data = {
            "type": "tool.result",
            "data": {
                "tool_call_id": "tc_123",
                "result": "/workspace",
            },
        }

        call_event = Event.from_dict(call_data)
        result_event = Event.from_dict(result_data)

        # Should be able to correlate using tool_call_id
        assert call_event.tool_call_id == result_event.tool_call_id
        assert call_event.tool_call_id == "tc_123"

    def test_session_info_from_dict(self) -> None:
        """Test SessionInfo.from_dict."""
        data = {
            "id": "sess_123",
            "title": "Test",
            "created_at": "2024-01-01T00:00:00Z",
            "state": "ready",
        }

        session = SessionInfo.from_dict(data)

        assert session.id == "sess_123"
        assert session.title == "Test"
        assert session.state == "ready"

    def test_prompt_response_from_dict(self) -> None:
        """Test PromptResponse.from_dict."""
        data = {
            "content": "The answer is 4",
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "tool_call_id": "tc_123",
                    "arguments": {"expression": "2+2"},
                    "output": "4",
                }
            ],
            "session_id": "sess_123",
            "stop_reason": "end_turn",
        }

        response = PromptResponse.from_dict(data)

        assert response.content == "The answer is 4"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "calculator"
        assert response.tool_calls[0].output == "4"


class TestInputValidation:
    """Test cases for input validation."""

    @pytest.mark.asyncio
    async def test_get_session_validates_session_id(self) -> None:
        """Test get_session validates session_id."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with pytest.raises(ValueError, match="Session ID is required"):
            await client.get_session("")

        with pytest.raises(ValueError):
            await client.get_session(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_delete_session_validates_session_id(self) -> None:
        """Test delete_session validates session_id."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with pytest.raises(ValueError, match="Session ID is required"):
            await client.delete_session("")

    @pytest.mark.asyncio
    async def test_prompt_validates_parameters(self) -> None:
        """Test prompt validates session_id and content."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        # Invalid session_id
        with pytest.raises(ValueError, match="Session ID is required"):
            async for _ in client.prompt("", "test"):
                break

        # Invalid content
        with pytest.raises(ValueError, match="content is required"):
            async for _ in client.prompt("sess_123", ""):
                break

    @pytest.mark.asyncio
    async def test_prompt_sync_validates_parameters(self) -> None:
        """Test prompt_sync validates parameters."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with pytest.raises(ValueError, match="Session ID is required"):
            await client.prompt_sync("", "test")

        with pytest.raises(ValueError, match="content is required"):
            await client.prompt_sync("sess_123", "")

    @pytest.mark.asyncio
    async def test_respond_approval_validates_parameters(self) -> None:
        """Test respond_approval validates all parameters."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with pytest.raises(ValueError, match="Session ID is required"):
            await client.respond_approval("", "req_1", "approve")

        with pytest.raises(ValueError, match="Request ID is required"):
            await client.respond_approval("sess_1", "", "approve")

        with pytest.raises(ValueError, match="Choice is required"):
            await client.respond_approval("sess_1", "req_1", "")

    @pytest.mark.asyncio
    async def test_resume_session_validates_session_id(self) -> None:
        """Test resume_session validates session_id."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with pytest.raises(ValueError, match="Session ID is required"):
            await client.resume_session("")

    def test_register_tool_validates_tool(self) -> None:
        """Test register_tool validates tool parameter."""
        from amplifier_sdk import AmplifierClient, ClientTool

        client = AmplifierClient()

        # Invalid tool object
        with pytest.raises(ValueError, match="must be a ClientTool"):
            client.register_tool(None)  # type: ignore

        # Invalid name
        with pytest.raises(ValueError, match="name is required"):
            client.register_tool(ClientTool(name="", description="test", handler=lambda x: x))

        # Invalid description
        with pytest.raises(ValueError, match="description is required"):
            client.register_tool(ClientTool(name="test", description="", handler=lambda x: x))

        # Invalid handler
        with pytest.raises(ValueError, match="handler must be callable"):
            client.register_tool(ClientTool(name="test", description="test", handler=None))  # type: ignore


class TestSessionResume:
    """Test cases for session resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_session(self) -> None:
        """Test resuming a session."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        mock_session_data = {
            "id": "sess_123",
            "title": "Previous Session",
            "state": "ready",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = mock_session_data
            mock_get.return_value = mock_response

            session = await client.resume_session("sess_123")

            assert session["id"] == "sess_123"
            assert session["title"] == "Previous Session"
            assert session["state"] == "ready"
            assert "send" in session
            assert "send_sync" in session
            assert "cancel" in session
            assert "delete" in session

    @pytest.mark.asyncio
    async def test_resume_session_provides_working_send_method(self) -> None:
        """Test that resumed session send method works."""
        from amplifier_sdk import AmplifierClient

        client = AmplifierClient()

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"id": "sess_123", "state": "ready"}
            mock_get.return_value = mock_response

            session = await client.resume_session("sess_123")

            # Verify send method exists and is callable
            assert callable(session["send"])

            # session["send"] returns an async generator
            result = session["send"]("Continue")
            assert hasattr(result, "__aiter__")
