/**
 * High-level Agent API for Amplifier SDK
 */

import { AmplifierClient } from './client';
import type { AgentConfig, ClientOptions, RunResponse, StreamEvent } from './types';

export interface AgentOptions extends AgentConfig, ClientOptions {}

export class Agent {
  private config: AgentConfig;
  private client: AmplifierClient;
  private agentId?: string;

  /**
   * Create a new Agent
   *
   * @example
   * ```typescript
   * // Simple usage
   * const agent = new Agent({ instructions: 'You help with code.' });
   * const response = await agent.run('Hello!');
   * console.log(response.content);
   *
   * // With tools
   * const agent = new Agent({
   *   instructions: 'You are a coding assistant.',
   *   tools: ['filesystem', 'bash'],
   *   provider: 'anthropic',
   *   model: 'claude-sonnet-4-20250514'
   * });
   *
   * // Streaming
   * for await (const event of agent.stream('Write a poem')) {
   *   process.stdout.write(event.data.content || '');
   * }
   *
   * // Multi-turn conversation
   * await agent.run('Remember my name is Alice');
   * await agent.run("What's my name?"); // Remembers context
   *
   * // Clean up when done
   * await agent.delete();
   * ```
   */
  constructor(options: AgentOptions) {
    this.config = {
      instructions: options.instructions,
      tools: options.tools,
      provider: options.provider || 'anthropic',
      model: options.model,
      bundle: options.bundle,
    };
    this.client = new AmplifierClient({
      baseUrl: options.baseUrl,
      apiKey: options.apiKey,
      timeout: options.timeout,
    });
  }

  /**
   * Get the agent ID (undefined if not yet created)
   */
  getAgentId(): string | undefined {
    return this.agentId;
  }

  private async ensureCreated(): Promise<string> {
    if (!this.agentId) {
      this.agentId = await this.client.createAgent({
        instructions: this.config.instructions,
        tools: this.config.tools,
        provider: this.config.provider,
        model: this.config.model,
        bundle: this.config.bundle,
      });
    }
    return this.agentId;
  }

  /**
   * Run a prompt and get response
   *
   * @param prompt - User message
   * @returns Response with content, tool_calls, and usage
   */
  async run(prompt: string): Promise<RunResponse> {
    const agentId = await this.ensureCreated();
    return this.client.run(agentId, prompt);
  }

  /**
   * Stream a prompt response
   *
   * @param prompt - User message
   * @yields StreamEvent for each token/event
   */
  async *stream(prompt: string): AsyncGenerator<StreamEvent> {
    const agentId = await this.ensureCreated();
    yield* this.client.stream(agentId, prompt);
  }

  /**
   * Delete the agent from server
   */
  async delete(): Promise<void> {
    if (this.agentId) {
      await this.client.deleteAgent(this.agentId);
      this.agentId = undefined;
    }
  }
}

/**
 * One-shot prompt execution
 *
 * Creates an agent, runs the prompt, and cleans up.
 *
 * @example
 * ```typescript
 * import { run } from '@anthropic/amplifier-sdk';
 *
 * const response = await run('What is 2+2?');
 * console.log(response.content);
 * ```
 */
export async function run(
  prompt: string,
  options: Partial<AgentOptions> = {}
): Promise<RunResponse> {
  const agent = new Agent({
    instructions: options.instructions || 'You are a helpful assistant.',
    tools: options.tools,
    provider: options.provider,
    model: options.model,
    bundle: options.bundle,
    baseUrl: options.baseUrl,
    apiKey: options.apiKey,
    timeout: options.timeout,
  });

  try {
    return await agent.run(prompt);
  } finally {
    await agent.delete();
  }
}
