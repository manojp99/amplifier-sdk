"""Tests for client-side behaviors."""

import pytest
from amplifier_sdk import AmplifierClient, BehaviorDefinition, ModuleConfig


class TestClientSideBehaviors:
    """Test cases for behavior functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return AmplifierClient()

    def test_define_behavior(self, client):
        """Test define_behavior creates a behavior."""
        behavior = client.define_behavior(
            BehaviorDefinition(
                name="test-behavior",
                description="Test behavior",
                instructions="Be helpful",
            )
        )

        assert behavior.name == "test-behavior"
        assert behavior.description == "Test behavior"
        assert behavior.instructions == "Be helpful"

    def test_define_behavior_requires_name(self, client):
        """Test define_behavior requires name."""
        with pytest.raises(ValueError, match="Behavior name is required"):
            client.define_behavior(BehaviorDefinition(name=""))

    def test_define_behavior_stores_for_retrieval(self, client):
        """Test defined behavior can be retrieved."""
        client.define_behavior(BehaviorDefinition(name="stored-behavior", instructions="Test"))

        retrieved = client.get_behavior("stored-behavior")
        assert retrieved is not None
        assert retrieved.name == "stored-behavior"

    def test_define_behavior_with_tools(self, client):
        """Test behavior can include tools."""
        behavior = client.define_behavior(
            BehaviorDefinition(
                name="tool-behavior",
                tools=[ModuleConfig(module="tool-bash")],
                client_tools=["custom-tool"],
            )
        )

        assert len(behavior.tools) == 1
        assert len(behavior.client_tools) == 1

    def test_define_behavior_with_providers(self, client):
        """Test behavior can include providers."""
        behavior = client.define_behavior(
            BehaviorDefinition(
                name="provider-behavior",
                providers=[
                    ModuleConfig(module="provider-anthropic", config={"model": "claude-sonnet"})
                ],
            )
        )

        assert len(behavior.providers) == 1
        assert behavior.providers[0].config == {"model": "claude-sonnet"}

    def test_get_behavior_nonexistent(self, client):
        """Test get_behavior returns None for non-existent behavior."""
        behavior = client.get_behavior("nonexistent")
        assert behavior is None

    def test_get_behavior_returns_defined(self, client):
        """Test get_behavior returns defined behavior."""
        client.define_behavior(BehaviorDefinition(name="test", instructions="Test"))
        behavior = client.get_behavior("test")
        assert behavior is not None
        assert behavior.name == "test"

    def test_get_behaviors_empty_initially(self, client):
        """Test get_behaviors returns empty list initially."""
        behaviors = client.get_behaviors()
        assert behaviors == []

    def test_get_behaviors_returns_all(self, client):
        """Test get_behaviors returns all defined behaviors."""
        client.define_behavior(BehaviorDefinition(name="behavior1", instructions="Test1"))
        client.define_behavior(BehaviorDefinition(name="behavior2", instructions="Test2"))
        client.define_behavior(BehaviorDefinition(name="behavior3", instructions="Test3"))

        behaviors = client.get_behaviors()
        assert len(behaviors) == 3
        names = [b.name for b in behaviors]
        assert "behavior1" in names
        assert "behavior2" in names
        assert "behavior3" in names

    def test_remove_behavior(self, client):
        """Test remove_behavior removes a behavior."""
        client.define_behavior(BehaviorDefinition(name="removable", instructions="Test"))
        assert client.get_behavior("removable") is not None

        removed = client.remove_behavior("removable")
        assert removed is True
        assert client.get_behavior("removable") is None

    def test_remove_behavior_nonexistent(self, client):
        """Test remove_behavior returns False for non-existent."""
        removed = client.remove_behavior("nonexistent")
        assert removed is False

    def test_merge_behaviors_instructions(self, client):
        """Test merging instructions from behavior."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(
                name="security", instructions="Always ask before sensitive operations"
            )
        )

        merged = client._merge_behaviors(
            BundleDefinition(name="agent", instructions="Be helpful"), ["security"]
        )

        assert "Be helpful" in merged.instructions
        assert "Always ask before sensitive operations" in merged.instructions

    def test_merge_behaviors_tools_without_duplicates(self, client):
        """Test merging tools deduplicates."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(
                name="toolset",
                tools=[
                    ModuleConfig(module="tool-bash"),
                    ModuleConfig(module="tool-filesystem"),
                ],
            )
        )

        merged = client._merge_behaviors(
            BundleDefinition(name="agent", tools=[ModuleConfig(module="tool-bash")]),
            ["toolset"],
        )

        assert len(merged.tools) == 2
        modules = [t.module for t in merged.tools]
        assert "tool-bash" in modules
        assert "tool-filesystem" in modules

    def test_merge_behaviors_client_tools_without_duplicates(self, client):
        """Test merging client tools deduplicates."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(name="client-toolset", client_tools=["tool1", "tool2"])
        )

        merged = client._merge_behaviors(
            BundleDefinition(name="agent", client_tools=["tool1", "tool3"]),
            ["client-toolset"],
        )

        assert len(merged.client_tools) == 3
        assert "tool1" in merged.client_tools
        assert "tool2" in merged.client_tools
        assert "tool3" in merged.client_tools

    def test_merge_behaviors_providers_without_duplicates(self, client):
        """Test merging providers deduplicates."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(
                name="providers",
                providers=[
                    ModuleConfig(module="provider-anthropic"),
                    ModuleConfig(module="provider-openai"),
                ],
            )
        )

        merged = client._merge_behaviors(
            BundleDefinition(name="agent", providers=[ModuleConfig(module="provider-anthropic")]),
            ["providers"],
        )

        assert len(merged.providers) == 2
        modules = [p.module for p in merged.providers]
        assert "provider-anthropic" in modules
        assert "provider-openai" in modules

    def test_merge_multiple_behaviors(self, client):
        """Test merging multiple behaviors."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(name="security", instructions="Be security-minded")
        )

        client.define_behavior(
            BehaviorDefinition(
                name="customer-support",
                instructions="Be empathetic",
                client_tools=["get-order"],
            )
        )

        merged = client._merge_behaviors(
            BundleDefinition(name="agent", instructions="Base instructions"),
            ["security", "customer-support"],
        )

        assert "Base instructions" in merged.instructions
        assert "Be security-minded" in merged.instructions
        assert "Be empathetic" in merged.instructions
        assert "get-order" in merged.client_tools

    def test_merge_undefined_behavior_raises(self, client):
        """Test merging undefined behavior raises error."""
        from amplifier_sdk.types import BundleDefinition

        with pytest.raises(ValueError, match="Behavior 'nonexistent' not found"):
            client._merge_behaviors(BundleDefinition(name="agent"), ["nonexistent"])

    def test_merge_preserves_base_properties(self, client):
        """Test merging preserves base bundle properties."""
        from amplifier_sdk.types import BundleDefinition

        client.define_behavior(
            BehaviorDefinition(name="addon", tools=[ModuleConfig(module="tool-bash")])
        )

        merged = client._merge_behaviors(
            BundleDefinition(
                name="agent",
                version="1.0.0",
                description="My agent",
                session={"debug": True},
            ),
            ["addon"],
        )

        assert merged.name == "agent"
        assert merged.version == "1.0.0"
        assert merged.description == "My agent"
        assert merged.session == {"debug": True}
