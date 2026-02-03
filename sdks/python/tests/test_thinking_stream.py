"""Tests for thinking stream helpers."""

import pytest
from amplifier_sdk import AmplifierClient
from amplifier_sdk.types import Event


class TestThinkingStreamHelpers:
    """Test cases for thinking stream functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return AmplifierClient()

    def test_on_thinking_registers_handler(self, client):
        """Test on_thinking registers handler."""
        handler = lambda thinking: None
        client.on_thinking(handler)

        assert len(client._thinking_handlers) == 1

    @pytest.mark.asyncio
    async def test_on_thinking_called_on_thinking_delta(self, client):
        """Test handler called with thinking state on thinking.delta."""
        calls = []

        def handler(thinking):
            calls.append(thinking)

        client.on_thinking(handler)

        event = Event(type="thinking.delta", data={"delta": "I should first..."})
        await client._emit_event(event)

        assert len(calls) == 1
        assert calls[0]["is_thinking"] is True
        assert calls[0]["content"] == "I should first..."

    @pytest.mark.asyncio
    async def test_accumulates_thinking_content(self, client):
        """Test thinking content accumulates across deltas."""
        calls = []
        client.on_thinking(lambda thinking: calls.append(thinking))

        await client._emit_event(Event(type="thinking.delta", data={"delta": "First "}))
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Second "}))
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Third"}))

        assert len(calls) == 3
        assert calls[2]["content"] == "First Second Third"
        assert calls[2]["is_thinking"] is True

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, client):
        """Test multiple thinking handlers supported."""
        calls1 = []
        calls2 = []

        client.on_thinking(lambda t: calls1.append(t))
        client.on_thinking(lambda t: calls2.append(t))

        event = Event(type="thinking.delta", data={"delta": "test"})
        await client._emit_event(event)

        assert len(calls1) == 1
        assert len(calls2) == 1

    @pytest.mark.asyncio
    async def test_async_handlers(self, client):
        """Test async thinking handlers."""
        calls = []

        async def async_handler(thinking):
            calls.append(thinking["content"])

        client.on_thinking(async_handler)

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert len(calls) == 1
        assert calls[0] == "test"

    @pytest.mark.asyncio
    async def test_handler_error_does_not_break_stream(self, client):
        """Test handler errors don't break event stream."""

        def error_handler(thinking):
            raise Exception("Handler failed")

        calls = []

        def good_handler(thinking):
            calls.append(thinking)

        client.on_thinking(error_handler)
        client.on_thinking(good_handler)

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert len(calls) == 1

    def test_off_thinking_unregisters_handler(self, client):
        """Test off_thinking removes handler."""
        handler = lambda thinking: None
        client.on_thinking(handler)
        client.off_thinking(handler)

        assert len(client._thinking_handlers) == 0

    @pytest.mark.asyncio
    async def test_off_thinking_only_removes_specified_handler(self, client):
        """Test off_thinking only removes specified handler."""
        calls1 = []
        calls2 = []

        handler1 = lambda t: calls1.append(t)
        handler2 = lambda t: calls2.append(t)

        client.on_thinking(handler1)
        client.on_thinking(handler2)
        client.off_thinking(handler1)

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert len(calls1) == 0
        assert len(calls2) == 1

    def test_get_thinking_state_initial(self, client):
        """Test get_thinking_state returns initial state."""
        state = client.get_thinking_state()

        assert state["is_thinking"] is False
        assert state["content"] == ""

    @pytest.mark.asyncio
    async def test_get_thinking_state_after_event(self, client):
        """Test get_thinking_state returns updated state."""
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Test"}))

        state = client.get_thinking_state()

        assert state["is_thinking"] is True
        assert state["content"] == "Test"

    @pytest.mark.asyncio
    async def test_get_thinking_state_shows_accumulated(self, client):
        """Test get_thinking_state shows accumulated content."""
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Part 1 "}))
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Part 2"}))

        state = client.get_thinking_state()

        assert state["content"] == "Part 1 Part 2"

    @pytest.mark.asyncio
    async def test_clear_thinking_state_resets(self, client):
        """Test clear_thinking_state resets state."""
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Test"}))

        assert client.get_thinking_state()["is_thinking"] is True

        client.clear_thinking_state()

        state = client.get_thinking_state()
        assert state["is_thinking"] is False
        assert state["content"] == ""

    @pytest.mark.asyncio
    async def test_clear_thinking_state_preserves_handlers(self, client):
        """Test clear_thinking_state doesn't remove handlers."""
        calls = []
        client.on_thinking(lambda t: calls.append(t))

        client.clear_thinking_state()

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_clear_allows_rebuild_after_clear(self, client):
        """Test state can be rebuilt after clear."""
        await client._emit_event(Event(type="thinking.delta", data={"delta": "First"}))
        client.clear_thinking_state()
        await client._emit_event(Event(type="thinking.delta", data={"delta": "Second"}))

        state = client.get_thinking_state()
        assert state["content"] == "Second"

    @pytest.mark.asyncio
    async def test_thinking_state_transitions(self, client):
        """Test isThinking flag transitions."""
        assert client.get_thinking_state()["is_thinking"] is False

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert client.get_thinking_state()["is_thinking"] is True

    @pytest.mark.asyncio
    async def test_thinking_persists_across_deltas(self, client):
        """Test isThinking stays true across multiple deltas."""
        await client._emit_event(Event(type="thinking.delta", data={"delta": "1"}))
        await client._emit_event(Event(type="thinking.delta", data={"delta": "2"}))
        await client._emit_event(Event(type="thinking.delta", data={"delta": "3"}))

        assert client.get_thinking_state()["is_thinking"] is True

    @pytest.mark.asyncio
    async def test_integration_with_generic_handlers(self, client):
        """Test thinking works alongside generic event handlers."""
        specific_calls = []
        generic_calls = []

        client.on_thinking(lambda t: specific_calls.append(t))
        client.on("thinking.delta", lambda e: generic_calls.append(e))

        await client._emit_event(Event(type="thinking.delta", data={"delta": "test"}))

        assert len(specific_calls) == 1
        assert len(generic_calls) == 1

    @pytest.mark.asyncio
    async def test_does_not_interfere_with_other_events(self, client):
        """Test thinking handlers don't interfere with other event types."""
        thinking_calls = []
        content_calls = []

        client.on_thinking(lambda t: thinking_calls.append(t))
        client.on("content.delta", lambda e: content_calls.append(e))

        await client._emit_event(Event(type="content.delta", data={"delta": "test"}))

        assert len(thinking_calls) == 0
        assert len(content_calls) == 1
