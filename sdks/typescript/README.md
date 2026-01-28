# Amplifier SDK for TypeScript

TypeScript client for Amplifier AI agents.

## Installation

```bash
npm install @anthropic/amplifier-sdk
```

## Quick Start

```typescript
import { Agent } from '@anthropic/amplifier-sdk';

// Create an agent
const agent = new Agent({
  instructions: 'You are a helpful coding assistant.',
  tools: ['filesystem', 'bash'],
});

// Run a prompt
const response = await agent.run('List all TypeScript files');
console.log(response.content);

// Multi-turn conversation (session state maintained)
await agent.run('Remember my name is Alice');
const response2 = await agent.run("What's my name?");
console.log(response2.content); // "Your name is Alice"

// Clean up
await agent.delete();
```

## Streaming

```typescript
import { Agent } from '@anthropic/amplifier-sdk';

const agent = new Agent({ instructions: 'You are a poet.' });

for await (const event of agent.stream('Write a haiku about coding')) {
  process.stdout.write(event.data.content || '');
}
```

## One-Shot Usage

```typescript
import { run } from '@anthropic/amplifier-sdk';

const response = await run('What is 2+2?');
console.log(response.content);
```

## Low-Level Client

```typescript
import { AmplifierClient } from '@anthropic/amplifier-sdk';

const client = new AmplifierClient({
  baseUrl: 'http://localhost:8080',
  apiKey: 'your-api-key', // optional
});

// Create agent
const agentId = await client.createAgent({
  instructions: 'You are helpful.',
  tools: ['bash'],
});

// Run prompt
const response = await client.run(agentId, 'Hello!');
console.log(response.content);

// Stream
for await (const event of client.stream(agentId, 'Write a poem')) {
  process.stdout.write(event.data.content || '');
}

// Delete
await client.deleteAgent(agentId);
```

## Recipes

```typescript
import { AmplifierClient } from '@anthropic/amplifier-sdk';

const client = new AmplifierClient();

// Execute recipe
const executionId = await client.executeRecipe({
  recipeYaml: `
name: code-review
steps:
  - id: analyze
    prompt: Analyze the code structure
  - id: review
    prompt: Review based on {{steps.analyze.result}}
`,
  context: { project: 'my-app' },
});

// Check status
const execution = await client.getRecipeExecution(executionId);
console.log(execution.status);

// Approve gate
await client.approveGate(executionId, 'review-gate');
```

## Configuration

```typescript
import { Agent } from '@anthropic/amplifier-sdk';

const agent = new Agent({
  instructions: 'You are helpful.',
  tools: ['filesystem', 'bash', 'web_search'],
  provider: 'anthropic',              // LLM provider
  model: 'claude-sonnet-4-20250514',     // Model name
  baseUrl: 'http://localhost:8080',   // Server URL
  apiKey: 'your-api-key',             // Optional auth
  timeout: 300000,                    // Timeout in ms
});
```

## Types

```typescript
import type {
  Agent,
  AgentConfig,
  RunResponse,
  StreamEvent,
  ToolCall,
  Usage,
  RecipeExecution,
} from '@anthropic/amplifier-sdk';

// RunResponse
interface RunResponse {
  content: string;
  tool_calls: ToolCall[];
  usage: Usage;
  stop_reason?: string;
}

// StreamEvent
interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

// ToolCall
interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}
```

## Requirements

- Node.js 18+ or modern browser with fetch support
- Amplifier server running at localhost:8080

## License

MIT
