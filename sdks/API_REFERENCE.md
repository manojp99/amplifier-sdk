# Amplifier SDK API Reference

Complete API documentation for TypeScript and Python SDKs.

---

## AmplifierClient

The main client class for interacting with the Amplifier runtime.

### Constructor

**TypeScript:**
```typescript
new AmplifierClient(config?: ClientConfig)
```

**Python:**
```python
AmplifierClient(base_url: str = "http://localhost:4096", timeout: float = 300.0)
```

**Parameters:**
- `baseUrl` / `base_url` - Runtime server URL (default: `http://localhost:4096`)
- `timeout` - Request timeout in milliseconds/seconds (default: 300000ms / 300s)
- `debug` (TS only) - Enable debug logging
- Observability hooks (TS only): `onRequest`, `onResponse`, `onError`, `onStateChange`, `onEvent`

**Example:**
```typescript
const client = new AmplifierClient({
  baseUrl: "http://localhost:4096",
  timeout: 60000,
  debug: true
});
```

---

## Session Management

### createSession()

Create a new AI agent session.

**TypeScript:**
```typescript
createSession(config?: SessionConfig): Promise<SessionInfo>
```

**Python:**
```python
async def create_session(
    bundle: str | BundleDefinition | None = None,
    provider: str | None = None,
    model: str | None = None,
    working_directory: str | None = None
) -> SessionInfo
```

**Parameters:**
- `bundle` - Bundle name (string) or bundle definition (object)
- `provider` - Provider override (e.g., "anthropic", "openai")
- `model` - Model override (e.g., "claude-sonnet-4-5-20250514")
- `workingDirectory` / `working_directory` - Working directory for session
- `behaviors` - Additional behaviors to compose

**Returns:** `SessionInfo` with `id`, `title`, `state`, `createdAt`

**Example:**
```typescript
// With named bundle
const session = await client.createSession({ bundle: "foundation" });

// With runtime bundle definition
const session = await client.createSession({
  bundle: {
    name: "my-agent",
    instructions: "You are a helpful assistant",
    tools: [{ module: "tool-bash" }],
    clientTools: ["custom-tool"]
  }
});
```

**Throws:**
- `AmplifierError` (TS) / `httpx.HTTPError` (Python) on failure

---

### getSession()

Get information about a session.

**TypeScript:**
```typescript
getSession(sessionId: string): Promise<SessionInfo>
```

**Python:**
```python
async def get_session(session_id: str) -> SessionInfo
```

**Parameters:**
- `sessionId` / `session_id` - Session ID to retrieve

**Returns:** `SessionInfo`

**Throws:**
- `AmplifierError` / `ValueError` if sessionId is invalid
- `AmplifierError` / `httpx.HTTPError` if session not found

---

### listSessions()

List all active sessions.

**TypeScript:**
```typescript
listSessions(): Promise<SessionInfo[]>
```

**Python:**
```python
async def list_sessions() -> list[SessionInfo]
```

**Returns:** Array/list of `SessionInfo` objects

**Example:**
```typescript
const sessions = await client.listSessions();
console.log(`${sessions.length} active sessions`);
```

---

### deleteSession()

Delete a session.

**TypeScript:**
```typescript
deleteSession(sessionId: string): Promise<boolean>
```

**Python:**
```python
async def delete_session(session_id: str) -> bool
```

**Parameters:**
- `sessionId` / `session_id` - Session ID to delete

**Returns:** `true` if successful, `false` otherwise

**Throws:**
- `AmplifierError` / `ValueError` if sessionId is invalid

---

### resumeSession()

Resume a previous session (convenience method).

**TypeScript:**
```typescript
resumeSession(sessionId: string): Promise<{
  id: string;
  title: string;
  state: string;
  send: (content: string) => AsyncGenerator<Event>;
  sendSync: (content: string) => Promise<PromptResponse>;
  cancel: () => Promise<boolean>;
  delete: () => Promise<boolean>;
}>
```

