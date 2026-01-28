/**
 * Tests for AmplifierClient
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AmplifierClient } from '../src/client';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('AmplifierClient', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe('constructor', () => {
    it('uses default base URL', () => {
      const client = new AmplifierClient();
      expect(client['baseUrl']).toBe('http://localhost:8080');
    });

    it('uses custom base URL', () => {
      const client = new AmplifierClient({ baseUrl: 'http://custom:9000' });
      expect(client['baseUrl']).toBe('http://custom:9000');
    });

    it('strips trailing slash from base URL', () => {
      const client = new AmplifierClient({ baseUrl: 'http://localhost:8080/' });
      expect(client['baseUrl']).toBe('http://localhost:8080');
    });

    it('stores API key', () => {
      const client = new AmplifierClient({ apiKey: 'secret' });
      expect(client['apiKey']).toBe('secret');
    });
  });

  describe('getHeaders', () => {
    it('always includes Content-Type', () => {
      const client = new AmplifierClient();
      const headers = client['getHeaders']();
      expect(headers['Content-Type']).toBe('application/json');
    });

    it('includes Authorization when API key set', () => {
      const client = new AmplifierClient({ apiKey: 'secret' });
      const headers = client['getHeaders']();
      expect(headers['Authorization']).toBe('Bearer secret');
    });

    it('omits Authorization when no API key', () => {
      const client = new AmplifierClient();
      const headers = client['getHeaders']();
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('health', () => {
    it('makes GET request to /health', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', version: '0.1.0' }),
      });

      const client = new AmplifierClient();
      const result = await client.health();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/health',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result.status).toBe('ok');
    });
  });

  describe('createAgent', () => {
    it('creates agent and returns ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ agent_id: 'agent-123' }),
      });

      const client = new AmplifierClient();
      const agentId = await client.createAgent({
        instructions: 'Be helpful.',
      });

      expect(agentId).toBe('agent-123');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/agents',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Be helpful.'),
        })
      );
    });

    it('includes tools when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ agent_id: 'agent-456' }),
      });

      const client = new AmplifierClient();
      await client.createAgent({
        instructions: 'Be helpful.',
        tools: ['bash', 'filesystem'],
      });

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.tools).toEqual(['bash', 'filesystem']);
    });
  });

  describe('run', () => {
    it('posts prompt and returns response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          content: 'Hello!',
          tool_calls: [],
          usage: { input_tokens: 10, output_tokens: 5 },
        }),
      });

      const client = new AmplifierClient();
      const result = await client.run('agent-123', 'Hi there!');

      expect(result.content).toBe('Hello!');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/agents/agent-123/run',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ prompt: 'Hi there!' }),
        })
      );
    });
  });

  describe('deleteAgent', () => {
    it('makes DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const client = new AmplifierClient();
      await client.deleteAgent('agent-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/agents/agent-123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('executeRecipe', () => {
    it('returns execution ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ execution_id: 'exec-123' }),
      });

      const client = new AmplifierClient();
      const result = await client.executeRecipe({
        recipeYaml: 'name: test\nsteps: []',
      });

      expect(result).toBe('exec-123');
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
      await expect(client.health()).rejects.toThrow('HTTP 404: Not found');
    });
  });
});
