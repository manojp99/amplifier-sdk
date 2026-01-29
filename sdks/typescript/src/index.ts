/**
 * Amplifier SDK - TypeScript client for Amplifier AI agents.
 *
 * @example
 * ```typescript
 * import { AmplifierClient, Agent, run } from '@amplifier/sdk';
 *
 * // Option 1: Use client directly
 * const client = new AmplifierClient();
 * const agentId = await client.createAgent({
 *   instructions: 'You are helpful.',
 *   provider: 'anthropic',
 *   tools: ['bash']
 * });
 * const response = await client.run(agentId, 'Hello!');
 * console.log(response.content);
 *
 * // Option 2: Use Agent class for higher-level interface
 * const agent = await Agent.create(client, {
 *   instructions: 'You are a coding assistant.',
 *   provider: 'anthropic',
 *   tools: ['bash', 'filesystem']
 * });
 * const response = await agent.run('Create a Python project');
 * await agent.delete();
 *
 * // Option 3: One-off execution
 * const result = await run({
 *   prompt: 'What is 2 + 2?',
 *   provider: 'anthropic'
 * });
 * console.log(result.content);
 * ```
 */

export { AmplifierClient } from './client';
export { Agent, run } from './agent';
export type {
  AgentConfig,
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
  ToolCall,
  Usage,
} from './types';