**Python:**
```python
async def resume_session(session_id: str) -> dict[str, Any]
```

**Returns:** Session object with helper methods

**Example:**
```typescript
const session = await client.resumeSession("sess_abc123");
for await (const event of session.send("Continue")) {
  // Handle events
}
```

---

## Prompting

### prompt()

Send a prompt and stream the response.

**TypeScript:**
```typescript
prompt(sessionId: string, content: string): AsyncGenerator<Event>
```

**Python:**
```python
async def prompt(
    session_id: str,
    content: str,
    stream: bool = True
) -> AsyncIterator[Event]
```

**Parameters:**
- `sessionId` / `session_id` - Session ID
- `content` - Prompt text
- `stream` (Python only) - Whether to stream (default: True)

**Yields:** `Event` objects as they arrive

**Example:**
```typescript
for await (const event of client.prompt(sessionId, "Hello!")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

**Throws:**
- `AmplifierError` / `ValueError` if parameters invalid
- `AmplifierError` / `httpx.HTTPError` on request failure

---

### promptSync()

Send a prompt and wait for complete response.

**TypeScript:**
```typescript
promptSync(sessionId: string, content: string): Promise<PromptResponse>
```

**Python:**
```python
async def prompt_sync(session_id: str, content: str) -> PromptResponse
```

**Returns:** `PromptResponse` with `content`, `toolCalls`, `sessionId`, `stopReason`

**Example:**
```typescript
const response = await client.promptSync(sessionId, "What is 2+2?");
console.log(response.content);  // "4"
```

---

### cancel()

Cancel ongoing execution.

**TypeScript:**
```typescript
cancel(sessionId: string): Promise<boolean>
```

**Python:**
```python
async def cancel(session_id: str) -> bool
```

**Returns:** `true` if cancelled successfully

---

## Client-Side Tools

### registerTool()

Register a tool that executes in your app.

**TypeScript:**
```typescript
registerTool(tool: ClientTool): void
```

**Python:**
```python
def register_tool(tool: ClientTool) -> None
```

**Parameters:**
- `tool` - ClientTool object with `name`, `description`, `parameters`, `handler`

**Example:**
```typescript
client.registerTool({
  name: "get-weather",
  description: "Get current weather for a city",
  parameters: {
    type: "object",
    properties: {
      city: { type: "string", description: "City name" }
    },
    required: ["city"]
  },
  handler: async ({ city }) => {
    const response = await fetch(`https://api.weather.com/${city}`);
    return await response.json();
  }
});
```

**Throws:**
- `AmplifierError` / `ValueError` if tool definition is invalid

---

### unregisterTool()

Remove a registered client-side tool.

**TypeScript:**
```typescript
unregisterTool(name: string): boolean
```

**Python:**
```python
def unregister_tool(name: str) -> bool
```

**Returns:** `true` if tool was removed

---

### getClientTools()

Get all registered client-side tools.

**TypeScript:**
```typescript
getClientTools(): ClientTool[]
```

**Python:**
```python
def get_client_tools() -> list[ClientTool]
```

**Returns:** Array/list of registered tools

---

## Event Handlers (TypeScript Only)

### on()

Register an event handler.

```typescript
on(eventType: string, handler: (event: Event) => void | Promise<void>): void
```

**Parameters:**
- `eventType` - Event type to listen for (e.g., "tool.call", "content.delta")
- `handler` - Function called when event occurs

**Example:**
```typescript
client.on("tool.call", (event) => {
  console.log(`🔧 ${event.data.tool_name}`);
});

