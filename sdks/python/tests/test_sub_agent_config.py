"""Tests for sub-agent configuration."""

from amplifier_sdk import AmplifierClient, BehaviorDefinition, BundleDefinition
from amplifier_sdk.types import AgentConfig


class TestSubAgentConfiguration:
    """Test cases for sub-agent configuration."""

    def test_agents_in_bundle_definition(self):
        """Test agents can be included in bundle."""
        bundle = BundleDefinition(
            name="multi-agent",
            agents=[
                AgentConfig(
                    name="code-reviewer",
                    description="Reviews code",
                    instructions="Review for bugs",
                    tools=["tool-filesystem"],
                )
            ],
        )

        assert bundle.agents is not None
        assert len(bundle.agents) == 1
        assert bundle.agents[0].name == "code-reviewer"

    def test_bundle_to_dict_includes_agents(self):
        """Test agents are included in to_dict()."""
        bundle = BundleDefinition(
            name="test",
            agents=[
                AgentConfig(name="specialist1", instructions="Task A"),
                AgentConfig(name="specialist2", instructions="Task B"),
            ],
        )

        bundle_dict = bundle.to_dict()

        assert "agents" in bundle_dict
        assert len(bundle_dict["agents"]) == 2
        assert bundle_dict["agents"][0]["name"] == "specialist1"

    def test_empty_agents_array(self):
        """Test empty agents array."""
        bundle = BundleDefinition(name="test", agents=[])

        bundle_dict = bundle.to_dict()

        # Empty list is falsy, so agents won't be in dict
        assert "agents" not in bundle_dict

    def test_missing_agents_field(self):
        """Test bundle without agents field."""
        bundle = BundleDefinition(name="test", instructions="Test")

        bundle_dict = bundle.to_dict()

        # Should not include agents if not specified
        assert "agents" not in bundle_dict or bundle_dict.get("agents") is None

    def test_agent_with_minimal_config(self):
        """Test minimal agent configuration."""
        bundle = BundleDefinition(name="test", agents=[AgentConfig(name="minimal")])

        agent = bundle.agents[0]

        assert agent.name == "minimal"

    def test_agent_with_full_config(self):
        """Test full agent configuration."""
        bundle = BundleDefinition(
            name="test",
            agents=[
                AgentConfig(
                    name="full-agent",
                    description="Fully configured",
                    instructions="Do complex task",
                    tools=["tool-bash", "tool-filesystem"],
                )
            ],
        )

        agent = bundle.agents[0]

        assert agent.name == "full-agent"
        assert agent.description == "Fully configured"
        assert agent.instructions == "Do complex task"
        assert agent.tools == ["tool-bash", "tool-filesystem"]

    def test_multiple_agents(self):
        """Test multiple agents in bundle."""
        bundle = BundleDefinition(
            name="team",
            agents=[
                AgentConfig(name="manager", instructions="Coordinate"),
                AgentConfig(name="worker1", instructions="Task A"),
                AgentConfig(name="worker2", instructions="Task B"),
            ],
        )

        assert len(bundle.agents) == 3
        names = [a.name for a in bundle.agents]
        assert names == ["manager", "worker1", "worker2"]

    def test_bundle_with_agents_and_behaviors(self):
        """Test bundle can have both agents and behaviors."""
        client = AmplifierClient()

        # Define a behavior
        client.define_behavior(
            BehaviorDefinition(name="security", instructions="Be security-conscious")
        )

        # Create bundle with both
        bundle = BundleDefinition(
            name="complex",
            instructions="Main instructions",
            agents=[{"name": "sub-agent", "instructions": "Sub instructions"}],
        )

        # Behaviors would be merged separately in createSession
        # Here we just verify the structure is valid
        assert bundle.agents is not None
        assert len(bundle.agents) == 1
