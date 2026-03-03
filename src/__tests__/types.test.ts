/**
 * Import-only smoke test for type exports.
 * This test will catch if a re-export is accidentally removed from index.ts.
 * It imports types that are used in Canvas's backend — if they disappear,
 * the import here will fail at build time.
 */
import { describe, it, expect } from "vitest";
import {
  AmplifierClient,
  AmplifierError,
  ErrorCode,
  ConnectionState,
  EventType,
  RecipeBuilder,
  StepBuilder,
  MODULE_CATALOG,
  getModulesByType,
  findModule,
  getAllModules,
} from "../index";

describe("index.ts — named exports exist", () => {
  it("exports AmplifierClient as a constructor", () => {
    expect(typeof AmplifierClient).toBe("function");
  });

  it("exports AmplifierError as a constructor", () => {
    expect(typeof AmplifierError).toBe("function");
  });

  it("exports ErrorCode enum with known values", () => {
    expect(ErrorCode.NetworkError).toBeDefined();
    expect(ErrorCode.SessionNotFound).toBeDefined();
  });

  it("exports ConnectionState enum with known values", () => {
    expect(ConnectionState.Connected).toBeDefined();
    expect(ConnectionState.Disconnected).toBeDefined();
  });

  it("exports EventType enum", () => {
    expect(EventType).toBeDefined();
  });

  it("exports RecipeBuilder as a constructor", () => {
    expect(typeof RecipeBuilder).toBe("function");
  });

  it("exports StepBuilder as a constructor", () => {
    expect(typeof StepBuilder).toBe("function");
  });

  it("exports MODULE_CATALOG as an object with expected keys", () => {
    expect(MODULE_CATALOG).toHaveProperty("providers");
    expect(MODULE_CATALOG).toHaveProperty("tools");
    expect(MODULE_CATALOG).toHaveProperty("orchestrators");
    expect(MODULE_CATALOG).toHaveProperty("contexts");
    expect(MODULE_CATALOG).toHaveProperty("hooks");
  });

  it("exports catalog functions", () => {
    expect(typeof getModulesByType).toBe("function");
    expect(typeof findModule).toBe("function");
    expect(typeof getAllModules).toBe("function");
  });
});
