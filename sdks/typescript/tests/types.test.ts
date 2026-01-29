/**
 * Tests for type definitions
 */

import { describe, it, expect } from 'vitest';
import type {
  AgentConfig,
  AgentInfo,
  CreateAgentOptions,
  RunResponse,
  StreamEvent,
  ToolCall,
  Usage,
} from '../src/types';

describe('Type Definitions', () => {
  describe('AgentConfig', () => {
    it('allows minimal config', () => {
      const config: AgentConfig = {
        instructions: 'You are helpful.',
        provider: 'anthropic',
      };
      expect(config.instructions).toBe('You are helpful.');
      expect(config.provider).toBe('anthropic');
      expect(config.tools).toBeUndefined();
    });

    it('allows full config', () => {
      const config: AgentConfig = {
        instructions: 'You are helpful.',
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514',
        tools: ['bash', 'filesystem'],
        orchestrator: 'streaming',
        context_manager: 'persistent',
        hooks: ['logging'],
        config: { key: 'value' },
      };
      expect(config.tools).toEqual(['bash', 'filesystem']);
      expect(config.provider).toBe('anthropic');
      expect(config.orchestrator).toBe('streaming');
    });
  });

  describe('CreateAgentOptions', () => {
    it('allows minimal options', () => {
      const options: CreateAgentOptions = {
        instructions: 'Be helpful.',
      };
      expect(options.instructions).toBe('Be helpful.');
      expect(options.provider).toBeUndefined();
    });

    it('allows full options', () => {
      const options: CreateAgentOptions = {
        instructions: 'Be helpful.',
        provider: 'openai',
        model: 'gpt-4o',
        tools: ['bash'],
        orchestrator: 'basic',
        contextManager: 'simple',
        hooks: ['logging'],
        config: { debug: true },
      };
      expect(options.provider).toBe('openai');
      expect(options.contextManager).toBe('simple');
    });
  });

  describe('ToolCall', () => {
    it('has required fields', () => {
      const toolCall: ToolCall = {
        id: 'tc_123',
        name: 'bash',
        input: { command: 'ls -la' },
      };
      expect(toolCall.id).toBe('tc_123');
      expect(toolCall.name).toBe('bash');
      expect(toolCall.input.command).toBe('ls -la');
    });

    it('allows optional output', () => {
      const toolCall: ToolCall = {
        id: 'tc_123',
        name: 'bash',
        input: { command: 'ls' },
        output: 'file1.txt\nfile2.txt',
      };
      expect(toolCall.output).toBe('file1.txt\nfile2.txt');
    });
  });

  describe('Usage', () => {
    it('has all token fields', () => {
      const usage: Usage = {
        input_tokens: 100,
        output_tokens: 50,
        total_tokens: 150,
      };
      expect(usage.input_tokens).toBe(100);
      expect(usage.output_tokens).toBe(50);
      expect(usage.total_tokens).toBe(150);
    });
  });

  describe('RunResponse', () => {
    it('has required fields', () => {
      const response: RunResponse = {
        content: 'Hello!',
        tool_calls: [],
        usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
        turn_count: 1,
      };
      expect(response.content).toBe('Hello!');
      expect(response.tool_calls).toEqual([]);
      expect(response.turn_count).toBe(1);
    });

    it('includes tool calls', () => {
      const toolCall: ToolCall = {
        id: 'call_123',
        name: 'bash',
        input: { command: 'ls -la' },
        output: 'file1.txt',
      };
      const response: RunResponse = {
        content: 'Running command...',
        tool_calls: [toolCall],
        usage: { input_tokens: 20, output_tokens: 10, total_tokens: 30 },
        turn_count: 2,
      };
      expect(response.tool_calls[0].name).toBe('bash');
      expect(response.turn_count).toBe(2);
    });
  });

  describe('StreamEvent', () => {
    it('has event and data', () => {
      const event: StreamEvent = {
        event: 'content_delta',
        data: { text: 'Hello' },
      };
      expect(event.event).toBe('content_delta');
      expect(event.data.text).toBe('Hello');
    });

    it('supports done event', () => {
      const event: StreamEvent = {
        event: 'done',
        data: {},
      };
      expect(event.event).toBe('done');
    });

    it('supports error event', () => {
      const event: StreamEvent = {
        event: 'error',
        data: { message: 'Something failed' },
      };
      expect(event.event).toBe('error');
      expect(event.data.message).toBe('Something failed');
    });
  });

  describe('AgentInfo', () => {
    it('has required fields', () => {
      const info: AgentInfo = {
        agent_id: 'ag_test123',
        created_at: '2024-01-01T00:00:00Z',
        status: 'ready',
        tools: [],
        message_count: 0,
      };
      expect(info.agent_id).toBe('ag_test123');
      expect(info.status).toBe('ready');
    });

    it('has optional fields', () => {
      const info: AgentInfo = {
        agent_id: 'ag_test123',
        created_at: '2024-01-01T00:00:00Z',
        status: 'ready',
        instructions: 'Be helpful.',
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514',
        tools: ['bash', 'filesystem'],
        message_count: 5,
      };
      expect(info.instructions).toBe('Be helpful.');
      expect(info.provider).toBe('anthropic');
      expect(info.tools).toEqual(['bash', 'filesystem']);
      expect(info.message_count).toBe(5);
    });
  });
});
