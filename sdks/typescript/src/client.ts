/**
 * HTTP client for Amplifier server.
 */

import type {
  AgentInfo,
  ClientOptions,
  CreateAgentOptions,
  HealthResponse,
  Message,
  ModulesResponse,
  RunOnceOptions,
  RunOptions,
  RunResponse,
  StreamEvent,
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
   * // Create agent
   * const agentId = await client.createAgent({
   *   instructions: 'You are helpful.',
   *   provider: 'anthropic',
   *   tools: ['bash']
   * });
   *
   * // Run prompt
   * const response = await client.run(agentId, 'Hello!');
   * console.log(response.content);
   *
   * // Stream response
   * for await (const event of client.stream(agentId, 'Write a poem')) {
   *   if (event.data.text) {
   *     process.stdout.write(event.data.text as string);
   *   }
   * }
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

  // Health

  /**
   * Check server health.
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/health');
  }

  // Modules

  /**
   * List available modules.
   */
  async listModules(): Promise<ModulesResponse> {
    return this.request<ModulesResponse>('GET', '/modules');
  }

  // Agents

  /**
   * Create a new agent.
   */
  async createAgent(options: CreateAgentOptions): Promise<string> {
    const payload = {
      instructions: options.instructions,
      provider: options.provider ?? 'anthropic',
      model: options.model,
      tools: options.tools ?? [],
      orchestrator: options.orchestrator ?? 'basic',
      context_manager: options.contextManager ?? 'simple',
      hooks: options.hooks ?? [],
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

  // Execution

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
   * Stream a prompt response.
   */
  async *stream(
    agentId: string,
    prompt: string,
    options: RunOptions = {}
  ): AsyncGenerator<StreamEvent> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/agents/${agentId}/stream`, {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          prompt,
          max_turns: options.maxTurns ?? 10,
        }),
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

  // Messages

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

  // One-off execution

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
