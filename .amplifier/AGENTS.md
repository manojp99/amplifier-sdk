# Amplifier SDK Repository

## Purpose

**This repository's primary goal is to TEST the Amplifier SDKs.**

The SDKs provide client libraries for apps to interact with `amplifier-app-runtime` via HTTP + SSE streaming.

## Architecture

```
Your App (examples/chat-app)
    │
    │  Uses SDK
    ▼
SDK (sdks/typescript/ or sdks/python/)
    │
    │  HTTP + SSE (streaming)
    ▼
amplifier-app-runtime (localhost:4096)
    │
    ▼
amplifier-foundation + amplifier-core
```

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `sdks/typescript/` | TypeScript SDK package |
| `sdks/python/` | Python SDK package |
| `examples/chat-app/` | Test app that uses the TypeScript SDK |
| `amplifier-app-runtime/` | Git submodule - the backend server |
| `docs/` | SDK roadmap and design docs |

## Development Workflow

### Starting the Test Environment

```bash
# 1. Start the runtime server (requires --http flag!)
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --http --port 4096

# 2. Start the chat app (uses the SDK)
cd examples/chat-app
npm run dev

# 3. Open http://localhost:3000
```

### Key Points

- The runtime MUST be started with `--http` flag (default is stdio mode)
- The chat app imports from `amplifier-sdk` package (linked from `sdks/typescript/`)
- Changes to the SDK require rebuilding: `cd sdks/typescript && npm run build`

## SDK Development

### TypeScript SDK

```bash
cd sdks/typescript
npm install
npm run build    # Build the SDK
npm test         # Run tests
```

### Python SDK

```bash
cd sdks/python
uv sync
uv run pytest    # Run tests
```

## Testing the SDK

The `examples/chat-app/` is the primary test vehicle:

1. It imports from `amplifier-sdk` (the TypeScript SDK)
2. Uses SDK methods like `client.createSession()`, `client.prompt()`
3. Displays real-time streamed content in a React UI

When making SDK changes:
1. Make changes in `sdks/typescript/src/`
2. Test in chat app (vite uses source directly via alias)

## CRITICAL: SDK-Only API Access

**Apps MUST use the SDK, not direct API calls.**

The whole point of this repo is to test the SDK layer. If apps call the runtime directly, the SDK isn't being tested.

### Enforcement

ESLint rule `amplifier/no-direct-api-calls` prevents direct API access:

```bash
# Run lint to check
cd examples/chat-app
npm run lint
```

**This will ERROR on:**
- `fetch('/v1/...')` - Direct API paths
- `fetch('http://localhost:4096/...')` - Direct runtime URLs

**Correct pattern:**
```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();
const session = await client.createSession({ bundle: "foundation" });
for await (const event of client.prompt(session.id, "Hello")) {
  // handle events
}
```

**Wrong pattern:**
```typescript
// DON'T DO THIS - bypasses SDK testing
fetch('/v1/session', { method: 'POST', ... });
```

## Current Phase

See `docs/SDK_ROADMAP.md` for the phased development plan.
See `docs/SPRINTS.md` for sprint-based development tracking.

**Phase 1:** ✅ Complete - session management, streaming, runtime bundles
**Phase 2:** ✅ Complete - client-side tools, approvals, session resume, event handlers
**Current Sprint:** Sprint 3 - Documentation (preparing for v0.1.0 release)
