# Getting Started with Amplifier SDK

This guide will help you get up and running with the Amplifier SDK in minutes.

---

## What is Amplifier SDK?

Amplifier SDK provides client libraries (TypeScript and Python) for building applications powered by AI agents. Instead of managing HTTP requests and SSE streams yourself, you get:

- ✅ **Type-safe client** - Full TypeScript types and Python type hints
- ✅ **Streaming responses** - Real-time AI responses via async iterators
- ✅ **Client-side tools** - Define tools that run in your app (zero deployment!)
- ✅ **Event handlers** - Subscribe to specific events (tool calls, approvals, thinking)
- ✅ **Session management** - Create, resume, and manage AI conversations

---

## Prerequisites

The Amplifier SDK is a **client library** that communicates with a **separate server component** (amplifier-app-runtime). You need both:

1. **Amplifier Runtime (Server)** - The AI agent execution engine
2. **Amplifier SDK (Client)** - This package (TypeScript or Python)

**Architecture:**
```
Your App → SDK (HTTP client) → Runtime Server → Amplifier Core
```

### 1. Install and Run the Runtime Server

The runtime is a **separate Python application** that must be running before you can use the SDK.

**Note:** The runtime repository is currently private. You need access to the repository.

```bash
# Clone the runtime repository
git clone git@github.com:manojp99/amplifier-app-runtime.git
cd amplifier-app-runtime

# Install dependencies
uv sync

# Configure a provider (required)
mkdir -p .amplifier
cat > .amplifier/settings.yaml << EOF
providers:
  - module: provider-anthropic
    config:
      priority: 1
EOF

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Start the server
uv run python -m amplifier_app_runtime.cli --http --port 4096
```

The runtime will be available at `http://localhost:4096`.

**Keep this server running** while using the SDK.

---

## Installation

**Note:** The SDK repository is currently private. You need GitHub access.

### TypeScript / JavaScript

```bash
# Install from private GitHub repo
npm install git+ssh://git@github.com/manojp99/amplifier-sdk.git#subdirectory=sdks/typescript
```

### Python

```bash
# Install from private GitHub repo
pip install git+ssh://git@github.com/manojp99/amplifier-sdk.git#subdirectory=sdks/python

# Or with uv
uv add git+ssh://git@github.com/manojp99/amplifier-sdk.git#subdirectory=sdks/python
```

**Authentication:** Ensure your SSH keys are configured with GitHub (`ssh -T git@github.com`)

---

## Quick Start

### TypeScript

```typescript
import { AmplifierClient } from "amplifier-sdk";

async function main() {
  const client = new AmplifierClient();

  // Create a session
  const session = await client.createSession({
    bundle: {
      name: "my-assistant",
      instructions: "You are a helpful assistant.",
    },
  });

  // Stream a response
  console.log("AI: ");
  for await (const event of client.prompt(session.id, "Hello! What can you do?")) {
    if (event.type === "content.delta") {
      process.stdout.write(event.data.delta);
    }
  }
  console.log("\n");

  // Clean up
  await client.deleteSession(session.id);
}

main();
```

### Python

```python
import asyncio
from amplifier_sdk import AmplifierClient

async def main():
    async with AmplifierClient() as client:
        # Create a session
        session = await client.create_session(
            bundle={
                "name": "my-assistant",
                "instructions": "You are a helpful assistant.",
            }
        )

        # Stream a response
        print("AI: ", end="")
        async for event in client.prompt(session.id, "Hello! What can you do?"):
            if event.type == "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)
        print()

        # Clean up
        await client.delete_session(session.id)

asyncio.run(main())
```

---

## Core Concepts

### Sessions

A session represents a conversation with an AI agent. Each session:
- Has a unique ID
- Maintains conversation history
- Uses a specific bundle configuration
- Can be resumed later

```typescript
// Create a session
const session = await client.createSession({
  bundle: { name: "assistant", instructions: "Be helpful" }
});

// Use the session
for await (const event of client.prompt(session.id, "Hi!")) {
  // Handle events
}

// Resume later
const resumed = await client.resumeSession(session.id);
for await (const event of resumed.send("Continue our conversation")) {
  // Pick up where you left off
}
```

### Bundles

Bundles define your agent's capabilities:

```typescript
const bundle = {
  name: "code-assistant",
  instructions: "You are an expert coding assistant.",
  tools: [
    { module: "tool-filesystem" },  // Server-side tool
    { module: "tool-bash" }
  ],
  clientTools: ["custom-db-lookup"],  // Client-side tool (runs in your app!)
  providers: [
    { module: "provider-anthropic", config: { model: "claude-sonnet-4-5-20250514" } }
  ]
};

const session = await client.createSession({ bundle });
```

