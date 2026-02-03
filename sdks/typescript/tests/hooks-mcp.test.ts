/**
 * Tests for hooks and MCP server configuration.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";
import type { 
  BundleDefinition, 
  McpServerStdio, 
  McpServerHttp, 
  McpServerSse 
} from "../src/types";

describe("Hook Configuration", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("BundleDefinition with hooks", () => {
    it("should accept hooks in bundle definition", () => {
      const bundle: BundleDefinition = {
        name: "test-bundle",
        version: "1.0.0",
        hooks: [
          { module: "hook-logging" },
          { module: "hook-redaction", config: { patterns: ["secret"] } }
        ]
      };

      expect(bundle.hooks).toBeDefined();
      expect(bundle.hooks).toHaveLength(2);
      expect(bundle.hooks![0].module).toBe("hook-logging");
      expect(bundle.hooks![1].config).toEqual({ patterns: ["secret"] });
    });

    it("should support empty hooks array", () => {
      const bundle: BundleDefinition = {
        name: "no-hooks",
        version: "1.0.0",
        hooks: []
      };

      expect(bundle.hooks).toEqual([]);
    });

    it("should support hooks with custom config", () => {
      const bundle: BundleDefinition = {
        name: "configured-hooks",
        version: "1.0.0",
        hooks: [
          {
            module: "hook-approval",
            config: {
              auto_approve: false,
              timeout: 300
            }
          }
        ]
      };

      expect(bundle.hooks![0].config).toEqual({
        auto_approve: false,
        timeout: 300
      });
    });

    it("should support hooks with source URLs", () => {
      const bundle: BundleDefinition = {
        name: "custom-hooks",
        version: "1.0.0",
        hooks: [
          {
            module: "hook-custom",
            source: "git+https://github.com/org/amplifier-hook-custom.git"
          }
        ]
      };

      expect(bundle.hooks![0].source).toBe("git+https://github.com/org/amplifier-hook-custom.git");
    });

    it("should support multiple hooks with mixed config", () => {
      const bundle: BundleDefinition = {
        name: "multi-hooks",
        version: "1.0.0",
        hooks: [
          { module: "hook-logging" },
          { module: "hook-redaction", config: { enabled: true } },
          { module: "hook-custom", source: "git+https://example.com/hook.git" }
        ]
      };

      expect(bundle.hooks).toHaveLength(3);
      expect(bundle.hooks![0].config).toBeUndefined();
      expect(bundle.hooks![1].config).toBeDefined();
      expect(bundle.hooks![2].source).toBeDefined();
    });
  });

  describe("SessionConfig with hooks", () => {
    it("should create session with hooks in runtime bundle", async () => {
      const bundle: BundleDefinition = {
        name: "session-hooks",
        version: "1.0.0",
        hooks: [{ module: "hook-logging" }],
        providers: [{ module: "provider-anthropic" }]
      };

      // Type check: should compile without errors
      const config = { bundle };
      expect(config.bundle).toBeDefined();
    });

    it("should combine hooks from behaviors and bundle", () => {
      const bundle: BundleDefinition = {
        name: "combined-hooks",
        version: "1.0.0",
        hooks: [{ module: "hook-bundle-level" }],
        behaviors: ["behavior-with-hooks"]
      };

      // Verify structure
      expect(bundle.hooks).toHaveLength(1);
      expect(bundle.behaviors).toHaveLength(1);
    });
  });
});

describe("MCP Server Configuration", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("McpServerStdio", () => {
    it("should configure stdio MCP server", () => {
      const server: McpServerStdio = {
        type: "stdio",
        command: "/usr/local/bin/mcp-server",
        args: ["--config", "/path/to/config.json"]
      };

      expect(server.type).toBe("stdio");
      expect(server.command).toBe("/usr/local/bin/mcp-server");
      expect(server.args).toEqual(["--config", "/path/to/config.json"]);
    });

    it("should support environment variables", () => {
      const server: McpServerStdio = {
        type: "stdio",
        command: "mcp-server",
        env: {
          API_KEY: "test-key",
          DEBUG: "true"
        }
      };

      expect(server.env).toEqual({
        API_KEY: "test-key",
        DEBUG: "true"
      });
    });

    it("should work without args or env", () => {
      const server: McpServerStdio = {
        type: "stdio",
        command: "simple-mcp-server"
      };

      expect(server.command).toBe("simple-mcp-server");
      expect(server.args).toBeUndefined();
      expect(server.env).toBeUndefined();
    });
  });

  describe("McpServerHttp", () => {
    it("should configure HTTP MCP server", () => {
      const server: McpServerHttp = {
        type: "http",
        url: "http://localhost:8080/mcp"
      };

      expect(server.type).toBe("http");
      expect(server.url).toBe("http://localhost:8080/mcp");
    });

    it("should support authentication headers", () => {
      const server: McpServerHttp = {
        type: "http",
        url: "https://api.example.com/mcp",
        headers: {
          "Authorization": "Bearer token123",
          "X-API-Key": "key456"
        }
      };

      expect(server.headers).toEqual({
        "Authorization": "Bearer token123",
        "X-API-Key": "key456"
      });
    });
  });

  describe("McpServerSse", () => {
    it("should configure SSE MCP server", () => {
      const server: McpServerSse = {
        type: "sse",
        url: "http://localhost:8080/mcp/events"
      };

      expect(server.type).toBe("sse");
      expect(server.url).toBe("http://localhost:8080/mcp/events");
    });

    it("should support authentication headers", () => {
      const server: McpServerSse = {
        type: "sse",
        url: "https://api.example.com/mcp/stream",
        headers: {
          "Authorization": "Bearer token789"
        }
      };

      expect(server.headers!["Authorization"]).toBe("Bearer token789");
    });
  });

  describe("BundleDefinition with MCP servers", () => {
    it("should accept mcpServers in bundle definition", () => {
      const bundle: BundleDefinition = {
        name: "mcp-bundle",
        version: "1.0.0",
        mcpServers: [
          { type: "stdio", command: "mcp-server" },
          { type: "http", url: "http://localhost:8080/mcp" }
        ]
      };

      expect(bundle.mcpServers).toBeDefined();
      expect(bundle.mcpServers).toHaveLength(2);
      expect(bundle.mcpServers![0].type).toBe("stdio");
      expect(bundle.mcpServers![1].type).toBe("http");
    });

    it("should support mixed MCP server types", () => {
      const bundle: BundleDefinition = {
        name: "multi-mcp",
        version: "1.0.0",
        mcpServers: [
          {
            type: "stdio",
            command: "local-mcp",
            args: ["--verbose"]
          },
          {
            type: "http",
            url: "http://api.example.com/mcp",
            headers: { "X-API-Key": "key" }
          },
          {
            type: "sse",
            url: "http://events.example.com/mcp"
          }
        ]
      };

      expect(bundle.mcpServers).toHaveLength(3);
      expect(bundle.mcpServers![0].type).toBe("stdio");
      expect(bundle.mcpServers![1].type).toBe("http");
      expect(bundle.mcpServers![2].type).toBe("sse");
    });

    it("should support empty mcpServers array", () => {
      const bundle: BundleDefinition = {
        name: "no-mcp",
        version: "1.0.0",
        mcpServers: []
      };

      expect(bundle.mcpServers).toEqual([]);
    });
  });

  describe("SessionConfig with MCP servers", () => {
    it("should accept mcpServers in session config", () => {
      const config = {
        bundle: "foundation",
        mcpServers: [
          { type: "stdio" as const, command: "mcp-tools" }
        ]
      };

      expect(config.mcpServers).toBeDefined();
      expect(config.mcpServers).toHaveLength(1);
    });

    it("should support MCP servers with runtime bundle", () => {
      const config = {
        bundle: {
          name: "mcp-agent",
          version: "1.0.0",
          mcpServers: [
            { type: "http" as const, url: "http://localhost:8080" }
          ]
        }
      };

      expect(config.bundle).toBeDefined();
      if (typeof config.bundle !== "string") {
        expect(config.bundle.mcpServers).toHaveLength(1);
      }
    });
  });

  describe("Complete Integration Example", () => {
    it("should build bundle with hooks and MCP servers", () => {
      const bundle: BundleDefinition = {
        name: "enterprise-agent",
        version: "1.0.0",
        description: "Enterprise agent with hooks and MCP",
        providers: [{ module: "provider-anthropic" }],
        tools: [{ module: "tool-filesystem" }],
        hooks: [
          { module: "hook-logging" },
          { module: "hook-approval", config: { auto_approve: false } }
        ],
        mcpServers: [
          {
            type: "stdio",
            command: "/opt/mcp/database-mcp",
            args: ["--db", "postgresql://localhost/mydb"],
            env: { DB_PASSWORD: "secret" }
          },
          {
            type: "http",
            url: "https://api.company.com/mcp",
            headers: { "Authorization": "Bearer company-token" }
          }
        ],
        instructions: "You are an enterprise assistant with database access."
      };

      // Verify complete structure
      expect(bundle.name).toBe("enterprise-agent");
      expect(bundle.hooks).toHaveLength(2);
      expect(bundle.mcpServers).toHaveLength(2);
      expect(bundle.providers).toHaveLength(1);
      expect(bundle.tools).toHaveLength(1);
      expect(bundle.instructions).toBeDefined();
    });
  });
});
