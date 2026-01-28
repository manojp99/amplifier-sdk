/**
 * Amplifier SDK - TypeScript client for Amplifier AI agents
 *
 * @example
 * ```typescript
 * import { Agent, run } from '@anthropic/amplifier-sdk';
 *
 * // High-level API
 * const agent = new Agent({ instructions: 'You help with code.' });
 * const response = await agent.run('Hello!');
 * console.log(response.content);
 *
 * // One-shot
 * const response = await run('What is 2+2?');
 *
 * // Streaming
 * for await (const event of agent.stream('Write a poem')) {
 *   process.stdout.write(event.data.content || '');
 * }
 * ```
 */

export { AmplifierClient } from './client';
export { Agent, run } from './agent';
export type { AgentOptions } from './agent';
export type {
  AgentConfig,
  ClientOptions,
  CreateAgentOptions,
  ExecuteRecipeOptions,
  RecipeExecution,
  RecipeStatus,
  RunResponse,
  StepResult,
  StreamEvent,
  ToolCall,
  Usage,
} from './types';