client.on("content.delta", (event) => {
  process.stdout.write(event.data.delta);
});
```

---

### off()

Unregister an event handler.

```typescript
off(eventType: string, handler: EventHandler): void
```

---

### once()

Register a one-time event handler (auto-unregisters after first call).

```typescript
once(eventType: string, handler: EventHandler): void
```

**Example:**
```typescript
client.once("content.end", (event) => {
  console.log("Response complete!");
});
```

---

### onApproval()

Register automatic approval handler.

**TypeScript:**
```typescript
onApproval(handler: (request: {
  requestId: string;
  prompt: string;
  toolName?: string;
  arguments?: Record<string, unknown>;
}) => Promise<boolean> | boolean): void
```

**Python:**
```python
def on_approval(handler: Callable) -> None
```

**Parameters:**
- `handler` - Function that receives approval request and returns boolean

**Example:**
```typescript
client.onApproval(async (request) => {
  const userChoice = await showDialog(request.prompt);
  return userChoice;  // SDK auto-responds with this value
});
```

---

## Agent Spawning Visibility

Track multi-agent workflows by subscribing to agent lifecycle events.

### onAgentSpawned()

Register a handler for agent spawned events.

**TypeScript:**
```typescript
onAgentSpawned(handler: AgentSpawnedHandler): void
```

**Python:**
```python
def on_agent_spawned(handler: AgentSpawnedHandler) -> None
```

**Parameters:**
- `handler` - Callback function for agent spawned events

**Handler Info:**
- `agentId` / `agent_id` (string) - Unique agent ID
- `agentName` / `agent_name` (string) - Agent name/type
- `parentId` / `parent_id` (string | null) - Parent agent ID, or null for root
- `timestamp` (string) - ISO timestamp

**Example:**
```typescript
client.onAgentSpawned((info) => {
  console.log(`🤖 ${info.agentName} spawned (${info.agentId})`);
  if (info.parentId) {
    console.log(`   Delegated by: ${info.parentId}`);
  }
});
```

**Python Example:**
```python
def handle_spawn(info):
    print(f"🤖 {info['agent_name']} spawned ({info['agent_id']})")
    if info['parent_id']:
        print(f"   Delegated by: {info['parent_id']}")

client.on_agent_spawned(handle_spawn)
```

---

### offAgentSpawned()

Unregister an agent spawned handler.

**TypeScript:**
```typescript
offAgentSpawned(handler: AgentSpawnedHandler): void
```

**Python:**
```python
def off_agent_spawned(handler: AgentSpawnedHandler) -> None
```

---

### onAgentCompleted()

Register a handler for agent completed events.

**TypeScript:**
```typescript
onAgentCompleted(handler: AgentCompletedHandler): void
```

**Python:**
```python
def on_agent_completed(handler: AgentCompletedHandler) -> None
```

**Parameters:**
- `handler` - Callback function for agent completed events

**Handler Info:**
- `agentId` / `agent_id` (string) - Agent ID
- `result` (string | undefined) - Agent result
- `error` (string | undefined) - Error message if failed
- `timestamp` (string) - ISO timestamp

**Example:**
```typescript
client.onAgentCompleted((info) => {
  console.log(`✅ Agent completed: ${info.agentId}`);
  if (info.error) {
    console.error(`   Error: ${info.error}`);
  } else if (info.result) {
    console.log(`   Result: ${info.result.substring(0, 100)}...`);
  }
});
```

---

### offAgentCompleted()

Unregister an agent completed handler.

**TypeScript:**
```typescript
offAgentCompleted(handler: AgentCompletedHandler): void
```

**Python:**
```python
def off_agent_completed(handler: AgentCompletedHandler) -> None
```

---

### getAgentHierarchy()

Get the current agent hierarchy tree.

**TypeScript:**
```typescript
getAgentHierarchy(): Map<string, AgentNode>
```

**Python:**
```python
def get_agent_hierarchy() -> dict[str, AgentNode]
```

**Returns:** Map/dict of agent IDs to `AgentNode` objects representing parent/child relationships

**Example:**
```typescript
const hierarchy = client.getAgentHierarchy();

// Find root agents (no parent)
const rootAgents = Array.from(hierarchy.values())
  .filter(node => node.parentId === null);

// Build tree visualization
function printTree(agentId: string, indent = 0) {
  const node = hierarchy.get(agentId);
  if (!node) return;
  
  console.log('  '.repeat(indent) + `${node.agentName} (${node.agentId})`);
  node.children.forEach(childId => printTree(childId, indent + 1));
}

