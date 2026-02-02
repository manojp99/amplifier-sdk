# Amplifier SDK

Multi-language client libraries for building applications powered by AI agents.

**Build AI-powered apps without managing HTTP requests, SSE streams, or protocol complexity.**

## Features

- ✅ **Type-Safe Client** - Full TypeScript types and Python type hints
- ✅ **Streaming Responses** - Real-time AI responses via async iterators
- ✅ **Client-Side Tools** - Define tools that run in your app (zero deployment!)
- ✅ **Event Handlers** - Subscribe to specific events (tool calls, approvals, thinking)
- ✅ **Event Correlation** - Match tool calls to results with `toolCallId`
- ✅ **Session Management** - Create, resume, and manage conversations
- ✅ **Approval Flow** - Human-in-the-loop for sensitive operations
- ✅ **Error Handling** - Structured errors with retry detection

## Installation

**Note:** This repository is currently **private**. The SDK and runtime are distributed separately via GitHub.

### 1. Install the Runtime (Server)

The runtime is a **separate Python application** that must be running:

```bash
git clone git@github.com:manojp99/amplifier-app-runtime.git
cd amplifier-app-runtime
uv sync
# Configure provider and start server
uv run python -m amplifier_app_runtime.cli --http --port 4096
```

### 2. Install the SDK (Client)

**TypeScript:**
```bash
npm install git+ssh://git@github.com/manojp99/amplifier-sdk.git#subdirectory=sdks/typescript
```

**Python:**
```bash
pip install git+ssh://git@github.com/manojp99/amplifier-sdk.git#subdirectory=sdks/python
```

**[📖 Full Installation Guide →](sdks/GETTING_STARTED.md)**

## Quick Start

**TypeScript:**
```typescript
import { AmplifierClient } from "amplifier-sdk";

// Connect to runtime server
const client = new AmplifierClient({ baseUrl: "http://localhost:4096" });

const session = await client.createSession({
  bundle: { name: "assistant", instructions: "Be helpful" }
});

for await (const event of client.prompt(session.id, "Hello!")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

**Python:**
```python
from amplifier_sdk import AmplifierClient

async with AmplifierClient(base_url="http://localhost:4096") as client:
    session = await client.create_session(bundle="foundation")
    async for event in client.prompt(session.id, "Hello!"):
        if event.type == "content.delta":
            print(event.data["delta"], end="", flush=True)
```

## Architecture

The SDK is a **client library** that communicates with a **separate server** (amplifier-app-runtime):

```
┌─────────────────────────────────────────────────────────────────────┐
│  Your App (uses SDK)                                                │
│      │                                                              │
│      │ Uses: import { AmplifierClient } from "amplifier-sdk"       │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │       Amplifier SDK (THIS PACKAGE)                          │   │
│  │         • TypeScript or Python client library               │   │
│  │         • HTTP client + SSE streaming                       │   │
│  │         • Type-safe API wrappers                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│      │                                                              │
│      │ HTTP + SSE (streaming)                                       │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │       amplifier-app-runtime (SEPARATE SERVER)               │   │
│  │         • localhost:4096                                    │   │
│  │         • REST API + SSE streaming                          │   │
│  │         • Session management                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│      │                                                              │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         amplifier-foundation + amplifier-core               │   │
│  │           (Bundles, Providers, Tools, Agents)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Think of it like:** AWS SDK (this) + AWS Services (runtime)

## SDKs

| Language | Package | Status |
|----------|---------|--------|
| Python | [sdks/python](sdks/python) | ✅ Ready |
| TypeScript | [sdks/typescript](sdks/typescript) | ✅ Ready |

## Quick Start

### 1. Start the Server

```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --port 4096
```

### 2. Use the SDK

**Python:**
```python
import asyncio
from amplifier_sdk import AmplifierClient

async def main():
    async with AmplifierClient() as client:
        # Create a session
        session = await client.create_session(bundle="foundation")
        
        # Stream a response
        async for event in client.prompt(session.id, "Hello!"):
            if event.type == "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)
        
        # Clean up
        await client.delete_session(session.id)

asyncio.run(main())
```

**TypeScript:**
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

// Clean up
await client.deleteSession(session.id);
```

**curl:**
```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:4096/v1/session \
  -H "Content-Type: application/json" \
  -d '{"bundle": "foundation"}')

SESSION_ID=$(echo $SESSION | jq -r '.id')

