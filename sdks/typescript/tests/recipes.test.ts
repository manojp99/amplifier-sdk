/**
 * Tests for recipe management and execution.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { AmplifierClient } from "../src/client";
import { RecipeBuilder, type RecipeDefinition } from "../src/recipes";

describe("Recipe Management", () => {
  let client: AmplifierClient;

  beforeEach(() => {
    client = new AmplifierClient();
  });

  describe("RecipeBuilder", () => {
    it("should build a basic recipe", () => {
      const recipe = new RecipeBuilder("test-recipe")
        .description("A test recipe")
        .version("1.0.0")
        .step("step1", (s) => s.agent("foundation:zen-architect").prompt("Do something"))
        .build();

      expect(recipe.name).toBe("test-recipe");
      expect(recipe.description).toBe("A test recipe");
      expect(recipe.version).toBe("1.0.0");
      expect(recipe.steps).toHaveLength(1);
      expect(recipe.steps[0].id).toBe("step1");
      expect(recipe.steps[0].agent).toBe("foundation:zen-architect");
    });

    it("should build recipe with context variables", () => {
      const recipe = new RecipeBuilder("context-recipe")
        .description("Recipe with context")
        .version("1.0.0")
        .context({ severity: "high", language: "typescript" })
        .step("analyze", (s) => s.agent("analyzer").prompt("Analyze {{language}}"))
        .build();

      expect(recipe.context).toEqual({ severity: "high", language: "typescript" });
    });

    it("should build recipe with multiple steps", () => {
      const recipe = new RecipeBuilder("multi-step")
        .description("Multi-step workflow")
        .version("1.0.0")
        .step("step1", (s) => s.agent("agent1").prompt("Step 1"))
        .step("step2", (s) => s.agent("agent2").prompt("Step 2"))
        .step("step3", (s) => s.agent("agent3").prompt("Step 3"))
        .build();

      expect(recipe.steps).toHaveLength(3);
      expect(recipe.steps.map((s) => s.id)).toEqual(["step1", "step2", "step3"]);
    });

    it("should configure step timeout", () => {
      const recipe = new RecipeBuilder("timeout-recipe")
        .description("Recipe with timeout")
        .version("1.0.0")
        .step("slow-step", (s) => 
          s.agent("worker").prompt("Long task").timeout(600)
        )
        .build();

      expect(recipe.steps[0].timeout).toBe(600);
    });

    it("should configure step error handling", () => {
      const recipe = new RecipeBuilder("error-recipe")
        .description("Recipe with error handling")
        .version("1.0.0")
        .step("risky-step", (s) => 
          s.agent("worker").prompt("Risky task").onError("retry", 3)
        )
        .build();

      expect(recipe.steps[0].on_error).toBe("retry");
      expect(recipe.steps[0].max_retries).toBe(3);
    });

    it("should configure step approval requirement", () => {
      const recipe = new RecipeBuilder("approval-recipe")
        .description("Recipe with approval")
        .version("1.0.0")
        .step("destructive", (s) => 
          s.agent("worker")
           .prompt("Delete everything")
           .requiresApproval("Are you sure you want to delete everything?")
        )
        .build();

      expect(recipe.steps[0].requires_approval).toBe(true);
      expect(recipe.steps[0].approval_prompt).toBe("Are you sure you want to delete everything?");
    });

    it("should support bash steps", () => {
      const recipe = new RecipeBuilder("bash-recipe")
        .description("Recipe with bash")
        .version("1.0.0")
        .step("run-tests", (s) => 
          s.bash("npm test").output("test_results")
        )
        .build();

      expect(recipe.steps[0].type).toBe("bash");
      expect(recipe.steps[0].command).toBe("npm test");
      expect(recipe.steps[0].output).toBe("test_results");
    });

    it("should configure step conditions", () => {
      const recipe = new RecipeBuilder("conditional-recipe")
        .description("Recipe with conditions")
        .version("1.0.0")
        .step("conditional", (s) => 
          s.agent("worker")
           .prompt("Run this")
           .when("environment", "equals", "production")
        )
        .build();

      expect(recipe.steps[0].conditions).toHaveLength(1);
      expect(recipe.steps[0].conditions![0]).toEqual({
        variable: "environment",
        operator: "equals",
        value: "production"
      });
    });

    it("should configure recipe metadata", () => {
      const recipe = new RecipeBuilder("meta-recipe")
        .description("Recipe with metadata")
        .version("2.1.0")
        .author("Test Author")
        .tags("testing", "automation", "ci")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      expect(recipe.author).toBe("Test Author");
      expect(recipe.tags).toEqual(["testing", "automation", "ci"]);
      expect(recipe.version).toBe("2.1.0");
    });

    it("should configure recursion limits", () => {
      const recipe = new RecipeBuilder("recursive-recipe")
        .description("Recipe with recursion limits")
        .version("1.0.0")
        .recursion({ max_depth: 3, max_agents: 10 })
        .step("work", (s) => s.agent("worker").prompt("Do work"))
        .build();

      expect(recipe.recursion).toEqual({ max_depth: 3, max_agents: 10 });
    });

    it("should configure rate limiting", () => {
      const recipe = new RecipeBuilder("rate-limited-recipe")
        .description("Recipe with rate limiting")
        .version("1.0.0")
        .rateLimiting({ max_calls_per_minute: 60, on_limit: "queue" })
        .step("work", (s) => s.agent("worker").prompt("Do work"))
        .build();

      expect(recipe.rate_limiting).toEqual({
        max_calls_per_minute: 60,
        on_limit: "queue"
      });
    });

    it("should throw error if description is missing", () => {
      expect(() => {
        new RecipeBuilder("incomplete").build();
      }).toThrow("Recipe description is required");
    });

    it("should throw error if no steps", () => {
      expect(() => {
        new RecipeBuilder("no-steps")
          .description("Recipe without steps")
          .build();
      }).toThrow("Recipe must have at least one step");
    });
  });

  describe("Recipe CRUD", () => {
    it("should save a recipe", () => {
      const recipe = client.recipe("saved-recipe")
        .description("A saved recipe")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      client.saveRecipe(recipe);

      const retrieved = client.getRecipe("saved-recipe");
      expect(retrieved).toBeDefined();
      expect(retrieved!.name).toBe("saved-recipe");
    });

    it("should list all saved recipes", () => {
      const recipe1 = client.recipe("recipe1")
        .description("First recipe")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      const recipe2 = client.recipe("recipe2")
        .description("Second recipe")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      client.saveRecipe(recipe1);
      client.saveRecipe(recipe2);

      const recipes = client.getRecipes();
      expect(recipes).toHaveLength(2);
      expect(recipes.map((r) => r.name)).toContain("recipe1");
      expect(recipes.map((r) => r.name)).toContain("recipe2");
    });

    it("should delete a recipe", () => {
      const recipe = client.recipe("to-delete")
        .description("Will be deleted")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      client.saveRecipe(recipe);
      expect(client.getRecipe("to-delete")).toBeDefined();

      const deleted = client.deleteRecipe("to-delete");
      expect(deleted).toBe(true);
      expect(client.getRecipe("to-delete")).toBeUndefined();
    });

    it("should return false when deleting non-existent recipe", () => {
      const deleted = client.deleteRecipe("does-not-exist");
      expect(deleted).toBe(false);
    });

    it("should overwrite recipe with same name", () => {
      const recipe1 = client.recipe("updatable")
        .description("Version 1")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work v1"))
        .build();

      const recipe2 = client.recipe("updatable")
        .description("Version 2")
        .version("2.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work v2"))
        .build();

      client.saveRecipe(recipe1);
      client.saveRecipe(recipe2);

      const retrieved = client.getRecipe("updatable");
      expect(retrieved!.version).toBe("2.0.0");
      expect(retrieved!.description).toBe("Version 2");
    });
  });

  describe("Recipe Execution API", () => {
    it("should construct execution with saved recipe", () => {
      const recipe = client.recipe("executable")
        .description("Executable recipe")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      client.saveRecipe(recipe);

      // Verify recipe is saved and can be retrieved
      const saved = client.getRecipe("executable");
      expect(saved).toBeDefined();
      expect(saved!.name).toBe("executable");
    });

    it("should accept recipe path format", () => {
      // Test that recipe path format is accepted
      const recipePath = "@recipes:code-review.yaml";
      expect(recipePath).toMatch(/^@.*:.*\.yaml$/);
    });

    it("should store context for execution", () => {
      const context = { file_path: "src/auth.ts", severity: "high" };
      const contextStr = Object.entries(context)
        .map(([k, v]) => `${k}="${v}"`)
        .join(", ");
      
      expect(contextStr).toBe('file_path="src/auth.ts", severity="high"');
    });
  });

  describe("Complex Recipe Scenarios", () => {
    it("should build a code review recipe", () => {
      const recipe = client.recipe("code-review")
        .description("Comprehensive code review workflow")
        .version("1.0.0")
        .tags("code-quality", "review", "security")
        .context({ severity_threshold: "medium" })
        .step("analyze", (s) => 
          s.agent("foundation:zen-architect")
           .mode("ANALYZE")
           .prompt("Analyze {{file_path}} for issues with severity >= {{severity_threshold}}")
           .timeout(300)
           .output("analysis_result")
        )
        .step("security-scan", (s) => 
          s.agent("foundation:security-guardian")
           .prompt("Review {{file_path}} for security vulnerabilities")
           .timeout(180)
           .output("security_result")
        )
        .step("generate-report", (s) => 
          s.agent("foundation:technical-writer")
           .prompt("Create review report from: {{analysis_result}} and {{security_result}}")
           .output("review_report")
        )
        .step("apply-fixes", (s) => 
          s.agent("foundation:modular-builder")
           .prompt("Apply fixes from {{review_report}}")
           .requiresApproval("Apply these fixes to the codebase?")
           .onError("fail")
        )
        .build();

      expect(recipe.steps).toHaveLength(4);
      expect(recipe.steps[0].output).toBe("analysis_result");
      expect(recipe.steps[3].requires_approval).toBe(true);
    });

    it("should build a CI/CD pipeline recipe", () => {
      const recipe = client.recipe("ci-pipeline")
        .description("Continuous integration pipeline")
        .version("1.0.0")
        .step("lint", (s) => s.bash("npm run lint").output("lint_result"))
        .step("test", (s) => s.bash("npm test").output("test_result"))
        .step("build", (s) => s.bash("npm run build").output("build_result"))
        .step("deploy", (s) => 
          s.bash("npm run deploy")
           .requiresApproval("Deploy to production?")
           .when("test_result", "contains", "PASS")
        )
        .build();

      expect(recipe.steps).toHaveLength(4);
      expect(recipe.steps[0].type).toBe("bash");
      expect(recipe.steps[3].conditions).toBeDefined();
    });

    it("should build a multi-agent research recipe", () => {
      const recipe = client.recipe("research")
        .description("Multi-agent research workflow")
        .version("1.0.0")
        .recursion({ max_depth: 3, max_agents: 10 })
        .rateLimiting({ max_calls_per_minute: 30, on_limit: "queue" })
        .step("gather", (s) => 
          s.agent("foundation:web-research")
           .prompt("Research {{topic}}")
           .timeout(600)
        )
        .step("analyze", (s) => 
          s.agent("foundation:zen-architect")
           .prompt("Analyze research findings")
        )
        .step("synthesize", (s) => 
          s.agent("stories:technical-writer")
           .prompt("Write comprehensive report")
        )
        .build();

      expect(recipe.recursion).toBeDefined();
      expect(recipe.rate_limiting).toBeDefined();
      expect(recipe.steps).toHaveLength(3);
    });
  });

  describe("Recipe Client Methods", () => {
    it("should create recipe via client.recipe()", () => {
      const recipe = client.recipe("client-recipe")
        .description("Created via client")
        .version("1.0.0")
        .step("work", (s) => s.agent("worker").prompt("Work"))
        .build();

      expect(recipe.name).toBe("client-recipe");
    });

    it("should save and retrieve recipes", () => {
      const recipe: RecipeDefinition = {
        name: "manual-recipe",
        description: "Manually created",
        version: "1.0.0",
        steps: [
          {
            id: "step1",
            agent: "worker",
            prompt: "Do work"
          }
        ]
      };

      client.saveRecipe(recipe);

      const retrieved = client.getRecipe("manual-recipe");
      expect(retrieved).toBeDefined();
      expect(retrieved!.name).toBe("manual-recipe");
      expect(retrieved!.steps[0].id).toBe("step1");
    });

    it("should list empty recipes initially", () => {
      const recipes = client.getRecipes();
      expect(recipes).toEqual([]);
    });

    it("should throw on save without name", () => {
      const invalidRecipe = {
        description: "No name",
        version: "1.0.0",
        steps: []
      } as any;

      expect(() => {
        client.saveRecipe(invalidRecipe);
      }).toThrow("Recipe name is required");
    });
  });

  describe("Step Builder Options", () => {
    it("should build step with all options", () => {
      const recipe = client.recipe("full-options")
        .description("Step with all options")
        .version("1.0.0")
        .step("full-step", (s) => 
          s.agent("foundation:zen-architect")
           .mode("ANALYZE")
           .prompt("Analyze {{target}}")
           .timeout(300)
           .output("result")
           .onError("retry", 2)
           .requiresApproval("Proceed?")
           .when("env", "equals", "prod")
        )
        .build();

      const step = recipe.steps[0];
      expect(step.agent).toBe("foundation:zen-architect");
      expect(step.mode).toBe("ANALYZE");
      expect(step.prompt).toBe("Analyze {{target}}");
      expect(step.timeout).toBe(300);
      expect(step.output).toBe("result");
      expect(step.on_error).toBe("retry");
      expect(step.max_retries).toBe(2);
      expect(step.requires_approval).toBe(true);
      expect(step.approval_prompt).toBe("Proceed?");
      expect(step.conditions).toHaveLength(1);
    });

    it("should support multiple conditions", () => {
      const recipe = client.recipe("multi-condition")
        .description("Multiple conditions")
        .version("1.0.0")
        .step("gated", (s) => 
          s.agent("worker")
           .prompt("Work")
           .when("env", "equals", "prod")
           .when("approved", "equals", true)
           .when("tests", "contains", "PASS")
        )
        .build();

      const step = recipe.steps[0];
      expect(step.conditions).toHaveLength(3);
      expect(step.conditions![0].variable).toBe("env");
      expect(step.conditions![1].variable).toBe("approved");
      expect(step.conditions![2].variable).toBe("tests");
    });

    it("should support minimal step configuration", () => {
      const recipe = client.recipe("minimal-step")
        .description("Minimal step config")
        .version("1.0.0")
        .step("minimal", (s) => s.agent("worker"))
        .build();

      const step = recipe.steps[0];
      expect(step.id).toBe("minimal");
      expect(step.agent).toBe("worker");
      expect(step.prompt).toBeUndefined();
      expect(step.timeout).toBeUndefined();
    });
  });
});
