/**
 * Tests for type definitions
 */

import { describe, it, expect } from 'vitest';
import type {
  AgentConfig,
  RunResponse,
  StreamEvent,
  ToolCall,
  Usage,
  RecipeExecution,
  RecipeStatus,
} from '../src/types';

describe('Type Definitions', () => {
  describe('AgentConfig', () => {
    it('allows minimal config', () => {
      const config: AgentConfig = {
        instructions: 'You are helpful.',
      };
      expect(config.instructions).toBe('You are helpful.');
      expect(config.tools).toBeUndefined();
      expect(config.provider).toBeUndefined();
    });

    it('allows full config', () => {
      const config: AgentConfig = {
        instructions: 'You are helpful.',
        tools: ['bash', 'filesystem'],
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514',
        bundle: 'my-bundle',
      };
      expect(config.tools).toEqual(['bash', 'filesystem']);
      expect(config.provider).toBe('anthropic');
    });
  });

  describe('RunResponse', () => {
    it('has required fields', () => {
      const response: RunResponse = {
        content: 'Hello!',
        tool_calls: [],
        usage: { input_tokens: 10, output_tokens: 5 },
      };
      expect(response.content).toBe('Hello!');
      expect(response.tool_calls).toEqual([]);
    });

    it('includes tool calls', () => {
      const toolCall: ToolCall = {
        id: 'call_123',
        name: 'bash',
        arguments: { command: 'ls -la' },
        result: 'file1.txt',
      };
      const response: RunResponse = {
        content: 'Running command...',
        tool_calls: [toolCall],
        usage: { input_tokens: 20, output_tokens: 10 },
        stop_reason: 'tool_use',
      };
      expect(response.tool_calls[0].name).toBe('bash');
      expect(response.stop_reason).toBe('tool_use');
    });
  });

  describe('StreamEvent', () => {
    it('has event and data', () => {
      const event: StreamEvent = {
        event: 'delta',
        data: { content: 'Hello' },
      };
      expect(event.event).toBe('delta');
      expect(event.data.content).toBe('Hello');
    });
  });

  describe('RecipeExecution', () => {
    it('tracks execution state', () => {
      const execution: RecipeExecution = {
        execution_id: 'exec-123',
        recipe_name: 'code-review',
        status: 'running',
        current_step: 'analyze',
        steps: [
          { step_id: 'setup', status: 'completed', content: 'Done' },
          { step_id: 'analyze', status: 'running' },
        ],
      };
      expect(execution.status).toBe('running');
      expect(execution.steps).toHaveLength(2);
    });

    it('supports all status types', () => {
      const statuses: RecipeStatus[] = [
        'pending',
        'running',
        'waiting_approval',
        'completed',
        'failed',
        'cancelled',
      ];
      statuses.forEach((status) => {
        const execution: RecipeExecution = {
          execution_id: 'test',
          recipe_name: 'test',
          status,
          steps: [],
        };
        expect(execution.status).toBe(status);
      });
    });
  });
});
