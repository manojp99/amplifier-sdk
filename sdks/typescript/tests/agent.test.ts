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
    deleteAgent: ReturnType<typeof vi.fn>;
    stream: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockClient = {
      createAgent: vi.fn().mockResolvedValue('agent-123'),
      run: vi.fn().mockResolvedValue({
        content: 'Hello!',
        tool_calls: [],
        usage: { input_tokens: 10, output_tokens: 5 },
      }),
      deleteAgent: vi.fn().mockResolvedValue(undefined),
      stream: vi.fn(),
    };
    vi.mocked(AmplifierClient).mockImplementation(() => mockClient as any);
  });

  describe('constructor', () => {
    it('stores instructions', () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      expect(agent['config'].instructions).toBe('Be helpful.');
    });

    it('defaults provider to anthropic', () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      expect(agent['config'].provider).toBe('anthropic');
    });

    it('allows custom provider', () => {
      const agent = new Agent({ instructions: 'Be helpful.', provider: 'openai' });
      expect(agent['config'].provider).toBe('openai');
    });

    it('stores tools', () => {
      const agent = new Agent({
        instructions: 'Be helpful.',
        tools: ['bash', 'filesystem'],
      });
      expect(agent['config'].tools).toEqual(['bash', 'filesystem']);
    });

    it('agent ID is initially undefined', () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      expect(agent.getAgentId()).toBeUndefined();
    });
  });

  describe('run', () => {
    it('creates agent on first call', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.run('Hello!');

      expect(mockClient.createAgent).toHaveBeenCalledTimes(1);
      expect(agent.getAgentId()).toBe('agent-123');
    });

    it('reuses agent ID on subsequent calls', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.run('Hello!');
      await agent.run('How are you?');

      expect(mockClient.createAgent).toHaveBeenCalledTimes(1);
      expect(mockClient.run).toHaveBeenCalledTimes(2);
    });

    it('returns response', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      const response = await agent.run('Hello!');

      expect(response.content).toBe('Hello!');
      expect(response.usage.input_tokens).toBe(10);
    });

    it('passes correct agent ID to client.run', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.run('Hello!');

      expect(mockClient.run).toHaveBeenCalledWith('agent-123', 'Hello!');
    });
  });

  describe('delete', () => {
    it('calls client.deleteAgent', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.run('Hello!'); // Creates agent
      await agent.delete();

      expect(mockClient.deleteAgent).toHaveBeenCalledWith('agent-123');
    });

    it('clears agent ID after delete', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.run('Hello!');
      await agent.delete();

      expect(agent.getAgentId()).toBeUndefined();
    });

    it('does nothing if agent not created', async () => {
      const agent = new Agent({ instructions: 'Be helpful.' });
      await agent.delete();

      expect(mockClient.deleteAgent).not.toHaveBeenCalled();
    });
  });
});

describe('run function', () => {
  let mockClient: {
    createAgent: ReturnType<typeof vi.fn>;
    run: ReturnType<typeof vi.fn>;
    deleteAgent: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockClient = {
      createAgent: vi.fn().mockResolvedValue('temp-agent'),
      run: vi.fn().mockResolvedValue({
        content: '42',
        tool_calls: [],
        usage: { input_tokens: 5, output_tokens: 2 },
      }),
      deleteAgent: vi.fn().mockResolvedValue(undefined),
    };
    vi.mocked(AmplifierClient).mockImplementation(() => mockClient as any);
  });

  it('creates, runs, and deletes agent', async () => {
    const response = await run('What is 2+2?');

    expect(response.content).toBe('42');
    expect(mockClient.createAgent).toHaveBeenCalledTimes(1);
    expect(mockClient.run).toHaveBeenCalledTimes(1);
    expect(mockClient.deleteAgent).toHaveBeenCalledTimes(1);
  });

  it('uses default instructions', async () => {
    await run('Hello');

    expect(mockClient.createAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions: 'You are a helpful assistant.',
      })
    );
  });

  it('allows custom instructions', async () => {
    await run('Hello', { instructions: 'Be concise.' });

    expect(mockClient.createAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions: 'Be concise.',
      })
    );
  });
});
