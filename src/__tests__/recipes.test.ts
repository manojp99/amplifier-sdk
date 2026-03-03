import { describe, it, expect } from "vitest";
import { RecipeBuilder, StepBuilder } from "../recipes";

describe("RecipeBuilder — basic construction", () => {
  it("builds a valid recipe with name, description, version, and one step", () => {
    const recipe = new RecipeBuilder("my-recipe")
      .description("Does something useful")
      .version("1.0.0")
      .step("do-work", (s) => s.agent("foundation:zen-architect").prompt("Do it"))
      .build();

    expect(recipe.name).toBe("my-recipe");
    expect(recipe.description).toBe("Does something useful");
    expect(recipe.version).toBe("1.0.0");
    expect(recipe.steps).toHaveLength(1);
    expect(recipe.steps[0].id).toBe("do-work");
    expect(recipe.steps[0].agent).toBe("foundation:zen-architect");
    expect(recipe.steps[0].prompt).toBe("Do it");
  });

  it("sets default version to 1.0.0", () => {
    const recipe = new RecipeBuilder("x")
      .description("test")
      .step("s", (s) => s.agent("a"))
      .build();
    expect(recipe.version).toBe("1.0.0");
  });

  it("throws if description is missing", () => {
    expect(() => new RecipeBuilder("no-desc").build()).toThrow("Recipe description is required");
  });

  it("throws if there are no steps", () => {
    expect(() =>
      new RecipeBuilder("no-steps").description("has description").build()
    ).toThrow("Recipe must have at least one step");
  });
});

describe("RecipeBuilder — chain methods", () => {
  it("adds multiple steps in order", () => {
    const recipe = new RecipeBuilder("multi")
      .description("multi-step")
      .step("a", (s) => s.agent("agent-a"))
      .step("b", (s) => s.agent("agent-b"))
      .step("c", (s) => s.agent("agent-c"))
      .build();

    expect(recipe.steps.map((s) => s.id)).toEqual(["a", "b", "c"]);
  });

  it("merges context objects when called multiple times", () => {
    const recipe = new RecipeBuilder("ctx")
      .description("context test")
      .context({ foo: 1 })
      .context({ bar: 2 })
      .step("s", (s) => s.agent("a"))
      .build();

    expect(recipe.context).toEqual({ foo: 1, bar: 2 });
  });

  it("sets author and tags", () => {
    const recipe = new RecipeBuilder("meta")
      .description("meta test")
      .author("Test Author")
      .tags("a", "b", "c")
      .step("s", (s) => s.agent("a"))
      .build();

    expect(recipe.author).toBe("Test Author");
    expect(recipe.tags).toEqual(["a", "b", "c"]);
  });

  it("configures recursion limits", () => {
    const recipe = new RecipeBuilder("recursive")
      .description("recursion test")
      .recursion({ max_depth: 3, max_agents: 10 })
      .step("s", (s) => s.agent("a"))
      .build();

    expect(recipe.recursion).toEqual({ max_depth: 3, max_agents: 10 });
  });

  it("configures rate limiting", () => {
    const recipe = new RecipeBuilder("rate-limited")
      .description("rate test")
      .rateLimiting({ max_calls_per_minute: 60, on_limit: "queue" })
      .step("s", (s) => s.agent("a"))
      .build();

    expect(recipe.rate_limiting).toEqual({ max_calls_per_minute: 60, on_limit: "queue" });
  });
});

describe("StepBuilder — step options", () => {
  const buildStepRecipe = (configureFn: (s: StepBuilder) => void) => {
    return new RecipeBuilder("test")
      .description("test")
      .step("my-step", configureFn)
      .build()
      .steps[0];
  };

  it("sets agent and type=agent", () => {
    const step = buildStepRecipe((s) => s.agent("foundation:zen-architect"));
    expect(step.agent).toBe("foundation:zen-architect");
    expect(step.type).toBe("agent");
  });

  it("sets bash command and type=bash", () => {
    const step = buildStepRecipe((s) => s.bash("npm test"));
    expect(step.type).toBe("bash");
    expect(step.command).toBe("npm test");
  });

  it("sets timeout", () => {
    const step = buildStepRecipe((s) => s.agent("a").timeout(300));
    expect(step.timeout).toBe(300);
  });

  it("sets output variable name", () => {
    const step = buildStepRecipe((s) => s.agent("a").output("my_result"));
    expect(step.output).toBe("my_result");
  });

  it("sets on_error and max_retries", () => {
    const step = buildStepRecipe((s) => s.agent("a").onError("retry", 3));
    expect(step.on_error).toBe("retry");
    expect(step.max_retries).toBe(3);
  });

  it("sets requires_approval and approval_prompt", () => {
    const step = buildStepRecipe((s) =>
      s.agent("a").requiresApproval("Are you sure?")
    );
    expect(step.requires_approval).toBe(true);
    expect(step.approval_prompt).toBe("Are you sure?");
  });

  it("adds conditions via when()", () => {
    const step = buildStepRecipe((s) =>
      s.agent("a").when("env", "equals", "production").when("approved", "equals", true)
    );
    expect(step.conditions).toHaveLength(2);
    expect(step.conditions![0]).toEqual({ variable: "env", operator: "equals", value: "production" });
    expect(step.conditions![1]).toEqual({ variable: "approved", operator: "equals", value: true });
  });
});
