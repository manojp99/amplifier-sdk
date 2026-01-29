/**
 * High-level Agent interface for Amplifier SDK.
 */

import { AmplifierClient } from './client';
import type {
  AgentInfo,
  CreateAgentOptions,
  Message,
  RunOptions,
  RunResponse,
  StreamEvent,
  ToolConfig,
} from './types';

export class Agent {
  private client: AmplifierClient;
  private _agentId: string;
  private _options: CreateAgentOptions;
  private _deleted = false;

  /**
   * Create a new Agent instance.
   *
   * Note: Use Agent.create() instead of direct construction.
   */
  private constructor(
    client: AmplifierClient,
    agentId: string,
    options: CreateAgentOptions
  ) {
    this.client = client;
    this._agentId = agentId;
    this._options = options;
  }

  /**
   * Get the agent ID.
   */
  get agentId(): string {
    return this._agentId;
  }

  /**
   * Get the agent's instructions.
   */
  get instructions(): string {
    return this._options.instructions;
  }

  /**
   * Get the agent's provider.
   */
  get provider(): string {
    return this._options.provider ?? 'anthropic';
  }

  /**
   * Get the agent's model.
   */
  get model(): string | undefined {
    return this._options.model;
  }

  /**
   * Get the agent's enabled tools (strings or ToolConfig objects).
   */
  get tools(): (string | ToolConfig)[] {
    return this._options.tools ?? [];
  }

  /**
   * Create a new agent.
   *
   * @example
   * ```typescript
   * const client = new AmplifierClient();
   * const agent = await Agent.create(client, {
   *   instructions: 'You are a coding assistant.',
   *   provider: 'anthropic',
   *   tools: ['bash', 'filesystem']
   * });
   *
   * try {
   *   // Run prompt
   *   const response = await agent.run('Create a Python project');
   *   console.log(response.content);
   *
   *   // Stream response
   *   for await (const event of agent.stream('Add a README')) {
   *     if (event.data.text) {
   *       process.stdout.write(event.data.text as string);
   *     }
   *   }
   *
   *   // Conversation continues automatically
   *   const response2 = await agent.run('Now add tests');
   * } finally {
   *   await agent.delete();
   * }
   * ```
   */
  static async create(
    client: AmplifierClient,
    options: CreateAgentOptions
  ): Promise<Agent> {
    const agentId = await client.createAgent(options);
    return new Agent(client, agentId, options);
  }

  /**
   * Run a prompt and get response.
   */
  async run(prompt: string, options: RunOptions = {}): Promise<RunResponse> {
    this.checkDeleted();
    return this.client.run(this._agentId, prompt, options);
  }

  /**
   * Stream a prompt response.
   */
  async *stream(
    prompt: string,
    options: RunOptions = {}
  ): AsyncGenerator<StreamEvent> {
    this.checkDeleted();
    yield* this.client.stream(this._agentId, prompt, options);
  }

  /**
   * Get current agent information.
   */
  async getInfo(): Promise<AgentInfo> {
    this.checkDeleted();
    return this.client.getAgent(this._agentId);
  }

  /**
   * Get conversation messages.
   */
  async getMessages(): Promise<Message[]> {
    this.checkDeleted();
    return this.client.getMessages(this._agentId);
  }

  /**
   * Clear conversation history (keeps system message).
   */
  async clearMessages(): Promise<void> {
    this.checkDeleted();
    await this.client.clearMessages(this._agentId);
  }

  /**
   * Delete this agent and cleanup resources.
   */
  async delete(): Promise<void> {
    if (!this._deleted) {
      await this.client.deleteAgent(this._agentId);
      this._deleted = true;
    }
  }

  private checkDeleted(): void {
    if (this._deleted) {
      throw new Error(`Agent ${this._agentId} has been deleted`);
    }
  }
}

/**
 * Run a one-off prompt without persistent agent.
 *
 * Convenience function for simple use cases.
 *
 * @example
 * ```typescript
 * import { run } from '@amplifier/sdk';
 *
 * const response = await run({
 *   prompt: 'What is 2 + 2?',
 *   provider: 'anthropic'
 * });
 * console.log(response.content);
 * ```
 */
export async function run(options: {
  prompt: string;
  instructions?: string;
  provider?: string;
  model?: string;
  tools?: string[];
  maxTurns?: number;
  baseUrl?: string;
}): Promise<RunResponse> {
  const client = new AmplifierClient({
    baseUrl: options.baseUrl ?? 'http://localhost:8000',
  });

  return client.runOnce({
    prompt: options.prompt,
    instructions: options.instructions,
    provider: options.provider,
    model: options.model,
    tools: options.tools,
    maxTurns: options.maxTurns,
  });
}
