/**
 * Recipe management and execution.
 * 
 * Provides types and utilities for building, managing, and executing
 * multi-step AI agent workflows (recipes).
 */

// =============================================================================
// Recipe Types
// =============================================================================

/**
 * Recursion protection configuration.
 */
export interface RecursionConfig {
  /** Maximum recipe invocation depth */
  max_depth?: number;
  /** Maximum total agent spawns across all depths */
  max_agents?: number;
}

/**
 * Rate limiting configuration.
 */
export interface RateLimitingConfig {
  /** Maximum LLM calls per minute */
  max_calls_per_minute?: number;
  /** Whether to fail or queue when limit reached */
  on_limit?: "fail" | "queue";
}

/**
 * Recipe step definition.
 */
export interface RecipeStep {
  /** Unique step identifier */
  id: string;
  
  /** Agent to execute this step (e.g., "foundation:zen-architect") */
  agent?: string;
  
  /** Agent mode (e.g., "ANALYZE", "ARCHITECT", "REVIEW") */
  mode?: string;
  
  /** Prompt template for the agent (supports {{variable}} interpolation) */
  prompt?: string;
  
  /** Step type: agent (default) or bash */
  type?: "agent" | "bash";
  
  /** Bash command to execute (when type="bash") */
  command?: string;
  
  /** Variable name to store step output */
  output?: string;
  
  /** Step timeout in seconds */
  timeout?: number;
  
  /** Error handling strategy */
  on_error?: "fail" | "continue" | "retry";
  
  /** Maximum retry attempts (when on_error="retry") */
  max_retries?: number;
  
  /** Whether this step requires human approval before executing */
  requires_approval?: boolean;
  
  /** Custom approval prompt text */
  approval_prompt?: string;
  
  /** Conditions that must be met for step to execute */
  conditions?: Array<{
    variable: string;
    operator: "equals" | "not_equals" | "contains" | "matches";
    value: any;
  }>;
  
  /** Steps to execute in a loop */
  foreach?: {
    items: string | any[];
    variable: string;
    steps: RecipeStep[];
  };
}

/**
 * Recipe definition.
 */
export interface RecipeDefinition {
  /** Unique recipe name */
  name: string;
  
  /** Human-readable description */
  description: string;
  
  /** Semantic version (e.g., "1.0.0") */
  version: string;
  
  /** Recipe author */
  author?: string;
  
  /** Creation timestamp (ISO8601) */
  created?: string;
  
  /** Last update timestamp (ISO8601) */
  updated?: string;
  
  /** Categorization tags */
  tags?: string[];
  
  /** Initial context variables */
  context?: Record<string, any>;
  
  /** Recursion protection settings */
  recursion?: RecursionConfig;
  
  /** Rate limiting settings */
  rate_limiting?: RateLimitingConfig;
  
  /** Workflow steps */
  steps: RecipeStep[];
}

/**
 * Recipe execution session info.
 */
export interface RecipeSession {
  /** Session identifier */
  session_id: string;
  
  /** Recipe name being executed */
  recipe_name: string;
  
  /** Execution start time */
  started: string;
  
  /** Current step index */
  current_step_index: number;
  
  /** List of completed step IDs */
  completed_steps: string[];
  
  /** Execution status */
  status?: "running" | "completed" | "failed" | "awaiting_approval";
  
  /** Error message if failed */
  error?: string;
}

/**
 * Recipe step progress event.
 */
export interface RecipeStepEvent {
  /** Step identifier */
  step_id: string;
  
  /** Step status */
  status: "started" | "completed" | "failed" | "skipped";
  
  /** Step output (if available) */
  output?: any;
  
  /** Error message (if failed) */
  error?: string;
  
  /** Execution duration in seconds */
  duration?: number;
}

/**
 * Recipe approval gate.
 */
export interface RecipeApprovalGate {
  /** Session identifier */
  session_id: string;
  
  /** Stage/step name requiring approval */
  stage_name: string;
  
  /** Approval prompt text */
  prompt: string;
  
  /** Context information for the approval decision */
  context?: Record<string, any>;
}

// =============================================================================
// Fluent Recipe Builder
// =============================================================================

/**
 * Fluent builder for creating recipes programmatically.
 * 
 * @example
 * ```typescript
 * const recipe = new RecipeBuilder("code-review")
 *   .description("Automated code review workflow")
 *   .version("1.0.0")
 *   .context({ severity: "high" })
 *   .step("analyze", (step) => 
 *     step.agent("foundation:zen-architect")
 *         .prompt("Analyze {{file_path}} for issues")
 *   )
 *   .build();
 * ```
 */
export class RecipeBuilder {
  private recipe: RecipeDefinition;
  
  constructor(name: string) {
    this.recipe = {
      name,
      description: "",
      version: "1.0.0",
      steps: [],
    };
  }
  
