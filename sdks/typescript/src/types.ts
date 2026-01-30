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
 * SSE event from the server.
 */
export interface Event {
  type: string;
  data: Record<string, unknown>;
  id?: string;
  correlationId?: string;
  sequence?: number;
  final?: boolean;
  timestamp?: string;
}

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
  /** Tool modules to load */
  tools?: ModuleConfig[];
  /** Hook modules to load */
  hooks?: ModuleConfig[];
  /** Orchestrator module */
  orchestrator?: ModuleConfig;
  /** Context module */
  context?: ModuleConfig;
  
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