# Send prompt (streaming)
curl -N -X POST "http://localhost:4096/v1/session/$SESSION_ID/prompt" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"content": "Hello!"}'

# Or synchronous
curl -X POST "http://localhost:4096/v1/session/$SESSION_ID/prompt/sync" \
  -H "Content-Type: application/json" \
  -d '{"content": "What is 2+2?"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/ping` | GET | Health check |
| `/v1/capabilities` | GET | Server capabilities |
| `/v1/session` | GET | List sessions |
| `/v1/session` | POST | Create session |
| `/v1/session/{id}` | GET | Get session |
| `/v1/session/{id}` | DELETE | Delete session |
| `/v1/session/{id}/prompt` | POST | Send prompt (streaming SSE) |
| `/v1/session/{id}/prompt/sync` | POST | Send prompt (wait for completion) |
| `/v1/session/{id}/cancel` | POST | Cancel execution |
| `/v1/session/{id}/approval` | POST | Respond to approval |

## Event Types

| Event | Description |
|-------|-------------|
| `content.delta` | Streaming text chunk |
| `content.end` | Content complete |
| `thinking.delta` | Reasoning/thinking |
| `tool.call` | Tool being called |
| `tool.result` | Tool result |
| `approval.required` | User approval needed |
| `agent.spawned` | Sub-agent started |
| `agent.completed` | Sub-agent finished |
| `error` | Error occurred |

## Documentation

- **[Getting Started](sdks/GETTING_STARTED.md)** - Installation and first steps
- **[API Reference](sdks/API_REFERENCE.md)** - Complete API documentation
- **[Security Guide](sdks/SECURITY.md)** - Security best practices
- **[Testing](sdks/TESTING.md)** - Test coverage and strategy
- **[Examples](sdks/EXAMPLES.md)** - Code snippets and patterns
- **[Roadmap](docs/SDK_ROADMAP.md)** - Feature roadmap
- **[Sprints](docs/SPRINTS.md)** - Development sprint tracking

## Key Features

### Client-Side Tools

Define tools that run in YOUR app, not on the server:

```typescript
client.registerTool({
  name: "get-customer",
  description: "Query your database",
  handler: async ({ customerId }) => {
    return await yourDatabase.customers.findById(customerId);
  }
});

// Use in session
const session = await client.createSession({
  bundle: {
    name: "support-agent",
    clientTools: ["get-customer"]  // Runs locally!
  }
});
```

**Benefits:** Zero deployment, instant hot-reload, direct access to your APIs.

### Event Handlers

Subscribe to specific events:

```typescript
client.on("tool.call", (event) => {
  console.log(`🔧 ${event.data.tool_name}`);
});

client.on("content.delta", (event) => {
  process.stdout.write(event.data.delta);
});
```

### Automatic Approvals

```typescript
client.onApproval(async (request) => {
  const userChoice = await showDialog(request.prompt);
  return userChoice;  // SDK auto-responds
});
```

### Event Correlation

Match tool calls to their results:

```typescript
if (event.type === "tool.call") {
  const callId = event.toolCallId;  // Use this to match
}

if (event.type === "tool.result") {
  const callId = event.toolCallId;  // Matches the call!
}
```

## Examples

See the `examples/` directory for working applications:

- **[Agent Playground](examples/agent-playground/)** - Interactive agent builder with all SDK features
- **[Chat App](examples/chat-app/)** - Simple chat interface

## Development

### Python SDK

```bash
cd sdks/python
uv sync
uv run pytest                 # Run tests (21 tests)
uv run ruff format src/       # Format code
```

### TypeScript SDK

```bash
cd sdks/typescript
npm install
npm run build                 # Build SDK
npm test                      # Run tests (71 tests)
npm run typecheck             # Type checking
```

## Project Status

**Current Version:** 0.1.0 (pre-release)  
**Test Coverage:** 92 tests (100% pass rate)  
**Phase 1:** ✅ Complete  
**Phase 2:** ✅ Complete  
**Sprint 3:** 📍 Documentation (in progress)

See [SPRINTS.md](docs/SPRINTS.md) for development tracking.

## Contributing

Contributions welcome! Please:

1. Read the [Getting Started](sdks/GETTING_STARTED.md) guide
2. Check [open issues](https://github.com/manojp99/amplifier-sdk/issues)
3. Follow the existing code style
4. Add tests for new features
5. Update documentation

## License

MIT