  /**
   * Set recipe description.
   */
  description(text: string): this {
    this.recipe.description = text;
    return this;
  }
  
  /**
   * Set recipe version (semantic versioning).
   */
  version(version: string): this {
    this.recipe.version = version;
    return this;
  }
  
  /**
   * Set recipe author.
   */
  author(author: string): this {
    this.recipe.author = author;
    return this;
  }
  
  /**
   * Add tags for categorization.
   */
  tags(...tags: string[]): this {
    this.recipe.tags = tags;
    return this;
  }
  
  /**
   * Set initial context variables.
   */
  context(ctx: Record<string, any>): this {
    this.recipe.context = { ...this.recipe.context, ...ctx };
    return this;
  }
  
  /**
   * Configure recursion protection.
   */
  recursion(config: RecursionConfig): this {
    this.recipe.recursion = config;
    return this;
  }
  
  /**
   * Configure rate limiting.
   */
  rateLimiting(config: RateLimitingConfig): this {
    this.recipe.rate_limiting = config;
    return this;
  }
  
  /**
   * Add a step to the recipe.
   * 
   * @param id - Step identifier
   * @param configure - Function to configure the step
   * 
   * @example
   * ```typescript
   * .step("analyze", (step) => 
   *   step.agent("foundation:zen-architect")
   *       .prompt("Analyze the code")
   *       .timeout(300)
   * )
   * ```
   */
  step(id: string, configure: (builder: StepBuilder) => void): this {
    const stepBuilder = new StepBuilder(id);
    configure(stepBuilder);
    this.recipe.steps.push(stepBuilder.build());
    return this;
  }
  
  /**
   * Build the final recipe definition.
   */
  build(): RecipeDefinition {
    if (!this.recipe.description) {
      throw new Error("Recipe description is required");
    }
    if (this.recipe.steps.length === 0) {
      throw new Error("Recipe must have at least one step");
    }
    return this.recipe;
  }
}

/**
 * Fluent builder for recipe steps.
 */
export class StepBuilder {
  private step: RecipeStep;
  
  constructor(id: string) {
    this.step = { id };
  }
  
  /**
   * Set the agent to execute this step.
   */
  agent(name: string): this {
    this.step.agent = name;
    this.step.type = "agent";
    return this;
  }
  
  /**
   * Set agent mode.
   */
  mode(mode: string): this {
    this.step.mode = mode;
    return this;
  }
  
  /**
   * Set the prompt template.
   */
  prompt(text: string): this {
    this.step.prompt = text;
    return this;
  }
  
  /**
   * Execute a bash command instead of an agent.
   */
  bash(command: string): this {
    this.step.type = "bash";
    this.step.command = command;
    return this;
  }
  
  /**
   * Store step output in a variable.
   */
  output(varName: string): this {
    this.step.output = varName;
    return this;
  }
  
  /**
   * Set step timeout in seconds.
   */
  timeout(seconds: number): this {
    this.step.timeout = seconds;
    return this;
  }
  
  /**
   * Configure error handling.
   */
  onError(strategy: "fail" | "continue" | "retry", maxRetries?: number): this {
    this.step.on_error = strategy;
    if (maxRetries !== undefined) {
      this.step.max_retries = maxRetries;
    }
    return this;
  }
  
  /**
   * Require human approval before executing this step.
   */
  requiresApproval(prompt?: string): this {
    this.step.requires_approval = true;
    if (prompt) {
      this.step.approval_prompt = prompt;
    }
    return this;
  }
  
  /**
   * Add execution condition.
   */
  when(
    variable: string, 
    operator: "equals" | "not_equals" | "contains" | "matches", 
    value: any
  ): this {
    if (!this.step.conditions) {
      this.step.conditions = [];
    }
    this.step.conditions.push({ variable, operator, value });
    return this;
  }
  
  /**
   * Build the step definition.
   */
  build(): RecipeStep {
    return this.step;
  }
}

// =============================================================================
// Recipe Execution Monitor
// =============================================================================

/**
 * Event handler for recipe events.
 */
type RecipeEventHandler = (event: RecipeStepEvent) => void | Promise<void>;

/**
 * Recipe execution monitor.
 * 
 * Provides event-based monitoring of recipe execution progress.
 */
export class RecipeExecution {
  private readonly client: any;
  private readonly sessionId: string;
  private readonly recipeName: string;
  private readonly stepHandlers: Map<string, Set<RecipeEventHandler>> = new Map();
  private readonly approvalHandlers: Set<(gate: RecipeApprovalGate) => Promise<boolean> | boolean> = new Set();
  private currentStep: string | null = null;
  private steps: Map<string, RecipeStepEvent> = new Map();
  
