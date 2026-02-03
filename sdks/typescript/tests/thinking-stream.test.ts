/**
 * Tests for thinking stream helpers.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { AmplifierClient } from "../src";

describe("Thinking Stream Helpers", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("onThinking", () => {
    it("should register thinking handler", () => {
      const handler = vi.fn();
      client.onThinking(handler);

      expect((client as any).thinkingHandlers.size).toBe(1);
    });

    it("should call handler with thinking state on thinking.delta", async () => {
      const handler = vi.fn();
      client.onThinking(handler);

      const event = {
        type: "thinking.delta",
        data: { delta: "I should first..." }
      };

      await (client as any).emitEvent(event);

      expect(handler).toHaveBeenCalledWith({
        isThinking: true,
        content: "I should first..."
      });
    });

    it("should accumulate thinking content across multiple deltas", async () => {
      const handler = vi.fn();
      client.onThinking(handler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "First " } });
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Second " } });
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Third" } });

      expect(handler).toHaveBeenCalledTimes(3);
      
      const lastCall = handler.mock.calls[2][0];
      expect(lastCall.content).toBe("First Second Third");
      expect(lastCall.isThinking).toBe(true);
    });

    it("should support multiple handlers", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.onThinking(handler1);
      client.onThinking(handler2);

      const event = { type: "thinking.delta", data: { delta: "test" } };
      await (client as any).emitEvent(event);

      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });

    it("should handle async handlers", async () => {
      const asyncHandler = vi.fn(async (thinking) => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return thinking.content;
      });

      client.onThinking(asyncHandler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(asyncHandler).toHaveBeenCalled();
    });

    it("should continue if handler throws error", async () => {
      const errorHandler = vi.fn(() => {
        throw new Error("Handler failed");
      });
      const goodHandler = vi.fn();

      client.onThinking(errorHandler);
      client.onThinking(goodHandler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(errorHandler).toHaveBeenCalled();
      expect(goodHandler).toHaveBeenCalled();
    });
  });

  describe("offThinking", () => {
    it("should unregister handler", async () => {
      const handler = vi.fn();
      client.onThinking(handler);
      client.offThinking(handler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(handler).not.toHaveBeenCalled();
    });

    it("should only remove specified handler", async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.onThinking(handler1);
      client.onThinking(handler2);
      client.offThinking(handler1);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });
  });

  describe("getThinkingState", () => {
    it("should return current thinking state", async () => {
      const state = client.getThinkingState();

      expect(state.isThinking).toBe(false);
      expect(state.content).toBe("");
    });

    it("should return updated state after thinking events", async () => {
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Test" } });

      const state = client.getThinkingState();

      expect(state.isThinking).toBe(true);
      expect(state.content).toBe("Test");
    });

    it("should show accumulated content", async () => {
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Part 1 " } });
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Part 2" } });

      const state = client.getThinkingState();

      expect(state.content).toBe("Part 1 Part 2");
    });
  });

  describe("clearThinkingState", () => {
    it("should reset thinking state", async () => {
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Test" } });

      expect(client.getThinkingState().isThinking).toBe(true);

      client.clearThinkingState();

      const state = client.getThinkingState();
      expect(state.isThinking).toBe(false);
      expect(state.content).toBe("");
    });

    it("should not affect handlers", async () => {
      const handler = vi.fn();
      client.onThinking(handler);

      client.clearThinkingState();

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(handler).toHaveBeenCalled();
    });

    it("should allow rebuilding state after clear", async () => {
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "First" } });
      client.clearThinkingState();
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Second" } });

      const state = client.getThinkingState();
      expect(state.content).toBe("Second");
    });
  });

  describe("Thinking State Transitions", () => {
    it("should set isThinking to true on first delta", async () => {
      expect(client.getThinkingState().isThinking).toBe(false);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(client.getThinkingState().isThinking).toBe(true);
    });

    it("should keep isThinking true across multiple deltas", async () => {
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "1" } });
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "2" } });
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "3" } });

      expect(client.getThinkingState().isThinking).toBe(true);
    });

    it("should reset content on clearThinkingState but keep handlers", async () => {
      const handler = vi.fn();
      client.onThinking(handler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "Old" } });
      client.clearThinkingState();
      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "New" } });

      expect(handler).toHaveBeenCalledTimes(2);
      expect(handler.mock.calls[1][0].content).toBe("New");
    });
  });

  describe("Integration with Event System", () => {
    it("should work alongside generic event handlers", async () => {
      const specificHandler = vi.fn();
      const genericHandler = vi.fn();

      client.onThinking(specificHandler);
      client.on("thinking.delta", genericHandler);

      await (client as any).emitEvent({ type: "thinking.delta", data: { delta: "test" } });

      expect(specificHandler).toHaveBeenCalled();
      expect(genericHandler).toHaveBeenCalled();
    });

    it("should not interfere with other event types", async () => {
      const thinkingHandler = vi.fn();
      const contentHandler = vi.fn();

      client.onThinking(thinkingHandler);
      client.on("content.delta", contentHandler);

      await (client as any).emitEvent({ type: "content.delta", data: { delta: "test" } });

      expect(thinkingHandler).not.toHaveBeenCalled();
      expect(contentHandler).toHaveBeenCalled();
    });
  });
});