### Events

All responses stream as events:

```typescript
for await (const event of client.prompt(sessionId, "Hello")) {
  switch (event.type) {
    case "content.delta":
      // Incremental text
      process.stdout.write(event.data.delta);
      break;
      
    case "tool.call":
      // AI is calling a tool
      console.log(`Using ${event.data.tool_name}...`);
      break;
      
    case "tool.result":
      // Tool completed
      console.log(`✓ Done`);
      break;
      
    case "approval.required":
      // AI needs permission
      const approve = await askUser(event.data.prompt);
      await client.respondApproval(sessionId, event.data.request_id, approve.toString());
      break;
      
    case "thinking.delta":
      // AI's reasoning (if enabled)
      console.log(`💭 ${event.data.delta}`);
      break;
      
    case "agent.spawned":
      // AI delegated to a specialist
      console.log(`🤖 Spawned: ${event.data.agent_name}`);
      break;
  }
}
```

---

## Common Patterns

### 1. Simple Chat

```typescript
const client = new AmplifierClient();

// One-shot execution (auto cleanup)
const response = await client.run("What is 2+2?");
console.log(response.content);
```

### 2. Event Subscription (Convenience API)

```typescript
const client = new AmplifierClient();

// Subscribe to specific events
client.on("tool.call", (event) => {
  console.log(`🔧 ${event.data.tool_name}`);
});

client.on("content.delta", (event) => {
  process.stdout.write(event.data.delta);
});

// Use the client
const session = await client.createSession({ bundle: "foundation" });
for await (const event of client.prompt(session.id, "Analyze this code")) {
  // Handlers automatically called
}
```

### 3. Client-Side Tools

```typescript
// Register a tool that runs in YOUR app
client.registerTool({
  name: "get-customer",
  description: "Get customer information from your database",
  parameters: {
    type: "object",
    properties: {
      customerId: { type: "string" }
    },
    required: ["customerId"]
  },
  handler: async ({ customerId }) => {
    // This runs in YOUR app with YOUR credentials
    return await yourDatabase.customers.findById(customerId);
  }
});

// Use it in a session
const session = await client.createSession({
  bundle: {
    name: "support-agent",
    instructions: "Help customers with orders",
    clientTools: ["get-customer"]  // SDK handles this locally!
  }
});

// When AI calls get-customer:
// 1. SDK intercepts the tool.call event
// 2. Runs YOUR handler locally
// 3. Sends result back to runtime
// 4. AI continues with the result
```

### 4. Automatic Approval Handling

```typescript
// Register approval handler
client.onApproval(async (request) => {
  // Show UI to user
  const userChoice = await showApprovalDialog({
    message: request.prompt,
    tool: request.toolName,
    args: request.arguments
  });
  
  // Return true to approve, false to deny
  return userChoice;
});

// SDK automatically responds to approval requests
for await (const event of client.prompt(sessionId, "Delete old logs")) {
  // If approval needed, your handler is called automatically
}
```

### 5. Session Resume

```typescript
// List previous sessions
const sessions = await client.listSessions();
console.log(sessions.map(s => `${s.id}: ${s.title}`));

// Resume a conversation
const session = await client.resumeSession(sessions[0].id);

// Continue where you left off
for await (const event of session.send("Let's continue")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

---

## TypeScript Type Safety

The SDK provides full type safety:

```typescript
for await (const event of client.prompt(sessionId, "Hello")) {
  // TypeScript knows the exact type of each event
  if (event.type === "content.delta") {
    // TypeScript knows event.data.delta exists!
    const text: string = event.data.delta;  // No casting needed
  }
  
  if (event.type === "tool.call") {
    // TypeScript knows these fields exist
    const toolName: string = event.data.tool_name;
    const args: Record<string, unknown> = event.data.arguments;
    const toolCallId: string = event.toolCallId;
  }
}
```

---

## Event Correlation

Match related events using correlation IDs:

```typescript
const toolCalls = new Map();

