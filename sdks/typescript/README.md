# Amplifier SDK for TypeScript

TypeScript client for [amplifier-app-runtime](https://github.com/manojp99/amplifier-app-runtime).

## Installation

```bash
npm install amplifier-sdk
```

Or with yarn:

```bash
yarn add amplifier-sdk
```

## Quick Start

```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();

// Create a session
const session = await client.createSession({ bundle: "foundation" });

// Stream a response
for await (const event of client.prompt(session.id, "Hello!")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta as string);
  }
}
console.log(); // Newline at end

// Clean up
await client.deleteSession(session.id);
```

## Usage Patterns

### Streaming Response

```typescript
const client = new AmplifierClient();
const session = await client.createSession();

for await (const event of client.prompt(session.id, "Tell me a story")) {
  switch (event.type) {
    case "content.delta":
      process.stdout.write(event.data.delta as string);
      break;
    case "tool.call":
      console.log(`\nUsing tool: ${event.data.tool_name}`);
      break;
    case "thinking.delta":
      console.log(`[thinking] ${event.data.delta}`);
      break;
    case "content.end":
      console.log(); // Done
      break;
  }
}
```

### Synchronous Response

```typescript
const client = new AmplifierClient();
const session = await client.createSession();

// Wait for complete response
const response = await client.promptSync(session.id, "What is 2+2?");
console.log(response.content); // "4"
console.log(response.toolCalls); // List of tool calls made
```

### One-Shot Execution

```typescript
import { run } from "amplifier-sdk";

// Creates session, runs prompt, returns result, cleans up
const response = await run("What is the capital of France?");
console.log(response.content);
```

### One-Shot Streaming

```typescript
const client = new AmplifierClient();

// Creates session, streams prompt, cleans up
for await (const event of client.stream("Tell me about TypeScript")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta as string);
  }
}
```

### Handling Approvals

```typescript
import * as readline from "readline";

const client = new AmplifierClient();
const session = await client.createSession();

for await (const event of client.prompt(session.id, "Delete all files")) {
  if (event.type === "approval.required") {
    // Agent is asking for permission
    const { request_id, prompt, options } = event.data;

    console.log(`Approval needed: ${prompt}`);
    console.log(`Options: ${options}`);

    // Get user input
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    const choice = await new Promise<string>((resolve) => {
      rl.question("Your choice: ", (answer) => {
        rl.close();
        resolve(answer);
      });
    });

    await client.respondApproval(session.id, request_id as string, choice);
  }
}
```

## API Reference

### AmplifierClient

```typescript
const client = new AmplifierClient({
  baseUrl: "http://localhost:4096", // Server URL
  timeout: 300000, // Request timeout (ms)
});
```

### Methods

| Method                                            | Description                        |
| ------------------------------------------------- | ---------------------------------- |
| `createSession(config)`                           | Create a new session               |
| `getSession(sessionId)`                           | Get session info                   |
| `listSessions()`                                  | List all sessions                  |
| `deleteSession(sessionId)`                        | Delete a session                   |
| `prompt(sessionId, content)`                      | Stream a prompt (async generator)  |
| `promptSync(sessionId, content)`                  | Wait for complete response         |
| `cancel(sessionId)`                               | Cancel ongoing execution           |
| `respondApproval(sessionId, requestId, choice)`   | Respond to approval                |
| `ping()`                                          | Check server health                |
| `capabilities()`                                  | Get server capabilities            |
| `run(content, config)`                            | One-shot execution                 |
| `stream(content, config)`                         | One-shot streaming                 |

### Event Types

| Type                | Description             |
| ------------------- | ----------------------- |
| `content.delta`     | Streaming text chunk    |
| `content.end`       | Content complete        |
| `thinking.delta`    | Reasoning/thinking chunk|
| `tool.call`         | Tool being called       |
| `tool.result`       | Tool result received    |
| `approval.required` | Approval needed         |
| `error`             | Error occurred          |

### Types

```typescript
interface SessionConfig {
  bundle?: string;
  provider?: string;
  model?: string;
  workingDirectory?: string;
}

interface Event {
  type: string;
  data: Record<string, unknown>;
  correlationId?: string;
  sequence?: number;
  final?: boolean;
}

interface PromptResponse {
  content: string;
  toolCalls: ToolCall[];
  sessionId?: string;
  stopReason?: string;
}
```

## Server Setup

Start the amplifier-app-runtime server:

```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --port 4096
```

## Browser Usage

The SDK uses the Fetch API and works in modern browsers:

```html
<script type="module">
  import { AmplifierClient } from "amplifier-sdk";

  const client = new AmplifierClient({ baseUrl: "http://localhost:4096" });
  const session = await client.createSession();

  for await (const event of client.prompt(session.id, "Hello!")) {
    if (event.type === "content.delta") {
      document.body.innerHTML += event.data.delta;
    }
  }
</script>
```

## License

MIT
