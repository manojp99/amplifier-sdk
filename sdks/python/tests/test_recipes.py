"""Tests for recipe management and execution."""

import pytest

from amplifier_sdk import (
    AmplifierClient,
    RecipeBuilder,
    RecipeDefinition,
    RecipeStep,
)


class TestRecipeBuilder:
    """Test cases for RecipeBuilder."""

    def test_build_basic_recipe(self):
        """Test building a basic recipe."""
        recipe = (
            RecipeBuilder("test-recipe")
            .description("A test recipe")
            .version("1.0.0")
            .step("step1", lambda s: s.agent("foundation:zen-architect").prompt("Do something"))
            .build()
        )

        assert recipe.name == "test-recipe"
        assert recipe.description == "A test recipe"
        assert recipe.version == "1.0.0"
        assert len(recipe.steps) == 1
        assert recipe.steps[0].id == "step1"
        assert recipe.steps[0].agent == "foundation:zen-architect"

    def test_build_recipe_with_context(self):
        """Test building recipe with context variables."""
        recipe = (
            RecipeBuilder("context-recipe")
            .description("Recipe with context")
            .version("1.0.0")
            .context({"severity": "high", "language": "python"})
            .step("analyze", lambda s: s.agent("analyzer").prompt("Analyze {{language}}"))
            .build()
        )

        assert recipe.context == {"severity": "high", "language": "python"}

    def test_build_recipe_with_multiple_steps(self):
        """Test building recipe with multiple steps."""
        recipe = (
            RecipeBuilder("multi-step")
            .description("Multi-step workflow")
            .version("1.0.0")
            .step("step1", lambda s: s.agent("agent1").prompt("Step 1"))
            .step("step2", lambda s: s.agent("agent2").prompt("Step 2"))
            .step("step3", lambda s: s.agent("agent3").prompt("Step 3"))
            .build()
        )

        assert len(recipe.steps) == 3
        assert [s.id for s in recipe.steps] == ["step1", "step2", "step3"]

    def test_configure_step_timeout(self):
        """Test configuring step timeout."""
        recipe = (
            RecipeBuilder("timeout-recipe")
            .description("Recipe with timeout")
            .version("1.0.0")
            .step("slow-step", lambda s: s.agent("worker").prompt("Long task").timeout(600))
            .build()
        )

        assert recipe.steps[0].timeout == 600

    def test_configure_step_error_handling(self):
        """Test configuring step error handling."""
        recipe = (
            RecipeBuilder("error-recipe")
            .description("Recipe with error handling")
            .version("1.0.0")
            .step(
                "risky-step", lambda s: s.agent("worker").prompt("Risky task").on_error("retry", 3)
            )
            .build()
        )

        assert recipe.steps[0].on_error == "retry"
        assert recipe.steps[0].max_retries == 3

    def test_configure_step_approval(self):
        """Test configuring step approval requirement."""
        recipe = (
            RecipeBuilder("approval-recipe")
            .description("Recipe with approval")
            .version("1.0.0")
            .step(
                "destructive",
                lambda s: s.agent("worker")
                .prompt("Delete everything")
                .requires_approval("Are you sure?"),
            )
            .build()
        )

        assert recipe.steps[0].requires_approval is True
        assert recipe.steps[0].approval_prompt == "Are you sure?"

    def test_bash_steps(self):
        """Test bash command steps."""
        recipe = (
            RecipeBuilder("bash-recipe")
            .description("Recipe with bash")
            .version("1.0.0")
            .step("run-tests", lambda s: s.bash("pytest").output("test_results"))
            .build()
        )

        assert recipe.steps[0].type == "bash"
        assert recipe.steps[0].command == "pytest"
        assert recipe.steps[0].output == "test_results"

    def test_configure_step_conditions(self):
        """Test configuring step conditions."""
        recipe = (
            RecipeBuilder("conditional-recipe")
            .description("Recipe with conditions")
            .version("1.0.0")
            .step(
                "conditional",
                lambda s: s.agent("worker")
                .prompt("Run this")
                .when("environment", "equals", "production"),
            )
            .build()
        )

        assert len(recipe.steps[0].conditions) == 1
        assert recipe.steps[0].conditions[0] == {
            "variable": "environment",
            "operator": "equals",
            "value": "production",
        }

    def test_configure_recipe_metadata(self):
        """Test configuring recipe metadata."""
        recipe = (
            RecipeBuilder("meta-recipe")
            .description("Recipe with metadata")
            .version("2.1.0")
            .author("Test Author")
            .tags("testing", "automation", "ci")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        assert recipe.author == "Test Author"
        assert recipe.tags == ["testing", "automation", "ci"]
        assert recipe.version == "2.1.0"

    def test_configure_recursion_limits(self):
        """Test configuring recursion limits."""
        from amplifier_sdk.recipes import RecursionConfig

        recipe = (
            RecipeBuilder("recursive-recipe")
            .description("Recipe with recursion limits")
            .version("1.0.0")
            .recursion(RecursionConfig(max_depth=3, max_agents=10))
            .step("work", lambda s: s.agent("worker").prompt("Do work"))
            .build()
        )

        assert recipe.recursion is not None
        assert recipe.recursion.max_depth == 3
        assert recipe.recursion.max_agents == 10

    def test_configure_rate_limiting(self):
        """Test configuring rate limiting."""
        from amplifier_sdk.recipes import RateLimitingConfig

        recipe = (
            RecipeBuilder("rate-limited-recipe")
            .description("Recipe with rate limiting")
            .version("1.0.0")
            .rate_limiting(RateLimitingConfig(max_calls_per_minute=60, on_limit="queue"))
            .step("work", lambda s: s.agent("worker").prompt("Do work"))
            .build()
        )

        assert recipe.rate_limiting is not None
        assert recipe.rate_limiting.max_calls_per_minute == 60
        assert recipe.rate_limiting.on_limit == "queue"

    def test_missing_description_raises_error(self):
        """Test that missing description raises error."""
        with pytest.raises(ValueError, match="description is required"):
            RecipeBuilder("incomplete").build()

    def test_no_steps_raises_error(self):
        """Test that recipe with no steps raises error."""
        with pytest.raises(ValueError, match="at least one step"):
            RecipeBuilder("no-steps").description("Recipe without steps").build()


class TestRecipeCRUD:
    """Test cases for recipe CRUD operations."""

    def test_save_recipe(self):
        """Test saving a recipe."""
        client = AmplifierClient()
        recipe = (
            RecipeBuilder("saved-recipe")
            .description("A saved recipe")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        client.save_recipe(recipe)

        retrieved = client.get_recipe("saved-recipe")
        assert retrieved is not None
        assert retrieved.name == "saved-recipe"

    def test_list_all_recipes(self):
        """Test listing all saved recipes."""
        client = AmplifierClient()

        recipe1 = (
            RecipeBuilder("recipe1")
            .description("First recipe")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        recipe2 = (
            RecipeBuilder("recipe2")
            .description("Second recipe")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        client.save_recipe(recipe1)
        client.save_recipe(recipe2)

        recipes = client.get_recipes()
        assert len(recipes) == 2
        assert "recipe1" in [r.name for r in recipes]
        assert "recipe2" in [r.name for r in recipes]

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        client = AmplifierClient()
        recipe = (
            RecipeBuilder("to-delete")
            .description("Will be deleted")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        client.save_recipe(recipe)
        assert client.get_recipe("to-delete") is not None

        deleted = client.delete_recipe("to-delete")
        assert deleted is True
        assert client.get_recipe("to-delete") is None

    def test_delete_nonexistent_recipe(self):
        """Test deleting non-existent recipe returns False."""
        client = AmplifierClient()
        deleted = client.delete_recipe("does-not-exist")
        assert deleted is False

    def test_overwrite_recipe(self):
        """Test overwriting recipe with same name."""
        client = AmplifierClient()

        recipe1 = (
            RecipeBuilder("updatable")
            .description("Version 1")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work v1"))
            .build()
        )

        recipe2 = (
            RecipeBuilder("updatable")
            .description("Version 2")
            .version("2.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work v2"))
            .build()
        )

        client.save_recipe(recipe1)
        client.save_recipe(recipe2)

        retrieved = client.get_recipe("updatable")
        assert retrieved.version == "2.0.0"
        assert retrieved.description == "Version 2"


class TestComplexRecipeScenarios:
    """Test cases for complex recipe scenarios."""

    def test_code_review_recipe(self):
        """Test building a code review recipe."""
        client = AmplifierClient()
        recipe = (
            client.recipe("code-review")
            .description("Comprehensive code review workflow")
            .version("1.0.0")
            .tags("code-quality", "review", "security")
            .context({"severity_threshold": "medium"})
            .step(
                "analyze",
                lambda s: s.agent("foundation:zen-architect")
                .mode("ANALYZE")
                .prompt("Analyze {{file_path}} for issues")
                .timeout(300)
                .output("analysis_result"),
            )
            .step(
                "security-scan",
                lambda s: s.agent("foundation:security-guardian")
                .prompt("Review {{file_path}} for security")
                .timeout(180)
                .output("security_result"),
            )
            .step(
                "generate-report",
                lambda s: s.agent("foundation:technical-writer")
                .prompt("Create report from: {{analysis_result}} and {{security_result}}")
                .output("review_report"),
            )
            .step(
                "apply-fixes",
                lambda s: s.agent("foundation:modular-builder")
                .prompt("Apply fixes from {{review_report}}")
                .requires_approval("Apply these fixes?")
                .on_error("fail"),
            )
            .build()
        )

        assert len(recipe.steps) == 4
        assert recipe.steps[0].output == "analysis_result"
        assert recipe.steps[3].requires_approval is True

    def test_ci_pipeline_recipe(self):
        """Test building a CI/CD pipeline recipe."""
        client = AmplifierClient()
        recipe = (
            client.recipe("ci-pipeline")
            .description("Continuous integration pipeline")
            .version("1.0.0")
            .step("lint", lambda s: s.bash("npm run lint").output("lint_result"))
            .step("test", lambda s: s.bash("npm test").output("test_result"))
            .step("build", lambda s: s.bash("npm run build").output("build_result"))
            .step(
                "deploy",
                lambda s: s.bash("npm run deploy")
                .requires_approval("Deploy to production?")
                .when("test_result", "contains", "PASS"),
            )
            .build()
        )

        assert len(recipe.steps) == 4
        assert recipe.steps[0].type == "bash"
        assert recipe.steps[3].conditions is not None

    def test_multi_agent_research_recipe(self):
        """Test building a multi-agent research recipe."""
        from amplifier_sdk.recipes import RateLimitingConfig, RecursionConfig

        client = AmplifierClient()
        recipe = (
            client.recipe("research")
            .description("Multi-agent research workflow")
            .version("1.0.0")
            .recursion(RecursionConfig(max_depth=3, max_agents=10))
            .rate_limiting(RateLimitingConfig(max_calls_per_minute=30, on_limit="queue"))
            .step(
                "gather",
                lambda s: s.agent("foundation:web-research")
                .prompt("Research {{topic}}")
                .timeout(600),
            )
            .step(
                "analyze", lambda s: s.agent("foundation:zen-architect").prompt("Analyze findings")
            )
            .step(
                "synthesize", lambda s: s.agent("stories:technical-writer").prompt("Write report")
            )
            .build()
        )

        assert recipe.recursion is not None
        assert recipe.rate_limiting is not None
        assert len(recipe.steps) == 3


class TestRecipeClientMethods:
    """Test cases for recipe client methods."""

    def test_create_recipe_via_client(self):
        """Test creating recipe via client.recipe()."""
        client = AmplifierClient()
        recipe = (
            client.recipe("client-recipe")
            .description("Created via client")
            .version("1.0.0")
            .step("work", lambda s: s.agent("worker").prompt("Work"))
            .build()
        )

        assert recipe.name == "client-recipe"

    def test_save_and_retrieve_recipes(self):
        """Test saving and retrieving recipes."""
        client = AmplifierClient()
        recipe = RecipeDefinition(
            name="manual-recipe",
            description="Manually created",
            version="1.0.0",
            steps=[RecipeStep(id="step1", agent="worker", prompt="Do work")],
        )

        client.save_recipe(recipe)

        retrieved = client.get_recipe("manual-recipe")
        assert retrieved is not None
        assert retrieved.name == "manual-recipe"
        assert retrieved.steps[0].id == "step1"

    def test_list_empty_recipes_initially(self):
        """Test that recipes list is empty initially."""
        client = AmplifierClient()
        recipes = client.get_recipes()
        assert recipes == []

    def test_save_without_name_raises_error(self):
        """Test that saving recipe without name raises error."""
        client = AmplifierClient()
        invalid_recipe = type("Recipe", (), {"name": None})()

        with pytest.raises(ValueError, match="name is required"):
            client.save_recipe(invalid_recipe)


class TestStepBuilderOptions:
    """Test cases for step builder options."""

    def test_step_with_all_options(self):
        """Test building step with all options."""
        recipe = (
            RecipeBuilder("full-options")
            .description("Step with all options")
            .version("1.0.0")
            .step(
                "full-step",
                lambda s: s.agent("foundation:zen-architect")
                .mode("ANALYZE")
                .prompt("Analyze {{target}}")
                .timeout(300)
                .output("result")
                .on_error("retry", 2)
                .requires_approval("Proceed?")
                .when("env", "equals", "prod"),
            )
            .build()
        )

        step = recipe.steps[0]
        assert step.agent == "foundation:zen-architect"
        assert step.mode == "ANALYZE"
        assert step.prompt == "Analyze {{target}}"
        assert step.timeout == 300
        assert step.output == "result"
        assert step.on_error == "retry"
        assert step.max_retries == 2
        assert step.requires_approval is True
        assert step.approval_prompt == "Proceed?"
        assert len(step.conditions) == 1

    def test_multiple_conditions(self):
        """Test step with multiple conditions."""
        recipe = (
            RecipeBuilder("multi-condition")
            .description("Multiple conditions")
            .version("1.0.0")
            .step(
                "gated",
                lambda s: s.agent("worker")
                .prompt("Work")
                .when("env", "equals", "prod")
                .when("approved", "equals", True)
                .when("tests", "contains", "PASS"),
            )
            .build()
        )

        step = recipe.steps[0]
        assert len(step.conditions) == 3
        assert step.conditions[0]["variable"] == "env"
        assert step.conditions[1]["variable"] == "approved"
        assert step.conditions[2]["variable"] == "tests"

    def test_minimal_step_configuration(self):
        """Test minimal step configuration."""
        recipe = (
            RecipeBuilder("minimal-step")
            .description("Minimal step config")
            .version("1.0.0")
            .step("minimal", lambda s: s.agent("worker"))
            .build()
        )

        step = recipe.steps[0]
        assert step.id == "minimal"
        assert step.agent == "worker"
        assert step.prompt is None
        assert step.timeout is None
