/**
 * Type definitions for Amplifier SDK.
 */

// =============================================================================
// Error Types
// =============================================================================

/**
 * Error codes for structured error handling.
 */
export enum ErrorCode {
  // Network errors
  NetworkError = "NETWORK_ERROR",
  Timeout = "TIMEOUT",
  ConnectionRefused = "CONNECTION_REFUSED",

  // HTTP errors
  BadRequest = "BAD_REQUEST",
  Unauthorized = "UNAUTHORIZED",
  Forbidden = "FORBIDDEN",
  NotFound = "NOT_FOUND",
  ServerError = "SERVER_ERROR",

  // Session errors
  SessionNotFound = "SESSION_NOT_FOUND",
  SessionExpired = "SESSION_EXPIRED",
  SessionBusy = "SESSION_BUSY",

  // Streaming errors
  StreamError = "STREAM_ERROR",
  StreamAborted = "STREAM_ABORTED",

  // General
  Unknown = "UNKNOWN",
}

/**
 * Structured error with code, status, and request context.
 */
export class AmplifierError extends Error {
  /** Error code for programmatic handling */
  readonly code: ErrorCode;
  /** HTTP status code (if applicable) */
  readonly status?: number;
  /** Request ID for correlation/debugging */
  readonly requestId?: string;
  /** Original error (if wrapped) */
  readonly cause?: Error;

  constructor(
    message: string,
    code: ErrorCode,
    options?: {
      status?: number;
      requestId?: string;
      cause?: Error;
    }
  ) {
    super(message);
    this.name = "AmplifierError";
    this.code = code;
    this.status = options?.status;
    this.requestId = options?.requestId;
    this.cause = options?.cause;
  }

  /** Check if error is retryable */
  get isRetryable(): boolean {
    return [
      ErrorCode.NetworkError,
      ErrorCode.Timeout,
      ErrorCode.ServerError,
    ].includes(this.code);
  }
}

// =============================================================================
// Connection State
// =============================================================================

/**
 * Connection state for observability.
 */
export enum ConnectionState {
  Disconnected = "disconnected",
  Connecting = "connecting",
  Connected = "connected",
  Reconnecting = "reconnecting",
  Error = "error",
}

// =============================================================================
// Observability Types
// =============================================================================

/**
 * Request information for observability hooks.
 */
export interface RequestInfo {
  /** Unique request ID */
  requestId: string;
  /** HTTP method */
  method: string;
  /** Request URL */
  url: string;
  /** Request headers (sensitive values redacted) */
  headers?: Record<string, string>;
  /** Request body (if JSON) */
  body?: unknown;
  /** Timestamp when request was initiated */
  timestamp: Date;
}

/**
 * Response information for observability hooks.
 */
export interface ResponseInfo {
  /** Request ID for correlation */
  requestId: string;
  /** HTTP status code */
  status: number;
  /** Response headers */
  headers?: Record<string, string>;
  /** Response body (if JSON) */
  body?: unknown;
  /** Duration in milliseconds */
  durationMs: number;
  /** Timestamp when response was received */
  timestamp: Date;
}

/**
 * State change information for observability.
 */
export interface StateChangeInfo {
  /** Previous state */
  from: ConnectionState;
  /** New state */
  to: ConnectionState;
  /** Reason for change (if applicable) */
  reason?: string;
  /** Timestamp of change */
  timestamp: Date;
}

// =============================================================================
// Event Types
// =============================================================================

/**
 * Event types emitted during streaming.
 */
export enum EventType {
  ContentDelta = "content.delta",
  ContentEnd = "content.end",
  ThinkingDelta = "thinking.delta",
  ToolCall = "tool.call",
  ToolResult = "tool.result",
  ApprovalRequired = "approval.required",
  AgentSpawned = "agent.spawned",
  AgentCompleted = "agent.completed",
  Error = "error",
}

/**
 * Base event properties shared across all event types.
 */
export interface BaseEvent {
  /** Event ID for deduplication */
  id?: string;
  /** Correlation ID for tracing related events */
  correlationId?: string;
  /** Sequence number in the stream */
  sequence?: number;
  /** Whether this is the final event */
  final?: boolean;
  /** ISO timestamp */
  timestamp?: string;
  /** Tool call ID (for tool.call and tool.result correlation) */
  toolCallId?: string;
  /** Agent ID that emitted this event (parent vs child distinction) */
  agentId?: string;
}

/**
 * Content delta event - incremental text content.
 */
export interface ContentDeltaEvent extends BaseEvent {
  type: "content.delta";
  data: {
    delta: string;
  };
}

/**
 * Content end event - marks completion of content streaming.
 */
export interface ContentEndEvent extends BaseEvent {
  type: "content.end";
  data: Record<string, unknown>;
}

/**
 * Thinking delta event - incremental reasoning/thinking content.
 */
export interface ThinkingDeltaEvent extends BaseEvent {
  type: "thinking.delta";
  data: {
    delta: string;
  };
}

