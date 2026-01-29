/**
 * Type definitions for Amplifier SDK
 */

// =============================================================================
// Configuration Types
// =============================================================================

export interface ProviderConfig {
  module: string;
  priority?: number;
  model?: string;
  config?: Record<string, unknown>;
}

export interface ToolConfig {
  module: string;
  config?: Record<string, unknown>;
}

export interface HookConfig {
  module: string;
  config?: Record<string, unknown>;
}

export interface ApprovalConfig {
  require_approval?: string[];
  auto_approve?: string[];
  timeout?: number;
}

export interface SubAgentConfig {
  instructions: string;
  provider?: string;
  model?: string;
  tools?: (string | ToolConfig)[];
  config?: Record<string, unknown>;
}

export interface AgentConfig {
  instructions: string;
  provider?: string;
  providers?: ProviderConfig[];
  model?: string;
  tools?: (string | ToolConfig)[];
  orchestrator?: string;
  context_manager?: string;
  hooks?: (string | HookConfig)[];
  approval?: ApprovalConfig;
  agents?: Record<string, SubAgentConfig>;
  config?: Record<string, unknown>;
}

// =============================================================================
// Response Types
// =============================================================================

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: string;
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface RunResponse {
  content: string;
  tool_calls: ToolCall[];
  usage: Usage;
  turn_count: number;
  sub_agents_spawned?: string[];
}

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface AgentInfo {
  agent_id: string;
  created_at: string;
  status: string;
  instructions?: string;
  provider?: string;
  model?: string;
  tools: string[];
  orchestrator?: string;
  context_manager?: string;
  hooks?: string[];
  agents?: string[];
  message_count: number;
  has_approval_config?: boolean;
}

export interface SubAgentInfo {
  agent_id: string;
  parent_id: string;
  agent_name: string;
  created_at: string;
}

export interface ApprovalInfo {
  approval_id: string;
  agent_id: string;
  tool: string;
  action: string;
  args: Record<string, unknown>;
  created_at: string;
  timeout_at: string;
}

export interface Message {
  role: string;
  content: string;
}

// =============================================================================
// Recipe Types
// =============================================================================

export interface RecipeStep {
  id: string;
  agent: string;
  prompt: string;
  condition?: string;
  requires_approval?: boolean;
}

export interface RecipeConfig {
  name: string;
  steps: RecipeStep[];
  agents?: Record<string, SubAgentConfig>;
  description?: string;
}

export interface RecipeStepResult {
  step_id: string;
  agent: string;
  status: string;
  content?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface RecipeExecution {
  execution_id: string;
  recipe_name: string;
  status: string;
  current_step?: string;
  steps: RecipeStepResult[];
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error?: string;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Client Options
// =============================================================================

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export interface CreateAgentOptions {
  instructions: string;
  provider?: string;
  providers?: ProviderConfig[];
  model?: string;
  tools?: (string | ToolConfig)[];
  orchestrator?: string;
  contextManager?: string;
  hooks?: (string | HookConfig)[];
  approval?: ApprovalConfig;
  agents?: Record<string, SubAgentConfig>;
  config?: Record<string, unknown>;
}

export interface RunOptions {
  maxTurns?: number;
  streamEvents?: string[];
}

export interface SpawnOptions {
  agentName: string;
  prompt?: string;
  inheritContext?: 'none' | 'recent' | 'all';
  inheritContextTurns?: number;
}

export interface RunOnceOptions {
  prompt: string;
  instructions?: string;
  provider?: string;
  model?: string;
  tools?: string[];
  maxTurns?: number;
}

export interface ExecuteRecipeOptions {
  recipe?: RecipeConfig;
  recipePath?: string;
  input?: Record<string, unknown>;
}

// =============================================================================
// Server Responses
// =============================================================================

export interface HealthResponse {
  status: string;
  version: string;
  core_version?: string;
}

export interface ModulesResponse {
  providers: string[];
  tools: string[];
  orchestrators: string[];
  context_managers: string[];
  hooks: string[];
}
