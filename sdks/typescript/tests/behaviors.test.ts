/**
 * Tests for client-side behaviors.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { AmplifierClient, type BehaviorDefinition } from "../src";

describe("Client-Side Behaviors", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("defineBehavior", () => {
    it("should define a behavior", () => {
      const behavior = client.defineBehavior({
        name: "test-behavior",
        description: "Test behavior",
        instructions: "Be helpful"
      });

      expect(behavior.name).toBe("test-behavior");
      expect(behavior.description).toBe("Test behavior");
      expect(behavior.instructions).toBe("Be helpful");
    });

    it("should throw error if name is missing", () => {
      expect(() => {
        client.defineBehavior({ name: "" } as BehaviorDefinition);
      }).toThrow("Behavior name is required");
    });

    it("should store behavior for later retrieval", () => {
      client.defineBehavior({
        name: "stored-behavior",
        instructions: "Test"
      });

      const retrieved = client.getBehavior("stored-behavior");
      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe("stored-behavior");
    });

    it("should support tools in behavior", () => {
      const behavior = client.defineBehavior({
        name: "tool-behavior",
        tools: [{ module: "tool-bash" }],
        clientTools: ["custom-tool"]
      });

      expect(behavior.tools).toHaveLength(1);
      expect(behavior.clientTools).toHaveLength(1);
    });

    it("should support providers in behavior", () => {
      const behavior = client.defineBehavior({
        name: "provider-behavior",
        providers: [{ module: "provider-anthropic", config: { model: "claude-sonnet" } }]
      });

      expect(behavior.providers).toHaveLength(1);
      expect(behavior.providers![0].config).toEqual({ model: "claude-sonnet" });
    });
  });

  describe("getBehavior", () => {
    it("should return undefined for non-existent behavior", () => {
      const behavior = client.getBehavior("nonexistent");
      expect(behavior).toBeUndefined();
    });

    it("should return defined behavior", () => {
      client.defineBehavior({ name: "test", instructions: "Test" });
      const behavior = client.getBehavior("test");
      expect(behavior?.name).toBe("test");
    });
  });

  describe("getBehaviors", () => {
    it("should return empty array initially", () => {
      const behaviors = client.getBehaviors();
      expect(behaviors).toEqual([]);
    });

    it("should return all defined behaviors", () => {
      client.defineBehavior({ name: "behavior1", instructions: "Test1" });
      client.defineBehavior({ name: "behavior2", instructions: "Test2" });
      client.defineBehavior({ name: "behavior3", instructions: "Test3" });

      const behaviors = client.getBehaviors();
      expect(behaviors).toHaveLength(3);
      expect(behaviors.map(b => b.name)).toContain("behavior1");
      expect(behaviors.map(b => b.name)).toContain("behavior2");
      expect(behaviors.map(b => b.name)).toContain("behavior3");
    });
  });

  describe("removeBehavior", () => {
    it("should remove a behavior", () => {
      client.defineBehavior({ name: "removable", instructions: "Test" });
      expect(client.getBehavior("removable")).toBeDefined();

      const removed = client.removeBehavior("removable");
      expect(removed).toBe(true);
      expect(client.getBehavior("removable")).toBeUndefined();
    });

    it("should return false for non-existent behavior", () => {
      const removed = client.removeBehavior("nonexistent");
      expect(removed).toBe(false);
    });
  });

  describe("Behavior Merging", () => {
    it("should merge instructions from behavior", () => {
      client.defineBehavior({
        name: "security",
        instructions: "Always ask before sensitive operations"
      });

      const merged = (client as any).mergeBehaviors(
        { name: "agent", instructions: "Be helpful" },
        ["security"]
      );

      expect(merged.instructions).toContain("Be helpful");
      expect(merged.instructions).toContain("Always ask before sensitive operations");
    });

    it("should merge tools without duplicates", () => {
      client.defineBehavior({
        name: "toolset",
        tools: [{ module: "tool-bash" }, { module: "tool-filesystem" }]
      });

      const merged = (client as any).mergeBehaviors(
        { name: "agent", tools: [{ module: "tool-bash" }] },
        ["toolset"]
      );

      expect(merged.tools).toHaveLength(2);
      const modules = merged.tools.map((t: any) => t.module);
      expect(modules).toContain("tool-bash");
      expect(modules).toContain("tool-filesystem");
    });

    it("should merge client tools without duplicates", () => {
      client.defineBehavior({
        name: "client-toolset",
        clientTools: ["tool1", "tool2"]
      });

      const merged = (client as any).mergeBehaviors(
        { name: "agent", clientTools: ["tool1", "tool3"] },
        ["client-toolset"]
      );

      expect(merged.clientTools).toHaveLength(3);
      expect(merged.clientTools).toContain("tool1");
      expect(merged.clientTools).toContain("tool2");
      expect(merged.clientTools).toContain("tool3");
    });

    it("should merge providers without duplicates", () => {
      client.defineBehavior({
        name: "providers",
        providers: [{ module: "provider-anthropic" }, { module: "provider-openai" }]
      });

      const merged = (client as any).mergeBehaviors(
        { name: "agent", providers: [{ module: "provider-anthropic" }] },
        ["providers"]
      );

      expect(merged.providers).toHaveLength(2);
      const modules = merged.providers.map((p: any) => p.module);
      expect(modules).toContain("provider-anthropic");
      expect(modules).toContain("provider-openai");
    });

    it("should merge multiple behaviors", () => {
      client.defineBehavior({
        name: "security",
        instructions: "Be security-minded"
      });

      client.defineBehavior({
        name: "customer-support",
        instructions: "Be empathetic",
        clientTools: ["get-order"]
      });

      const merged = (client as any).mergeBehaviors(
        { name: "agent", instructions: "Base instructions" },
        ["security", "customer-support"]
      );

      expect(merged.instructions).toContain("Base instructions");
      expect(merged.instructions).toContain("Be security-minded");
      expect(merged.instructions).toContain("Be empathetic");
      expect(merged.clientTools).toContain("get-order");
    });

    it("should throw error for undefined behavior", () => {
      expect(() => {
        (client as any).mergeBehaviors(
          { name: "agent" },
          ["nonexistent-behavior"]
        );
      }).toThrow("Behavior 'nonexistent-behavior' not found");
    });

    it("should preserve base bundle properties", () => {
      client.defineBehavior({
        name: "addon",
        tools: [{ module: "tool-bash" }]
      });

      const merged = (client as any).mergeBehaviors(
        {
          name: "agent",
          version: "1.0.0",
          description: "My agent",
          session: { debug: true }
        },
        ["addon"]
      );

      expect(merged.name).toBe("agent");
      expect(merged.version).toBe("1.0.0");
      expect(merged.description).toBe("My agent");
      expect(merged.session).toEqual({ debug: true });
    });
  });
});