/**
 * Tool call event - agent is calling a tool.
 */
export interface ToolCallEvent extends BaseEvent {
  type: "tool.call";
  data: {
    tool_name: string;
    tool_call_id?: string;
    arguments: Record<string, unknown>;
  };
  toolCallId: string;
}

/**
 * Tool result event - tool execution completed.
 */
export interface ToolResultEvent extends BaseEvent {
  type: "tool.result";
  data: {
    tool_name?: string;
    tool_call_id?: string;
    result: unknown;
    error?: string;
  };
  toolCallId: string;
}

/**
 * Approval required event - agent needs user permission.
 */
export interface ApprovalRequiredEvent extends BaseEvent {
  type: "approval.required";
  data: {
    request_id: string;
    prompt: string;
    tool_name?: string;
    arguments?: Record<string, unknown>;
  };
}

/**
 * Agent spawned event - sub-agent started.
 */
export interface AgentSpawnedEvent extends BaseEvent {
  type: "agent.spawned";
  data: {
    agent_id: string;
    agent_name: string;
    parent_id?: string;
  };
}

/**
 * Agent completed event - sub-agent finished.
 */
export interface AgentCompletedEvent extends BaseEvent {
  type: "agent.completed";
  data: {
    agent_id: string;
    result?: string;
    error?: string;
  };
}

/**
 * Error event.
 */
export interface ErrorEvent extends BaseEvent {
  type: "error";
  data: {
    error: string;
    code?: string;
    details?: Record<string, unknown>;
  };
}

/**
 * Generic event for unknown/future event types.
 */
export interface GenericEvent extends BaseEvent {
  type: string;
  data: Record<string, unknown>;
}

/**
 * All possible SSE events from the server.
 * Discriminated union enables type-safe event handling.
 */
export type Event =
  | ContentDeltaEvent
  | ContentEndEvent
  | ThinkingDeltaEvent
  | ToolCallEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | AgentSpawnedEvent
  | AgentCompletedEvent
  | ErrorEvent
  | GenericEvent;

/**
 * Module definition for providers, tools, hooks.
 */
export interface ModuleConfig {
  /** Module name (e.g., "provider-anthropic", "tool-filesystem") */
  module: string;
  /** Optional source URL for the module */
  source?: string;
  /** Module-specific configuration */
  config?: Record<string, unknown>;
}

/**
 * Agent definition within a bundle.
 */
export interface AgentConfig {
  /** Agent name */
  name: string;
  /** Agent description */
  description?: string;
  /** System instructions for this agent */
  instructions?: string;
  /** Tools available to this agent */
  tools?: string[];
}

/**
 * Client-side behavior definition.
 * 
 * Behaviors are reusable capability packages that can be composed.
 */
export interface BehaviorDefinition {
  /** Behavior name */
  name: string;
  /** Behavior description */
  description?: string;
  /** System instructions to merge */
  instructions?: string;
  /** Server-side tools to include */
  tools?: ModuleConfig[];
  /** Client-side tools to include */
  clientTools?: string[];
  /** Providers to use */
  providers?: ModuleConfig[];
  /** Hooks to apply */
  hooks?: ModuleConfig[];
}

/**
 * MCP (Model Context Protocol) server configuration.
 * 
 * MCP servers provide external tools and resources to the agent.
 */
export type McpServerConfig = McpServerStdio | McpServerHttp | McpServerSse;

/**
 * MCP server via stdio (spawns a process).
 */
export interface McpServerStdio {
  /** Server type */
  type: "stdio";
  /** Command to execute */
  command: string;
  /** Command arguments */
  args?: string[];
  /** Environment variables */
  env?: Record<string, string>;
}

/**
 * MCP server via HTTP.
 */
export interface McpServerHttp {
  /** Server type */
  type: "http";
  /** Server URL */
  url: string;
  /** Authentication headers */
  headers?: Record<string, string>;
}

/**
 * MCP server via SSE (Server-Sent Events).
 */
export interface McpServerSse {
  /** Server type */
  type: "sse";
  /** Server URL */
  url: string;
  /** Authentication headers */
  headers?: Record<string, string>;
}

/**
 * Bundle definition for runtime bundle creation.
 * 
 * This allows you to define a complete bundle configuration
 * programmatically instead of referencing a pre-existing bundle by name.
 */
export interface BundleDefinition {
  /** Bundle name */
  name: string;
  /** Bundle version (default: "1.0.0") */
  version?: string;
  /** Bundle description */
  description?: string;
  
  /** Provider modules to load */
  providers?: ModuleConfig[];
  /** Tool modules to load (server-side) */
  tools?: ModuleConfig[];
  /** Client-side tools (handled by SDK, not server) */
  clientTools?: string[];
  /** Hook modules to load */
  hooks?: ModuleConfig[];
  /** Orchestrator module */
  orchestrator?: ModuleConfig;
  /** Context module */
  context?: ModuleConfig;
  
  /** MCP servers to connect */
  mcpServers?: McpServerConfig[];
  
