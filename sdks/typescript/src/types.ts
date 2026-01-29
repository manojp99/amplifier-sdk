/**
 * Type definitions for Amplifier SDK
 */

export interface AgentConfig {
  instructions: string;
  provider: string;
  model?: string;
  tools?: string[];
  orchestrator?: string;
  context_manager?: string;
  hooks?: string[];
  config?: Record<string, unknown>;
}

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
  message_count: number;
}

export interface Message {
  role: string;
  content: string;
}

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export interface CreateAgentOptions {
  instructions: string;
  provider?: string;
  model?: string;
  tools?: string[];
  orchestrator?: string;
  contextManager?: string;
  hooks?: string[];
  config?: Record<string, unknown>;
}

export interface RunOptions {
  maxTurns?: number;
}

export interface RunOnceOptions {
  prompt: string;
  instructions?: string;
  provider?: string;
  model?: string;
  tools?: string[];
  maxTurns?: number;
}

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
