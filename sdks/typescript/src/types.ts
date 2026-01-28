/**
 * Type definitions for Amplifier SDK
 */

export interface AgentConfig {
  instructions: string;
  tools?: string[];
  provider?: string;
  model?: string;
  bundle?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
}

export interface RunResponse {
  content: string;
  tool_calls: ToolCall[];
  usage: Usage;
  stop_reason?: string;
}

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export type RecipeStatus =
  | 'pending'
  | 'running'
  | 'waiting_approval'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface StepResult {
  step_id: string;
  status: string;
  content?: string;
  error?: string;
}

export interface RecipeExecution {
  execution_id: string;
  recipe_name: string;
  status: RecipeStatus;
  current_step?: string;
  steps: StepResult[];
  error?: string;
  created_at?: string;
}

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export interface CreateAgentOptions {
  instructions: string;
  tools?: string[];
  provider?: string;
  model?: string;
  bundle?: string;
}

export interface ExecuteRecipeOptions {
  recipePath?: string;
  recipeYaml?: string;
  context?: Record<string, unknown>;
}
