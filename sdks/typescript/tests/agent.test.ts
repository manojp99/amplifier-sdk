/**
 * Tests for Agent class
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Agent, run } from '../src/agent';
import { AmplifierClient } from '../src/client';

// Mock the client
vi.mock('../src/client', () => ({
  AmplifierClient: vi.fn(),
}));

describe('Agent', () => {
  let mockClient: {
    createAgent: ReturnType<typeof vi.fn>;
    run: ReturnType<typeof vi.fn>;
    getAgent: ReturnType<typeof vi.fn>;
    getMessages: ReturnType<typeof vi.fn>;
    clearMessages: ReturnType<typeof vi.fn>;
    deleteAgent: ReturnType<typeof vi.fn>;
    stream: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockClient = {
      createAgent: vi.fn().mockResolvedValue('ag_test123'),
      run: vi.fn().mockResolvedValue({
        content: 'Hello!',
        tool_calls: [],
        usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
        turn_count: 1,
      }),
      getAgent: vi.fn().mockResolvedValue({
        agent_id: 'ag_test123',
        status: 'ready',
        instructions: 'Be helpful.',
        provider: 'anthropic',
        tools: ['bash'],
        message_count: 2,
      }),
      getMessages: vi.fn().mockResolvedValue([
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi!' },
      ]),
      clearMessages: vi.fn().mockResolvedValue(undefined),
      deleteAgent: vi.fn().mockResolvedValue(undefined),
      stream: vi.fn(),
    };
  });

  describe('create', () => {
    it('creates agent on server', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });

      expect(mockClient.createAgent).toHaveBeenCalledTimes(1);
      expect(agent.agentId).toBe('ag_test123');
    });

    it('stores instructions', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });

      expect(agent.instructions).toBe('Be helpful.');
    });

    it('defaults provider to anthropic', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });

      expect(agent.provider).toBe('anthropic');
    });

    it('allows custom provider', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
        provider: 'openai',
      });

      expect(agent.provider).toBe('openai');
    });

    it('stores tools', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
        tools: ['bash', 'filesystem'],
      });

      expect(agent.tools).toEqual(['bash', 'filesystem']);
    });

    it('stores model', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
        model: 'claude-sonnet-4-20250514',
      });

      expect(agent.model).toBe('claude-sonnet-4-20250514');
    });
  });

  describe('run', () => {
    it('calls client.run with agent ID', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.run('Hello!');

      expect(mockClient.run).toHaveBeenCalledWith('ag_test123', 'Hello!', {});
    });

    it('returns response', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      const response = await agent.run('Hello!');

      expect(response.content).toBe('Hello!');
      expect(response.usage.input_tokens).toBe(10);
    });

    it('passes maxTurns option', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.run('Work hard', { maxTurns: 20 });

      expect(mockClient.run).toHaveBeenCalledWith('ag_test123', 'Work hard', {
        maxTurns: 20,
      });
    });

    it('throws error after agent deleted', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.delete();

      await expect(agent.run('Hello!')).rejects.toThrow('has been deleted');
    });
  });

  describe('getInfo', () => {
    it('returns agent information', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      const info = await agent.getInfo();

      expect(mockClient.getAgent).toHaveBeenCalledWith('ag_test123');
      expect(info.agent_id).toBe('ag_test123');
      expect(info.status).toBe('ready');
    });
  });

  describe('getMessages', () => {
    it('returns conversation history', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      const messages = await agent.getMessages();

      expect(mockClient.getMessages).toHaveBeenCalledWith('ag_test123');
      expect(messages).toHaveLength(2);
    });
  });

  describe('clearMessages', () => {
    it('clears conversation history', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.clearMessages();

      expect(mockClient.clearMessages).toHaveBeenCalledWith('ag_test123');
    });
  });

  describe('delete', () => {
    it('calls client.deleteAgent', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.delete();

      expect(mockClient.deleteAgent).toHaveBeenCalledWith('ag_test123');
    });

    it('delete twice only calls client once', async () => {
      const agent = await Agent.create(mockClient as any, {
        instructions: 'Be helpful.',
      });
      await agent.delete();
      await agent.delete();

      expect(mockClient.deleteAgent).toHaveBeenCalledTimes(1);
    });
  });
});

describe('run function', () => {
  let mockClient: {
    runOnce: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockClient = {
      runOnce: vi.fn().mockResolvedValue({
        content: '42',
        tool_calls: [],
        usage: { input_tokens: 5, output_tokens: 2, total_tokens: 7 },
        turn_count: 1,
      }),
    };
    vi.mocked(AmplifierClient).mockImplementation(() => mockClient as any);
  });

  it('runs one-off prompt', async () => {
    const response = await run({ prompt: 'What is 2+2?' });

    expect(response.content).toBe('42');
    expect(mockClient.runOnce).toHaveBeenCalledTimes(1);
  });

  it('uses default instructions', async () => {
    await run({ prompt: 'Hello' });

    expect(mockClient.runOnce).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: 'Hello',
      })
    );
  });

  it('allows custom instructions', async () => {
    await run({ prompt: 'Hello', instructions: 'Be concise.' });

    expect(mockClient.runOnce).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions: 'Be concise.',
      })
    );
  });

  it('allows custom provider', async () => {
    await run({ prompt: 'Hello', provider: 'openai' });

    expect(mockClient.runOnce).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'openai',
      })
    );
  });
});
