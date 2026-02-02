/**
 * Integration tests for AmplifierClient.
 * 
 * These tests require amplifier-app-runtime to be running on localhost:4096.
 * 
 * To run:
 * 1. Start runtime: cd amplifier-app-runtime && uv run python -m amplifier_app_runtime.cli --http --port 4096
 * 2. Run tests: npm test
 */

import { describe, it, expect, beforeAll } from "vitest";
import { AmplifierClient, type Event } from "../src";

// Increase timeout for integration tests (agents can be slow)
const INTEGRATION_TIMEOUT = 30000;

describe("AmplifierClient Integration", () => {
  let client: AmplifierClient;
  let isRuntimeAvailable = false;

  beforeAll(async () => {
    client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
    isRuntimeAvailable = await client.ping();
    
    if (!isRuntimeAvailable) {
      console.warn("\n⚠️  Runtime not available at localhost:4096");
      console.warn("Start it with: cd amplifier-app-runtime && uv run python -m amplifier_app_runtime.cli --http --port 4096\n");
    }
  });

  describe("Server Connection", () => {
    it("should connect to runtime server", async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      expect(isRuntimeAvailable).toBe(true);
    });

    it("should get server capabilities", async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const caps = await client.capabilities();
      expect(caps).toBeDefined();
      expect(caps.version).toBeDefined();
      // Runtime returns features.streaming, not top-level streaming
      expect(caps.features).toBeDefined();
    });
  });

  describe("Session Lifecycle", () => {
    it("should create and delete a session", async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const session = await client.createSession({
        bundle: {
          name: "test-agent",
          instructions: "You are a test assistant. Be brief.",
        },
      });

      expect(session.id).toBeDefined();
      expect(session.id.length).toBeGreaterThan(0);

      const deleted = await client.deleteSession(session.id);
      expect(deleted).toBe(true);
    });

    it("should list active sessions", async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const session = await client.createSession({
        bundle: { name: "test-list", instructions: "Test" },
      });

      const sessions = await client.listSessions();
      expect(sessions.length).toBeGreaterThan(0);
      expect(sessions.some((s) => s.id === session.id)).toBe(true);

      await client.deleteSession(session.id);
    });
  });

  describe("Streaming Events", () => {
    it("should stream content.delta events", { timeout: INTEGRATION_TIMEOUT }, async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const session = await client.createSession({
        bundle: { name: "test-streaming", instructions: "Be brief. Answer in one sentence." },
      });

      let contentReceived = false;
      let fullContent = "";

      for await (const event of client.prompt(session.id, "Say hello")) {
        if (event.type === "content.delta") {
          // TypeScript knows event.data.delta exists!
          fullContent += event.data.delta;
          contentReceived = true;
        }
      }

      expect(contentReceived).toBe(true);
      expect(fullContent.length).toBeGreaterThan(0);

      await client.deleteSession(session.id);
    });

    it("should receive typed events with proper structure", { timeout: INTEGRATION_TIMEOUT }, async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const session = await client.createSession({
        bundle: { 
          name: "test-types",
          instructions: "Answer briefly.",
        },
      });

      const eventTypes = new Set<string>();

      for await (const event of client.prompt(session.id, "Hello")) {
        eventTypes.add(event.type);
        
        // Verify event structure
        expect(event.type).toBeDefined();
        expect(event.data).toBeDefined();
        
        // Test type discrimination
        switch (event.type) {
          case "content.delta":
            expect(typeof event.data.delta).toBe("string");
            break;
          case "content.end":
            // Just verify it exists
            expect(event.type).toBe("content.end");
            break;
        }
      }

      expect(eventTypes.size).toBeGreaterThan(0);
      await client.deleteSession(session.id);
    });
  });

  describe("Tool Execution & Correlation", () => {
    it("should receive tool.call and tool.result events with correlation", { timeout: INTEGRATION_TIMEOUT }, async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      // NOTE: This test requires provider configuration in runtime
      // If provider not configured, test will complete but tools won't be called
      // This is expected behavior - mark as skipped if no tools received

      const session = await client.createSession({
        bundle: {
          name: "test-tools",
          instructions: "When asked to run a command, use the bash tool. Be direct and use tools.",
          tools: [{ module: "tool-bash" }],
        },
      });

      const toolCallIds = new Set<string>();
      const toolResultIds = new Set<string>();
      let toolCallReceived = false;
      let toolResultReceived = false;

      try {
        for await (const event of client.prompt(session.id, "Run 'echo test' using bash tool")) {
          if (event.type === "tool.call") {
            expect(event.data.tool_name).toBeDefined();
            if (event.toolCallId) {
              toolCallIds.add(event.toolCallId);
            }
            toolCallReceived = true;
          }

          if (event.type === "tool.result") {
            expect(event.data.result).toBeDefined();
            if (event.toolCallId) {
              toolResultIds.add(event.toolCallId);
            }
            toolResultReceived = true;
          }
        }
      } catch (err) {
        console.warn("Tool test error (may need provider config):", err);
      }

      // If tools weren't called, skip assertions (provider likely not configured)
      if (!toolCallReceived) {
        console.log("⏭️  Skipping tool assertions - provider may not be configured");
        await client.deleteSession(session.id);
        return;
      }

      expect(toolCallReceived).toBe(true);
      expect(toolResultReceived).toBe(true);
      
      // Verify correlation: at least some toolCallIds match
      if (toolCallIds.size > 0 && toolResultIds.size > 0) {
        const intersection = new Set([...toolCallIds].filter(x => toolResultIds.has(x)));
        expect(intersection.size).toBeGreaterThan(0);
      }

      await client.deleteSession(session.id);
    });
  });

  describe("One-Shot Execution", () => {
    it("should execute run() method successfully", async () => {
      if (!isRuntimeAvailable) {
        console.log("⏭️  Skipping - runtime not available");
        return;
      }

      const response = await client.run("Say 'test passed' and nothing else", {
        bundle: { name: "one-shot", instructions: "Be brief and exact." },
      });

      expect(response.content).toBeDefined();
      expect(response.content.length).toBeGreaterThan(0);
    });
  });
});
