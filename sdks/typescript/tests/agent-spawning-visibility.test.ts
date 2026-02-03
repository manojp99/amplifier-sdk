/**
 * Tests for Agent Spawning Visibility feature.
 * 
 * Tests the onAgentSpawned, onAgentCompleted, getAgentHierarchy, and clearAgentHierarchy
 * methods, along with hierarchy tracking and edge case handling.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";
import type { Event, AgentNode } from "../src/types";

describe("Agent Spawning Visibility", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
  });

  // Helper to simulate event emission
  async function emitEvent(event: Partial<Event>): Promise<void> {
    await (client as any).emitEvent(event);
  }

  // Helper to simulate agent spawned event
  async function simulateAgentSpawned(
    agentId: string,
    parentId: string | null = null,
    agentName: string = "test-agent"
  ): Promise<void> {
    await emitEvent({
      type: "agent.spawned",
      data: {
        agent_id: agentId,
        agent_name: agentName,
        parent_id: parentId,
      },
      timestamp: new Date().toISOString(),
    });
  }

  // Helper to simulate agent completed event
  async function simulateAgentCompleted(
    agentId: string,
    result?: string,
    error?: string
  ): Promise<void> {
    await emitEvent({
      type: "agent.completed",
      data: {
        agent_id: agentId,
        result,
        error,
      },
      timestamp: new Date().toISOString(),
    });
  }

  describe("onAgentSpawned", () => {
    it("should register handler for agent spawned events", async () => {
      const handler = vi.fn();
      client.onAgentSpawned(handler);

      await simulateAgentSpawned("agent-123", null, "foundation:explorer");

      expect(handler).toHaveBeenCalledWith({
        agentId: "agent-123",
        agentName: "foundation:explorer",
        parentId: null,
        timestamp: expect.any(String),
      });
    });

    it("should call handler with parent ID when present", async () => {
      const handler = vi.fn();
      client.onAgentSpawned(handler);

      await simulateAgentSpawned("child-1", "parent-1", "foundation:bug-hunter");

      expect(handler).toHaveBeenCalledWith({
        agentId: "child-1",
        agentName: "foundation:bug-hunter",
        parentId: "parent-1",
        timestamp: expect.any(String),
      });
    });

    it("should support multiple handlers", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.onAgentSpawned(handler1);
      client.onAgentSpawned(handler2);

      await simulateAgentSpawned("agent-1");

      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });

    it("should support async handlers", async () => {
      const handler = vi.fn(async (info) => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
      client.onAgentSpawned(handler);

      await simulateAgentSpawned("agent-1");

      expect(handler).toHaveBeenCalled();
    });

    it("should continue if handler throws error", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation();
      const errorHandler = vi.fn(() => {
        throw new Error("Handler error");
      });
      const successHandler = vi.fn();

      client.onAgentSpawned(errorHandler);
      client.onAgentSpawned(successHandler);

      await simulateAgentSpawned("agent-1");

      expect(errorHandler).toHaveBeenCalled();
      expect(successHandler).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });

    it("should not call handler if agent_id is missing", async () => {
      const handler = vi.fn();
      client.onAgentSpawned(handler);

      await emitEvent({
        type: "agent.spawned",
        data: {
          agent_name: "test",
          // Missing agent_id
        },
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it("should handle handlers added during event emission", async () => {
      const handler1 = vi.fn(() => {
        // Add another handler during emission
        client.onAgentSpawned(handler2);
      });
      const handler2 = vi.fn();

      client.onAgentSpawned(handler1);
      await simulateAgentSpawned("agent-1");

      expect(handler1).toHaveBeenCalled();
      // handler2 should not be called for this event (added after iteration started)
      expect(handler2).not.toHaveBeenCalled();

      // But should be called for next event
      await simulateAgentSpawned("agent-2");
      expect(handler2).toHaveBeenCalled();
    });
  });

  describe("offAgentSpawned", () => {
    it("should remove registered handler", async () => {
      const handler = vi.fn();
      client.onAgentSpawned(handler);
      client.offAgentSpawned(handler);

      await simulateAgentSpawned("agent-1");

      expect(handler).not.toHaveBeenCalled();
    });

    it("should not error when removing non-existent handler", () => {
      const handler = vi.fn();
      expect(() => client.offAgentSpawned(handler)).not.toThrow();
    });

    it("should only remove specified handler", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.onAgentSpawned(handler1);
      client.onAgentSpawned(handler2);

      client.offAgentSpawned(handler1);

      await simulateAgentSpawned("agent-1");

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });
  });

  describe("onAgentCompleted", () => {
    it("should call handler when agent completes with result", async () => {
      const handler = vi.fn();
      client.onAgentCompleted(handler);

      await simulateAgentCompleted("agent-123", "Task completed successfully");

      expect(handler).toHaveBeenCalledWith({
        agentId: "agent-123",
        result: "Task completed successfully",
        error: undefined,
        timestamp: expect.any(String),
      });
    });

    it("should call handler when agent completes with error", async () => {
      const handler = vi.fn();
      client.onAgentCompleted(handler);

      await simulateAgentCompleted("agent-123", undefined, "Task failed");

      expect(handler).toHaveBeenCalledWith({
        agentId: "agent-123",
        result: undefined,
        error: "Task failed",
        timestamp: expect.any(String),
      });
    });

    it("should support multiple handlers", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.onAgentCompleted(handler1);
      client.onAgentCompleted(handler2);

      await simulateAgentCompleted("agent-1", "Done");

      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });

    it("should support async handlers", async () => {
      const handler = vi.fn(async (info) => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
      client.onAgentCompleted(handler);

      await simulateAgentCompleted("agent-1", "Done");

      expect(handler).toHaveBeenCalled();
    });

    it("should continue if handler throws error", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation();
      const errorHandler = vi.fn(() => {
        throw new Error("Handler error");
      });
      const successHandler = vi.fn();

      client.onAgentCompleted(errorHandler);
      client.onAgentCompleted(successHandler);

      await simulateAgentCompleted("agent-1", "Done");

      expect(errorHandler).toHaveBeenCalled();
      expect(successHandler).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });

    it("should not call handler if agent_id is missing", async () => {
      const handler = vi.fn();
      client.onAgentCompleted(handler);

      await emitEvent({
        type: "agent.completed",
        data: {
          result: "Done",
          // Missing agent_id
        },
      });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe("offAgentCompleted", () => {
    it("should remove registered handler", async () => {
      const handler = vi.fn();
      client.onAgentCompleted(handler);
      client.offAgentCompleted(handler);

      await simulateAgentCompleted("agent-1", "Done");

      expect(handler).not.toHaveBeenCalled();
    });

    it("should not error when removing non-existent handler", () => {
      const handler = vi.fn();
      expect(() => client.offAgentCompleted(handler)).not.toThrow();
    });

    it("should only remove specified handler", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      client.onAgentCompleted(handler1);
      client.onAgentCompleted(handler2);

      client.offAgentCompleted(handler1);

      await simulateAgentCompleted("agent-1", "Done");

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });
  });

  describe("getAgentHierarchy", () => {
    it("should return empty map initially", () => {
      const hierarchy = client.getAgentHierarchy();
      expect(hierarchy.size).toBe(0);
    });

    it("should track single agent spawn", async () => {
      await simulateAgentSpawned("root", null, "foundation");

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(1);
      const node = hierarchy.get("root");
      expect(node).toBeDefined();
      expect(node?.agentId).toBe("root");
      expect(node?.agentName).toBe("foundation");
      expect(node?.parentId).toBe(null);
      expect(node?.children).toEqual([]);
      expect(node?.spawnedAt).toBeTruthy();
      expect(node?.completedAt).toBe(null);
    });

    it("should track parent-child relationships", async () => {
      await simulateAgentSpawned("root", null, "foundation");
      await simulateAgentSpawned("child-1", "root", "explorer");
      await simulateAgentSpawned("child-2", "root", "bug-hunter");

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(3);

      const root = hierarchy.get("root");
      expect(root?.children).toEqual(["child-1", "child-2"]);

      const child1 = hierarchy.get("child-1");
      expect(child1?.parentId).toBe("root");
      expect(child1?.agentName).toBe("explorer");

      const child2 = hierarchy.get("child-2");
      expect(child2?.parentId).toBe("root");
      expect(child2?.agentName).toBe("bug-hunter");
    });

    it("should track deep nesting", async () => {
      await simulateAgentSpawned("root", null, "foundation");
      await simulateAgentSpawned("level-1", "root", "explorer");
      await simulateAgentSpawned("level-2", "level-1", "bug-hunter");
      await simulateAgentSpawned("level-3", "level-2", "zen-architect");

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(4);
      expect(hierarchy.get("root")?.children).toContain("level-1");
      expect(hierarchy.get("level-1")?.children).toContain("level-2");
      expect(hierarchy.get("level-2")?.children).toContain("level-3");
      expect(hierarchy.get("level-3")?.parentId).toBe("level-2");
    });

    it("should update node on completion", async () => {
      await simulateAgentSpawned("agent-1", null, "test");
      await simulateAgentCompleted("agent-1", "Task completed");

      const hierarchy = client.getAgentHierarchy();
      const node = hierarchy.get("agent-1");

      expect(node?.completedAt).toBeTruthy();
      expect(node?.result).toBe("Task completed");
      expect(node?.error).toBeUndefined();
    });

    it("should update node with error on failed completion", async () => {
      await simulateAgentSpawned("agent-1", null, "test");
      await simulateAgentCompleted("agent-1", undefined, "Task failed");

      const hierarchy = client.getAgentHierarchy();
      const node = hierarchy.get("agent-1");

      expect(node?.completedAt).toBeTruthy();
      expect(node?.error).toBe("Task failed");
      expect(node?.result).toBeUndefined();
    });

    it("should handle completion before spawn", async () => {
      // Complete before spawn
      await simulateAgentCompleted("agent-1", "Done");

      let hierarchy = client.getAgentHierarchy();
      let node = hierarchy.get("agent-1");

      // Node should exist with completion data
      expect(node).toBeDefined();
      expect(node?.result).toBe("Done");

      // Now spawn the agent
      await simulateAgentSpawned("agent-1", null, "test");

      hierarchy = client.getAgentHierarchy();
      node = hierarchy.get("agent-1");

      // Should have both spawn and completion data
      expect(node?.agentName).toBe("test");
      expect(node?.result).toBe("Done");
    });

    it("should handle duplicate spawn events", async () => {
      await simulateAgentSpawned("agent-1", null, "first-name");
      await simulateAgentSpawned("agent-1", null, "second-name");

      const hierarchy = client.getAgentHierarchy();

      // Should have one node with updated name
      expect(hierarchy.size).toBe(1);
      const node = hierarchy.get("agent-1");
      expect(node?.agentName).toBe("second-name");
    });

    it("should create placeholder parent if missing", async () => {
      // Spawn child without parent existing
      await simulateAgentSpawned("child-1", "missing-parent", "explorer");

      const hierarchy = client.getAgentHierarchy();

      // Both child and placeholder parent should exist
      expect(hierarchy.size).toBe(2);

      const parent = hierarchy.get("missing-parent");
      expect(parent).toBeDefined();
      expect(parent?.agentName).toBe("unknown");
      expect(parent?.children).toContain("child-1");

      const child = hierarchy.get("child-1");
      expect(child?.parentId).toBe("missing-parent");
    });

    it("should not duplicate children on re-spawn", async () => {
      await simulateAgentSpawned("parent", null, "foundation");
      await simulateAgentSpawned("child", "parent", "explorer");
      await simulateAgentSpawned("child", "parent", "explorer-v2");

      const hierarchy = client.getAgentHierarchy();
      const parent = hierarchy.get("parent");

      // Child should appear only once
      expect(parent?.children).toEqual(["child"]);
    });

    it("should return a copy of hierarchy", async () => {
      await simulateAgentSpawned("agent-1", null, "test");

      const hierarchy1 = client.getAgentHierarchy();
      const hierarchy2 = client.getAgentHierarchy();

      // Should be different objects
      expect(hierarchy1).not.toBe(hierarchy2);

      // But have same content
      expect(hierarchy1.size).toBe(hierarchy2.size);
      expect(hierarchy1.get("agent-1")?.agentId).toBe(
        hierarchy2.get("agent-1")?.agentId
      );
    });
  });

  describe("clearAgentHierarchy", () => {
    it("should clear all agents from hierarchy", async () => {
      await simulateAgentSpawned("agent-1");
      await simulateAgentSpawned("agent-2");
      await simulateAgentSpawned("agent-3");

      expect(client.getAgentHierarchy().size).toBe(3);

      client.clearAgentHierarchy();

      expect(client.getAgentHierarchy().size).toBe(0);
    });

    it("should not affect handlers", async () => {
      const handler = vi.fn();
      client.onAgentSpawned(handler);

      await simulateAgentSpawned("agent-1");
      client.clearAgentHierarchy();
      await simulateAgentSpawned("agent-2");

      // Handler should still be called after clear
      expect(handler).toHaveBeenCalledTimes(2);
    });

    it("should allow rebuilding hierarchy after clear", async () => {
      await simulateAgentSpawned("agent-1");
      client.clearAgentHierarchy();
      await simulateAgentSpawned("agent-2");

      const hierarchy = client.getAgentHierarchy();
      expect(hierarchy.size).toBe(1);
      expect(hierarchy.has("agent-1")).toBe(false);
      expect(hierarchy.has("agent-2")).toBe(true);
    });
  });

  describe("Hierarchy Edge Cases", () => {
    it("should handle multiple root agents", async () => {
      await simulateAgentSpawned("root-1", null, "foundation");
      await simulateAgentSpawned("root-2", null, "python-dev");
      await simulateAgentSpawned("root-3", null, "design-intelligence");

      const hierarchy = client.getAgentHierarchy();
      const roots = Array.from(hierarchy.values()).filter(
        (node) => node.parentId === null
      );

      expect(roots).toHaveLength(3);
    });

    it("should handle complex tree structures", async () => {
      // Build a complex tree:
      //        root
      //       /  |  \
      //      a   b   c
      //     / \      |
      //    d   e     f
      //             / \
      //            g   h

      await simulateAgentSpawned("root", null);
      await simulateAgentSpawned("a", "root");
      await simulateAgentSpawned("b", "root");
      await simulateAgentSpawned("c", "root");
      await simulateAgentSpawned("d", "a");
      await simulateAgentSpawned("e", "a");
      await simulateAgentSpawned("f", "c");
      await simulateAgentSpawned("g", "f");
      await simulateAgentSpawned("h", "f");

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(9);
      expect(hierarchy.get("root")?.children).toEqual(["a", "b", "c"]);
      expect(hierarchy.get("a")?.children).toEqual(["d", "e"]);
      expect(hierarchy.get("c")?.children).toEqual(["f"]);
      expect(hierarchy.get("f")?.children).toEqual(["g", "h"]);
    });

    it("should handle agent with many children", async () => {
      await simulateAgentSpawned("parent", null);

      // Add 100 children
      for (let i = 0; i < 100; i++) {
        await simulateAgentSpawned(`child-${i}`, "parent");
      }

      const hierarchy = client.getAgentHierarchy();
      const parent = hierarchy.get("parent");

      expect(hierarchy.size).toBe(101);
      expect(parent?.children).toHaveLength(100);
    });

    it("should preserve timestamps across spawn and complete", async () => {
      const spawnTime = new Date("2024-01-01T10:00:00Z").toISOString();
      const completeTime = new Date("2024-01-01T10:05:00Z").toISOString();

      await emitEvent({
        type: "agent.spawned",
        data: { agent_id: "agent-1", agent_name: "test" },
        timestamp: spawnTime,
      });

      await emitEvent({
        type: "agent.completed",
        data: { agent_id: "agent-1", result: "Done" },
        timestamp: completeTime,
      });

      const node = client.getAgentHierarchy().get("agent-1");

      expect(node?.spawnedAt).toBe(spawnTime);
      expect(node?.completedAt).toBe(completeTime);
    });

    it("should handle missing agent_name gracefully", async () => {
      await emitEvent({
        type: "agent.spawned",
        data: {
          agent_id: "agent-1",
          // Missing agent_name
        },
      });

      const node = client.getAgentHierarchy().get("agent-1");

      expect(node?.agentName).toBe("unknown");
    });
  });

  describe("Integration with Event System", () => {
    it("should work with generic event handlers", async () => {
      const agentSpawnedHandler = vi.fn();
      const genericHandler = vi.fn();

      client.onAgentSpawned(agentSpawnedHandler);
      client.on("agent.spawned", genericHandler);

      await simulateAgentSpawned("agent-1");

      // Both handlers should be called
      expect(agentSpawnedHandler).toHaveBeenCalled();
      expect(genericHandler).toHaveBeenCalled();
    });

    it("should track hierarchy even without handlers", async () => {
      // No handlers registered
      await simulateAgentSpawned("agent-1");

      const hierarchy = client.getAgentHierarchy();

      // Hierarchy should still be tracked
      expect(hierarchy.size).toBe(1);
    });

    it("should handle interleaved spawn and complete events", async () => {
      await simulateAgentSpawned("agent-1", null, "first");
      await simulateAgentSpawned("agent-2", "agent-1", "second");
      await simulateAgentCompleted("agent-2", "Done");
      await simulateAgentSpawned("agent-3", "agent-1", "third");
      await simulateAgentCompleted("agent-1", "All done");

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(3);
      expect(hierarchy.get("agent-1")?.completedAt).toBeTruthy();
      expect(hierarchy.get("agent-2")?.completedAt).toBeTruthy();
      expect(hierarchy.get("agent-3")?.completedAt).toBe(null);
    });
  });

  describe("Memory and Performance", () => {
    it("should handle large hierarchies efficiently", async () => {
      const startTime = Date.now();

      // Create 1000 agents
      for (let i = 0; i < 1000; i++) {
        await simulateAgentSpawned(`agent-${i}`, i > 0 ? `agent-${i - 1}` : null);
      }

      const endTime = Date.now();

      const hierarchy = client.getAgentHierarchy();

      expect(hierarchy.size).toBe(1000);
      expect(endTime - startTime).toBeLessThan(5000); // Should complete in reasonable time
    });

    it("should not leak memory when clearing hierarchy", async () => {
      for (let i = 0; i < 100; i++) {
        await simulateAgentSpawned(`agent-${i}`);
      }

      client.clearAgentHierarchy();

      expect(client.getAgentHierarchy().size).toBe(0);

      // Add new agents - should start fresh
      await simulateAgentSpawned("new-agent");
      expect(client.getAgentHierarchy().size).toBe(1);
    });
  });

  describe("Type Safety", () => {
    it("should properly type AgentNode interface", () => {
      const node: AgentNode = {
        agentId: "test",
        agentName: "test-agent",
        parentId: null,
        children: [],
        spawnedAt: new Date().toISOString(),
        completedAt: null,
      };

      expect(node.agentId).toBe("test");
    });

    it("should properly type handler callbacks", () => {
      const spawnHandler: (info: {
        agentId: string;
        agentName: string;
        parentId: string | null;
        timestamp: string;
      }) => void = (info) => {
        expect(info.agentId).toBeTruthy();
      };

      const completeHandler: (info: {
        agentId: string;
        result?: string;
        error?: string;
        timestamp: string;
      }) => void = (info) => {
        expect(info.agentId).toBeTruthy();
      };

      client.onAgentSpawned(spawnHandler);
      client.onAgentCompleted(completeHandler);
    });
  });
});
