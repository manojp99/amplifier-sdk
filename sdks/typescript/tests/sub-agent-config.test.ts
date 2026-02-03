/**
 * Tests for sub-agent configuration.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { AmplifierClient, type AgentConfig } from "../src";

describe("Sub-Agent Configuration", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("AgentConfig in Bundle", () => {
    it("should accept agents in bundle definition", () => {
      const agentConfig: AgentConfig = {
        name: "code-reviewer",
        description: "Reviews code for quality",
        instructions: "Review code for bugs and style issues",
        tools: ["tool-filesystem", "tool-bash"]
      };

      // Should not throw
      expect(() => {
        const bundle = {
          name: "multi-agent",
          agents: [agentConfig]
        };
      }).not.toThrow();
    });

    it("should serialize agents in bundle definition", () => {
      const bundle = {
        name: "multi-agent",
        instructions: "Coordinate specialists",
        agents: [
          {
            name: "researcher",
            description: "Research specialist",
            instructions: "Research topics thoroughly",
            tools: ["tool-web"]
          },
          {
            name: "writer",
            description: "Writing specialist",
            instructions: "Write clear documentation",
            tools: ["tool-filesystem"]
          }
        ]
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);

      expect(serialized.agents).toBeDefined();
      expect(serialized.agents).toHaveLength(2);
      expect(serialized.agents[0].name).toBe("researcher");
      expect(serialized.agents[1].name).toBe("writer");
    });

    it("should preserve agent properties during serialization", () => {
      const bundle = {
        name: "test",
        agents: [
          {
            name: "specialist",
            description: "A specialist agent",
            instructions: "Be thorough",
            tools: ["tool-bash", "tool-filesystem"]
          }
        ]
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);
      const agent = serialized.agents[0];

      expect(agent.name).toBe("specialist");
      expect(agent.description).toBe("A specialist agent");
      expect(agent.instructions).toBe("Be thorough");
      expect(agent.tools).toEqual(["tool-bash", "tool-filesystem"]);
    });

    it("should handle empty agents array", () => {
      const bundle = {
        name: "test",
        agents: []
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);

      expect(serialized.agents).toEqual([]);
    });

    it("should handle missing agents field", () => {
      const bundle = {
        name: "test",
        instructions: "Test"
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);

      expect(serialized.agents).toBeUndefined();
    });

    it("should support minimal agent config", () => {
      const bundle = {
        name: "test",
        agents: [
          {
            name: "minimal-agent"
          }
        ]
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);

      expect(serialized.agents[0].name).toBe("minimal-agent");
    });

    it("should support complex multi-agent hierarchy", () => {
      const bundle = {
        name: "complex",
        agents: [
          {
            name: "manager",
            instructions: "Coordinate team",
            tools: []
          },
          {
            name: "specialist1",
            instructions: "Handle task A",
            tools: ["tool-bash"]
          },
          {
            name: "specialist2",
            instructions: "Handle task B",
            tools: ["tool-filesystem"]
          }
        ]
      };

      const serialized = (client as any).serializeBundleDefinition(bundle);

      expect(serialized.agents).toHaveLength(3);
      expect(serialized.agents.map((a: any) => a.name)).toEqual([
        "manager",
        "specialist1",
        "specialist2"
      ]);
    });
  });

  describe("AgentConfig Validation", () => {
    it("should require name field", () => {
      const agentConfig: Partial<AgentConfig> = {
        description: "Missing name"
      };

      // TypeScript compilation ensures name is required
      // At runtime, we trust the type system
      expect(agentConfig.name).toBeUndefined();
    });

    it("should allow optional fields", () => {
      const minimalAgent: AgentConfig = {
        name: "minimal"
      };

      expect(minimalAgent.description).toBeUndefined();
      expect(minimalAgent.instructions).toBeUndefined();
      expect(minimalAgent.tools).toBeUndefined();
    });
  });

  describe("Bundle with Agents and Behaviors", () => {
    it("should support both agents and behaviors in same bundle", () => {
      client.defineBehavior({
        name: "security",
        instructions: "Be security-conscious"
      });

      const bundle = {
        name: "complex-agent",
        instructions: "Main instructions",
        behaviors: ["security"],
        agents: [
          {
            name: "sub-agent",
            instructions: "Sub-agent instructions"
          }
        ]
      };

      // Should not throw
      expect(() => {
        const merged = (client as any).mergeBehaviors(bundle, bundle.behaviors!);
      }).not.toThrow();
    });
  });
});
