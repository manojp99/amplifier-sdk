import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AmplifierClient } from '../src/client';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('AmplifierClient', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('uses default base URL', () => {
      const client = new AmplifierClient();
      expect(client['baseUrl']).toBe('http://localhost:8000');
    });

    it('accepts custom base URL', () => {
      const client = new AmplifierClient({ baseUrl: 'http://custom:9000/' });
      expect(client['baseUrl']).toBe('http://custom:9000');
    });

    it('stores API key', () => {
      const client = new AmplifierClient({ apiKey: 'test-key' });
      expect(client['apiKey']).toBe('test-key');
    });
  });

  describe('health', () => {
    it('returns server health status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', version: '0.1.0' }),
      });

      const client = new AmplifierClient();
      const result = await client.health();

      expect(result.status).toBe('ok');
      expect(result.version).toBe('0.1.0');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/health',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('createAgent', () => {
    it('creates agent and returns ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ agent_id: 'ag_test123' }),
      });

      const client = new AmplifierClient();
      const agentId = await client.createAgent({
        instructions: 'Be helpful.',
        provider: 'anthropic',
        tools: ['bash'],
      });

      expect(agentId).toBe('ag_test123');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/agents',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Be helpful.'),
        })
      );
    });

    it('uses default provider', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ agent_id: 'ag_test' }),
      });

      const client = new AmplifierClient();
      await client.createAgent({ instructions: 'Test' });

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.provider).toBe('anthropic');
    });
  });

  describe('listAgents', () => {
    it('returns list of agent IDs', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ agents: ['ag_1', 'ag_2'] }),
      });

      const client = new AmplifierClient();
      const agents = await client.listAgents();

      expect(agents).toEqual(['ag_1', 'ag_2']);
    });
  });

  describe('getAgent', () => {
    it('returns agent info', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          agent_id: 'ag_test',
          status: 'ready',
          instructions: 'Be helpful.',
          provider: 'anthropic',
          tools: ['bash'],
          message_count: 0,
        }),
      });

      const client = new AmplifierClient();
      const info = await client.getAgent('ag_test');

      expect(info.agent_id).toBe('ag_test');
      expect(info.status).toBe('ready');
      expect(info.tools).toContain('bash');
    });
  });

  describe('deleteAgent', () => {
    it('deletes agent', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deleted: true }),
      });

      const client = new AmplifierClient();
      await client.deleteAgent('ag_test');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/agents/ag_test',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('run', () => {
    it('runs prompt and returns response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          content: 'Hello!',
          tool_calls: [],
          usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
          turn_count: 1,
        }),
      });

      const client = new AmplifierClient();
      const result = await client.run('ag_test', 'Hello');

      expect(result.content).toBe('Hello!');
      expect(result.turn_count).toBe(1);
      expect(result.usage.total_tokens).toBe(15);
    });

    it('passes max_turns option', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          content: 'Done',
          tool_calls: [],
          usage: {},
          turn_count: 5,
        }),
      });

      const client = new AmplifierClient();
      await client.run('ag_test', 'Work', { maxTurns: 20 });

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.max_turns).toBe(20);
    });
  });

  describe('getMessages', () => {
    it('returns conversation messages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          messages: [
            { role: 'user', content: 'Hello' },
            { role: 'assistant', content: 'Hi!' },
          ],
        }),
      });

      const client = new AmplifierClient();
      const messages = await client.getMessages('ag_test');

      expect(messages).toHaveLength(2);
      expect(messages[0].role).toBe('user');
    });
  });

  describe('clearMessages', () => {
    it('clears agent messages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ cleared: true }),
      });

      const client = new AmplifierClient();
      await client.clearMessages('ag_test');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/agents/ag_test/messages',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('runOnce', () => {
    it('runs one-off prompt', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          content: 'Answer',
          tool_calls: [],
          usage: {},
          turn_count: 1,
        }),
      });

      const client = new AmplifierClient();
      const result = await client.runOnce({
        prompt: 'Question?',
        instructions: 'Be brief.',
        provider: 'anthropic',
      });

      expect(result.content).toBe('Answer');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/run',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('error handling', () => {
    it('throws on HTTP error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Not found',
      });

      const client = new AmplifierClient();
      await expect(client.getAgent('ag_missing')).rejects.toThrow('HTTP 404');
    });
  });

  describe('authentication', () => {
    it('includes Authorization header when API key set', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok' }),
      });

      const client = new AmplifierClient({ apiKey: 'secret-key' });
      await client.health();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer secret-key',
          }),
        })
      );
    });
  });
});