for await (const event of client.prompt(sessionId, "Run some tools")) {
  if (event.type === "tool.call") {
    // Store tool call with its ID
    toolCalls.set(event.toolCallId, {
      name: event.data.tool_name,
      args: event.data.arguments,
      startTime: Date.now()
    });
  }
  
  if (event.type === "tool.result") {
    // Match result to original call
    const call = toolCalls.get(event.toolCallId);
    const duration = Date.now() - call.startTime;
    console.log(`${call.name} completed in ${duration}ms`);
  }
}
```

---

## Configuration

### Client Configuration

```typescript
const client = new AmplifierClient({
  baseUrl: "http://localhost:4096",  // Default
  timeout: 300000,  // 5 minutes (default)
  
  // Observability hooks
  debug: true,
  onRequest: (req) => console.log(`→ ${req.method} ${req.url}`),
  onResponse: (res) => console.log(`← ${res.status} (${res.durationMs}ms)`),
  onError: (err) => console.error(`✗ ${err.code}: ${err.message}`),
  onStateChange: (info) => updateConnectionUI(info.to),
  onEvent: (event) => logEvent(event),
});
```

### Bundle Configuration

```typescript
const bundle = {
  // Identity
  name: "my-agent",
  version: "1.0.0",
  description: "A helpful agent",
  
  // Behavior
  instructions: "You are a helpful assistant specialized in...",
  
  // Capabilities
  tools: [
    { module: "tool-filesystem" },
    { module: "tool-bash", config: { timeout: 30 } }
  ],
  clientTools: ["custom-tool"],  // Your local tools
  providers: [
    { module: "provider-anthropic", config: { model: "claude-sonnet-4-5-20250514" } }
  ],
  
  // Session config
  session: {
    debug: true,
    maxTurns: 10
  }
};
```

---

## Error Handling

All SDK methods throw `AmplifierError` with structured error codes:

```typescript
import { AmplifierError, ErrorCode } from "amplifier-sdk";

try {
  const session = await client.createSession();
} catch (err) {
  if (err instanceof AmplifierError) {
    console.error(`Error [${err.code}]: ${err.message}`);
    console.error(`Request ID: ${err.requestId}`);
    console.error(`HTTP Status: ${err.status}`);
    
    // Check if retryable
    if (err.isRetryable) {
      console.log("This error can be retried");
    }
    
    // Handle specific error codes
    switch (err.code) {
      case ErrorCode.ConnectionRefused:
        console.log("Is the runtime server running?");
        break;
      case ErrorCode.Timeout:
        console.log("Request took too long");
        break;
      case ErrorCode.BadRequest:
        console.log("Invalid parameters");
        break;
    }
  }
}
```

---

## Next Steps

### Learn More

- **API Reference:** See `API_REFERENCE.md` for complete API documentation
- **Examples:** See `EXAMPLES.md` for code snippets and patterns
- **Security:** See `SECURITY.md` for security best practices
- **Roadmap:** See `../docs/SDK_ROADMAP.md` for future features
- **Testing:** See `TESTING.md` for test coverage details

### Example Apps

Check out the example applications:

- **Agent Playground:** `examples/agent-playground/` - Interactive agent builder
- **Chat App:** `examples/chat-app/` - Simple chat interface

### Get Help

- **Issues:** https://github.com/manojp99/amplifier-sdk/issues
- **Discussions:** https://github.com/manojp99/amplifier-sdk/discussions
- **Documentation:** https://github.com/manojp99/amplifier-sdk

---

## Troubleshooting

### Runtime Not Available

```
Error: Connection refused at http://localhost:4096
```

**Solution:** Start the runtime server:
```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --http --port 4096
```

### No Providers Mounted

```
Error: Failed to create session - no providers configured
```

**Solution:** Configure a provider in runtime's `.amplifier/settings.yaml` and set API key:
```bash
export ANTHROPIC_API_KEY=your_key
# or
export OPENAI_API_KEY=your_key
```

### TypeScript Import Errors

```
Cannot find module 'amplifier-sdk'
```

**Solution:** Make sure the SDK is built:
```bash
cd sdks/typescript
npm run build
```

### Import Type Errors in TypeScript

**Solution:** Make sure you're importing types:
```typescript
import { AmplifierClient, type Event, type BundleDefinition } from "amplifier-sdk";
```

### Python Async Errors

```
RuntimeWarning: coroutine was never awaited
```

**Solution:** Use `async with` and `await`:
```python
async with AmplifierClient() as client:
    session = await client.create_session(...)
    async for event in client.prompt(...):
        ...
```

---

## What's Next?

Now that you have the basics:

1. **Explore client-side tools** - Define tools that access your APIs
2. **Add event handlers** - Subscribe to specific events  
3. **Try the playground** - See all features in action at `examples/agent-playground/`
4. **Build your app** - Use the SDK to power your application

Happy building! 🚀
