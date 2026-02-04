/**
 * Tests for client-side tool schema transmission to runtime.
 * 
 * This tests the critical bug fix where client tools must send their
 * schemas (description, parameters) to the runtime, not just names.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";

describe("Client Tool Schema Transmission", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  it("should send full tool schemas when creating session with clientTools", () => {
    // Register a client-side tool
    client.registerTool({
      name: "test-tool",
      description: "A test tool for validation",
      parameters: {
        type: "object",
        properties: {
          input: { type: "string" }
        },
        required: ["input"]
      },
      handler: async () => ({ success: true })
    });

    // Create bundle with client tool reference
    const bundle = {
      name: "test-bundle",
      clientTools: ["test-tool"],
      providers: [{ module: "provider-anthropic" }]
    };

    // Serialize bundle (this is what gets sent to runtime)
    const serialized = (client as any).serializeBundleDefinition(bundle);

    // Verify clientTools contains full schema, not just name
    expect(serialized.clientTools).toBeDefined();
    expect(serialized.clientTools).toHaveLength(1);
    expect(serialized.clientTools[0]).toEqual({
      name: "test-tool",
      description: "A test tool for validation",
      parameters: {
        type: "object",
        properties: {
          input: { type: "string" }
        },
        required: ["input"]
      }
    });
  });

  it("should handle unregistered client tools gracefully", () => {
    // Bundle references tool that hasn't been registered
    const bundle = {
      name: "test-bundle",
      clientTools: ["unregistered-tool"],
      providers: [{ module: "provider-anthropic" }]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    // Should still serialize, but with minimal schema
    expect(serialized.clientTools).toBeDefined();
    expect(serialized.clientTools).toHaveLength(1);
    expect(serialized.clientTools[0]).toEqual({
      name: "unregistered-tool"
    });
  });

  it("should send schemas for multiple client tools", () => {
    client.registerTool({
      name: "tool-one",
      description: "First tool",
      parameters: { type: "object" },
      handler: async () => ({})
    });

    client.registerTool({
      name: "tool-two",
      description: "Second tool",
      parameters: {
        type: "object",
        properties: {
          param: { type: "string" }
        }
      },
      handler: async () => ({})
    });

    const bundle = {
      name: "multi-tool-bundle",
      clientTools: ["tool-one", "tool-two"],
      providers: [{ module: "provider-anthropic" }]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    expect(serialized.clientTools).toHaveLength(2);
    expect(serialized.clientTools[0].name).toBe("tool-one");
    expect(serialized.clientTools[0].description).toBe("First tool");
    expect(serialized.clientTools[1].name).toBe("tool-two");
    expect(serialized.clientTools[1].description).toBe("Second tool");
  });

  it("should handle mix of registered and unregistered tools", () => {
    client.registerTool({
      name: "registered",
      description: "This is registered",
      handler: async () => ({})
    });

    const bundle = {
      name: "mixed-bundle",
      clientTools: ["registered", "not-registered"],
      providers: [{ module: "provider-anthropic" }]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    expect(serialized.clientTools).toHaveLength(2);
    
    // Registered tool has full schema
    expect(serialized.clientTools[0]).toEqual({
      name: "registered",
      description: "This is registered",
      parameters: {}
    });
    
    // Unregistered tool has name only
    expect(serialized.clientTools[1]).toEqual({
      name: "not-registered"
    });
  });

  it("should handle bundle with no clientTools", () => {
    const bundle = {
      name: "no-tools-bundle",
      providers: [{ module: "provider-anthropic" }]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    expect(serialized.clientTools).toBeUndefined();
  });

  it("should handle empty clientTools array", () => {
    const bundle = {
      name: "empty-tools-bundle",
      clientTools: [],
      providers: [{ module: "provider-anthropic" }]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    expect(serialized.clientTools).toEqual([]);
  });

  it("should include parameters even when empty object", () => {
    client.registerTool({
      name: "no-params-tool",
      description: "Tool without parameters",
      // No parameters field
      handler: async () => ({})
    });

    const bundle = {
      name: "test",
      clientTools: ["no-params-tool"]
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    // Should default to empty object
    expect(serialized.clientTools[0].parameters).toEqual({});
  });

  it("should preserve tool registration order", () => {
    const tools = ["alpha", "beta", "charlie"];
    
    tools.forEach(name => {
      client.registerTool({
        name,
        description: `Tool ${name}`,
        handler: async () => ({})
      });
    });

    const bundle = {
      name: "ordered-bundle",
      clientTools: tools
    };

    const serialized = (client as any).serializeBundleDefinition(bundle);

    expect(serialized.clientTools.map((t: any) => t.name)).toEqual(tools);
  });
});
