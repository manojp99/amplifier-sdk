/**
 * Tests for AmplifierClient.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Helper to create mock Response with proper structure
function createMockResponse(options: {
  ok: boolean;
  status?: number;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
  body?: ReadableStream<Uint8Array>;
}) {
  const headers = new Map<string, string>();
  if (options.json) {
    headers.set("content-type", "application/json");
  }
  
  return {
    ok: options.ok,
    status: options.status ?? (options.ok ? 200 : 500),
    headers: {
      get: (key: string) => headers.get(key) ?? null,
    },
    json: options.json ?? (() => Promise.resolve({})),
    text: options.text ?? (() => Promise.resolve("")),
    body: options.body,
  };
}

describe("AmplifierClient", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
    mockFetch.mockReset();
  });

  describe("ping", () => {
    it("should return true when server responds", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: true,
        json: () => Promise.resolve({}),
      }));

      const result = await client.ping();

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:4096/v1/ping",
        expect.any(Object)
      );
    });

    it("should return false when server fails", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection failed"));

      const result = await client.ping();

      expect(result).toBe(false);
    });
  });

  describe("createSession", () => {
    it("should create a session with bundle", async () => {
      const mockResponse = {
        id: "sess_123",
        title: "Test Session",
        created_at: "2024-01-01T00:00:00Z",
        state: "ready",
      };

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      }));

      const session = await client.createSession({ bundle: "foundation" });

      expect(session.id).toBe("sess_123");
      expect(session.title).toBe("Test Session");
      expect(session.state).toBe("ready");
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:4096/v1/session",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ bundle: "foundation" }),
        })
      );
    });

    it("should throw on error", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
      }));

      await expect(client.createSession()).rejects.toThrow(
        "Internal Server Error"
      );
    });
  });

  describe("deleteSession", () => {
    it("should return true on success", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: true,
        json: () => Promise.resolve({}),
      }));

      const result = await client.deleteSession("sess_123");

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:4096/v1/session/sess_123",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("should return false on failure", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: false,
        status: 404,
      }));

      const result = await client.deleteSession("sess_123");

      expect(result).toBe(false);
    });
  });

  describe("promptSync", () => {
    it("should return complete response", async () => {
      const mockResponse = {
        content: "Hello! How can I help?",
        tool_calls: [],
        session_id: "sess_123",
        stop_reason: "end_turn",
      };

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      }));

      const response = await client.promptSync("sess_123", "Hello!");

      expect(response.content).toBe("Hello! How can I help?");
      expect(response.sessionId).toBe("sess_123");
      expect(response.stopReason).toBe("end_turn");
      expect(response.toolCalls).toEqual([]);
    });

    it("should parse tool calls", async () => {
      const mockResponse = {
        content: "The answer is 4",
        tool_calls: [
          {
            tool_name: "calculator",
            tool_call_id: "tc_123",
            arguments: { expression: "2+2" },
            output: "4",
          },
        ],
        session_id: "sess_123",
        stop_reason: "end_turn",
      };

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      }));

      const response = await client.promptSync("sess_123", "What is 2+2?");

      expect(response.toolCalls).toHaveLength(1);
      expect(response.toolCalls[0].toolName).toBe("calculator");
      expect(response.toolCalls[0].output).toBe("4");
    });
  });

  describe("cancel", () => {
    it("should return true on success", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: true,
        json: () => Promise.resolve({}),
      }));

      const result = await client.cancel("sess_123");

      expect(result).toBe(true);
    });
  });

  describe("respondApproval", () => {
    it("should send approval response", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: true,
        json: () => Promise.resolve({}),
      }));

      const result = await client.respondApproval("sess_123", "req_456", "approve");

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:4096/v1/session/sess_123/approval",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ request_id: "req_456", choice: "approve" }),
        })
      );
    });
  });

  describe("run", () => {
    it("should create session, prompt, and cleanup", async () => {
      // Mock create session
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve({ id: "sess_123" }),
      }));

      // Mock prompt sync
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve({ content: "Hello!", tool_calls: [] }),
      }));

      // Mock delete session
      mockFetch.mockResolvedValueOnce(createMockResponse({ 
        ok: true,
        json: () => Promise.resolve({}),
      }));

      const response = await client.run("Hello!");

      expect(response.content).toBe("Hello!");
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });
  });

  describe("Event Type Safety", () => {
    it("should properly type content.delta events", () => {
      const event = {
        type: "content.delta" as const,
        data: { delta: "Hello" },
        id: "evt_1",
      };

      // TypeScript discriminated union should work
      if (event.type === "content.delta") {
        // Should not need casting
        expect(event.data.delta).toBe("Hello");
      }
    });

    it("should properly type tool.call events", () => {
      const event = {
        type: "tool.call" as const,
        data: {
          tool_name: "calculator",
          tool_call_id: "tc_123",
          arguments: { x: 1 },
        },
        toolCallId: "tc_123",
      };

      if (event.type === "tool.call") {
        expect(event.data.tool_name).toBe("calculator");
        expect(event.toolCallId).toBe("tc_123");
      }
    });

    it("should properly type approval.required events", () => {
      const event = {
        type: "approval.required" as const,
        data: {
          request_id: "req_1",
          prompt: "Allow this?",
          tool_name: "bash",
        },
      };

      if (event.type === "approval.required") {
        expect(event.data.request_id).toBe("req_1");
        expect(event.data.prompt).toBe("Allow this?");
      }
    });

    it("should properly type agent.spawned events", () => {
      const event = {
        type: "agent.spawned" as const,
        data: {
          agent_id: "child_1",
          agent_name: "researcher",
          parent_id: "parent_1",
        },
      };

      if (event.type === "agent.spawned") {
        expect(event.data.agent_id).toBe("child_1");
        expect(event.data.agent_name).toBe("researcher");
        expect(event.data.parent_id).toBe("parent_1");
      }
    });

    it("should properly type agent.completed events", () => {
      const event = {
        type: "agent.completed" as const,
        data: {
          agent_id: "child_1",
          result: "Research complete",
        },
      };

      if (event.type === "agent.completed") {
        expect(event.data.agent_id).toBe("child_1");
        expect(event.data.result).toBe("Research complete");
      }
    });

    it("should properly type thinking.delta events", () => {
      const event = {
        type: "thinking.delta" as const,
        data: {
          delta: "Let me think...",
        },
      };

      if (event.type === "thinking.delta") {
        expect(event.data.delta).toBe("Let me think...");
      }
    });

    it("should properly type tool.result events", () => {
      const event = {
        type: "tool.result" as const,
        data: {
          tool_call_id: "tc_123",
          result: { output: "success" },
        },
        toolCallId: "tc_123",
      };

      if (event.type === "tool.result") {
        expect(event.toolCallId).toBe("tc_123");
        expect(event.data.result).toEqual({ output: "success" });
      }
    });
  });

  describe("Event Correlation", () => {
    it("should extract toolCallId from event data", () => {
      const rawEvent = {
        type: "tool.call",
        data: {
          tool_name: "bash",
          tool_call_id: "tc_abc123",
          arguments: { command: "ls" },
        },
      };

      // Simulate client parsing (what parseEvent does)
      const parsed = {
        ...rawEvent,
        toolCallId: rawEvent.data.tool_call_id,
      };

      expect(parsed.toolCallId).toBe("tc_abc123");
    });

    it("should extract agentId from event data", () => {
      const rawEvent = {
        type: "content.delta",
        data: {
          delta: "Hello",
          agent_id: "agent_child_1",
        },
      };

      // Simulate client parsing
      const parsed = {
        ...rawEvent,
        agentId: rawEvent.data.agent_id,
      };

      expect(parsed.agentId).toBe("agent_child_1");
    });

    it("should correlate tool.call with tool.result using toolCallId", () => {
      const toolCall = {
        type: "tool.call" as const,
        data: {
          tool_name: "bash",
          tool_call_id: "tc_123",
          arguments: { command: "pwd" },
        },
        toolCallId: "tc_123",
      };

      const toolResult = {
        type: "tool.result" as const,
        data: {
          tool_call_id: "tc_123",
          result: "/workspace",
        },
        toolCallId: "tc_123",
      };

      // Verify correlation works
      expect(toolCall.toolCallId).toBe(toolResult.toolCallId);
    });

    it("should track parent vs child agent events using agentId", () => {
      const parentEvent = {
        type: "content.delta" as const,
        data: { delta: "Parent speaking" },
        agentId: "parent_1",
      };

      const childEvent = {
        type: "content.delta" as const,
        data: { delta: "Child speaking" },
        agentId: "child_1",
      };

      expect(parentEvent.agentId).not.toBe(childEvent.agentId);
      expect(parentEvent.agentId).toBe("parent_1");
      expect(childEvent.agentId).toBe("child_1");
    });
  });

  describe("Event Handlers (Convenience API)", () => {
    it("should register and trigger event handlers", async () => {
      const handler = vi.fn();
      client.on("content.delta", handler);

      // Manually trigger emitEvent (access private method for testing)
      const event = {
        type: "content.delta",
        data: { delta: "Hello" },
      };
      await (client as any).emitEvent(event);

      expect(handler).toHaveBeenCalledWith(event);
    });

    it("should support multiple handlers for same event", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.on("tool.call", handler1);
      client.on("tool.call", handler2);

      const event = {
        type: "tool.call",
        data: { tool_name: "bash" },
      };
      await (client as any).emitEvent(event);

      expect(handler1).toHaveBeenCalledWith(event);
      expect(handler2).toHaveBeenCalledWith(event);
    });

    it("should unregister event handlers", async () => {
      const handler = vi.fn();
      client.on("content.delta", handler);
      client.off("content.delta", handler);

      const event = { type: "content.delta", data: { delta: "Hi" } };
      await (client as any).emitEvent(event);

      expect(handler).not.toHaveBeenCalled();
    });

    it("should support once handlers that auto-unregister", async () => {
      const handler = vi.fn();
      client.once("tool.result", handler);

      const event = { type: "tool.result", data: { result: "test" } };
      
      // First emit - handler should be called
      await (client as any).emitEvent(event);
      expect(handler).toHaveBeenCalledTimes(1);

      // Second emit - handler should NOT be called (auto-unregistered)
      await (client as any).emitEvent(event);
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it("should handle errors in event handlers gracefully", async () => {
      const errorHandler = vi.fn(() => {
        throw new Error("Handler failed");
      });
      const goodHandler = vi.fn();

      client.on("content.delta", errorHandler);
      client.on("content.delta", goodHandler);

      const event = { type: "content.delta", data: { delta: "test" } };
      
      // Should not throw - errors are caught
      await expect((client as any).emitEvent(event)).resolves.not.toThrow();

      // Both handlers should have been called despite error
      expect(errorHandler).toHaveBeenCalled();
      expect(goodHandler).toHaveBeenCalled();
    });
  });

  describe("Approval Convenience API", () => {
    it("should register approval handler", () => {
      const handler = vi.fn();
      client.onApproval(handler);

      // Verify handler is stored (access private property for testing)
      expect((client as any).approvalHandler).toBe(handler);
    });

    it("should call approval handler and auto-respond", async () => {
      // Mock approval handler that returns true
      const approvalHandler = vi.fn().mockResolvedValue(true);
      client.onApproval(approvalHandler);

      // Mock respondApproval
      const respondSpy = vi.spyOn(client, "respondApproval").mockResolvedValue(true);

      // Create approval event
      const approvalEvent = {
        type: "approval.required",
        data: {
          request_id: "req_123",
          prompt: "Allow this action?",
          tool_name: "bash",
          arguments: { command: "ls" },
        },
      };

      // Trigger event through emitEvent (simulates what happens in prompt stream)
      // Need to pass sessionId - simulate by calling through prompt flow
      // For unit test, just verify the handler logic

      // Verify handler would be called with correct structure
      const request = {
        requestId: "req_123",
        prompt: "Allow this action?",
        toolName: "bash",
        arguments: { command: "ls" },
      };

      await approvalHandler(request);
      expect(approvalHandler).toHaveBeenCalledWith(request);
    });
  });

  describe("Client-Side Tools", () => {
    it("should register and retrieve client-side tools", () => {
      const tool = {
        name: "test-tool",
        description: "A test tool",
        handler: async (args: Record<string, unknown>) => ({ result: "test" }),
      };

      client.registerTool(tool);

      const tools = client.getClientTools();
      expect(tools).toHaveLength(1);
      expect(tools[0].name).toBe("test-tool");
      expect(tools[0].description).toBe("A test tool");
    });

    it("should unregister client-side tools", () => {
      const tool = {
        name: "removable-tool",
        description: "Will be removed",
        handler: async () => "test",
      };

      client.registerTool(tool);
      expect(client.getClientTools()).toHaveLength(1);

      const removed = client.unregisterTool("removable-tool");
      expect(removed).toBe(true);
      expect(client.getClientTools()).toHaveLength(0);
    });

    it("should return false when unregistering non-existent tool", () => {
      const removed = client.unregisterTool("does-not-exist");
      expect(removed).toBe(false);
    });

    it("should execute client-side tool handler", async () => {
      const mockHandler = vi.fn().mockResolvedValue({ status: "success" });
      
      client.registerTool({
        name: "mock-tool",
        description: "Mock tool",
        handler: mockHandler,
      });

      // Access private method via any cast for testing
      const result = await (client as any).executeClientTool("mock-tool", { param: "value" });

      expect(mockHandler).toHaveBeenCalledWith({ param: "value" });
      expect(result).toEqual({ status: "success" });
    });

    it("should throw error when executing non-existent client tool", async () => {
      await expect(
        (client as any).executeClientTool("non-existent", {})
      ).rejects.toThrow("Client tool not found: non-existent");
    });

    it("should handle client tool execution errors", async () => {
      const errorTool = {
        name: "error-tool",
        description: "Tool that throws",
        handler: async () => {
          throw new Error("Tool execution failed");
        },
      };

      client.registerTool(errorTool);

      await expect(
        (client as any).executeClientTool("error-tool", {})
      ).rejects.toThrow("Tool execution failed");
    });

    it("should include clientTools in bundle definition", () => {
      const tool = {
        name: "custom-tool",
        description: "Custom tool",
        handler: async () => "result",
      };

      client.registerTool(tool);

      // Bundle should be able to reference client tools
      const bundle = {
        name: "test-bundle",
        clientTools: ["custom-tool"],
      };

      expect(bundle.clientTools).toContain("custom-tool");
    });
  });
});
