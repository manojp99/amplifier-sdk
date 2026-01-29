/**
 * HTTP client for Amplifier server.
 */

import type {
  AgentInfo,
  ApprovalInfo,
  ClientOptions,
  CreateAgentOptions,
  ExecuteRecipeOptions,
  HealthResponse,
  Message,
  ModulesResponse,
  RecipeExecution,
  RunOnceOptions,
  RunOptions,
  RunResponse,
  SpawnOptions,
  StreamEvent,
  SubAgentInfo,
} from './types';

export class AmplifierClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  /**
   * Create a new Amplifier client.
   *
   * @example
   * ```typescript
   * const client = new AmplifierClient({
   *   baseUrl: 'http://localhost:8000'
   * });
   *
   * // Create agent with full module wiring
   * const agentId = await client.createAgent({
   *   instructions: 'You are helpful.',
   *   provider: 'anthropic',
   *   model: 'claude-sonnet-4-20250514',
   *   tools: ['bash', 'filesystem'],
   *   orchestrator: 'streaming',
   *   hooks: ['logging'],
   *   agents: {
   *     researcher: {
   *       instructions: 'You research topics.',
   *       tools: ['web_search']
   *     }
   *   }
   * });
   *
   * // Run prompt
   * const response = await client.run(agentId, 'Hello!');
   * console.log(response.content);
   *
   * // Spawn sub-agent
   * const subAgentId = await client.spawnAgent(agentId, {
   *   agentName: 'researcher',
   *   prompt: 'Research Python async'
   * });
   *
   * // Stream with rich events
   * for await (const event of client.stream(agentId, 'Write a poem')) {
   *   if (event.event === 'content:delta') {
   *     process.stdout.write(event.data.text as string);
   *   } else if (event.event === 'tool:start') {
   *     console.log(`\nUsing tool: ${event.data.tool}`);
   *   }
   * }
   *
   * // Execute recipe
   * const execution = await client.executeRecipe({
   *   recipe: {
   *     name: 'analysis',
   *     steps: [
   *       { id: 'step1', agent: 'analyzer', prompt: 'Analyze this' }
   *     ]
   *   },
   *   input: { topic: 'AI' }
   * });
   *
   * // Cleanup
   * await client.deleteAgent(agentId);
   * ```
   */
  constructor(options: ClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? 'http://localhost:8000').replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 300000;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: this.getHeaders(),
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP ${response.status}: ${error}`);
      }

      return (await response.json()) as T;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ===========================================================================
  // Health & Modules
  // ===========================================================================

  /**
   * Check server health.
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/health');
  }

  /**
   * List available modules.
   */
  async listModules(): Promise<ModulesResponse> {
    return this.request<ModulesResponse>('GET', '/modules');
  }

  // ===========================================================================
  // Agent CRUD
  // ===========================================================================

  /**
   * Create a new agent with full module wiring support.
   */
  async createAgent(options: CreateAgentOptions): Promise<string> {
    const payload = {
      instructions: options.instructions,
      provider: options.provider ?? 'anthropic',
      providers: options.providers,
      model: options.model,
      tools: options.tools ?? [],
      orchestrator: options.orchestrator ?? 'basic',
      context_manager: options.contextManager ?? 'simple',
      hooks: options.hooks ?? [],
      approval: options.approval,
      agents: options.agents,
      config: options.config ?? {},
    };

    const response = await this.request<{ agent_id: string }>('POST', '/agents', payload);
    return response.agent_id;
  }

  /**
   * Get agent information.
   */
  async getAgent(agentId: string): Promise<AgentInfo> {
    return this.request<AgentInfo>('GET', `/agents/${agentId}`);
  }

  /**
   * List all agent IDs.
   */
  async listAgents(): Promise<string[]> {
    const response = await this.request<{ agents: string[] }>('GET', '/agents');
    return response.agents;
  }

  /**
   * Delete an agent.
   */
  async deleteAgent(agentId: string): Promise<void> {
    await this.request<{ deleted: boolean }>('DELETE', `/agents/${agentId}`);
  }

  // ===========================================================================
  // Execution
  // ===========================================================================

  /**
   * Run a prompt and get response.
   */
  async run(
    agentId: string,
    prompt: string,
    options: RunOptions = {}
  ): Promise<RunResponse> {
    return this.request<RunResponse>('POST', `/agents/${agentId}/run`, {
      prompt,
      max_turns: options.maxTurns ?? 10,
    });
  }

  /**
   * Stream a prompt response with rich event taxonomy.
   *
   * Events include:
   * - session:start/end - Session lifecycle
   * - prompt:start/complete - Prompt processing
   * - content:start/delta/complete - Content streaming
   * - tool:start/result - Tool execution
   * - agent:spawn/complete - Sub-agent spawning
   * - approval:requested/responded - Human-in-loop
   * - done - Execution complete
   */
  async *stream(
    agentId: string,
    prompt: string,
    options: RunOptions = {}
  ): AsyncGenerator<StreamEvent> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const payload: Record<string, unknown> = {
        prompt,
        max_turns: options.maxTurns ?? 10,
      };
      if (options.streamEvents) {
        payload.stream_events = options.streamEvents;
      }

      const response = await fetch(`${this.baseUrl}/agents/${agentId}/stream`, {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP ${response.status}: ${error}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue;

          if (trimmedLine.startsWith('event:')) {
            currentEvent = trimmedLine.slice(6).trim();
          } else if (trimmedLine.startsWith('data:')) {
            const dataStr = trimmedLine.slice(5).trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                yield { event: currentEvent, data };
              } catch {
                // Skip invalid JSON
              }
            }
          }
        }
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ===========================================================================
  // Multi-Agent Orchestration
  // ===========================================================================

  /**
   * Spawn a sub-agent from a parent agent.
   */
  async spawnAgent(parentId: string, options: SpawnOptions): Promise<string> {
    const payload = {
      agent_name: options.agentName,
      prompt: options.prompt,
      inherit_context: options.inheritContext ?? 'none',
      inherit_context_turns: options.inheritContextTurns ?? 5,
    };

    const response = await this.request<{ agent_id: string }>(
      'POST',
      `/agents/${parentId}/spawn`,
      payload
    );
    return response.agent_id;
  }

  /**
   * List sub-agents spawned by a parent agent.
   */
  async listSubAgents(parentId: string): Promise<SubAgentInfo[]> {
    const response = await this.request<{ sub_agents: SubAgentInfo[] }>(
      'GET',
      `/agents/${parentId}/sub-agents`
    );
    return response.sub_agents;
  }

  // ===========================================================================
  // Approval System
  // ===========================================================================

  /**
   * List pending approval requests for an agent.
   */
  async listPendingApprovals(agentId: string): Promise<ApprovalInfo[]> {
    const response = await this.request<{ approvals: ApprovalInfo[] }>(
      'GET',
      `/agents/${agentId}/approvals`
    );
    return response.approvals;
  }

  /**
   * Approve a pending request.
   */
  async approve(agentId: string, approvalId: string, reason?: string): Promise<void> {
    await this.request(
      'POST',
      `/agents/${agentId}/approvals/${approvalId}`,
      { approved: true, reason }
    );
  }

  /**
   * Deny a pending request.
   */
  async deny(agentId: string, approvalId: string, reason?: string): Promise<void> {
    await this.request(
      'POST',
      `/agents/${agentId}/approvals/${approvalId}`,
      { approved: false, reason }
    );
  }

  // ===========================================================================
  // Recipes (Multi-Step Workflows)
  // ===========================================================================

  /**
   * Execute a recipe (multi-step workflow).
   */
  async executeRecipe(options: ExecuteRecipeOptions): Promise<RecipeExecution> {
    const payload: Record<string, unknown> = {
      input: options.input ?? {},
    };
    if (options.recipe) {
      payload.recipe = options.recipe;
    } else if (options.recipePath) {
      payload.recipe_path = options.recipePath;
    } else {
      throw new Error('Either recipe or recipePath is required');
    }

    return this.request<RecipeExecution>('POST', '/recipes', payload);
  }

  /**
   * Get recipe execution status.
   */
  async getRecipeExecution(executionId: string): Promise<RecipeExecution> {
    return this.request<RecipeExecution>('GET', `/recipes/${executionId}`);
  }

  /**
   * Stream events from a recipe execution.
   *
   * Events include:
   * - recipe:start/complete/failed - Recipe lifecycle
   * - step:start/complete/failed/skipped - Step lifecycle
   * - approval:requested - Approval needed
   */
  async *streamRecipe(executionId: string): AsyncGenerator<StreamEvent> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/recipes/${executionId}/stream`, {
        method: 'GET',
        headers: {
          ...this.getHeaders(),
          Accept: 'text/event-stream',
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`HTTP ${response.status}: ${error}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue;

          if (trimmedLine.startsWith('event:')) {
            currentEvent = trimmedLine.slice(6).trim();
          } else if (trimmedLine.startsWith('data:')) {
            const dataStr = trimmedLine.slice(5).trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                yield { event: currentEvent, data };
              } catch {
                // Skip invalid JSON
              }
            }
          }
        }
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Approve a recipe step.
   */
  async approveRecipeStep(executionId: string, stepId: string, reason?: string): Promise<void> {
    await this.request(
      'POST',
      `/recipes/${executionId}/approvals/${stepId}`,
      { approved: true, reason }
    );
  }

  /**
   * Deny a recipe step.
   */
  async denyRecipeStep(executionId: string, stepId: string, reason?: string): Promise<void> {
    await this.request(
      'POST',
      `/recipes/${executionId}/approvals/${stepId}`,
      { approved: false, reason }
    );
  }

  /**
   * List all recipe executions.
   */
  async listRecipeExecutions(): Promise<RecipeExecution[]> {
    const response = await this.request<{ executions: RecipeExecution[] }>('GET', '/recipes');
    return response.executions;
  }

  /**
   * Cancel a recipe execution.
   */
  async cancelRecipe(executionId: string): Promise<void> {
    await this.request('DELETE', `/recipes/${executionId}`);
  }

  // ===========================================================================
  // Messages
  // ===========================================================================

  /**
   * Get conversation messages for an agent.
   */
  async getMessages(agentId: string): Promise<Message[]> {
    const response = await this.request<{ messages: Message[] }>(
      'GET',
      `/agents/${agentId}/messages`
    );
    return response.messages;
  }

  /**
   * Clear conversation messages for an agent.
   */
  async clearMessages(agentId: string): Promise<void> {
    await this.request<{ cleared: boolean }>('DELETE', `/agents/${agentId}/messages`);
  }

  // ===========================================================================
  // One-off Execution
  // ===========================================================================

  /**
   * Run a one-off prompt without persistent agent.
   */
  async runOnce(options: RunOnceOptions): Promise<RunResponse> {
    const payload = {
      prompt: options.prompt,
      instructions: options.instructions ?? 'You are a helpful assistant.',
      provider: options.provider ?? 'anthropic',
      model: options.model,
      tools: options.tools ?? [],
      max_turns: options.maxTurns ?? 10,
    };

    return this.request<RunResponse>('POST', '/run', payload);
  }
}
