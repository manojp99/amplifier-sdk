import { describe, it, expect } from "vitest";
import {
  getModulesByType,
  findModule,
  getAllModules,
  MODULE_CATALOG,
  PROVIDERS,
  TOOLS,
  ORCHESTRATORS,
  CONTEXTS,
  HOOKS,
} from "../catalog";

describe("catalog — getModulesByType", () => {
  it("returns only providers when type is 'provider'", () => {
    const result = getModulesByType("provider");
    expect(result).toBe(PROVIDERS);
    expect(result.every((m) => m.type === "provider")).toBe(true);
  });

  it("returns only tools when type is 'tool'", () => {
    const result = getModulesByType("tool");
    expect(result).toBe(TOOLS);
    expect(result.every((m) => m.type === "tool")).toBe(true);
  });

  it("returns only orchestrators when type is 'orchestrator'", () => {
    const result = getModulesByType("orchestrator");
    expect(result).toBe(ORCHESTRATORS);
  });

  it("returns only contexts when type is 'context'", () => {
    const result = getModulesByType("context");
    expect(result).toBe(CONTEXTS);
  });

  it("returns only hooks when type is 'hook'", () => {
    const result = getModulesByType("hook");
    expect(result).toBe(HOOKS);
  });

  it("each returned module has required fields", () => {
    for (const type of ["provider", "tool", "orchestrator", "context", "hook"] as const) {
      const modules = getModulesByType(type);
      for (const m of modules) {
        expect(m).toHaveProperty("id");
        expect(m).toHaveProperty("type");
        expect(m).toHaveProperty("name");
        expect(m).toHaveProperty("description");
      }
    }
  });
});

describe("catalog — findModule", () => {
  it("finds a known provider by id", () => {
    const m = findModule("provider-anthropic");
    expect(m).toBeDefined();
    expect(m!.id).toBe("provider-anthropic");
    expect(m!.type).toBe("provider");
  });

  it("finds a known tool by id", () => {
    const m = findModule("tool-bash");
    expect(m).toBeDefined();
    expect(m!.type).toBe("tool");
  });

  it("returns undefined for unknown id", () => {
    const m = findModule("does-not-exist");
    expect(m).toBeUndefined();
  });
});

describe("catalog — getAllModules", () => {
  it("returns all modules combined", () => {
    const all = getAllModules();
    const expected =
      PROVIDERS.length +
      TOOLS.length +
      ORCHESTRATORS.length +
      CONTEXTS.length +
      HOOKS.length;
    expect(all).toHaveLength(expected);
  });

  it("contains modules from every type", () => {
    const all = getAllModules();
    const types = new Set(all.map((m) => m.type));
    expect(types).toContain("provider");
    expect(types).toContain("tool");
    expect(types).toContain("orchestrator");
    expect(types).toContain("context");
    expect(types).toContain("hook");
  });

  it("MODULE_CATALOG contains the same modules", () => {
    const all = getAllModules();
    const catalogTotal =
      MODULE_CATALOG.providers.length +
      MODULE_CATALOG.tools.length +
      MODULE_CATALOG.orchestrators.length +
      MODULE_CATALOG.contexts.length +
      MODULE_CATALOG.hooks.length;
    expect(all).toHaveLength(catalogTotal);
  });
});
