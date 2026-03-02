/**
 * Amplifier SDK Client.
 *
 * HTTP client for communicating with amplifier-app-runtime server.
 * Supports both streaming (SSE) and synchronous request modes.
 * Includes full observability via hooks for request/response/error/state tracking.
 */

import {
  AmplifierError,
  ConnectionState,
  ErrorCode,
  type AgentNode,
  type AgentSpawnedHandler,
  type AgentCompletedHandler,
  type BehaviorDefinition,
  type BundleDefinition,
  type Capabilities,
  type ClientConfig,
  type ClientTool,
  type Event,
  type ModuleConfig,
  type PromptResponse,
  type RequestInfo,
  type ResponseInfo,
  type SessionConfig,
  type SessionInfo,
  type StateChangeInfo,
  type ToolCall,
} from "./types";

import { RecipeBuilder, RecipeExecution } from "./recipes";
import type { RecipeDefinition } from "./recipes";

/**
 * Generate a unique request ID.
 */
function generateRequestId(): string {
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * HTTP client for amplifier-app-runtime server.
 *
 * @example Basic usage:
 * ```typescript
 * const client = new AmplifierClient();
 * const session = await client.createSession({ bundle: "foundation" });
 * for await (const event of client.prompt(session.id, "Hello!")) {
 *   if (event.type === "content.delta") {
 *     process.stdout.write(event.data.delta as string);
 *   }
 * }
 * ```
 *
 * @example With observability hooks:
 * ```typescript
 * const client = new AmplifierClient({
 *   debug: true,
 *   onRequest: (req) => console.log(`[REQ] ${req.method} ${req.url}`),
 *   onResponse: (res) => console.log(`[RES] ${res.status} in ${res.durationMs}ms`),
 *   onError: (err) => console.error(`[ERR] ${err.code}: ${err.message}`),
 *   onStateChange: (info) => console.log(`[STATE] ${info.from} -> ${info.to}`),
 * });
 * ```
 */
/**
 * Event handler function type.
 */
type EventHandler = (event: Event) => void | Promise<void>;

/**
 * Approval handler function type.
 */
type ApprovalHandler = (request: {
  requestId: string;
  prompt: string;
  toolName?: string;
  arguments?: Record<string, unknown>;
}) => Promise<boolean> | boolean;

/**
 * Thinking state.
 */
type ThinkingState = {
  isThinking: boolean;
  content: string;
};

/**
 * Thinking handler function type.
 */
type ThinkingHandler = (thinking: ThinkingState) => void | Promise<void>;

export class AmplifierClient {
  private readonly config: ClientConfig;
  private readonly baseUrl: string;
  private readonly timeout: number;
  private _connectionState: ConnectionState = ConnectionState.Disconnected;
  private readonly clientTools: Map<string, ClientTool> = new Map();
  private readonly eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private approvalHandler: ApprovalHandler | null = null;
  private readonly agentSpawnedHandlers: Set<AgentSpawnedHandler> = new Set();
  private readonly agentCompletedHandlers: Set<AgentCompletedHandler> = new Set();
  private readonly agentHierarchy: Map<string, AgentNode> = new Map();
  private readonly thinkingHandlers: Set<ThinkingHandler> = new Set();
  private isThinking: boolean = false;
  private currentThinkingContent: string = "";
  private readonly behaviors: Map<string, BehaviorDefinition> = new Map();
  private readonly recipes: Map<string, RecipeDefinition> = new Map();

  constructor(config: ClientConfig = {}) {
    this.config = config;
    this.baseUrl = (config.baseUrl ?? "http://localhost:4096").replace(/\/$/, "");
    this.timeout = config.timeout ?? 300000;
  }

  // ===========================================================================
  // Connection State (Observable)
  // ===========================================================================

  /**
   * Current connection state.
   */
  get connectionState(): ConnectionState {
    return this._connectionState;
  }

  private setConnectionState(state: ConnectionState, reason?: string): void {
    if (this._connectionState === state) return;

    const info: StateChangeInfo = {
      from: this._connectionState,
      to: state,
      reason,
      timestamp: new Date(),
    };

    this._connectionState = state;
    this.debug(`State change: ${info.from} -> ${info.to}${reason ? ` (${reason})` : ""}`);
    this.config.onStateChange?.(info);
  }

  // ===========================================================================
  // Health & Capabilities
  // ===========================================================================

  /**
   * Check if server is alive.
   */
  async ping(): Promise<boolean> {
    try {
      this.setConnectionState(ConnectionState.Connecting);
      await this.request("GET", "/v1/ping");
      this.setConnectionState(ConnectionState.Connected);
      return true;
    } catch {
      this.setConnectionState(ConnectionState.Disconnected, "ping failed");
      return false;
    }
  }

  /**
   * Get server capabilities.
   */
  async capabilities(): Promise<Capabilities> {
    const data = await this.request("GET", "/v1/capabilities");
    return data as Capabilities;
  }

  // ===========================================================================
  // Session Management
  // ===========================================================================

  /**
   * Create a new session.
   *
   * @example Using a named bundle:
   * ```typescript
   * const session = await client.createSession({ bundle: "foundation" });
   * ```
   *
   * @example Using a runtime bundle definition:
   * ```typescript
   * const session = await client.createSession({
   *   bundle: {
   *     name: "my-custom-agent",
   *     providers: [{ module: "provider-anthropic" }],
   *     tools: [{ module: "tool-filesystem" }],
   *     instructions: "You are a helpful coding assistant."
   *   }
   * });
   * ```
   */
  async createSession(config: SessionConfig = {}): Promise<SessionInfo> {
    const body: Record<string, unknown> = {};

    if (config.bundle) {
      if (typeof config.bundle === "string") {
        body.bundle = config.bundle;
      } else {
        let bundleDefinition = config.bundle;
        
        // Merge behaviors if specified
        if (bundleDefinition.behaviors && bundleDefinition.behaviors.length > 0) {
          bundleDefinition = this.mergeBehaviors(bundleDefinition, bundleDefinition.behaviors);
          // Remove behaviors field after merging (runtime doesn't understand it)
          const { behaviors, ...rest } = bundleDefinition;
          bundleDefinition = rest;
        }
        
        body.bundle_definition = this.serializeBundleDefinition(bundleDefinition);
      }
    }

    if (config.provider) body.provider = config.provider;
    if (config.model) body.model = config.model;
    if (config.workingDirectory) body.working_directory = config.workingDirectory;
    if (config.storageDirectory) body.storage_directory = config.storageDirectory;
    if (config.behaviors) body.behaviors = config.behaviors;

    const data = await this.request("POST", "/v1/session", body);
    return this.parseSessionInfo(data as Record<string, unknown>);
  }

  /**
   * Get session information.
   */
  async getSession(sessionId: string): Promise<SessionInfo> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    const data = await this.request("GET", `/v1/session/${sessionId}`);
    return this.parseSessionInfo(data as Record<string, unknown>);
  }

  /**
   * List all sessions.
   */
  async listSessions(): Promise<SessionInfo[]> {
    const data = await this.request("GET", "/v1/session") as Record<string, unknown>;
    const sessions = (data.sessions ?? data.active ?? []) as Record<string, unknown>[];
    return sessions.map((s) => this.parseSessionInfo(s));
  }

  /**
   * Resume a previous session (convenience method).
   * 
   * This is a convenience wrapper that fetches session info and provides
   * helper methods for continuing the conversation.
   * 
   * @example
   * ```typescript
   * const session = await client.resumeSession("sess_abc123");
   * 
   * // Continue the conversation
   * for await (const event of session.send("Where were we?")) {
   *   if (event.type === "content.delta") {
   *     process.stdout.write(event.data.delta);
   *   }
   * }
   * ```
   */
  async resumeSession(sessionId: string) {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    
    const info = await this.getSession(sessionId);
    
    return {
      ...info,
      send: (content: string) => this.prompt(sessionId, content),
      sendSync: (content: string) => this.promptSync(sessionId, content),
      cancel: () => this.cancel(sessionId),
      delete: () => this.deleteSession(sessionId),
    };
  }

  /**
   * Delete a session.
   */
  async deleteSession(sessionId: string): Promise<boolean> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    try {
      await this.request("DELETE", `/v1/session/${sessionId}`);
      return true;
    } catch {
      return false;
    }
  }

  // ===========================================================================
  // Prompt Execution
  // ===========================================================================

  /**
   * Send a prompt and stream the response.
   *
   * @example
   * ```typescript
   * for await (const event of client.prompt(sessionId, "Hello!")) {
   *   if (event.type === "content.delta") {
   *     process.stdout.write(event.data.delta as string);
   *   } else if (event.type === "tool.call") {
   *     console.log(`Calling tool: ${event.data.tool_name}`);
   *   }
   * }
   * ```
   */
  async *prompt(sessionId: string, content: string): AsyncGenerator<Event> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!content || typeof content !== "string") {
      throw new AmplifierError(
        "Prompt content is required and must be a string",
        ErrorCode.BadRequest
      );
    }

    const requestId = generateRequestId();
    const url = `${this.baseUrl}/v1/session/${sessionId}/prompt`;
    const body = { content, stream: true };
    const startTime = Date.now();

    // Emit request info
    const requestInfo: RequestInfo = {
      requestId,
      method: "POST",
      url,
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body,
      timestamp: new Date(),
    };
    this.debug(`[${requestId}] POST ${url}`);
    this.config.onRequest?.(requestInfo);

    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeout),
      });
    } catch (err) {
      const error = this.wrapError(err, requestId);
      this.config.onError?.(error);
      throw error;
    }

    // Emit response info
    const responseInfo: ResponseInfo = {
      requestId,
      status: response.status,
      durationMs: Date.now() - startTime,
      timestamp: new Date(),
    };
    this.debug(`[${requestId}] ${response.status} in ${responseInfo.durationMs}ms`);
    this.config.onResponse?.(responseInfo);

    if (!response.ok) {
      const error = this.createHttpError(response.status, requestId, await response.text());
      this.config.onError?.(error);
      throw error;
    }

    if (!response.body) {
      const error = new AmplifierError("No response body", ErrorCode.StreamError, { requestId });
      this.config.onError?.(error);
      throw error;
    }

    // Stream events
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data:")) continue;

          const dataStr = trimmed.slice(5).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            for (const event of this.parseEvent(data)) {
              this.debug(`[${requestId}] Event: ${event.type}`);
              this.config.onEvent?.(event);
              
              // Intercept client-side tool calls
              if (event.type === "tool.call") {
                const toolName = event.data.tool_name as string;
                const toolCallId = event.toolCallId || (event.data.tool_call_id as string);
                
                // Check if this is a client-side tool
                if (this.clientTools.has(toolName)) {
                  this.debug(`[${requestId}] Intercepting client-side tool: ${toolName}`);
                  
                  // Execute the tool locally
                  try {
                    const args = (event.data.arguments as Record<string, unknown>) || {};
                    const result = await this.executeClientTool(toolName, args);
                    
                    // Send result back to server
                    await this.request("POST", `/v1/session/${sessionId}/tool-result`, {
                      tool_call_id: toolCallId,
                      result,
                    });
                    
                    this.debug(`[${requestId}] Client-side tool result sent: ${toolName}`);
                  } catch (err) {
                    const error = err as Error;
                    this.debug(`[${requestId}] Client-side tool error: ${toolName} - ${error.message}`);
                    
                    // Send error back to server
                    await this.request("POST", `/v1/session/${sessionId}/tool-result`, {
                      tool_call_id: toolCallId,
                      error: error.message,
                    });
                  }
                  
                  // Don't yield the tool.call event - it's handled
                  continue;
                }
              }

              // Handle approval requests with registered handler
              if (event.type === "approval.required" && this.approvalHandler) {
                const requestId = event.data.request_id as string;
                const prompt = event.data.prompt as string;
                const toolName = event.data.tool_name as string | undefined;
                const args = event.data.arguments as Record<string, unknown> | undefined;

                try {
                  const approved = await this.approvalHandler({
                    requestId,
                    prompt,
                    toolName,
                    arguments: args,
                  });

                  // Automatically respond to approval
                  await this.respondApproval(sessionId, requestId, approved.toString());
                  this.debug(`[${requestId}] Auto-responded to approval: ${approved}`);
                } catch (err) {
                  console.error("Approval handler error:", err);
                }
              }
              
              // Emit to registered event handlers (includes agent-specific handling)
              await this.emitEvent(event);
              
              yield event;
            }
          } catch {
            // Skip invalid JSON
          }
        }
      }
    } catch (err) {
      const error = this.wrapError(err, requestId);
      this.config.onError?.(error);
      throw error;
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Send a prompt and wait for complete response.
   */
  async promptSync(sessionId: string, content: string): Promise<PromptResponse> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!content || typeof content !== "string") {
      throw new AmplifierError(
        "Prompt content is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    const data = await this.request("POST", `/v1/session/${sessionId}/prompt/sync`, { content });
    return this.parsePromptResponse(data as Record<string, unknown>);
  }

  /**
   * Cancel ongoing execution.
   */
  async cancel(sessionId: string): Promise<boolean> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    try {
      await this.request("POST", `/v1/session/${sessionId}/cancel`);
      return true;
    } catch {
      return false;
    }
  }

  // ===========================================================================
  // Client-Side Tools
  // ===========================================================================

  /**
   * Register a client-side tool.
   * 
   * Client-side tools run in your app (not on the server) and give the AI
   * access to your local APIs, databases, and services.
   * 
   * @example
   * ```typescript
   * client.registerTool({
   *   name: "get-customer",
   *   description: "Get customer information by ID",
   *   parameters: {
   *     type: "object",
   *     properties: {
   *       customerId: { type: "string" }
   *     },
   *     required: ["customerId"]
   *   },
   *   handler: async ({ customerId }) => {
   *     return await yourAPI.getCustomer(customerId);
   *   }
   * });
   * ```
   */
  registerTool(tool: ClientTool): void {
    if (!tool || typeof tool !== "object") {
      throw new AmplifierError(
        "Tool must be an object",
        ErrorCode.BadRequest
      );
    }
    if (!tool.name || typeof tool.name !== "string") {
      throw new AmplifierError(
        "Tool name is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!tool.description || typeof tool.description !== "string") {
      throw new AmplifierError(
        "Tool description is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!tool.handler || typeof tool.handler !== "function") {
      throw new AmplifierError(
        "Tool handler is required and must be a function",
        ErrorCode.BadRequest
      );
    }

    this.clientTools.set(tool.name, tool);
    this.debug(`Registered client-side tool: ${tool.name}`);
  }

  /**
   * Unregister a client-side tool.
   */
  unregisterTool(name: string): boolean {
    const removed = this.clientTools.delete(name);
    if (removed) {
      this.debug(`Unregistered client-side tool: ${name}`);
    }
    return removed;
  }

  /**
   * Get all registered client-side tools.
   */
  getClientTools(): ClientTool[] {
    return Array.from(this.clientTools.values());
  }

  /**
   * Execute a client-side tool handler.
   */
  private async executeClientTool(
    toolName: string,
    args: Record<string, unknown>
  ): Promise<unknown> {
    const tool = this.clientTools.get(toolName);
    if (!tool) {
      throw new Error(`Client tool not found: ${toolName}`);
    }

    try {
      this.debug(`Executing client-side tool: ${toolName}`);
      const result = await tool.handler(args);
      return result;
    } catch (err) {
      const error = err as Error;
      this.debug(`Client tool error: ${toolName} - ${error.message}`);
      throw error;
    }
  }

  // ===========================================================================
  // Event Handlers (Convenience API)
  // ===========================================================================

  /**
   * Register an event handler.
   * 
   * @example
   * ```typescript
   * client.on("tool.call", (event) => {
   *   console.log(`Calling tool: ${event.data.tool_name}`);
   * });
   * 
   * client.on("content.delta", (event) => {
   *   process.stdout.write(event.data.delta);
   * });
   * ```
   */
  on(eventType: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  /**
   * Unregister an event handler.
   */
  off(eventType: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Register a one-time event handler.
   */
  once(eventType: string, handler: EventHandler): void {
    const wrappedHandler: EventHandler = (event) => {
      handler(event);
      this.off(eventType, wrappedHandler);
    };
    this.on(eventType, wrappedHandler);
  }

  /**
   * Emit event to registered handlers.
   * Handles both generic event handlers and agent-specific handlers.
   */
  private async emitEvent(event: Partial<Event>): Promise<void> {
    // Handle agent-specific events first (updates hierarchy + calls specific handlers)
    if (event.type === "agent.spawned") {
      await this.handleAgentSpawned(event as Event);
    } else if (event.type === "agent.completed") {
      await this.handleAgentCompleted(event as Event);
    } else if (event.type === "thinking.delta") {
      await this.handleThinking(event as Event);
    }
    
    // Then call generic event handlers
    const handlers = this.eventHandlers.get(event.type!);
    if (handlers) {
      // Convert Set to Array for iteration (TS compatibility)
      for (const handler of Array.from(handlers)) {
        try {
          await handler(event as Event);
        } catch (err) {
          console.error(`Event handler error for ${event.type}:`, err);
        }
      }
    }
  }

  /**
   * Handle agent.spawned event and update hierarchy.
   */
  private async handleAgentSpawned(event: Event): Promise<void> {
    // Type guard - this should only be called for agent.spawned events
    if (event.type !== "agent.spawned") return;
    
    const data = event.data;
    const agentId = data.agent_id as string;
    const agentName = data.agent_name as string;
    const parentId = (data.parent_id as string | undefined) ?? null;
    const timestamp = event.timestamp ?? new Date().toISOString();

    // Validate required fields
    if (!agentId) {
      this.debug("Warning: agent.spawned event missing agent_id, skipping hierarchy update");
      return;
    }

    // Update or create agent node
    const existingNode = this.agentHierarchy.get(agentId);
    const node: AgentNode = {
      agentId,
      agentName: agentName || existingNode?.agentName || "unknown",
      parentId,
      children: existingNode?.children ?? [],
      spawnedAt: existingNode?.spawnedAt ?? timestamp,
      completedAt: existingNode?.completedAt ?? null,
      result: existingNode?.result,
      error: existingNode?.error,
    };

    this.agentHierarchy.set(agentId, node);

    // Update parent's children list
    if (parentId) {
      const parent = this.agentHierarchy.get(parentId);
      if (parent && !parent.children.includes(agentId)) {
        parent.children.push(agentId);
      } else if (!parent) {
        // Create placeholder parent if it doesn't exist yet
        const placeholderParent: AgentNode = {
          agentId: parentId,
          agentName: "unknown",
          parentId: null,
          children: [agentId],
          spawnedAt: timestamp,
          completedAt: null,
        };
        this.agentHierarchy.set(parentId, placeholderParent);
      }
    }

    // Call registered handlers
    const info = {
      agentId,
      agentName: node.agentName,
      parentId,
      timestamp,
    };

    for (const handler of Array.from(this.agentSpawnedHandlers)) {
      try {
        await handler(info);
      } catch (err) {
        console.error("Agent spawned handler error:", err);
      }
    }
  }

  /**
   * Handle agent.completed event and update hierarchy.
   */
  private async handleAgentCompleted(event: Event): Promise<void> {
    // Type guard - this should only be called for agent.completed events
    if (event.type !== "agent.completed") return;
    
    const data = event.data;
    const agentId = data.agent_id as string;
    const result = data.result as string | undefined;
    const error = data.error as string | undefined;
    const timestamp = event.timestamp ?? new Date().toISOString();

    // Validate required fields
    if (!agentId) {
      this.debug("Warning: agent.completed event missing agent_id, skipping hierarchy update");
      return;
    }

    // Update existing node or create if completion came before spawn
    const existingNode = this.agentHierarchy.get(agentId);
    if (existingNode) {
      existingNode.completedAt = timestamp;
      existingNode.result = result;
      existingNode.error = error;
    } else {
      // Completion before spawn - create node with completion data
      const node: AgentNode = {
        agentId,
        agentName: "unknown",
        parentId: null,
        children: [],
        spawnedAt: timestamp,
        completedAt: timestamp,
        result,
        error,
      };
      this.agentHierarchy.set(agentId, node);
    }

    // Call registered handlers
    const info = {
      agentId,
      result,
      error,
      timestamp,
    };

    for (const handler of Array.from(this.agentCompletedHandlers)) {
      try {
        await handler(info);
      } catch (err) {
        console.error("Agent completed handler error:", err);
      }
    }
  }

  // ===========================================================================
  // Approval System
  // ===========================================================================

  /**
   * Respond to an approval request.
   */
  async respondApproval(
    sessionId: string,
    requestId: string,
    choice: string
  ): Promise<boolean> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new AmplifierError(
        "Session ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!requestId || typeof requestId !== "string") {
      throw new AmplifierError(
        "Request ID is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    if (!choice || typeof choice !== "string") {
      throw new AmplifierError(
        "Choice is required and must be a string",
        ErrorCode.BadRequest
      );
    }
    try {
      await this.request("POST", `/v1/session/${sessionId}/approval`, {
        request_id: requestId,
        choice,
      });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Register an approval handler (convenience method).
   * 
   * When the AI requests approval, your handler will be called automatically.
   * Return true to approve, false to deny.
   * 
   * @example
   * ```typescript
   * client.onApproval(async (request) => {
   *   const userChoice = await showDialog({
   *     title: "Permission Required",
   *     message: request.prompt,
   *     tool: request.toolName
   *   });
   *   return userChoice; // true = approve, false = deny
   * });
   * ```
   */
  onApproval(handler: ApprovalHandler): void {
    this.approvalHandler = handler;
  }

  // ===========================================================================
  // Agent Spawning Visibility
  // ===========================================================================

  /**
   * Register a handler for agent spawned events.
   * 
   * Called when the AI delegates to a sub-agent. Provides agent ID, name,
   * and parent ID for tracking the agent hierarchy.
   * 
   * @example
   * ```typescript
   * client.onAgentSpawned((info) => {
   *   console.log(`🤖 Agent spawned: ${info.agentName} (${info.agentId})`);
   *   if (info.parentId) {
   *     console.log(`   Parent: ${info.parentId}`);
   *   }
   * });
   * ```
   * 
   * @param handler - Callback function for agent spawned events
   */
  onAgentSpawned(handler: AgentSpawnedHandler): void {
    this.agentSpawnedHandlers.add(handler);
  }

  /**
   * Unregister an agent spawned handler.
   * 
   * @param handler - Handler to remove
   */
  offAgentSpawned(handler: AgentSpawnedHandler): void {
    this.agentSpawnedHandlers.delete(handler);
  }

  /**
   * Register a handler for agent completed events.
   * 
   * Called when a sub-agent finishes execution. Provides result or error.
   * 
   * @example
   * ```typescript
   * client.onAgentCompleted((info) => {
   *   console.log(`✅ Agent completed: ${info.agentId}`);
   *   if (info.error) {
   *     console.error(`   Error: ${info.error}`);
   *   } else if (info.result) {
   *     console.log(`   Result: ${info.result}`);
   *   }
   * });
   * ```
   * 
   * @param handler - Callback function for agent completed events
   */
  onAgentCompleted(handler: AgentCompletedHandler): void {
    this.agentCompletedHandlers.add(handler);
  }

  /**
   * Unregister an agent completed handler.
   * 
   * @param handler - Handler to remove
   */
  offAgentCompleted(handler: AgentCompletedHandler): void {
    this.agentCompletedHandlers.delete(handler);
  }

  /**
   * Get the current agent hierarchy.
   * 
   * Returns a map of agent IDs to AgentNode objects, representing the
   * parent/child relationships between agents spawned during this session.
   * 
   * @example
   * ```typescript
   * const hierarchy = client.getAgentHierarchy();
   * 
   * // Find root agents (no parent)
   * const rootAgents = Array.from(hierarchy.values())
   *   .filter(node => node.parentId === null);
   * 
   * // Build tree visualization
   * function printTree(agentId: string, indent = 0) {
   *   const node = hierarchy.get(agentId);
   *   if (!node) return;
   *   
   *   console.log('  '.repeat(indent) + `${node.agentName} (${node.agentId})`);
   *   node.children.forEach(childId => printTree(childId, indent + 1));
   * }
   * rootAgents.forEach(node => printTree(node.agentId));
   * ```
   * 
   * @returns Map of agent IDs to AgentNode objects
   */
  getAgentHierarchy(): Map<string, AgentNode> {
    return new Map(this.agentHierarchy);
  }

  /**
   * Clear the agent hierarchy.
   * 
   * Useful when starting a new prompt or resetting state.
   */
  clearAgentHierarchy(): void {
    this.agentHierarchy.clear();
  }

  // ===========================================================================
  // Thinking Stream Helpers
  // ===========================================================================

  /**
   * Handle thinking.delta event and update state.
   */
  private async handleThinking(event: Event): Promise<void> {
    if (event.type !== "thinking.delta") return;

    const delta = event.data.delta as string;
    
    // Update thinking state
    if (!this.isThinking) {
      this.isThinking = true;
      this.currentThinkingContent = "";
    }
    
    this.currentThinkingContent += delta;

    // Call registered handlers
    const thinkingState: ThinkingState = {
      isThinking: this.isThinking,
      content: this.currentThinkingContent
    };

    for (const handler of Array.from(this.thinkingHandlers)) {
      try {
        await handler(thinkingState);
      } catch (err) {
        console.error("Thinking handler error:", err);
      }
    }
  }

  /**
   * Register thinking event handler (convenience method).
   * 
   * Subscribe to AI reasoning/thinking events with automatic state tracking.
   * 
   * @example
   * ```typescript
   * client.onThinking((thinking) => {
   *   if (thinking.isThinking) {
   *     showThinkingPanel(thinking.content);
   *   } else {
   *     hideThinkingPanel();
   *   }
   * });
   * ```
   */
  onThinking(handler: ThinkingHandler): void {
    this.thinkingHandlers.add(handler);
  }

  /**
   * Unregister thinking handler.
   */
  offThinking(handler: ThinkingHandler): void {
    this.thinkingHandlers.delete(handler);
  }

  /**
   * Get current thinking state.
   */
  getThinkingState(): ThinkingState {
    return {
      isThinking: this.isThinking,
      content: this.currentThinkingContent
    };
  }

  /**
   * Clear thinking state.
   * 
   * Useful when starting a new prompt or when thinking completes.
   */
  clearThinkingState(): void {
    this.isThinking = false;
    this.currentThinkingContent = "";
  }

  // ===========================================================================
  // Client-Side Behaviors
  // ===========================================================================

  /**
   * Define a reusable behavior.
   * 
   * Behaviors are capability packages that can be composed into bundles.
   * 
   * @example
   * ```typescript
   * const customerSupport = client.defineBehavior({
   *   name: "customer-support",
   *   instructions: "Help customers with orders and returns",
   *   clientTools: ["get-order", "process-refund"]
   * });
   * 
   * // Use in session
   * const session = await client.createSession({
   *   bundle: {
   *     name: "support-agent",
   *     behaviors: ["customer-support"]
   *   }
   * });
   * ```
   */
  defineBehavior(behavior: BehaviorDefinition): BehaviorDefinition {
    if (!behavior.name) {
      throw new AmplifierError(
        "Behavior name is required",
        ErrorCode.BadRequest
      );
    }
    
    this.behaviors.set(behavior.name, behavior);
    this.debug(`Defined behavior: ${behavior.name}`);
    return behavior;
  }

  /**
   * Get a defined behavior by name.
   */
  getBehavior(name: string): BehaviorDefinition | undefined {
    return this.behaviors.get(name);
  }

  /**
   * Get all defined behaviors.
   */
  getBehaviors(): BehaviorDefinition[] {
    return Array.from(this.behaviors.values());
  }

  /**
   * Remove a behavior definition.
   */
  removeBehavior(name: string): boolean {
    return this.behaviors.delete(name);
  }

  /**
   * Merge multiple behaviors into a single bundle configuration.
   * 
   * @internal Used by createSession when behaviors are specified
   */
  private mergeBehaviors(
    base: BundleDefinition,
    behaviorNames: string[]
  ): BundleDefinition {
    const merged = { ...base };

    for (const behaviorName of behaviorNames) {
      const behavior = this.behaviors.get(behaviorName);
      if (!behavior) {
        throw new AmplifierError(
          `Behavior '${behaviorName}' not found. Define it with defineBehavior() first.`,
          ErrorCode.BadRequest
        );
      }

      // Merge instructions (concatenate with newlines)
      if (behavior.instructions) {
        merged.instructions = merged.instructions
          ? `${merged.instructions}\n\n${behavior.instructions}`
          : behavior.instructions;
      }

      // Merge tools (deduplicate by module name)
      if (behavior.tools) {
        merged.tools = merged.tools || [];
        const existingModules = new Set(merged.tools.map((t: ModuleConfig) => t.module));
        for (const tool of behavior.tools) {
          if (!existingModules.has(tool.module)) {
            merged.tools.push(tool);
          }
        }
      }

      // Merge clientTools (deduplicate)
      if (behavior.clientTools) {
        merged.clientTools = merged.clientTools || [];
        const existingClientTools = new Set(merged.clientTools);
        for (const tool of behavior.clientTools) {
          if (!existingClientTools.has(tool)) {
            merged.clientTools.push(tool);
          }
        }
      }

      // Merge providers (take first of each provider type)
      if (behavior.providers) {
        merged.providers = merged.providers || [];
        const existingProviders = new Set(merged.providers.map((p: ModuleConfig) => p.module));
        for (const provider of behavior.providers) {
          if (!existingProviders.has(provider.module)) {
            merged.providers.push(provider);
          }
        }
      }

      // Merge hooks
      if (behavior.hooks) {
        merged.hooks = merged.hooks || [];
        const existingHooks = new Set(merged.hooks.map((h: ModuleConfig) => h.module));
        for (const hook of behavior.hooks) {
          if (!existingHooks.has(hook.module)) {
            merged.hooks.push(hook);
          }
        }
      }
    }

    return merged;
  }

  // ===========================================================================
  // Recipe Management
  // ===========================================================================

  /**
   * Create a new recipe builder.
   * 
   * @example
   * ```typescript
   * const recipe = client.recipe("code-review")
   *   .description("Automated code review workflow")
   *   .version("1.0.0")
   *   .step("analyze", (step) => 
   *     step.agent("foundation:zen-architect").prompt("Analyze code")
   *   )
   *   .build();
   * 
   * await client.saveRecipe(recipe);
   * ```
   */
  recipe(name: string): RecipeBuilder {
    return new RecipeBuilder(name);
  }

  /**
   * Save a recipe definition (stores locally in SDK).
   */
  saveRecipe(recipe: RecipeDefinition): void {
    if (!recipe.name) {
      throw new AmplifierError("Recipe name is required", ErrorCode.BadRequest);
    }
    this.recipes.set(recipe.name, recipe);
    this.debug(`Saved recipe: ${recipe.name} v${recipe.version}`);
  }

  /**
   * Get a saved recipe by name.
   */
  getRecipe(name: string): RecipeDefinition | undefined {
    return this.recipes.get(name);
  }

  /**
   * List all saved recipes.
   */
  getRecipes(): RecipeDefinition[] {
    return Array.from(this.recipes.values());
  }

  /**
   * Delete a saved recipe.
   */
  deleteRecipe(name: string): boolean {
    return this.recipes.delete(name);
  }

  /**
   * Execute a recipe by name or path.
   * 
   * @param recipePathOrName - Recipe name (from saved recipes) or path (YAML file)
   * @param context - Context variables for the recipe
   * @param sessionId - Optional session ID to use (creates new session if not provided)
   * 
   * @example
   * ```typescript
   * // Execute saved recipe
   * const execution = await client.executeRecipe("code-review", {
   *   file_path: "src/auth.ts",
   *   severity: "high"
   * });
   * 
   * // Execute recipe from file
   * const execution = await client.executeRecipe("@recipes:code-review.yaml", {
   *   file_path: "src/auth.ts"
   * });
   * 
   * // Monitor progress
   * execution.on("step.started", (step) => console.log(`Step: ${step.step_id}`));
   * ```
   */
  async executeRecipe(
    recipePathOrName: string,
    context: Record<string, any> = {},
    sessionId?: string
  ): Promise<RecipeExecution> {
    
    // Determine if it's a saved recipe or a path
    const savedRecipe = this.recipes.get(recipePathOrName);
    const recipePath = savedRecipe ? undefined : recipePathOrName;
    
    // Create session if not provided (with foundation bundle for recipes tool)
    const sid = sessionId ?? (await this.createSession({ bundle: "foundation" })).id;
    
    // Build prompt to execute recipe
    let prompt = "";
    if (savedRecipe) {
      // For saved recipes, we need to convert to YAML and execute
      // For now, use the runtime's recipes tool with the name
      prompt = `Execute the recipe "${recipePathOrName}" using the recipes tool.`;
    } else {
      // For recipe paths, ask runtime to execute
      prompt = `Execute the recipe at "${recipePath}" using the recipes tool.`;
    }
    
    // Add context if provided
    if (Object.keys(context).length > 0) {
      const contextStr = Object.entries(context)
        .map(([k, v]) => `${k}="${v}"`)
        .join(", ");
      prompt += ` Pass these context variables: ${contextStr}.`;
    }
    
    // Create execution monitor
    const execution = new RecipeExecution(this, sid, recipePathOrName);
    
    // Start execution in background
    (async () => {
      try {
        for await (const event of this.prompt(sid, prompt)) {
          execution.handleEvent(event);
        }
      } catch (error) {
        execution.handleError(error as Error);
      }
    })();
    
    return execution;
  }

  /**
   * List active recipe sessions.
   * 
   * @example
   * ```typescript
   * const sessions = await client.listRecipeSessions();
   * for (const session of sessions) {
   *   console.log(`${session.recipe_name}: ${session.status}`);
   * }
   * ```
   */
  async listRecipeSessions(): Promise<import("./recipes").RecipeSession[]> {
    // Use recipes tool to list sessions
    const session = await this.createSession({});
    
    try {
      // For now, return empty list
      // Real implementation would parse AI response
      return [];
    } finally {
      await this.deleteSession(session.id);
    }
  }

  /**
   * Resume an interrupted recipe.
   * 
   * @param sessionId - Recipe session ID to resume
   * 
   * @example
   * ```typescript
   * const execution = await client.resumeRecipe("recipe_session_123");
   * execution.on("step.completed", (step) => console.log(`Resumed: ${step.step_id}`));
   * ```
   */
  async resumeRecipe(sessionId: string): Promise<RecipeExecution> {
    // Verify session exists
    await this.getSession(sessionId);
    
    // Create execution monitor for existing session
    const execution = new RecipeExecution(this, sessionId, "resumed");
    
    // Resume execution
    const prompt = "Resume the recipe execution from where it left off.";
    
    (async () => {
      try {
        for await (const event of this.prompt(sessionId, prompt)) {
          execution.handleEvent(event);
        }
      } catch (error) {
        execution.handleError(error as Error);
      }
    })();
    
    return execution;
  }

  /**
   * Approve a recipe stage/step.
   * 
   * @param sessionId - Recipe session ID
   * @param stageName - Name of the stage to approve
   * 
   * @example
   * ```typescript
   * await client.approveRecipeStage(sessionId, "deploy-to-production");
   * ```
   */
  async approveRecipeStage(sessionId: string, stageName: string): Promise<void> {
    const prompt = `Approve the "${stageName}" stage in the current recipe execution.`;
    await this.promptSync(sessionId, prompt);
  }

  /**
   * Deny a recipe stage/step.
   * 
   * @param sessionId - Recipe session ID
   * @param stageName - Name of the stage to deny
   * @param reason - Optional reason for denial
   * 
   * @example
   * ```typescript
   * await client.denyRecipeStage(sessionId, "deploy", "Tests are failing");
   * ```
   */
  async denyRecipeStage(
    sessionId: string,
    stageName: string,
    reason?: string
  ): Promise<void> {
    let prompt = `Deny the "${stageName}" stage in the current recipe execution.`;
    if (reason) {
      prompt += ` Reason: ${reason}`;
    }
    await this.promptSync(sessionId, prompt);
  }

  /**
   * Cancel a running recipe.
   * 
   * @param sessionId - Recipe session ID to cancel
   * 
   * @example
   * ```typescript
   * await client.cancelRecipe(sessionId);
   * ```
   */
  async cancelRecipe(sessionId: string): Promise<void> {
    // Send cancel command
    const prompt = "Cancel the current recipe execution.";
    await this.promptSync(sessionId, prompt);
    
    // Clean up session
    await this.deleteSession(sessionId);
  }

  // ===========================================================================
  // Convenience Methods
  // ===========================================================================

  /**
   * One-shot execution: create session, run prompt, return response.
   */
  async run(content: string, config: SessionConfig = {}): Promise<PromptResponse> {
    const session = await this.createSession(config);
    try {
      return await this.promptSync(session.id, content);
    } finally {
      await this.deleteSession(session.id);
    }
  }

  /**
   * One-shot streaming: create session, stream prompt, cleanup.
   */
  async *stream(content: string, config: SessionConfig = {}): AsyncGenerator<Event> {
    const session = await this.createSession(config);
    try {
      yield* this.prompt(session.id, content);
    } finally {
      await this.deleteSession(session.id);
    }
  }

  // ===========================================================================
  // Private: HTTP Request with Observability
  // ===========================================================================

  private async request(
    method: string,
    path: string,
    body?: unknown
  ): Promise<unknown> {
    const requestId = generateRequestId();
    const url = `${this.baseUrl}${path}`;
    const startTime = Date.now();

    // Emit request info
    const requestInfo: RequestInfo = {
      requestId,
      method,
      url,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body,
      timestamp: new Date(),
    };
    this.debug(`[${requestId}] ${method} ${url}`);
    this.config.onRequest?.(requestInfo);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(this.timeout),
      });
    } catch (err) {
      const error = this.wrapError(err, requestId);
      this.config.onError?.(error);
      throw error;
    }

    const durationMs = Date.now() - startTime;

    // Parse response
    let responseBody: unknown;
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      responseBody = await response.json();
    } else {
      responseBody = await response.text();
    }

    // Emit response info
    const responseInfo: ResponseInfo = {
      requestId,
      status: response.status,
      body: responseBody,
      durationMs,
      timestamp: new Date(),
    };
    this.debug(`[${requestId}] ${response.status} in ${durationMs}ms`);
    this.config.onResponse?.(responseInfo);

    if (!response.ok) {
      const error = this.createHttpError(
        response.status,
        requestId,
        typeof responseBody === "string" ? responseBody : JSON.stringify(responseBody)
      );
      this.config.onError?.(error);
      throw error;
    }

    return responseBody;
  }

  // ===========================================================================
  // Private: Error Handling
  // ===========================================================================

  private createHttpError(status: number, requestId: string, body?: string): AmplifierError {
    const codeMap: Record<number, ErrorCode> = {
      400: ErrorCode.BadRequest,
      401: ErrorCode.Unauthorized,
      403: ErrorCode.Forbidden,
      404: ErrorCode.NotFound,
      500: ErrorCode.ServerError,
      502: ErrorCode.ServerError,
      503: ErrorCode.ServerError,
    };

    const code = codeMap[status] ?? ErrorCode.Unknown;
    const message = body || `HTTP ${status}`;

    return new AmplifierError(message, code, { status, requestId });
  }

  private wrapError(err: unknown, requestId: string): AmplifierError {
    if (err instanceof AmplifierError) {
      return err;
    }

    const error = err as Error;
    const message = error?.message ?? String(err);

    // Detect specific error types
    if (message.includes("timeout") || message.includes("aborted")) {
      return new AmplifierError(message, ErrorCode.Timeout, { requestId, cause: error });
    }
    if (message.includes("ECONNREFUSED") || message.includes("fetch failed")) {
      return new AmplifierError(message, ErrorCode.ConnectionRefused, { requestId, cause: error });
    }

    return new AmplifierError(message, ErrorCode.NetworkError, { requestId, cause: error });
  }

  // ===========================================================================
  // Private: Parsing Helpers
  // ===========================================================================

  private parseSessionInfo(data: Record<string, unknown>): SessionInfo {
    return {
      id: (data.id ?? data.session_id ?? "") as string,
      title: (data.title ?? "") as string,
      bundle: (data.bundle ?? undefined) as string | undefined,
      createdAt: (data.created_at ?? "") as string,
      updatedAt: (data.updated_at ?? "") as string,
      state: (data.state ?? "ready") as string,
    };
  }

  private parseEvent(data: Record<string, unknown>): Event[] {
    const eventData = (data.data ?? {}) as Record<string, unknown>;
    const eventType = (data.type ?? "") as string;

    const baseEvent: Event = {
      type: eventType,
      data: eventData,
      id: data.id as string | undefined,
      correlationId: data.correlation_id as string | undefined,
      sequence: data.sequence as number | undefined,
      final: (data.final ?? false) as boolean,
      timestamp: data.timestamp as string | undefined,
      // Extract tool_call_id from data for correlation
      toolCallId: eventData.tool_call_id as string | undefined,
      // Extract agent_id from data for parent/child distinction
      agentId: eventData.agent_id as string | undefined,
    };

    // Server sends full content in content.end - emit synthetic content.delta for streaming UX
    if (eventType === "content.end" && eventData.content) {
      const deltaEvent: Event = {
        ...baseEvent,
        type: "content.delta",
        data: { delta: eventData.content },
      };
      return [deltaEvent, baseEvent];
    }

    return [baseEvent];
  }

  private parsePromptResponse(data: Record<string, unknown>): PromptResponse {
    const toolCalls = ((data.tool_calls ?? []) as Record<string, unknown>[]).map(
      (tc): ToolCall => ({
        toolName: (tc.tool_name ?? "") as string,
        toolCallId: (tc.tool_call_id ?? "") as string,
        arguments: (tc.arguments ?? {}) as Record<string, unknown>,
        output: tc.output,
      })
    );

    return {
      content: (data.content ?? "") as string,
      toolCalls,
      sessionId: (data.session_id ?? "") as string,
      stopReason: (data.stop_reason ?? "") as string,
    };
  }

  private serializeBundleDefinition(
    bundle: import("./types").BundleDefinition
  ): Record<string, unknown> {
    // Transform clientTools from names to full schemas
    const clientToolSchemas = bundle.clientTools?.map((toolName) => {
      const tool = this.clientTools.get(toolName);
      if (!tool) {
        this.debug(`Warning: Client tool "${toolName}" referenced but not registered`);
        // Return basic schema if tool not registered yet
        return { name: toolName };
      }
      
      // Send full schema so LLM knows about the tool
      return {
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters || {},
      };
    });
    
    return {
      name: bundle.name,
      version: bundle.version ?? "1.0.0",
      description: bundle.description,
      providers: bundle.providers,
      tools: bundle.tools,
      clientTools: clientToolSchemas,  // Full schemas, not just names!
      hooks: bundle.hooks,
      orchestrator: bundle.orchestrator,
      context: bundle.context,
      mcpServers: bundle.mcpServers,
      agents: bundle.agents?.map((a) => ({
        name: a.name,
        description: a.description,
        instructions: a.instructions,
        tools: a.tools,
      })),
      instructions: bundle.instructions,
      session: bundle.session,
      includes: bundle.includes,
    };
  }

  // ===========================================================================
  // Private: Debug Logging
  // ===========================================================================

  private debug(message: string): void {
    if (this.config.debug) {
      console.log(`[AmplifierSDK] ${message}`);
    }
  }
}

/**
 * Quick one-shot execution.
 *
 * @example
 * ```typescript
 * import { run } from "amplifier-sdk";
 *
 * const response = await run("What is 2+2?");
 * console.log(response.content);
 * ```
 */
export async function run(
  content: string,
  config: SessionConfig & ClientConfig = {}
): Promise<PromptResponse> {
  const client = new AmplifierClient(config);
  return client.run(content, config);
}