  constructor(client: any, sessionId: string, recipeName: string) {
    this.client = client;
    this.sessionId = sessionId;
    this.recipeName = recipeName;
  }
  
  /**
   * Get the session ID for this recipe execution.
   */
  get id(): string {
    return this.sessionId;
  }
  
  /**
   * Get the recipe name being executed.
   */
  get recipe(): string {
    return this.recipeName;
  }
  
  /**
   * Register a handler for step events.
   * 
   * @example
   * ```typescript
   * execution.on("step.started", (step) => {
   *   console.log(`Starting step: ${step.step_id}`);
   * });
   * 
   * execution.on("step.completed", (step) => {
   *   console.log(`Completed: ${step.step_id}`);
   *   console.log(`Output:`, step.output);
   * });
   * ```
   */
  on(event: "step.started" | "step.completed" | "step.failed" | "step.skipped", handler: RecipeEventHandler): this {
    if (!this.stepHandlers.has(event)) {
      this.stepHandlers.set(event, new Set());
    }
    this.stepHandlers.get(event)!.add(handler);
    return this;
  }
  
  /**
   * Remove an event handler.
   */
  off(event: "step.started" | "step.completed" | "step.failed" | "step.skipped", handler: RecipeEventHandler): this {
    this.stepHandlers.get(event)?.delete(handler);
    return this;
  }
  
  /**
   * Register handler for approval gates.
   * 
   * @example
   * ```typescript
   * execution.onApproval(async (gate) => {
   *   const shouldContinue = await askUser(gate.prompt);
   *   return shouldContinue;
   * });
   * ```
   */
  onApproval(handler: (gate: RecipeApprovalGate) => Promise<boolean> | boolean): this {
    this.approvalHandlers.add(handler);
    return this;
  }
  
  /**
   * Get the current step being executed.
   */
  getCurrentStep(): string | null {
    return this.currentStep;
  }
  
  /**
   * Get completed steps.
   */
  getCompletedSteps(): RecipeStepEvent[] {
    return Array.from(this.steps.values()).filter(s => s.status === "completed");
  }
  
  /**
   * Get all step events.
   */
  getSteps(): RecipeStepEvent[] {
    return Array.from(this.steps.values());
  }
  
  /**
   * Internal: Handle incoming events from the stream.
   */
  handleEvent(event: any): void {
    // Parse recipe-specific events from the stream
    // Recipe events come through tool.call and tool.result for the recipes tool
    
    if (event.type === "tool.call" && event.data.tool === "recipes") {
      const operation = event.data.arguments?.operation;
      
      if (operation === "execute") {
        // Recipe execution started
        this.emitStepEvent({
          step_id: "recipe-start",
          status: "started",
        });
      }
    }
    
    if (event.type === "tool.result" && event.data.tool === "recipes") {
      const result = event.data.result;
      
      // Check for step completion events
      if (result?.step_id) {
        const stepEvent: RecipeStepEvent = {
          step_id: result.step_id,
          status: result.status || "completed",
          output: result.output,
          error: result.error,
          duration: result.duration,
        };
        
        this.steps.set(result.step_id, stepEvent);
        this.currentStep = result.step_id;
        this.emitStepEvent(stepEvent);
      }
    }
    
    // Handle approval requests
    if (event.type === "approval.required") {
      const gate: RecipeApprovalGate = {
        session_id: this.sessionId,
        stage_name: event.data.stage || "unknown",
        prompt: event.data.prompt || "",
        context: event.data.context,
      };
      
      this.handleApprovalGate(gate);
    }
  }
  
  /**
   * Internal: Handle errors.
   */
  handleError(error: Error): void {
    this.emitStepEvent({
      step_id: "recipe-error",
      status: "failed",
      error: error.message,
    });
  }
  
  private emitStepEvent(event: RecipeStepEvent): void {
    const eventType = `step.${event.status}` as "step.started" | "step.completed" | "step.failed" | "step.skipped";
    const handlers = this.stepHandlers.get(eventType);
    
    if (handlers) {
      for (const handler of handlers) {
        Promise.resolve(handler(event)).catch((err) => {
          console.error(`Error in recipe event handler:`, err);
        });
      }
    }
  }
  
  private async handleApprovalGate(gate: RecipeApprovalGate): Promise<void> {
    if (this.approvalHandlers.size === 0) {
      console.warn(`Recipe approval required but no handler registered: ${gate.prompt}`);
      return;
    }
    
    // Call first approval handler
    const handler = this.approvalHandlers.values().next().value;
    if (handler) {
      const approved = await Promise.resolve(handler(gate));
      
      // Send approval response to runtime
      if (approved) {
        await this.client.approveRecipeStage(this.sessionId, gate.stage_name);
      } else {
        await this.client.denyRecipeStage(this.sessionId, gate.stage_name, "User denied");
      }
    }
  }
}
