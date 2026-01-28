# Amplifier SDK

Multi-language SDKs for Amplifier, powered by a local HTTP server.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Your App (Python, TypeScript, Go, ...)            │
│      │                                              │
│      │ HTTP + SSE                                   │
│      ▼                                              │
│  ┌─────────────────────────────────────────────┐   │
│  │       amplifier-server (localhost)          │   │
│  │         REST API + Streaming                │   │
│  └─────────────────────────────────────────────┘   │
│      │                                              │
│      ▼                                              │
│  ┌─────────────────────────────────────────────┐   │
│  │         amplifier-foundation                │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start the Server

```bash
cd amplifier-server
pip install -e .

export ANTHROPIC_API_KEY=your-key
amplifier-server
```

### 2. Use from Any Language

**Python:**
```python
import httpx

client = httpx.Client(base_url="http://localhost:8080")

# Create agent
agent = client.post("/agents", json={
    "instructions": "You help with code.",
    "provider": "anthropic"
}).json()

# Run prompt
response = client.post(f"/agents/{agent['agent_id']}/run", json={
    "prompt": "Hello!"
}).json()

print(response["content"])
```

**TypeScript:**
```typescript
// Create agent
const agent = await fetch('http://localhost:8080/agents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ instructions: 'You help with code.', provider: 'anthropic' })
}).then(r => r.json());

// Run prompt
const response = await fetch(`http://localhost:8080/agents/${agent.agent_id}/run`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: 'Hello!' })
}).then(r => r.json());

console.log(response.content);
```

**curl:**
```bash
# Create agent
AGENT=$(curl -s -X POST http://localhost:8080/agents \
  -H "Content-Type: application/json" \
  -d '{"instructions": "You help with code.", "provider": "anthropic"}')

AGENT_ID=$(echo $AGENT | jq -r '.agent_id')

# Run prompt
curl -X POST "http://localhost:8080/agents/$AGENT_ID/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/agents` | POST | Create agent |
| `/agents/{id}/run` | POST | Execute prompt |
| `/agents/{id}/stream` | POST | Stream execution (SSE) |
| `/agents/{id}` | DELETE | Delete agent |
| `/recipes/execute` | POST | Execute recipe |
| `/recipes/{id}` | GET | Get execution status |

See [amplifier-server/README.md](amplifier-server/README.md) for full API documentation.

## Documentation

- [Why Server + SDK?](docs/WHY_SDK.md) - Architecture rationale
- [Server API Plan](docs/SERVER_API_PLAN.md) - Full API specification

## License

MIT
