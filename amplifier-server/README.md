# Amplifier Server

Local HTTP server exposing Amplifier capabilities via REST/SSE endpoints.

## Quick Start

```bash
# Install
pip install -e .

# Set API keys
export ANTHROPIC_API_KEY=your-key
export AMPLIFIER_API_KEY=your-server-api-key  # Optional, for auth

# Run
amplifier-server
```

Server runs at `http://localhost:8080`

## API Endpoints

### Health

```bash
curl http://localhost:8080/health
```

### Agents

```bash
# Create agent
curl -X POST http://localhost:8080/agents \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "You are a helpful assistant.",
    "tools": ["filesystem", "bash"],
    "provider": "anthropic"
  }'

# Run prompt
curl -X POST http://localhost:8080/agents/{agent_id}/run \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List files in current directory"}'

# Stream prompt (SSE)
curl -X POST http://localhost:8080/agents/{agent_id}/stream \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing"}'

# Delete agent
curl -X DELETE http://localhost:8080/agents/{agent_id} \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY"
```

### Recipes

```bash
# Execute recipe
curl -X POST http://localhost:8080/recipes/execute \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "recipe_yaml": "name: test\nsteps:\n  - id: step1\n    prompt: Hello",
    "context": {"project": "my-app"}
  }'

# Get execution status
curl http://localhost:8080/recipes/{execution_id} \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY"

# Approve gate
curl -X POST http://localhost:8080/recipes/{execution_id}/approve \
  -H "Authorization: Bearer $AMPLIFIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"step_id": "review-gate"}'
```

### OpenAPI Docs

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- OpenAPI JSON: http://localhost:8080/openapi.json

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AMPLIFIER_HOST` | `127.0.0.1` | Server host |
| `AMPLIFIER_PORT` | `8080` | Server port |
| `AMPLIFIER_API_KEY` | None | API key for auth (optional) |
| `AMPLIFIER_REQUIRE_AUTH` | `true` | Require API key |
| `AMPLIFIER_DEFAULT_PROVIDER` | `anthropic` | Default LLM provider |
| `AMPLIFIER_DEFAULT_MODEL` | None | Default model |
| `AMPLIFIER_MAX_SESSIONS` | `100` | Max concurrent sessions |
| `AMPLIFIER_LOG_LEVEL` | `info` | Log level |

Provider API keys:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `AZURE_OPENAI_API_KEY`

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Client (any language)                              │
│      │                                              │
│      │ HTTP + SSE                                   │
│      ▼                                              │
│  ┌─────────────────────────────────────────────┐   │
│  │         amplifier-server (FastAPI)          │   │
│  │  /agents  /recipes  /health                 │   │
│  └─────────────────────────────────────────────┘   │
│      │                                              │
│      ▼                                              │
│  ┌─────────────────────────────────────────────┐   │
│  │         amplifier-foundation                │   │
│  │   Bundles, Providers, Tools, Sessions       │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## License

MIT
