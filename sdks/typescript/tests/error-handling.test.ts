/**
 * Error handling tests for AmplifierClient.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { AmplifierClient, AmplifierError, ErrorCode } from "../src";

const mockFetch = vi.fn();
global.fetch = mockFetch;

function createMockResponse(options: {
  ok: boolean;
  status?: number;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
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
  };
}

describe("Error Handling", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
    mockFetch.mockReset();
  });

  describe("Network Errors", () => {
    it("should handle connection refused", async () => {
      mockFetch.mockRejectedValueOnce(new Error("fetch failed"));

      await expect(client.ping()).resolves.toBe(false);
    });

    it("should handle timeout errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("timeout exceeded"));

      try {
        await client.createSession();
        expect.fail("Should have thrown error");
      } catch (err) {
        expect(err).toBeInstanceOf(AmplifierError);
        expect((err as AmplifierError).code).toBe(ErrorCode.Timeout);
        expect((err as AmplifierError).isRetryable).toBe(true);
      }
    });

    it("should handle aborted requests", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Request aborted"));

      try {
        await client.createSession();
      } catch (err) {
        expect(err).toBeInstanceOf(AmplifierError);
      }
    });
  });

  describe("HTTP Status Errors", () => {
    it("should handle 400 Bad Request", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 400,
        text: () => Promise.resolve("Invalid bundle configuration"),
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect(err).toBeInstanceOf(AmplifierError);
        expect((err as AmplifierError).code).toBe(ErrorCode.BadRequest);
        expect((err as AmplifierError).message).toContain("Invalid bundle");
      }
    });

    it("should handle 401 Unauthorized", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 401,
        text: () => Promise.resolve("Unauthorized"),
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).code).toBe(ErrorCode.Unauthorized);
      }
    });

    it("should handle 404 Not Found", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 404,
        text: () => Promise.resolve("Session not found"),
      }));

      try {
        await client.getSession("nonexistent");
      } catch (err) {
        expect((err as AmplifierError).code).toBe(ErrorCode.NotFound);
        expect((err as AmplifierError).message).toContain("Session not found");
      }
    });

    it("should handle 500 Server Error", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).code).toBe(ErrorCode.ServerError);
        expect((err as AmplifierError).isRetryable).toBe(true);
      }
    });
  });

  describe("Error Properties", () => {
    it("should include request ID in errors", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 500,
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).requestId).toBeDefined();
        expect((err as AmplifierError).requestId).toMatch(/^req_/);
      }
    });

    it("should include HTTP status in errors", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 403,
        text: () => Promise.resolve("Forbidden"),
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).status).toBe(403);
      }
    });

    it("should mark server errors as retryable", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 503,
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).isRetryable).toBe(true);
      }
    });

    it("should mark client errors as not retryable", async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 400,
      }));

      try {
        await client.createSession();
      } catch (err) {
        expect((err as AmplifierError).isRetryable).toBe(false);
      }
    });
  });

  describe("Observability Hooks", () => {
    it("should call onError hook on failures", async () => {
      const errorHandler = vi.fn();
      const clientWithHooks = new AmplifierClient({
        onError: errorHandler,
      });

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: false,
        status: 500,
      }));

      try {
        await clientWithHooks.createSession();
      } catch {
        // Expected to throw
      }

      expect(errorHandler).toHaveBeenCalled();
      expect(errorHandler.mock.calls[0][0]).toBeInstanceOf(AmplifierError);
    });

    it("should call onRequest hook before requests", async () => {
      const requestHandler = vi.fn();
      const clientWithHooks = new AmplifierClient({
        onRequest: requestHandler,
      });

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve({}),
      }));

      await clientWithHooks.ping();

      expect(requestHandler).toHaveBeenCalled();
      expect(requestHandler.mock.calls[0][0].method).toBe("GET");
      expect(requestHandler.mock.calls[0][0].url).toContain("/v1/ping");
    });

    it("should call onResponse hook after successful requests", async () => {
      const responseHandler = vi.fn();
      const clientWithHooks = new AmplifierClient({
        onResponse: responseHandler,
      });

      mockFetch.mockResolvedValueOnce(createMockResponse({
        ok: true,
        json: () => Promise.resolve({}),
      }));

      await clientWithHooks.ping();

      expect(responseHandler).toHaveBeenCalled();
      expect(responseHandler.mock.calls[0][0].status).toBe(200);
      expect(responseHandler.mock.calls[0][0].durationMs).toBeGreaterThanOrEqual(0);
    });
  });

  describe("Input Validation", () => {
    it("should validate sessionId in getSession", async () => {
      await expect(client.getSession("")).rejects.toThrow(AmplifierError);
      await expect((client as any).getSession(null)).rejects.toThrow(AmplifierError);
      await expect((client as any).getSession(123)).rejects.toThrow(AmplifierError);
    });

    it("should validate sessionId in deleteSession", async () => {
      await expect(client.deleteSession("")).rejects.toThrow(AmplifierError);
      await expect((client as any).deleteSession(null)).rejects.toThrow(AmplifierError);
    });

    it("should validate sessionId and content in prompt", async () => {
      // Invalid sessionId
      await expect(
        (async () => {
          for await (const _ of client.prompt("", "test")) {
            break;
          }
        })()
      ).rejects.toThrow(AmplifierError);

      // Invalid content
      await expect(
        (async () => {
          for await (const _ of client.prompt("sess_123", "")) {
            break;
          }
        })()
      ).rejects.toThrow(AmplifierError);
    });

    it("should validate sessionId and content in promptSync", async () => {
      await expect(client.promptSync("", "test")).rejects.toThrow(AmplifierError);
      await expect(client.promptSync("sess_123", "")).rejects.toThrow(AmplifierError);
    });

    it("should validate sessionId in cancel", async () => {
      await expect(client.cancel("")).rejects.toThrow(AmplifierError);
    });

    it("should validate parameters in respondApproval", async () => {
      await expect(client.respondApproval("", "req_1", "approve")).rejects.toThrow(AmplifierError);
      await expect(client.respondApproval("sess_1", "", "approve")).rejects.toThrow(AmplifierError);
      await expect(client.respondApproval("sess_1", "req_1", "")).rejects.toThrow(AmplifierError);
    });

    it("should validate sessionId in resumeSession", async () => {
      await expect(client.resumeSession("")).rejects.toThrow(AmplifierError);
      await expect((client as any).resumeSession(null)).rejects.toThrow(AmplifierError);
    });

    it("should validate tool in registerTool", () => {
      expect(() => (client as any).registerTool(null)).toThrow(AmplifierError);
      expect(() => (client as any).registerTool({ name: "" })).toThrow(AmplifierError);
      expect(() => client.registerTool({ name: "test", description: "", handler: async () => {} })).toThrow(AmplifierError);
      expect(() => client.registerTool({ name: "test", description: "test", handler: null as any })).toThrow(AmplifierError);
    });

    it("should provide helpful error messages for validation failures", async () => {
      try {
        await client.getSession("");
      } catch (err) {
        expect((err as AmplifierError).message).toContain("Session ID is required");
      }

      try {
        await client.promptSync("sess_1", "");
      } catch (err) {
        expect((err as AmplifierError).message).toContain("content is required");
      }
    });
  });

  describe("Client-Side Tool Errors", () => {
    it("should handle tool execution errors gracefully", async () => {
      const errorTool = {
        name: "failing-tool",
        description: "Tool that throws",
        handler: async () => {
          throw new Error("Tool execution failed");
        },
      };

      client.registerTool(errorTool);

      await expect(
        (client as any).executeClientTool("failing-tool", {})
      ).rejects.toThrow("Tool execution failed");
    });
  });
});
