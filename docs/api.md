# TypeScript SDK API Reference

This document covers the complete public API of the `@workspaces/amplifier-sdk` package.

**Contents**
- [AmplifierClient](#amplifierclient)
- [Standalone Functions](#standalone-functions)
- [RecipeBuilder](#recipebuilder)
- [StepBuilder](#stepbuilder)
- [RecipeExecution](#recipeexecution)
- [Module Catalog](#module-catalog)
- [Types & Interfaces](#types--interfaces)
- [Enums](#enums)
- [Error Handling](#error-handling)

---

## AmplifierClient

The primary class for all SDK interactions.

```typescript
import { AmplifierClient } from "@workspaces/amplifier-sdk";

const client = new AmplifierClient(config?: ClientConfig);
```

### Constructor

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | [`ClientConfig`](#clientconfig) | No | Client configuration options |

**Defaults:** `baseUrl` = `http://localhost:4096`, `timeout` = `300000` ms

---

### Connection

#### `ping()`

Checks whether the runtime server is reachable.

```typescript
const alive = await client.ping(); // boolean
```

#### `capabilities()`

Returns the runtime server's capabilities.

```typescript
const caps = await client.capabilities();
// {
//   version: string,
//   streaming: boolean,
//   tools: string[],
//   providers: string[],
//   features: string[]
// }
```

#### `connectionState` _(getter)_

Returns the current [`ConnectionState`](#connectionstate).

```typescript
const state = client.connectionState; // ConnectionState
```

---

### Sessions

#### `createSession(config?)`

Creates a new AI agent session.

```typescript
const session = await client.createSession(config?: SessionConfig);
// Returns: SessionInfo
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | [`SessionConfig`](#sessionconfig) | No | Session options (bundle, provider, model, etc.) |

#### `getSession(sessionId)`

Retrieves session metadata.

```typescript
const session = await client.getSession(sessionId: string);
// Returns: SessionInfo
```

#### `listSessions()`

Returns all known sessions.

```typescript
const sessions = await client.listSessions();
// Returns: SessionInfo[]
```

#### `resumeSession(sessionId)`

Resumes an existing session and returns a convenience wrapper with bound methods.

```typescript
const session = await client.resumeSession(sessionId: string);

// The returned object includes:
session.id              // string
session.send(content)   // AsyncGenerator<Event>  — streaming prompt
session.sendSync(content) // Promise<PromptResponse> — blocking prompt
session.cancel()        // Promise<boolean>
session.delete()        // Promise<boolean>
```

#### `deleteSession(sessionId)`

Deletes a session and frees its resources.

```typescript
const deleted = await client.deleteSession(sessionId: string);
// Returns: boolean
```

---

### Prompting

#### `prompt(sessionId, content)`

Sends a prompt to a session and streams back events via an async generator.

```typescript
for await (const event of client.prompt(sessionId: string, content: string)) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

Returns: `AsyncGenerator<Event>`

See [Event Types](#event-types) for all possible event shapes.

#### `promptSync(sessionId, content)`

Sends a prompt and waits for the full response before returning.

```typescript
const response = await client.promptSync(sessionId: string, content: string);
// Returns: PromptResponse
// { content: string, toolCalls: ToolCall[], sessionId?: string, stopReason?: string }
```

#### `cancel(sessionId)`

Cancels an in-progress prompt.

```typescript
const cancelled = await client.cancel(sessionId: string);
// Returns: boolean
```

#### `stream(content, config?)`

One-shot helper: creates a session, streams the response, then cleans up.

```typescript
for await (const event of client.stream(content: string, config?: SessionConfig & ClientConfig)) {
  // ...
}
```

Returns: `AsyncGenerator<Event>`

#### `run(content, config?)`

One-shot helper: creates a session, sends a blocking prompt, then cleans up.

```typescript
const response = await client.run(content: string, config?: SessionConfig & ClientConfig);
// Returns: PromptResponse
```

---

### Event Subscriptions

Subscribe to any event type emitted by the client.

#### `on(eventType, handler)`

```typescript
client.on(eventType: string, handler: (event: Event) => void): void
```

#### `off(eventType, handler)`

```typescript
client.off(eventType: string, handler: (event: Event) => void): void
```

#### `once(eventType, handler)`

Registers a one-time handler that removes itself after the first call.

```typescript
client.once(eventType: string, handler: (event: Event) => void): void
```

---

### Approval Handling

When a session requires human (or programmatic) approval before executing a tool:

#### `onApproval(handler)`

Registers an automatic approval handler. The handler receives an `ApprovalRequiredEvent` and should return `"approve"` or `"deny"`.

```typescript
client.onApproval(handler: (event: ApprovalRequiredEvent) => Promise<"approve" | "deny"> | "approve" | "deny"): void
```

#### `respondApproval(sessionId, requestId, choice)`

Manually responds to an approval request.

```typescript
await client.respondApproval(
  sessionId: string,
  requestId: string,
  choice: "approve" | "deny"
);
// Returns: boolean
```

---

### Agent Lifecycle Tracking

Monitor sub-agents spawned during multi-agent workflows.

#### `onAgentSpawned(handler)` / `offAgentSpawned(handler)`

```typescript
client.onAgentSpawned(handler: (event: AgentSpawnedEvent) => void): void
client.offAgentSpawned(handler: (event: AgentSpawnedEvent) => void): void
```

#### `onAgentCompleted(handler)` / `offAgentCompleted(handler)`

```typescript
client.onAgentCompleted(handler: (event: AgentCompletedEvent) => void): void
client.offAgentCompleted(handler: (event: AgentCompletedEvent) => void): void
```

#### `getAgentHierarchy()`

Returns a map of all tracked agents and their parent/child relationships.

```typescript
const hierarchy = client.getAgentHierarchy();
// Returns: Map<string, AgentNode>
// AgentNode: { agentId, agentName, parentId?, children: string[], spawned, completed? }
```

#### `clearAgentHierarchy()`

Resets the tracked agent tree.

```typescript
client.clearAgentHierarchy(): void
```

---

### Thinking / Reasoning Stream

#### `onThinking(handler)` / `offThinking(handler)`

Subscribe to the AI's intermediate thinking steps when supported by the model.

```typescript
client.onThinking(handler: (event: ThinkingDeltaEvent) => void): void
client.offThinking(handler: (event: ThinkingDeltaEvent) => void): void
```

#### `getThinkingState()`

```typescript
const state = client.getThinkingState();
// Returns: { isThinking: boolean, content: string }
```

#### `clearThinkingState()`

```typescript
client.clearThinkingState(): void
```

---

### Client-Side Tools

Register tools that execute in your application. The LLM can call them, but the handler runs locally — not on the server.

#### `registerTool(tool)`

```typescript
client.registerTool(tool: ClientTool): void
```

**`ClientTool` shape:**

```typescript
{
  name: string;
  description: string;
  parameters?: {
    type: "object";
    properties: Record<string, { type: string; description?: string; [key: string]: unknown }>;
    required?: string[];
  };
  handler: (args: Record<string, unknown>) => Promise<unknown> | unknown;
}
```

#### `unregisterTool(name)`

```typescript
client.unregisterTool(name: string): boolean
```

#### `getClientTools()`

```typescript
client.getClientTools(): ClientTool[]
```

---

### Behaviors

Behaviors are reusable capability packages that can be applied to sessions.

#### `defineBehavior(behavior)`

```typescript
const behavior = client.defineBehavior(behavior: BehaviorDefinition): BehaviorDefinition
```

#### `getBehavior(name)`

```typescript
client.getBehavior(name: string): BehaviorDefinition | undefined
```

#### `getBehaviors()`

```typescript
client.getBehaviors(): BehaviorDefinition[]
```

#### `removeBehavior(name)`

```typescript
client.removeBehavior(name: string): boolean
```

---

### Recipes

#### `recipe(name)`

Creates a new [`RecipeBuilder`](#recipebuilder) for building a multi-step workflow.

```typescript
const builder = client.recipe(name: string): RecipeBuilder
```

#### `saveRecipe(recipe)`

Saves a built recipe in the client for later execution.

```typescript
client.saveRecipe(recipe: RecipeDefinition): void
```

#### `getRecipe(name)`

```typescript
client.getRecipe(name: string): RecipeDefinition | undefined
```

#### `getRecipes()`

```typescript
client.getRecipes(): RecipeDefinition[]
```

#### `deleteRecipe(name)`

```typescript
client.deleteRecipe(name: string): boolean
```

#### `executeRecipe(nameOrPath, context?, sessionId?)`

Executes a recipe (by saved name, or a path to a YAML file) and returns a [`RecipeExecution`](#recipeexecution) handle.

```typescript
const execution = await client.executeRecipe(
  nameOrPath: string,
  context?: Record<string, unknown>,
  sessionId?: string
): Promise<RecipeExecution>
```

#### `resumeRecipe(sessionId)`

Resumes a previously interrupted recipe execution.

```typescript
const execution = await client.resumeRecipe(sessionId: string): Promise<RecipeExecution>
```

#### `approveRecipeStage(sessionId, stageName)`

```typescript
await client.approveRecipeStage(sessionId: string, stageName: string): Promise<void>
```

#### `denyRecipeStage(sessionId, stageName, reason?)`

```typescript
await client.denyRecipeStage(sessionId: string, stageName: string, reason?: string): Promise<void>
```

#### `cancelRecipe(sessionId)`

```typescript
await client.cancelRecipe(sessionId: string): Promise<void>
```

---

## Standalone Functions

### `run(content, config?)`

A convenience function for one-shot prompts. Automatically creates a session, sends the prompt, and deletes the session.

```typescript
import { run } from "@workspaces/amplifier-sdk";

const response = await run(
  content: string,
  config?: SessionConfig & ClientConfig
): Promise<PromptResponse>
```

**Example:**

```typescript
const { content } = await run("Summarize the Rust ownership model.");
console.log(content);
```

---

## RecipeBuilder

Fluent builder for constructing `RecipeDefinition` objects.

```typescript
const builder = client.recipe("my-recipe")
  .description("What this recipe does")
  .version("1.0.0")
  .author("Your Name")
  .tags(["automation", "code"])
  .context({ input_dir: "/src" })
  .recursion({ max_depth: 3, max_agents: 10 })
  .rateLimiting({ max_calls_per_minute: 20, on_limit: "wait" })
  .step("step-id", (step) => step.agent("myAgent").prompt("Do something"))
  .build();
```

### Methods

| Method | Parameters | Description |
|---|---|---|
| `.description(text)` | `string` | **(required)** Human-readable description |
| `.version(v)` | `string` | SemVer string (default: `"1.0.0"`) |
| `.author(name)` | `string` | Recipe author |
| `.tags(tags)` | `string[]` | Searchable tags |
| `.context(ctx)` | `Record<string, unknown>` | Default context variables for all steps |
| `.recursion(opts)` | `{ max_depth?: number, max_agents?: number }` | Recursion limits |
| `.rateLimiting(opts)` | `{ max_calls_per_minute?: number, on_limit?: "wait"\|"error" }` | Rate limit config |
| `.step(id, fn)` | `(id: string, fn: (step: StepBuilder) => StepBuilder)` | Add a step |
| `.build()` | — | Returns the final `RecipeDefinition`. Throws if `description` or `steps` are missing |

---

## StepBuilder

Passed into each `.step()` callback on `RecipeBuilder`. Configures individual recipe steps.

```typescript
.step("analyze", (step) =>
  step
    .agent("code-reviewer")
    .prompt("Analyze {{input_file}}")
    .output("analysis_result")
    .timeout(120)
    .onError("retry", 2)
    .requiresApproval("Approve this analysis?")
    .when("run_analysis", "==", true)
)
```

### Methods

| Method | Parameters | Description |
|---|---|---|
| `.agent(name)` | `string` | Agent to delegate this step to |
| `.mode(mode)` | `string` | Override the agent's mode |
| `.prompt(text)` | `string` | Prompt text (supports `{{variable}}` interpolation) |
| `.bash(command)` | `string` | Shell command to run instead of an agent prompt |
| `.output(varName)` | `string` | Store step output in this context variable |
| `.timeout(seconds)` | `number` | Step-level timeout in seconds |
| `.onError(strategy, maxRetries?)` | `"fail"\|"continue"\|"retry"`, `number?` | Error handling strategy |
| `.requiresApproval(prompt?)` | `string?` | Gate this step behind a human approval |
| `.when(variable, operator, value)` | `string, "=="\|"!="\|">"\|"<"\|">="\|"<="`, `unknown` | Conditional execution |

---

## RecipeExecution

Returned by `client.executeRecipe()`. Provides event hooks and state inspection.

```typescript
const execution = await client.executeRecipe("my-recipe", { input: "hello" });
```

### Properties

| Property | Type | Description |
|---|---|---|
| `id` | `string` | Recipe session ID |
| `recipe` | `string` | Recipe name |

### Event Hooks

```typescript
execution.on("step.started",   ({ stepId }) => { ... });
execution.on("step.completed", ({ stepId, output }) => { ... });
execution.on("step.failed",    ({ stepId, error }) => { ... });
execution.on("step.skipped",   ({ stepId, reason }) => { ... });
```

#### `onApproval(handler)`

Handle approval gates during execution.

```typescript
execution.onApproval(async ({ stepId, prompt }) => {
  const answer = await askUser(prompt);
  return answer === "yes" ? "approve" : "deny";
});
```

### State Inspection

```typescript
execution.getCurrentStep(): string | undefined    // ID of the running step
execution.getCompletedSteps(): string[]           // IDs of finished steps
execution.getSteps(): RecipeStep[]                // Full step definitions
```

---

## Module Catalog

The SDK ships a static catalog of all known Amplifier modules.

```typescript
import {
  MODULE_CATALOG,
  PROVIDERS,
  TOOLS,
  ORCHESTRATORS,
  CONTEXTS,
  HOOKS,
  findModule,
  getModulesByType,
  getAllModules,
} from "@workspaces/amplifier-sdk";
```

### Constants

| Constant | Type | Contents |
|---|---|---|
| `PROVIDERS` | `CatalogModule[]` | `provider-anthropic`, `provider-openai`, `provider-azure`, `provider-ollama`, `provider-google` |
| `TOOLS` | `CatalogModule[]` | `tool-bash`, `tool-filesystem`, `tool-web`, `tool-web-fetch`, `tool-task`, `tool-delegate`, `tool-recipes` |
| `ORCHESTRATORS` | `CatalogModule[]` | `loop-basic`, `loop-streaming`, `loop-events` |
| `CONTEXTS` | `CatalogModule[]` | `context-simple`, `context-persistent` |
| `HOOKS` | `CatalogModule[]` | `hook-logging`, `hook-approval`, `hook-shell`, `hook-redaction` |
| `MODULE_CATALOG` | `Record<string, CatalogModule[]>` | All modules grouped by type |

### Functions

#### `findModule(id)`

```typescript
const module = findModule("tool-bash");
// Returns: CatalogModule | undefined
```

#### `getModulesByType(type)`

```typescript
const tools = getModulesByType("tool");
// Returns: CatalogModule[]
// type: "provider" | "tool" | "orchestrator" | "context" | "hook"
```

#### `getAllModules()`

```typescript
const all = getAllModules();
// Returns: CatalogModule[]
```

### `CatalogModule` shape

```typescript
{
  id: string;
  type: "provider" | "tool" | "orchestrator" | "context" | "hook";
  name: string;
  description: string;
  defaultSource?: string;
}
```

---

## Types & Interfaces

### `ClientConfig`

Configuration passed to `new AmplifierClient(config)`.

```typescript
interface ClientConfig {
  baseUrl?: string;         // default: "http://localhost:4096"
  timeout?: number;         // default: 300000 (ms)
  defaultBundle?: string | BundleDefinition;
  onRequest?: (info: RequestInfo) => void;
  onResponse?: (info: ResponseInfo) => void;
  onError?: (error: AmplifierError) => void;
  onStateChange?: (info: StateChangeInfo) => void;
  onEvent?: (event: Event) => void;
  debug?: boolean;          // default: false — logs all HTTP requests/responses
}
```

### `SessionConfig`

Options for creating a session.

```typescript
interface SessionConfig {
  bundle?: string | BundleDefinition;
  provider?: string;
  model?: string;
  workingDirectory?: string;
  storageDirectory?: string;
  behaviors?: string[];
  mcpServers?: McpServerConfig[];
}
```

### `SessionInfo`

```typescript
interface SessionInfo {
  id: string;
  title?: string;
  state?: string;
  bundle?: string;
  createdAt?: string;
  updatedAt?: string;
}
```

### `PromptResponse`

Returned by `promptSync()`, `run()`, and `client.run()`.

```typescript
interface PromptResponse {
  content: string;
  toolCalls: ToolCall[];
  sessionId?: string;
  stopReason?: string;
}
```

### `BundleDefinition`

Inline bundle definition — use instead of a named bundle string to fully customize an agent session.

```typescript
interface BundleDefinition {
  name: string;
  version?: string;
  description?: string;
  providers?: ModuleConfig[];
  tools?: ModuleConfig[];
  clientTools?: string[];
  hooks?: ModuleConfig[];
  orchestrator?: ModuleConfig;
  context?: ModuleConfig;
  mcpServers?: McpServerConfig[];
  agents?: AgentConfig[];
  instructions?: string;
  session?: {
    debug?: boolean;
    maxTurns?: number;
    [key: string]: unknown;
  };
  includes?: string[];
  behaviors?: string[];
}
```

### `ModuleConfig`

```typescript
interface ModuleConfig {
  module: string;           // module ID, e.g. "tool-bash"
  source?: string;          // optional git+https:// or file:// URI
  config?: Record<string, unknown>;
}
```

### `BehaviorDefinition`

```typescript
interface BehaviorDefinition {
  name: string;
  description?: string;
  instructions?: string;
  tools?: ModuleConfig[];
  clientTools?: string[];
  providers?: ModuleConfig[];
  hooks?: ModuleConfig[];
}
```

### `AgentConfig`

```typescript
interface AgentConfig {
  name: string;
  description?: string;
  instructions?: string;
  tools?: string[];
}
```

### `Capabilities`

```typescript
interface Capabilities {
  version: string;
  streaming: boolean;
  tools: string[];
  providers: string[];
  features: string[];
}
```

### MCP Server Config

```typescript
type McpServerConfig = McpServerStdio | McpServerHttp | McpServerSse;

interface McpServerStdio {
  type: "stdio";
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

interface McpServerHttp {
  type: "http";
  url: string;
  headers?: Record<string, string>;
}

interface McpServerSse {
  type: "sse";
  url: string;
  headers?: Record<string, string>;
}
```

### `RecipeDefinition`

```typescript
interface RecipeDefinition {
  name: string;
  description: string;
  version: string;
  author?: string;
  created?: string;
  updated?: string;
  tags?: string[];
  context?: Record<string, unknown>;
  recursion?: {
    max_depth?: number;
    max_agents?: number;
  };
  rate_limiting?: {
    max_calls_per_minute?: number;
    on_limit?: "wait" | "error";
  };
  steps: RecipeStep[];
}
```

### `RecipeStep`

```typescript
interface RecipeStep {
  id: string;
  agent?: string;
  mode?: string;
  prompt?: string;
  type?: "agent" | "bash";
  command?: string;
  output?: string;
  timeout?: number;
  on_error?: "fail" | "continue" | "retry";
  max_retries?: number;
  requires_approval?: boolean;
  approval_prompt?: string;
  conditions?: Array<{
    variable: string;
    operator: "==" | "!=" | ">" | "<" | ">=" | "<=";
    value: unknown;
  }>;
  foreach?: {
    items: string;      // context variable name holding an array
    variable: string;   // loop variable name
    steps: RecipeStep[];
  };
}
```

---

## Event Types

All events emitted by `client.prompt()` and `client.stream()` are discriminated unions. Every event extends `BaseEvent`:

```typescript
interface BaseEvent {
  id?: string;
  correlationId?: string;
  sequence?: number;
  final?: boolean;
  timestamp?: string;
  toolCallId?: string;
  agentId?: string;
}
```

### `content.delta`

A chunk of the AI's streamed text response.

```typescript
{ type: "content.delta", data: { delta: string } }
```

### `content.end`

Marks the end of the AI's content stream for a turn.

```typescript
{ type: "content.end", data: {} }
```

### `thinking.delta`

A chunk of the AI's internal reasoning (when supported by the model).

```typescript
{ type: "thinking.delta", data: { delta: string } }
```

### `tool.call`

The AI is calling a tool.

```typescript
{
  type: "tool.call",
  data: {
    tool_name: string;
    tool_call_id?: string;
    arguments: Record<string, unknown>;
  }
}
```

### `tool.result`

The result of a tool invocation.

```typescript
{
  type: "tool.result",
  data: {
    tool_name?: string;
    tool_call_id?: string;
    result: unknown;
    error?: string;
  }
}
```

### `approval.required`

The session is paused awaiting human approval.

```typescript
{
  type: "approval.required",
  data: {
    request_id: string;
    prompt: string;
    tool_name?: string;
    arguments?: Record<string, unknown>;
  }
}
```

Respond with [`client.respondApproval()`](#respondapprovalsessionid-requestid-choice) or [`client.onApproval()`](#onapprovalhandler).

### `agent.spawned`

A sub-agent has been created.

```typescript
{
  type: "agent.spawned",
  data: {
    agent_id: string;
    agent_name: string;
    parent_id?: string;
  }
}
```

### `agent.completed`

A sub-agent has finished.

```typescript
{
  type: "agent.completed",
  data: {
    agent_id: string;
    result?: unknown;
    error?: string;
  }
}
```

### `error`

An error occurred during streaming.

```typescript
{
  type: "error",
  data: {
    error: string;
    code?: string;
    details?: Record<string, unknown>;
  }
}
```

---

## Enums

### `ConnectionState`

```typescript
enum ConnectionState {
  Disconnected = "disconnected",
  Connecting   = "connecting",
  Connected    = "connected",
  Reconnecting = "reconnecting",
  Error        = "error",
}
```

### `EventType`

Convenience constants for event type strings.

```typescript
enum EventType {
  ContentDelta     = "content.delta",
  ContentEnd       = "content.end",
  ThinkingDelta    = "thinking.delta",
  ToolCall         = "tool.call",
  ToolResult       = "tool.result",
  ApprovalRequired = "approval.required",
  AgentSpawned     = "agent.spawned",
  AgentCompleted   = "agent.completed",
  Error            = "error",
}
```

**Example:**

```typescript
import { EventType } from "@workspaces/amplifier-sdk";

for await (const event of client.prompt(sessionId, "Hello")) {
  if (event.type === EventType.ContentDelta) {
    process.stdout.write(event.data.delta);
  }
}
```

### `ErrorCode`

```typescript
enum ErrorCode {
  NETWORK_ERROR       = "NETWORK_ERROR",
  TIMEOUT             = "TIMEOUT",
  CONNECTION_REFUSED  = "CONNECTION_REFUSED",
  BAD_REQUEST         = "BAD_REQUEST",
  UNAUTHORIZED        = "UNAUTHORIZED",
  FORBIDDEN           = "FORBIDDEN",
  NOT_FOUND           = "NOT_FOUND",
  SERVER_ERROR        = "SERVER_ERROR",
  SESSION_NOT_FOUND   = "SESSION_NOT_FOUND",
  SESSION_EXPIRED     = "SESSION_EXPIRED",
  SESSION_BUSY        = "SESSION_BUSY",
  STREAM_ERROR        = "STREAM_ERROR",
  STREAM_ABORTED      = "STREAM_ABORTED",
  UNKNOWN             = "UNKNOWN",
}
```

---

## Error Handling

All SDK errors are instances of `AmplifierError`, which extends the native `Error` class.

```typescript
import { AmplifierError, ErrorCode } from "@workspaces/amplifier-sdk";

try {
  const session = await client.createSession();
  const response = await client.promptSync(session.id, "Hello");
} catch (err) {
  if (err instanceof AmplifierError) {
    console.error("Code:", err.code);        // ErrorCode
    console.error("HTTP status:", err.status); // number | undefined
    console.error("Request ID:", err.requestId); // string | undefined

    if (err.isRetryable) {
      // Retryable: NETWORK_ERROR, TIMEOUT, SERVER_ERROR
      console.log("Consider retrying this request.");
    }
  }
}
```

### `AmplifierError` fields

| Field | Type | Description |
|---|---|---|
| `message` | `string` | Human-readable description |
| `code` | [`ErrorCode`](#errorcode) | Machine-readable error code |
| `status` | `number \| undefined` | HTTP status code (if applicable) |
| `requestId` | `string \| undefined` | Server-side request ID for debugging |
| `cause` | `Error \| undefined` | Underlying original error |
| `isRetryable` | `boolean` | `true` for `NETWORK_ERROR`, `TIMEOUT`, `SERVER_ERROR` |
