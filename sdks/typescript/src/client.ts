/**
 * HTTP client for Amplifier server
 */

import type {
  ClientOptions,
  CreateAgentOptions,
  ExecuteRecipeOptions,
  RecipeExecution,
  RunResponse,
  StreamEvent,
} from './types';

export class AmplifierClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  /**
   * Create a new Amplifier client
   *
   * @example
   * ```typescript
   * const client = new AmplifierClient({
   *   baseUrl: 'http://localhost:8080',
   *   apiKey: 'your-api-key'
   * });
   *
   * const agentId = await client.createAgent({
   *   instructions: 'You are helpful.',
   *   tools: ['bash']
   * });
   *
   * const response = await client.run(agentId, 'Hello!');
   * console.log(response.content);
   * ```
   */
  constructor(options: ClientOptions = {}) {
    this.baseUrl = (options.baseUrl || 'http://localhost:8080').replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.timeout = options.timeout || 300000;
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

      return response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // Health

  async health(): Promise<{ status: string }> {
    return this.request('GET', '/health');
  }

  // Agents

  async createAgent(options: CreateAgentOptions): Promise<string> {
    const response = await this.request<{ agent_id: string }>('POST', '/agents', {
      instructions: options.instructions,
      tools: options.tools,
      provider: options.provider || 'anthropic',
      model: options.model,
      bundle: options.bundle,
    });
    return response.agent_id;
  }

  async getAgent(agentId: string): Promise<Record<string, unknown>> {
    return this.request('GET', `/agents/${agentId}`);
  }

  async listAgents(): Promise<{ agents: Record<string, unknown>[] }> {
    return this.request('GET', '/agents');
  }

  async deleteAgent(agentId: string): Promise<void> {
    await this.request('DELETE', `/agents/${agentId}`);
  }

  async run(agentId: string, prompt: string): Promise<RunResponse> {
    return this.request('POST', `/agents/${agentId}/run`, { prompt });
  }

  async *stream(agentId: string, prompt: string): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${this.baseUrl}/agents/${agentId}/stream`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ prompt }),
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

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                yield {
                  event: data.event || 'message',
                  data,
                };
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // Recipes

  async executeRecipe(options: ExecuteRecipeOptions): Promise<string> {
    const response = await this.request<{ execution_id: string }>(
      'POST',
      '/recipes/execute',
      {
        recipe_path: options.recipePath,
        recipe_yaml: options.recipeYaml,
        context: options.context,
      }
    );
    return response.execution_id;
  }

  async getRecipeExecution(executionId: string): Promise<RecipeExecution> {
    return this.request('GET', `/recipes/${executionId}`);
  }

  async approveGate(executionId: string, stepId: string): Promise<void> {
    await this.request('POST', `/recipes/${executionId}/approve`, {
      step_id: stepId,
    });
  }

  async denyGate(executionId: string, stepId: string, reason = ''): Promise<void> {
    await this.request('POST', `/recipes/${executionId}/deny`, {
      step_id: stepId,
      reason,
    });
  }
}
