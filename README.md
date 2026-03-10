# Amplifier SDK

A TypeScript client SDK for interacting with the [Amplifier](https://github.com/microsoft/amplifier) runtime server. The SDK handles session management, streaming AI responses, and recipe execution over a clean HTTP/SSE interface.

## Architecture

```
Your Application
      │
      │ @workspaces/amplifier-sdk  (this package)
      ▼
┌─────────────────────┐
│   AmplifierClient   │  HTTP + Server-Sent Events
└─────────┬───────────┘
          │  http://localhost:4096
          ▼
┌─────────────────────┐
│  amplifier-runtime  │  Python · Starlette · uvicorn
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   amplifier-core    │  AI agent kernel
└─────────────────────┘
```

The **TypeScript SDK** (`src/`) talks to the **Python runtime server** (`runtime/`) over HTTP and Server-Sent Events. The runtime manages AI agent sessions, streams events, and integrates with the amplifier-core ecosystem.

---

## Requirements

- **Node.js** ≥ 18
- **Python** ≥ 3.11 (for the runtime server)
- An LLM provider API key (Anthropic, OpenAI, Azure, or Google)

---

## Installation

### TypeScript SDK

```bash
npm install @workspaces/amplifier-sdk
# or
pnpm add @workspaces/amplifier-sdk
# or
yarn add @workspaces/amplifier-sdk
```

### Python Runtime Server

```bash
pip install amplifier-app-runtime
# or
uv pip install amplifier-app-runtime
```

---

## Quick Start

### 1. Start the runtime server

```bash
# Set your provider API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start the server (default: http://localhost:4096)
amplifier-runtime
```

### 2. Send your first prompt

```typescript
import { run } from "@workspaces/amplifier-sdk";

const response = await run("What is the capital of France?");
console.log(response.content); // "The capital of France is Paris."
```

### 3. Stream a response

```typescript
import { AmplifierClient } from "@workspaces/amplifier-sdk";

const client = new AmplifierClient();
const session = await client.createSession();

for await (const event of client.prompt(session.id, "Write me a haiku about TypeScript.")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

---

## Usage Examples

### One-shot request

```typescript
import { run } from "@workspaces/amplifier-sdk";

const response = await run("Summarize the Rust ownership model in 3 bullet points.");
console.log(response.content);
```

### Client with custom configuration

```typescript
import { AmplifierClient } from "@workspaces/amplifier-sdk";

const client = new AmplifierClient({
  baseUrl: "http://my-server:4096",
  timeout: 60_000,
  debug: true,
  onEvent: (event) => console.log("[event]", event.type),
});
```

### Session management

```typescript
const client = new AmplifierClient();

// Create a session
const session = await client.createSession({
  bundle: "foundation",
  provider: "anthropic",
  model: "claude-sonnet-4-5",
});

// Send a prompt and stream the response
for await (const event of client.prompt(session.id, "Hello!")) {
  if (event.type === "content.delta") process.stdout.write(event.data.delta);
}

// Resume later
const resumed = await client.resumeSession(session.id);
await resumed.sendSync("What did I just say?");

// Clean up
await client.deleteSession(session.id);
```

### Approval gates

```typescript
const client = new AmplifierClient();

// Automatically respond to approval requests
client.onApproval(async (request) => {
  console.log(`Approval requested: ${request.prompt}`);
  return "approve"; // or "deny"
});

const session = await client.createSession({
  bundle: "foundation",
});

for await (const event of client.prompt(session.id, "Delete the temp files.")) {
  if (event.type === "approval.required") {
    console.log("Tool needs approval:", event.data.tool_name);
  }
}
```

### Multi-agent tracking

```typescript
const client = new AmplifierClient();

client.onAgentSpawned((info) => {
  console.log(`Agent spawned: ${info.agent_name} (id: ${info.agent_id})`);
});

client.onAgentCompleted((info) => {
  console.log(`Agent completed: ${info.agent_id}`);
});

const session = await client.createSession();
for await (const event of client.stream("Run a multi-step research task.")) {
  // events flow here; agent lifecycle is tracked via handlers above
}

const hierarchy = client.getAgentHierarchy();
console.log("Agent tree:", hierarchy);
```

### Recipes

Build and execute multi-step agent workflows:

```typescript
const client = new AmplifierClient();

const recipe = client
  .recipe("code-review")
  .description("Automated code review workflow")
  .version("1.0.0")
  .step("analyze", (step) =>
    step
      .agent("reviewer")
      .prompt("Analyze the code in {{input_file}} for issues.")
      .output("analysis")
  )
  .step("report", (step) =>
    step
      .agent("writer")
      .prompt("Write a concise report from this analysis: {{analysis}}")
      .output("report")
  )
  .build();

client.saveRecipe(recipe);

const execution = await client.executeRecipe("code-review", {
  input_file: "src/auth.ts",
});

execution.on("step.completed", ({ stepId, output }) => {
  console.log(`Step ${stepId} done:`, output);
});
```

### Custom bundle definition

```typescript
const client = new AmplifierClient();

const session = await client.createSession({
  bundle: {
    name: "my-agent",
    providers: [{ module: "provider-anthropic" }],
    tools: [
      { module: "tool-bash" },
      { module: "tool-filesystem" },
    ],
    orchestrator: { module: "loop-streaming" },
    instructions: "You are a helpful DevOps assistant.",
    session: {
      maxTurns: 20,
    },
  },
});
```

---

## Module Catalog

The SDK ships a static catalog of known Amplifier modules:

```typescript
import { PROVIDERS, TOOLS, ORCHESTRATORS, CONTEXTS, HOOKS, findModule, getModulesByType } from "@workspaces/amplifier-sdk";

console.log(PROVIDERS);      // provider-anthropic, provider-openai, ...
console.log(TOOLS);          // tool-bash, tool-filesystem, ...
console.log(ORCHESTRATORS);  // loop-basic, loop-streaming, loop-events

const tool = findModule("tool-bash");
const allTools = getModulesByType("tool");
```

---

## Runtime Server Reference

### Starting the server

```bash
amplifier-runtime                            # default: 127.0.0.1:4096
amplifier-runtime --host 0.0.0.0 --port 8080
amplifier-runtime --log-level debug
amplifier-runtime --reload                   # auto-reload on code changes
```

### Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Auto-load Anthropic (Claude) provider |
| `OPENAI_API_KEY` | Auto-load OpenAI (GPT) provider |
| `AZURE_OPENAI_API_KEY` | Auto-load Azure OpenAI provider |
| `GOOGLE_API_KEY` | Auto-load Google (Gemini) provider |
| `AMPLIFIER_NO_PERSIST=1` | Disable all session disk writes |
| `AMPLIFIER_STORAGE_DIR` | Override session storage directory |
| `AMPLIFIER_MODULE_<ID>` | Override a module path for local dev |
| `LOG_LEVEL` | Log verbosity: `debug`, `info`, `warning`, `error` |

---

## Development

### Build the TypeScript SDK

```bash
npm install
npm run build     # outputs to dist/
npm run dev       # watch mode
```

### Run tests

```bash
# TypeScript
npm test

# Python runtime
cd runtime
pip install -e ".[dev]"
pytest
```

### Project structure

```
amplifier-sdk/
├── src/
│   ├── index.ts       # Public exports
│   ├── client.ts      # AmplifierClient + run()
│   ├── types.ts       # All types, interfaces, enums
│   ├── recipes.ts     # RecipeBuilder, StepBuilder
│   └── catalog.ts     # Static module catalog
├── runtime/           # Python runtime server (submodule)
└── docs/              # API reference
    ├── api.md         # TypeScript SDK reference
    └── rest-api.md    # HTTP REST API reference
```

---

## Documentation

- [TypeScript SDK API Reference](docs/api.md)
- [REST API Reference](docs/rest-api.md)
- [Runtime Server README](runtime/README.md)
- [Amplifier Ecosystem](https://github.com/microsoft/amplifier)

---

## License

MIT
