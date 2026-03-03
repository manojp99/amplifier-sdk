# Amplifier Runtime

A thin HTTP server that exposes [Amplifier](https://github.com/microsoft/amplifier) AI agent capabilities over REST + SSE.

## Quick Start

```bash
cd services/amplifier-runtime
uv sync
uv run amplifier-runtime --port 4096
```

## Endpoints

All endpoints are under `/v1/`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check |
| GET | `/v1/session` | List active and saved sessions |
| POST | `/v1/session` | Create a new session |
| GET | `/v1/session/{id}` | Get session details |
| DELETE | `/v1/session/{id}` | Delete a session |
| POST | `/v1/session/{id}/prompt` | Execute prompt (SSE stream) |
| POST | `/v1/session/{id}/prompt/sync` | Execute prompt (blocking) |
| POST | `/v1/session/{id}/cancel` | Cancel running execution |
| POST | `/v1/session/{id}/approval` | Respond to approval gate |
| GET | `/v1/modules` | List installed Amplifier modules |
| GET | `/v1/event` | Global SSE event stream |

## Usage Examples

```bash
# Health check
curl http://localhost:4096/v1/health

# Create session
curl -X POST http://localhost:4096/v1/session \
  -H 'Content-Type: application/json' \
  -d '{"bundle": "default"}'

# Send prompt (SSE stream)
curl -N http://localhost:4096/v1/session/{id}/prompt \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Hello"}'

# List modules
curl http://localhost:4096/v1/modules
```

## CLI Options

```
amplifier-runtime                       # Start on default port (4096)
amplifier-runtime --port 8080           # Custom port
amplifier-runtime --host 0.0.0.0        # Bind to all interfaces
amplifier-runtime --reload              # Auto-reload on code changes
```

## Project Structure

```
src/amplifier_app_runtime/
├── app.py          # Starlette ASGI app + CORS
├── cli.py          # CLI entry point (uvicorn)
├── events.py       # Event types, Bus, SSE response
├── store.py        # Session persistence (JSON files)
├── bundles.py      # Bundle loading + module resolution
├── streaming.py    # Streaming hook, approval, display, spawn
├── sessions.py     # ManagedSession + SessionManager
└── routes.py       # HTTP route handlers
```

## Development

```bash
uv sync
uv run ruff check src/       # Lint
uv run ruff format src/       # Format
uv run pytest                 # Tests
```

## Docker (Production)

The Docker image is used for production builds, not for local development.

```bash
docker build -t amplifier-runtime .
docker run -p 4096:4096 amplifier-runtime
```

## License

MIT
