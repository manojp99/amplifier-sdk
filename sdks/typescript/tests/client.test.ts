/**
 * Tests for AmplifierClient.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("AmplifierClient", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
    mockFetch.mockReset();
  });

  describe("ping", () => {
    it("should return true when server responds", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

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
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
      });

      await expect(client.createSession()).rejects.toThrow(
        "Failed to create session: 500"
      );
    });
  });

  describe("deleteSession", () => {
    it("should return true on success", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await client.deleteSession("sess_123");

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:4096/v1/session/sess_123",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("should return false on failure", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const response = await client.promptSync("sess_123", "What is 2+2?");

      expect(response.toolCalls).toHaveLength(1);
      expect(response.toolCalls[0].toolName).toBe("calculator");
      expect(response.toolCalls[0].output).toBe("4");
    });
  });

  describe("cancel", () => {
    it("should return true on success", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await client.cancel("sess_123");

      expect(result).toBe(true);
    });
  });

  describe("respondApproval", () => {
    it("should send approval response", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

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
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: "sess_123" }),
      });

      // Mock prompt sync
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ content: "Hello!", tool_calls: [] }),
      });

      // Mock delete session
      mockFetch.mockResolvedValueOnce({ ok: true });

      const response = await client.run("Hello!");

      expect(response.content).toBe("Hello!");
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });
  });
});