rootAgents.forEach(node => printTree(node.agentId));
```

**Python Example:**
```python
hierarchy = client.get_agent_hierarchy()

# Find root agents
root_agents = [
    node for node in hierarchy.values() 
    if node.parent_id is None
]

# Print tree
def print_tree(agent_id: str, indent: int = 0):
    node = hierarchy.get(agent_id)
    if not node:
        return
    print('  ' * indent + f"{node.agent_name} ({node.agent_id})")
    for child_id in node.children:
        print_tree(child_id, indent + 1)

for node in root_agents:
    print_tree(node.agent_id)
```

---

### clearAgentHierarchy()

Clear the agent hierarchy. Useful when starting a new task or resetting state.

**TypeScript:**
```typescript
clearAgentHierarchy(): void
```

**Python:**
```python
def clear_agent_hierarchy() -> None
```

**Example:**
```typescript
// Between major tasks
client.clearAgentHierarchy();
```

---

## Approval System

### respondApproval()

Manually respond to an approval request.

**TypeScript:**
```typescript
respondApproval(sessionId: string, requestId: string, choice: string): Promise<boolean>
```

**Python:**
```python
async def respond_approval(session_id: str, request_id: str, choice: str) -> bool
```

**Parameters:**
- `sessionId` / `session_id` - Session ID
- `requestId` / `request_id` - Approval request ID (from `approval.required` event)
- `choice` - Choice value ("approve", "deny", "true", "false", etc.)

**Example:**
```typescript
for await (const event of client.prompt(sessionId, "Delete files")) {
  if (event.type === "approval.required") {
    const approved = await askUser(event.data.prompt);
    await client.respondApproval(sessionId, event.data.request_id, approved.toString());
  }
}
```

---

## Convenience Methods

### run()

One-shot execution (create session, run prompt, cleanup).

**TypeScript:**
```typescript
run(content: string, config?: SessionConfig): Promise<PromptResponse>
```

**Python:**
```python
# Not yet implemented in Python
```

**Example:**
```typescript
const response = await client.run("What is 2+2?", {
  bundle: { name: "math-helper", instructions: "Be concise" }
});
console.log(response.content);
```

---

### stream()

One-shot streaming (create session, stream, cleanup).

**TypeScript:**
```typescript
stream(content: string, config?: SessionConfig): AsyncGenerator<Event>
```

**Example:**
```typescript
for await (const event of client.stream("Hello!")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

---

## Health & Capabilities

### ping()

Check if runtime server is available.

**TypeScript:**
```typescript
ping(): Promise<boolean>
```

**Python:**
```python
async def ping() -> bool
```

**Returns:** `true` if server responds

**Example:**
```typescript
const isAvailable = await client.ping();
if (!isAvailable) {
  console.error("Runtime server not available");
}
```

---

### capabilities()

Get server capabilities.

**TypeScript:**
```typescript
capabilities(): Promise<Capabilities>
```

**Python:**
```python
# Not yet implemented
```

**Returns:** `Capabilities` object with `version`, `streaming`, `tools`, `providers`, `features`

---

## Types

### Event

Represents a server-sent event.

**TypeScript:**
```typescript
type Event = 
  | ContentDeltaEvent
  | ThinkingDeltaEvent
  | ToolCallEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | AgentSpawnedEvent
  | AgentCompletedEvent
  | ErrorEvent
  | GenericEvent;

interface ContentDeltaEvent {
  type: "content.delta";
  data: { delta: string };
  id?: string;
  toolCallId?: string;
  agentId?: string;
}
```

**Python:**
```python
@dataclass
class Event:
    type: str
    data: dict[str, Any]
    id: str = ""
    correlation_id: str | None = None
    tool_call_id: str | None = None
    agent_id: str | None = None
```

**Common Fields:**
- `type` - Event type (content.delta, tool.call, etc.)
- `data` - Event-specific payload
- `id` - Event ID
- `toolCallId` / `tool_call_id` - For correlating tool.call → tool.result
- `agentId` / `agent_id` - Which agent emitted this event

---

### SessionInfo

Information about a session.

**TypeScript:**
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

**Python:**
```python
@dataclass
class SessionInfo:
    id: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    state: str = "ready"
```

---

### BundleDefinition

Runtime bundle configuration.

**TypeScript:**
```typescript
interface BundleDefinition {
  name: string;
  version?: string;
  description?: string;
  
  // Capabilities
  providers?: ModuleConfig[];
  tools?: ModuleConfig[];          // Server-side tools
  clientTools?: string[];          // Client-side tools (SDK-handled)
  hooks?: ModuleConfig[];
  orchestrator?: ModuleConfig;
  context?: ModuleConfig;
  
  // Configuration
  agents?: AgentConfig[];
  instructions?: string;
  session?: Record<string, unknown>;
  includes?: string[];
}
```

**Python:**
```python
@dataclass
class BundleDefinition:
    name: str
    version: str = "1.0.0"
    description: str | None = None
    providers: list[ModuleConfig] = field(default_factory=list)
    tools: list[ModuleConfig] = field(default_factory=list)
    client_tools: list[str] = field(default_factory=list)
    # ... (same fields as TypeScript)
```

---

### AgentNode

Agent hierarchy node for tracking parent/child relationships.

**TypeScript:**
```typescript
interface AgentNode {
  agentId: string;
  agentName: string;
  parentId: string | null;
  children: string[];
  spawnedAt: string;
  completedAt: string | null;
  result?: string;
  error?: string;
}
```

**Python:**
```python
@dataclass
class AgentNode:
    agent_id: str
    agent_name: str
    parent_id: str | None
    children: list[str]
    spawned_at: str
    completed_at: str | None
    result: str | None
    error: str | None
```

**Fields:**
- `agentId` / `agent_id` - Unique agent identifier
- `agentName` / `agent_name` - Agent type (e.g., "foundation:explorer")
- `parentId` / `parent_id` - Parent agent ID (null for root agents)
- `children` - Array/list of child agent IDs
- `spawnedAt` / `spawned_at` - ISO timestamp when agent started
- `completedAt` / `completed_at` - ISO timestamp when agent finished (null if running)
- `result` - Agent result text (after completion)
- `error` - Error message if agent failed

---

### ClientTool

Client-side tool definition.

**TypeScript:**
```typescript
interface ClientTool {
  name: string;
  description: string;
  parameters?: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
  handler: (args: Record<string, unknown>) => Promise<unknown> | unknown;
}
```

**Python:**
```python
@dataclass
class ClientTool:
    name: str
    description: str
    handler: Callable[[dict[str, Any]], Any]
    parameters: dict[str, Any] = field(default_factory=dict)
```

---

### PromptResponse

Complete response from synchronous prompt.

**TypeScript:**
```typescript
interface PromptResponse {
  content: string;
  toolCalls: ToolCall[];
  sessionId?: string;
  stopReason?: string;
}
```

**Python:**
```python
@dataclass
class PromptResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    session_id: str = ""
    stop_reason: str = ""
```

---

### AmplifierError (TypeScript Only)

Structured error with error codes.

```typescript
class AmplifierError extends Error {
  readonly code: ErrorCode;
  readonly status?: number;
  readonly requestId?: string;
  readonly cause?: Error;
  readonly isRetryable: boolean;
}
```

**Error Codes:**
- `NetworkError` - Network/connection issues
- `Timeout` - Request timeout
- `ConnectionRefused` - Server not reachable
- `BadRequest` - Invalid parameters (400)
- `Unauthorized` - Auth required (401)
- `Forbidden` - Access denied (403)
- `NotFound` - Resource not found (404)
- `ServerError` - Server error (500)
- `StreamError` - Streaming issues
- `Unknown` - Unexpected errors

**Retryable Errors:**
- `NetworkError`, `Timeout`, `ServerError`

**Example:**
```typescript
try {
  await client.createSession();
} catch (err) {
  if (err instanceof AmplifierError) {
    console.error(`[${err.code}] ${err.message}`);
    
    if (err.isRetryable) {
      // Retry logic
    }
  }
}
```

---

## Event Types

### Content Events

**content.delta** - Incremental text content
```typescript
{
  type: "content.delta",
  data: { delta: string }
}
```

**content.end** - Content streaming complete
```typescript
{
  type: "content.end",
  data: { /* varies */ }
}
```

---

### Tool Events

**tool.call** - AI is calling a tool
```typescript
{
  type: "tool.call",
  data: {
    tool_name: string,
    tool_call_id: string,
    arguments: Record<string, unknown>
  },
  toolCallId: string  // For correlation
}
```

**tool.result** - Tool execution completed
```typescript
{
  type: "tool.result",
  data: {
    tool_call_id: string,
    result: unknown
  },
  toolCallId: string  // Matches tool.call
}
```

---

### Approval Events

**approval.required** - AI needs permission
```typescript
{
  type: "approval.required",
  data: {
    request_id: string,
    prompt: string,
    tool_name?: string,
    arguments?: Record<string, unknown>
  }
}
```

---

### Agent Events

**agent.spawned** - Sub-agent started
```typescript
{
  type: "agent.spawned",
  data: {
    agent_id: string,
    agent_name: string,
    parent_id?: string
  }
}
```

**agent.completed** - Sub-agent finished
```typescript
{
  type: "agent.completed",
  data: {
    agent_id: string,
    result?: string,
    error?: string
  }
}
```

---

### Thinking Events

**thinking.delta** - AI reasoning process
```typescript
{
  type: "thinking.delta",
  data: { delta: string }
}
```

---

### Error Events

**error** - Error occurred
```typescript
{
  type: "error",
  data: {
    error: string,
    code?: string,
    details?: Record<string, unknown>
  }
}
```

---

## Observability Hooks (TypeScript Only)

### onRequest

Called before each HTTP request.

```typescript
onRequest?: (info: RequestInfo) => void;

interface RequestInfo {
  requestId: string;
  method: string;
  url: string;
  headers?: Record<string, string>;
  body?: unknown;
  timestamp: Date;
}
```

---

### onResponse

Called after each HTTP response.

```typescript
onResponse?: (info: ResponseInfo) => void;

interface ResponseInfo {
  requestId: string;
  status: number;
  headers?: Record<string, string>;
  body?: unknown;
  durationMs: number;
  timestamp: Date;
}
```

---

### onError

Called when errors occur.

```typescript
onError?: (error: AmplifierError) => void;
```

---

### onStateChange

Called when connection state changes.

```typescript
onStateChange?: (info: StateChangeInfo) => void;

interface StateChangeInfo {
  from: ConnectionState;
  to: ConnectionState;
  reason?: string;
  timestamp: Date;
}

enum ConnectionState {
  Disconnected,
  Connecting,
  Connected,
  Reconnecting,
  Error
}
```

---

### onEvent

Called for every streaming event.

```typescript
onEvent?: (event: Event) => void;
```

---

## Python Context Manager

Python SDK supports async context manager for automatic cleanup:

```python
async with AmplifierClient() as client:
    session = await client.create_session(bundle="foundation")
    async for event in client.prompt(session.id, "Hello"):
        print(event.type)
    # Client automatically closed on exit
```

---

## Version

Get SDK version:

**TypeScript:**
```typescript
import { version } from "amplifier-sdk/package.json";
```

**Python:**
```python
from amplifier_sdk import __version__
print(__version__)  # "0.1.0"
```

---

## See Also

- **Getting Started:** `GETTING_STARTED.md` - Installation and first steps
- **Examples:** `EXAMPLES.md` - Code snippets and patterns
- **Security:** `SECURITY.md` - Security best practices
- **Testing:** `TESTING.md` - Test coverage details
