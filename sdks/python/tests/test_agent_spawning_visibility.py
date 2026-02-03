"""Tests for Agent Spawning Visibility feature.

Tests the on_agent_spawned, on_agent_completed, get_agent_hierarchy, and
clear_agent_hierarchy methods, along with hierarchy tracking and edge case handling.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from amplifier_sdk import AgentNode, AmplifierClient, Event


class TestAgentSpawningVisibility:
    """Test cases for agent spawning visibility feature."""

    @pytest.fixture
    def client(self) -> AmplifierClient:
        """Create a test client."""
        return AmplifierClient(base_url="http://localhost:4096")

    async def emit_event(self, client: AmplifierClient, event: Event) -> None:
        """Helper to simulate event emission."""
        await client._emit_event(event)

    async def simulate_agent_spawned(
        self,
        client: AmplifierClient,
        agent_id: str,
        parent_id: str | None = None,
        agent_name: str = "test-agent",
    ) -> None:
        """Helper to simulate agent spawned event."""
        event = Event(
            type="agent.spawned",
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_id": parent_id,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    async def simulate_agent_completed(
        self,
        client: AmplifierClient,
        agent_id: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """Helper to simulate agent completed event."""
        event_data: dict[str, Any] = {"agent_id": agent_id}
        if result is not None:
            event_data["result"] = result
        if error is not None:
            event_data["error"] = error

        event = Event(
            type="agent.completed",
            data=event_data,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    @pytest.mark.asyncio
    async def test_on_agent_spawned_registers_handler(self, client: AmplifierClient) -> None:
        """Handler should be called when agent.spawned event received."""
        handler_called = False
        handler_info = None

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called, handler_info
            handler_called = True
            handler_info = info

        client.on_agent_spawned(handler)

        await self.simulate_agent_spawned(client, "agent-123", None, "foundation:explorer")

        assert handler_called
        assert handler_info is not None
        assert handler_info["agent_id"] == "agent-123"
        assert handler_info["agent_name"] == "foundation:explorer"
        assert handler_info["parent_id"] is None
        assert "timestamp" in handler_info

    @pytest.mark.asyncio
    async def test_on_agent_spawned_with_parent_id(self, client: AmplifierClient) -> None:
        """Handler should receive parent ID when present."""
        handler_info = None

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_info
            handler_info = info

        client.on_agent_spawned(handler)

        await self.simulate_agent_spawned(client, "child-1", "parent-1", "foundation:bug-hunter")

        assert handler_info is not None
        assert handler_info["agent_id"] == "child-1"
        assert handler_info["agent_name"] == "foundation:bug-hunter"
        assert handler_info["parent_id"] == "parent-1"

    @pytest.mark.asyncio
    async def test_on_agent_spawned_multiple_handlers(self, client: AmplifierClient) -> None:
        """Should support multiple handlers."""
        handler1_called = False
        handler2_called = False

        def handler1(info: dict[str, Any]) -> None:
            nonlocal handler1_called
            handler1_called = True

        def handler2(info: dict[str, Any]) -> None:
            nonlocal handler2_called
            handler2_called = True

        client.on_agent_spawned(handler1)
        client.on_agent_spawned(handler2)

        await self.simulate_agent_spawned(client, "agent-1")

        assert handler1_called
        assert handler2_called

    @pytest.mark.asyncio
    async def test_on_agent_spawned_async_handler(self, client: AmplifierClient) -> None:
        """Should support async handlers."""
        handler_called = False

        async def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            await asyncio.sleep(0.01)
            handler_called = True

        client.on_agent_spawned(handler)

        await self.simulate_agent_spawned(client, "agent-1")

        assert handler_called

    @pytest.mark.asyncio
    async def test_on_agent_spawned_error_handling(self, client: AmplifierClient) -> None:
        """Should continue if handler throws error."""
        handler1_called = False
        handler2_called = False

        def error_handler(info: dict[str, Any]) -> None:
            nonlocal handler1_called
            handler1_called = True
            raise ValueError("Handler error")

        def success_handler(info: dict[str, Any]) -> None:
            nonlocal handler2_called
            handler2_called = True

        client.on_agent_spawned(error_handler)
        client.on_agent_spawned(success_handler)

        # Should not raise
        await self.simulate_agent_spawned(client, "agent-1")

        assert handler1_called
        assert handler2_called

    @pytest.mark.asyncio
    async def test_on_agent_spawned_missing_agent_id(self, client: AmplifierClient) -> None:
        """Should not call handler if agent_id is missing."""
        handler_called = False

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            handler_called = True

        client.on_agent_spawned(handler)

        event = Event(
            type="agent.spawned",
            data={"agent_name": "test"},  # Missing agent_id
        )
        await self.emit_event(client, event)

        assert not handler_called

    @pytest.mark.asyncio
    async def test_off_agent_spawned_removes_handler(self, client: AmplifierClient) -> None:
        """Should remove registered handler."""
        handler_called = False

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            handler_called = True

        client.on_agent_spawned(handler)
        client.off_agent_spawned(handler)

        await self.simulate_agent_spawned(client, "agent-1")

        assert not handler_called

    @pytest.mark.asyncio
    async def test_off_agent_spawned_non_existent_handler(self, client: AmplifierClient) -> None:
        """Should not error when removing non-existent handler."""

        def handler(info: dict[str, Any]) -> None:
            pass

        # Should not raise
        client.off_agent_spawned(handler)

    @pytest.mark.asyncio
    async def test_off_agent_spawned_only_removes_specified(self, client: AmplifierClient) -> None:
        """Should only remove specified handler."""
        handler1_called = False
        handler2_called = False

        def handler1(info: dict[str, Any]) -> None:
            nonlocal handler1_called
            handler1_called = True

        def handler2(info: dict[str, Any]) -> None:
            nonlocal handler2_called
            handler2_called = True

        client.on_agent_spawned(handler1)
        client.on_agent_spawned(handler2)
        client.off_agent_spawned(handler1)

        await self.simulate_agent_spawned(client, "agent-1")

        assert not handler1_called
        assert handler2_called

    @pytest.mark.asyncio
    async def test_on_agent_completed_with_result(self, client: AmplifierClient) -> None:
        """Handler should receive result field."""
        handler_info = None

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_info
            handler_info = info

        client.on_agent_completed(handler)

        await self.simulate_agent_completed(client, "agent-123", "Task completed")

        assert handler_info is not None
        assert handler_info["agent_id"] == "agent-123"
        assert handler_info["result"] == "Task completed"
        assert handler_info.get("error") is None

    @pytest.mark.asyncio
    async def test_on_agent_completed_with_error(self, client: AmplifierClient) -> None:
        """Handler should receive error field."""
        handler_info = None

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_info
            handler_info = info

        client.on_agent_completed(handler)

        await self.simulate_agent_completed(client, "agent-123", None, "Task failed")

        assert handler_info is not None
        assert handler_info["agent_id"] == "agent-123"
        assert handler_info["error"] == "Task failed"
        assert handler_info.get("result") is None

    @pytest.mark.asyncio
    async def test_on_agent_completed_multiple_handlers(self, client: AmplifierClient) -> None:
        """Should support multiple handlers."""
        handler1_called = False
        handler2_called = False

        def handler1(info: dict[str, Any]) -> None:
            nonlocal handler1_called
            handler1_called = True

        def handler2(info: dict[str, Any]) -> None:
            nonlocal handler2_called
            handler2_called = True

        client.on_agent_completed(handler1)
        client.on_agent_completed(handler2)

        await self.simulate_agent_completed(client, "agent-1", "Done")

        assert handler1_called
        assert handler2_called

    @pytest.mark.asyncio
    async def test_on_agent_completed_async_handler(self, client: AmplifierClient) -> None:
        """Should support async handlers."""
        handler_called = False

        async def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            await asyncio.sleep(0.01)
            handler_called = True

        client.on_agent_completed(handler)

        await self.simulate_agent_completed(client, "agent-1", "Done")

        assert handler_called

    @pytest.mark.asyncio
    async def test_on_agent_completed_error_handling(self, client: AmplifierClient) -> None:
        """Should continue if handler throws error."""
        handler1_called = False
        handler2_called = False

        def error_handler(info: dict[str, Any]) -> None:
            nonlocal handler1_called
            handler1_called = True
            raise ValueError("Handler error")

        def success_handler(info: dict[str, Any]) -> None:
            nonlocal handler2_called
            handler2_called = True

        client.on_agent_completed(error_handler)
        client.on_agent_completed(success_handler)

        # Should not raise
        await self.simulate_agent_completed(client, "agent-1", "Done")

        assert handler1_called
        assert handler2_called

    @pytest.mark.asyncio
    async def test_on_agent_completed_missing_agent_id(self, client: AmplifierClient) -> None:
        """Should not call handler if agent_id is missing."""
        handler_called = False

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            handler_called = True

        client.on_agent_completed(handler)

        event = Event(
            type="agent.completed",
            data={"result": "Done"},  # Missing agent_id
        )
        await self.emit_event(client, event)

        assert not handler_called

    @pytest.mark.asyncio
    async def test_off_agent_completed_removes_handler(self, client: AmplifierClient) -> None:
        """Should remove registered handler."""
        handler_called = False

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_called
            handler_called = True

        client.on_agent_completed(handler)
        client.off_agent_completed(handler)

        await self.simulate_agent_completed(client, "agent-1", "Done")

        assert not handler_called

    @pytest.mark.asyncio
    async def test_off_agent_completed_non_existent_handler(self, client: AmplifierClient) -> None:
        """Should not error when removing non-existent handler."""

        def handler(info: dict[str, Any]) -> None:
            pass

        # Should not raise
        client.off_agent_completed(handler)

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_empty_initially(self, client: AmplifierClient) -> None:
        """Should return empty dict initially."""
        hierarchy = client.get_agent_hierarchy()
        assert len(hierarchy) == 0

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_single_agent(self, client: AmplifierClient) -> None:
        """Should track single agent spawn."""
        await self.simulate_agent_spawned(client, "root", None, "foundation")

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 1
        node = hierarchy.get("root")
        assert node is not None
        assert node.agent_id == "root"
        assert node.agent_name == "foundation"
        assert node.parent_id is None
        assert node.children == []
        assert node.spawned_at != ""
        assert node.completed_at is None

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_parent_child_relationships(
        self, client: AmplifierClient
    ) -> None:
        """Should track parent-child relationships."""
        await self.simulate_agent_spawned(client, "root", None, "foundation")
        await self.simulate_agent_spawned(client, "child-1", "root", "explorer")
        await self.simulate_agent_spawned(client, "child-2", "root", "bug-hunter")

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 3

        root = hierarchy.get("root")
        assert root is not None
        assert root.children == ["child-1", "child-2"]

        child1 = hierarchy.get("child-1")
        assert child1 is not None
        assert child1.parent_id == "root"
        assert child1.agent_name == "explorer"

        child2 = hierarchy.get("child-2")
        assert child2 is not None
        assert child2.parent_id == "root"
        assert child2.agent_name == "bug-hunter"

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_deep_nesting(self, client: AmplifierClient) -> None:
        """Should track deep nesting."""
        await self.simulate_agent_spawned(client, "root", None, "foundation")
        await self.simulate_agent_spawned(client, "level-1", "root", "explorer")
        await self.simulate_agent_spawned(client, "level-2", "level-1", "bug-hunter")
        await self.simulate_agent_spawned(client, "level-3", "level-2", "zen-architect")

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 4
        assert "level-1" in hierarchy["root"].children
        assert "level-2" in hierarchy["level-1"].children
        assert "level-3" in hierarchy["level-2"].children
        assert hierarchy["level-3"].parent_id == "level-2"

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_update_on_completion(self, client: AmplifierClient) -> None:
        """Should update node on completion."""
        await self.simulate_agent_spawned(client, "agent-1", None, "test")
        await self.simulate_agent_completed(client, "agent-1", "Task completed")

        hierarchy = client.get_agent_hierarchy()
        node = hierarchy.get("agent-1")

        assert node is not None
        assert node.completed_at is not None
        assert node.result == "Task completed"
        assert node.error is None

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_update_with_error(self, client: AmplifierClient) -> None:
        """Should update node with error on failed completion."""
        await self.simulate_agent_spawned(client, "agent-1", None, "test")
        await self.simulate_agent_completed(client, "agent-1", None, "Task failed")

        hierarchy = client.get_agent_hierarchy()
        node = hierarchy.get("agent-1")

        assert node is not None
        assert node.completed_at is not None
        assert node.error == "Task failed"
        assert node.result is None

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_completion_before_spawn(
        self, client: AmplifierClient
    ) -> None:
        """Should handle completion before spawn."""
        # Complete before spawn
        await self.simulate_agent_completed(client, "agent-1", "Done")

        hierarchy = client.get_agent_hierarchy()
        node = hierarchy.get("agent-1")

        # Node should exist with completion data
        assert node is not None
        assert node.result == "Done"

        # Now spawn the agent
        await self.simulate_agent_spawned(client, "agent-1", None, "test")

        hierarchy = client.get_agent_hierarchy()
        node = hierarchy.get("agent-1")

        # Should have both spawn and completion data
        assert node is not None
        assert node.agent_name == "test"
        assert node.result == "Done"

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_duplicate_spawn(self, client: AmplifierClient) -> None:
        """Should handle duplicate spawn events."""
        await self.simulate_agent_spawned(client, "agent-1", None, "first-name")
        await self.simulate_agent_spawned(client, "agent-1", None, "second-name")

        hierarchy = client.get_agent_hierarchy()

        # Should have one node with updated name
        assert len(hierarchy) == 1
        node = hierarchy.get("agent-1")
        assert node is not None
        assert node.agent_name == "second-name"

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_placeholder_parent(self, client: AmplifierClient) -> None:
        """Should create placeholder parent if missing."""
        # Spawn child without parent existing
        await self.simulate_agent_spawned(client, "child-1", "missing-parent", "explorer")

        hierarchy = client.get_agent_hierarchy()

        # Both child and placeholder parent should exist
        assert len(hierarchy) == 2

        parent = hierarchy.get("missing-parent")
        assert parent is not None
        assert parent.agent_name == "unknown"
        assert "child-1" in parent.children

        child = hierarchy.get("child-1")
        assert child is not None
        assert child.parent_id == "missing-parent"

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_no_duplicate_children(self, client: AmplifierClient) -> None:
        """Should not duplicate children on re-spawn."""
        await self.simulate_agent_spawned(client, "parent", None, "foundation")
        await self.simulate_agent_spawned(client, "child", "parent", "explorer")
        await self.simulate_agent_spawned(client, "child", "parent", "explorer-v2")

        hierarchy = client.get_agent_hierarchy()
        parent = hierarchy.get("parent")

        # Child should appear only once
        assert parent is not None
        assert parent.children == ["child"]

    @pytest.mark.asyncio
    async def test_get_agent_hierarchy_returns_copy(self, client: AmplifierClient) -> None:
        """Should return a copy of hierarchy."""
        await self.simulate_agent_spawned(client, "agent-1", None, "test")

        hierarchy1 = client.get_agent_hierarchy()
        hierarchy2 = client.get_agent_hierarchy()

        # Should be different objects
        assert hierarchy1 is not hierarchy2

        # But have same content
        assert len(hierarchy1) == len(hierarchy2)
        assert hierarchy1["agent-1"].agent_id == hierarchy2["agent-1"].agent_id

    @pytest.mark.asyncio
    async def test_clear_agent_hierarchy(self, client: AmplifierClient) -> None:
        """Should clear all agents from hierarchy."""
        await self.simulate_agent_spawned(client, "agent-1")
        await self.simulate_agent_spawned(client, "agent-2")
        await self.simulate_agent_spawned(client, "agent-3")

        assert len(client.get_agent_hierarchy()) == 3

        client.clear_agent_hierarchy()

        assert len(client.get_agent_hierarchy()) == 0

    @pytest.mark.asyncio
    async def test_clear_agent_hierarchy_preserves_handlers(self, client: AmplifierClient) -> None:
        """Should not affect handlers."""
        handler_call_count = 0

        def handler(info: dict[str, Any]) -> None:
            nonlocal handler_call_count
            handler_call_count += 1

        client.on_agent_spawned(handler)

        await self.simulate_agent_spawned(client, "agent-1")
        client.clear_agent_hierarchy()
        await self.simulate_agent_spawned(client, "agent-2")

        # Handler should still be called after clear
        assert handler_call_count == 2

    @pytest.mark.asyncio
    async def test_clear_agent_hierarchy_rebuild(self, client: AmplifierClient) -> None:
        """Should allow rebuilding hierarchy after clear."""
        await self.simulate_agent_spawned(client, "agent-1")
        client.clear_agent_hierarchy()
        await self.simulate_agent_spawned(client, "agent-2")

        hierarchy = client.get_agent_hierarchy()
        assert len(hierarchy) == 1
        assert "agent-1" not in hierarchy
        assert "agent-2" in hierarchy


class TestHierarchyEdgeCases:
    """Test edge cases in hierarchy tracking."""

    @pytest.fixture
    def client(self) -> AmplifierClient:
        """Create a test client."""
        return AmplifierClient(base_url="http://localhost:4096")

    async def emit_event(self, client: AmplifierClient, event: Event) -> None:
        """Helper to simulate event emission."""
        await client._emit_event(event)

    async def simulate_agent_spawned(
        self,
        client: AmplifierClient,
        agent_id: str,
        parent_id: str | None = None,
        agent_name: str = "test-agent",
    ) -> None:
        """Helper to simulate agent spawned event."""
        event = Event(
            type="agent.spawned",
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_id": parent_id,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    async def simulate_agent_completed(
        self,
        client: AmplifierClient,
        agent_id: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """Helper to simulate agent completed event."""
        event_data: dict[str, Any] = {"agent_id": agent_id}
        if result is not None:
            event_data["result"] = result
        if error is not None:
            event_data["error"] = error

        event = Event(
            type="agent.completed",
            data=event_data,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    @pytest.mark.asyncio
    async def test_multiple_root_agents(self, client: AmplifierClient) -> None:
        """Should handle multiple root agents."""
        await self.simulate_agent_spawned(client, "root-1", None, "foundation")
        await self.simulate_agent_spawned(client, "root-2", None, "python-dev")
        await self.simulate_agent_spawned(client, "root-3", None, "design-intelligence")

        hierarchy = client.get_agent_hierarchy()
        roots = [node for node in hierarchy.values() if node.parent_id is None]

        assert len(roots) == 3

    @pytest.mark.asyncio
    async def test_complex_tree_structure(self, client: AmplifierClient) -> None:
        """Should handle complex tree structures."""
        # Build a complex tree:
        #        root
        #       /  |  \
        #      a   b   c
        #     / \      |
        #    d   e     f
        #             / \
        #            g   h

        await self.simulate_agent_spawned(client, "root")
        await self.simulate_agent_spawned(client, "a", "root")
        await self.simulate_agent_spawned(client, "b", "root")
        await self.simulate_agent_spawned(client, "c", "root")
        await self.simulate_agent_spawned(client, "d", "a")
        await self.simulate_agent_spawned(client, "e", "a")
        await self.simulate_agent_spawned(client, "f", "c")
        await self.simulate_agent_spawned(client, "g", "f")
        await self.simulate_agent_spawned(client, "h", "f")

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 9
        assert hierarchy["root"].children == ["a", "b", "c"]
        assert hierarchy["a"].children == ["d", "e"]
        assert hierarchy["c"].children == ["f"]
        assert hierarchy["f"].children == ["g", "h"]

    @pytest.mark.asyncio
    async def test_agent_with_many_children(self, client: AmplifierClient) -> None:
        """Should handle agent with many children."""
        await self.simulate_agent_spawned(client, "parent")

        # Add 100 children
        for i in range(100):
            await self.simulate_agent_spawned(client, f"child-{i}", "parent")

        hierarchy = client.get_agent_hierarchy()
        parent = hierarchy.get("parent")

        assert len(hierarchy) == 101
        assert parent is not None
        assert len(parent.children) == 100

    @pytest.mark.asyncio
    async def test_preserve_timestamps(self, client: AmplifierClient) -> None:
        """Should preserve timestamps across spawn and complete."""
        spawn_time = "2024-01-01T10:00:00Z"
        complete_time = "2024-01-01T10:05:00Z"

        spawn_event = Event(
            type="agent.spawned",
            data={"agent_id": "agent-1", "agent_name": "test"},
            timestamp=spawn_time,
        )
        await self.emit_event(client, spawn_event)

        complete_event = Event(
            type="agent.completed",
            data={"agent_id": "agent-1", "result": "Done"},
            timestamp=complete_time,
        )
        await self.emit_event(client, complete_event)

        node = client.get_agent_hierarchy()["agent-1"]

        assert node.spawned_at == spawn_time
        assert node.completed_at == complete_time

    @pytest.mark.asyncio
    async def test_missing_agent_name(self, client: AmplifierClient) -> None:
        """Should handle missing agent_name gracefully."""
        event = Event(
            type="agent.spawned",
            data={"agent_id": "agent-1"},  # Missing agent_name
        )
        await self.emit_event(client, event)

        node = client.get_agent_hierarchy().get("agent-1")

        assert node is not None
        assert node.agent_name == "unknown"

    @pytest.mark.asyncio
    async def test_interleaved_spawn_complete_events(self, client: AmplifierClient) -> None:
        """Should handle interleaved spawn and complete events."""
        await self.simulate_agent_spawned(client, "agent-1", None, "first")
        await self.simulate_agent_spawned(client, "agent-2", "agent-1", "second")
        await self.simulate_agent_completed(client, "agent-2", "Done")
        await self.simulate_agent_spawned(client, "agent-3", "agent-1", "third")
        await self.simulate_agent_completed(client, "agent-1", "All done")

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 3
        assert hierarchy["agent-1"].completed_at is not None
        assert hierarchy["agent-2"].completed_at is not None
        assert hierarchy["agent-3"].completed_at is None


class TestIntegrationWithEventSystem:
    """Test integration with the existing event system."""

    @pytest.fixture
    def client(self) -> AmplifierClient:
        """Create a test client."""
        return AmplifierClient(base_url="http://localhost:4096")

    async def emit_event(self, client: AmplifierClient, event: Event) -> None:
        """Helper to simulate event emission."""
        await client._emit_event(event)

    async def simulate_agent_spawned(
        self,
        client: AmplifierClient,
        agent_id: str,
        parent_id: str | None = None,
        agent_name: str = "test-agent",
    ) -> None:
        """Helper to simulate agent spawned event."""
        event = Event(
            type="agent.spawned",
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_id": parent_id,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    @pytest.mark.asyncio
    async def test_works_with_generic_event_handlers(self, client: AmplifierClient) -> None:
        """Should work with generic event handlers."""
        agent_spawned_called = False
        generic_called = False

        def agent_spawned_handler(info: dict[str, Any]) -> None:
            nonlocal agent_spawned_called
            agent_spawned_called = True

        def generic_handler(event: Event) -> None:
            nonlocal generic_called
            generic_called = True

        client.on_agent_spawned(agent_spawned_handler)
        client.on("agent.spawned", generic_handler)

        await self.simulate_agent_spawned(client, "agent-1")

        # Both handlers should be called
        assert agent_spawned_called
        assert generic_called

    @pytest.mark.asyncio
    async def test_tracks_hierarchy_without_handlers(self, client: AmplifierClient) -> None:
        """Should track hierarchy even without handlers."""
        # No handlers registered
        await self.simulate_agent_spawned(client, "agent-1")

        hierarchy = client.get_agent_hierarchy()

        # Hierarchy should still be tracked
        assert len(hierarchy) == 1


class TestMemoryAndPerformance:
    """Test memory and performance characteristics."""

    @pytest.fixture
    def client(self) -> AmplifierClient:
        """Create a test client."""
        return AmplifierClient(base_url="http://localhost:4096")

    async def emit_event(self, client: AmplifierClient, event: Event) -> None:
        """Helper to simulate event emission."""
        await client._emit_event(event)

    async def simulate_agent_spawned(
        self,
        client: AmplifierClient,
        agent_id: str,
        parent_id: str | None = None,
        agent_name: str = "test-agent",
    ) -> None:
        """Helper to simulate agent spawned event."""
        event = Event(
            type="agent.spawned",
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_id": parent_id,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await self.emit_event(client, event)

    @pytest.mark.asyncio
    async def test_large_hierarchies(self, client: AmplifierClient) -> None:
        """Should handle large hierarchies efficiently."""
        import time

        start_time = time.time()

        # Create 1000 agents
        for i in range(1000):
            parent_id = f"agent-{i - 1}" if i > 0 else None
            await self.simulate_agent_spawned(client, f"agent-{i}", parent_id)

        end_time = time.time()

        hierarchy = client.get_agent_hierarchy()

        assert len(hierarchy) == 1000
        assert (end_time - start_time) < 5.0  # Should complete in reasonable time

    @pytest.mark.asyncio
    async def test_no_memory_leak_on_clear(self, client: AmplifierClient) -> None:
        """Should not leak memory when clearing hierarchy."""
        for i in range(100):
            await self.simulate_agent_spawned(client, f"agent-{i}")

        client.clear_agent_hierarchy()

        assert len(client.get_agent_hierarchy()) == 0

        # Add new agents - should start fresh
        await self.simulate_agent_spawned(client, "new-agent")
        assert len(client.get_agent_hierarchy()) == 1


class TestTypeSafety:
    """Test type safety and data structure validation."""

    def test_agent_node_structure(self) -> None:
        """Should properly construct AgentNode."""
        node = AgentNode(
            agent_id="test",
            agent_name="test-agent",
            parent_id=None,
            children=[],
            spawned_at=datetime.utcnow().isoformat() + "Z",
            completed_at=None,
        )

        assert node.agent_id == "test"
        assert node.agent_name == "test-agent"
        assert node.parent_id is None
        assert node.children == []
        assert node.spawned_at != ""
        assert node.completed_at is None

    def test_agent_node_with_result(self) -> None:
        """Should handle result and error fields."""
        node = AgentNode(
            agent_id="test",
            agent_name="test-agent",
            parent_id=None,
            children=[],
            spawned_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:01:00Z",
            result="Success",
            error=None,
        )

        assert node.result == "Success"
        assert node.error is None


class TestCleanup:
    """Test cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_close_clears_hierarchy(self) -> None:
        """Should clear hierarchy on close."""
        client = AmplifierClient(base_url="http://localhost:4096")

        event = Event(
            type="agent.spawned",
            data={"agent_id": "agent-1", "agent_name": "test"},
        )
        await client._emit_event(event)

        assert len(client.get_agent_hierarchy()) == 1

        await client.close()

        # Hierarchy should be cleared
        assert len(client.get_agent_hierarchy()) == 0
