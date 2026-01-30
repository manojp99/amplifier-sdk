# Amplifier SDK

Multi-language SDKs for [amplifier-app-runtime](https://github.com/manojp99/amplifier-app-runtime).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Your App (Python, TypeScript, Go, ...)                             │
│      │                                                              │
│      │ HTTP + SSE (streaming)                                       │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │       amplifier-app-runtime (localhost:4096)                │   │
│  │         • REST API + SSE streaming                          │   │
│  │         • Session management                                │   │
│  │         • ACP protocol support                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│      │                                                              │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         amplifier-foundation + amplifier-core               │   │
│  │           (Bundles, Providers, Tools, Agents)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

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

## Project Structure

```
amplifier-sdk/
├── amplifier-app-runtime/    # Server (git submodule)
├── sdks/
│   ├── python/               # Python SDK
│   │   ├── src/amplifier_sdk/
│   │   │   ├── client.py     # HTTP client
│   │   │   └── types.py      # Type definitions
│   │   └── pyproject.toml
│   └── typescript/           # TypeScript SDK
│       ├── src/
│       │   ├── client.ts     # HTTP client
│       │   └── types.ts      # Type definitions
│       └── package.json
└── README.md
```

## Development

### Python SDK

```bash
cd sdks/python
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

### TypeScript SDK

```bash
cd sdks/typescript
npm install
npm run build
npm test
```

## License

MIT