  /** Agent definitions */
  agents?: AgentConfig[];
  
  /** System instructions (injected into all prompts) */
  instructions?: string;
  
  /** Session configuration */
  session?: {
    debug?: boolean;
    maxTurns?: number;
    [key: string]: unknown;
  };
  
  /** Other bundles to compose/inherit from */
  includes?: string[];
  
  /** Behaviors to compose (client-side) */
  behaviors?: string[];
}

/**
 * Session configuration - supports both named bundles and runtime definitions.
 */
export interface SessionConfig {
  /** 
   * Bundle to use - either a name (string) or a full definition (object).
   * 
   * @example Using a named bundle:
   * ```typescript
   * { bundle: "foundation" }
   * ```
   * 
   * @example Using a runtime bundle definition:
   * ```typescript
   * { 
   *   bundle: {
   *     name: "my-agent",
   *     providers: [{ module: "provider-anthropic" }],
   *     tools: [{ module: "tool-filesystem" }],
   *     instructions: "You are a coding assistant."
   *   }
   * }
   * ```
   */
  bundle?: string | BundleDefinition;
  
  /** Override the provider (by name) */
  provider?: string;
  /** Override the model */
  model?: string;
  /** Working directory for the session */
  workingDirectory?: string;
  /** Additional behaviors to compose */
  behaviors?: string[];
  /** MCP servers to connect */
  mcpServers?: McpServerConfig[];
}

/**
 * Session information returned after creation.
 */
export interface SessionInfo {
  id: string;
  title?: string;
  state?: string;
  bundle?: string;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Tool call information.
 */
export interface ToolCall {
  toolName: string;
  toolCallId: string;
  arguments: Record<string, unknown>;
  output?: unknown;
}

/**
 * Response from synchronous prompt.
 */
export interface PromptResponse {
  content: string;
  toolCalls: ToolCall[];
  sessionId?: string;
  stopReason?: string;
}

/**
 * Approval request from the agent.
 */
export interface ApprovalRequest {
  requestId: string;
  prompt: string;
  options: string[];
  toolName?: string;
  arguments?: Record<string, unknown>;
}

/**
 * Server capabilities.
 */
export interface Capabilities {
  version: string;
  streaming: boolean;
  tools: string[];
  providers: string[];
  features: string[];
}

/**
 * Client-side tool definition.
 * Tools registered with the SDK run locally in the app, not on the server.
 */
export interface ClientTool {
  /** Tool name (must match what's in bundle.clientTools) */
  name: string;
  /** Tool description for AI */
  description: string;
  /** Parameter schema (JSON Schema) */
  parameters?: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
  /** Handler function that executes the tool */
  handler: (args: Record<string, unknown>) => Promise<unknown> | unknown;
}

/**
 * Client configuration.
 */
export interface ClientConfig {
  /** Server base URL (default: http://localhost:4096) */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 300000) */
  timeout?: number;
  /** Default bundle for new sessions */
  defaultBundle?: string | BundleDefinition;

  // ===========================================================================
  // Observability Hooks
  // ===========================================================================

  /**
   * Called before each HTTP request.
   * Use for logging, tracing, or request modification.
   */
  onRequest?: (info: RequestInfo) => void;

  /**
   * Called after each HTTP response.
   * Use for logging, metrics, or response inspection.
   */
  onResponse?: (info: ResponseInfo) => void;

  /**
   * Called when an error occurs.
   * Use for error tracking, alerting, or recovery logic.
   */
  onError?: (error: AmplifierError) => void;

  /**
   * Called when connection state changes.
   * Use for UI updates or reconnection logic.
   */
  onStateChange?: (info: StateChangeInfo) => void;

  /**
   * Called for each streaming event.
   * Use for event logging or debugging.
   */
  onEvent?: (event: Event) => void;

  /**
   * Enable debug mode for verbose console logging.
   * @default false
   */
  debug?: boolean;
}

// =============================================================================
// Agent Spawning Visibility Types
// =============================================================================

/**
 * Agent hierarchy node for tracking parent/child relationships.
 */
export interface AgentNode {
  /** Unique agent ID */
  agentId: string;
  /** Agent name (bundle/agent type) */
  agentName: string;
  /** Parent agent ID (null for root) */
  parentId: string | null;
  /** Child agent IDs */
  children: string[];
  /** Agent spawn timestamp */
  spawnedAt: string;
  /** Agent completion timestamp (null if still running) */
  completedAt: string | null;
  /** Agent result (available after completion) */
  result?: string;
  /** Agent error (if failed) */
  error?: string;
}

/**
 * Agent spawned callback.
 */
export type AgentSpawnedHandler = (info: {
  agentId: string;
  agentName: string;
  parentId: string | null;
  timestamp: string;
}) => void | Promise<void>;

/**
 * Agent completed callback.
 */
export type AgentCompletedHandler = (info: {
  agentId: string;
  result?: string;
  error?: string;
  timestamp: string;
}) => void | Promise<void>;
