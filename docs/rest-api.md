# REST API Reference

The Amplifier runtime server exposes an HTTP API that the TypeScript SDK communicates with. You can also call it directly from any HTTP client.

**Base URL:** `http://localhost:4096` (default)

**All endpoints are prefixed with `/v1/`.**

---

## Contents

- [Health & Capabilities](#health--capabilities)
- [Sessions](#sessions)
- [Prompting](#prompting)
- [Approvals](#approvals)
- [Modules](#modules)
- [Global Event Stream](#global-event-stream)
- [SSE Event Protocol](#sse-event-protocol)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Health & Capabilities

### `GET /v1/health`

Confirms the server is running.

**Response `200`**

```json
{
  "status": "ok"
}
```

---

## Sessions

### `GET /v1/session`

Returns all active (in-memory) and saved (on-disk) sessions.

**Response `200`**

```json
{
  "active": [
    {
      "id": "sess_abc123",
      "title": "My session",
      "state": "ready",
      "bundle": "foundation",
      "createdAt": "2024-01-01T12:00:00Z",
      "updatedAt": "2024-01-01T12:01:00Z"
    }
  ],
  "saved": []
}
```

---

### `POST /v1/session`

Creates a new AI agent session.

**Request body** (all fields optional)

```json
{
  "bundle": "foundation",
  "bundle_definition": { ... },
  "provider": "anthropic",
  "model": "claude-sonnet-4-5",
  "working_directory": "/home/user/project",
  "storage_directory": "/home/user/.sessions",
  "behaviors": ["code-review"],
  "client_tools": [
    {
      "name": "get_weather",
      "description": "Get weather for a city",
      "parameters": {
        "type": "object",
        "properties": {
          "city": { "type": "string" }
        },
        "required": ["city"]
      }
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `bundle` | `string` | Named bundle identifier (e.g. `"foundation"`) |
| `bundle_definition` | `object` | Inline bundle definition (see [BundleDefinition](#bundledefinition)) |
| `provider` | `string` | Provider module ID (e.g. `"provider-anthropic"`) |
| `model` | `string` | Model name (e.g. `"claude-sonnet-4-5"`) |
| `working_directory` | `string` | Working directory for tool execution |
| `storage_directory` | `string` | Directory for session persistence |
| `behaviors` | `string[]` | Behavior names to apply |
| `client_tools` | `object[]` | Client-side tool schemas (handlers run in the calling app) |

**Response `201`**

```json
{
  "id": "sess_abc123",
  "title": null,
  "state": "ready",
  "bundle": "foundation",
  "createdAt": "2024-01-01T12:00:00Z",
  "updatedAt": "2024-01-01T12:00:00Z"
}
```

**Response `400`** — invalid request body or bundle not found

**Response `500`** — session initialization failed

---

### `GET /v1/session/{id}`

Retrieves metadata for a single session.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Response `200`** — [SessionInfo](#sessioninfo)

**Response `404`**

```json
{ "error": "Session not found", "session_id": "sess_abc123" }
```

---

### `DELETE /v1/session/{id}`

Deletes a session and frees its resources.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Response `200`**

```json
{ "deleted": true, "session_id": "sess_abc123" }
```

**Response `404`**

```json
{ "deleted": false, "session_id": "sess_abc123", "error": "Session not found" }
```

---

## Prompting

### `POST /v1/session/{id}/prompt`

Sends a prompt to a session and streams back events.

This endpoint returns a **Server-Sent Events (SSE)** stream by default. Each event is a JSON object prefixed with `data: `.

Set the `Accept` header to `application/x-ndjson` to receive newline-delimited JSON instead.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Request headers**

| Header | Value | Description |
|---|---|---|
| `Content-Type` | `application/json` | Required |
| `Accept` | `text/event-stream` (default) or `application/x-ndjson` | Response format |

**Request body**

```json
{ "content": "Write a haiku about TypeScript." }
```

**Response `200`** — `Content-Type: text/event-stream`

```
data: {"type":"ack","data":{},"correlation_id":"req_xyz","sequence":0,"final":false}

data: {"type":"content.start","data":{},"correlation_id":"req_xyz","sequence":1,"final":false}

data: {"type":"content.delta","data":{"delta":"Angle brackets wrap"},"correlation_id":"req_xyz","sequence":2,"final":false}

data: {"type":"content.delta","data":{"delta":" the code in silent types"},"correlation_id":"req_xyz","sequence":3,"final":false}

data: {"type":"content.end","data":{},"correlation_id":"req_xyz","sequence":4,"final":false}

data: {"type":"result","data":{"content":"Angle brackets wrap the code in silent types","tool_calls":[],"turn":1,"state":"ready"},"correlation_id":"req_xyz","sequence":5,"final":true}
```

See [SSE Event Protocol](#sse-event-protocol) for all event types.

**Response `404`** — session not found

**Response `409`** — session is currently busy (another prompt is active)

**Response `500`** — internal error

---

### `POST /v1/session/{id}/prompt/sync`

Sends a prompt and waits for the full response before returning. Does not stream.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Request body**

```json
{ "content": "What is 2 + 2?" }
```

**Response `200`**

```json
{
  "session_id": "sess_abc123",
  "content": "4",
  "tool_calls": [],
  "turn": 1,
  "state": "ready"
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | `string` | Session ID |
| `content` | `string` | The full AI response text |
| `tool_calls` | `object[]` | Any tool calls made during the response |
| `turn` | `number` | Turn number within this session |
| `state` | `string` | Session state after completion |

**Response `404`** — session not found

**Response `409`** — session is busy

---

### `POST /v1/session/{id}/cancel`

Cancels a prompt that is currently in progress.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Response `200`**

```json
{ "cancelled": true, "session_id": "sess_abc123" }
```

**Response `404`** — session not found

---

## Approvals

Some tool calls require explicit approval before execution. When an approval is required, the SSE stream emits an `approval.required` event and the session pauses.

### `POST /v1/session/{id}/approval`

Responds to a pending approval request, allowing the session to resume.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | `string` | Session ID |

**Request body**

```json
{
  "request_id": "apr_abc123",
  "choice": "approve"
}
```

| Field | Type | Values | Description |
|---|---|---|---|
| `request_id` | `string` | — | The `request_id` from the `approval.required` event |
| `choice` | `string` | `"approve"` or `"deny"` | Whether to allow the tool to proceed |

**Response `200`**

```json
{ "responded": true, "session_id": "sess_abc123", "choice": "approve" }
```

**Response `404`** — session or approval request not found

**Approval workflow:**

```
1. Client sends POST /v1/session/{id}/prompt
2. Server streams: ...tool.call → approval.required (final=false, stream paused)
3. Client sends POST /v1/session/{id}/approval { request_id, choice: "approve" }
4. Server resumes stream: tool.result → content.delta → ... → result
```

---

## Modules

### `GET /v1/modules`

Lists all registered bundles available on the server.

**Response `200`**

```json
{
  "bundles": [
    {
      "name": "foundation",
      "description": "The standard Amplifier foundation bundle",
      "uri": "git+https://github.com/microsoft/amplifier-foundation@main"
    }
  ]
}
```

---

## Global Event Stream

### `GET /v1/event`

Opens a global SSE stream that emits all events from all sessions. Useful for monitoring, logging, or building dashboards.

**Response** — `Content-Type: text/event-stream`

Events are the same format as the per-session prompt stream (see [SSE Event Protocol](#sse-event-protocol)), but include events from all active sessions. Each event's `correlation_id` can be used to correlate it back to a specific session/request.

---

## SSE Event Protocol

All streaming endpoints use Server-Sent Events. Each frame is a JSON object on a `data:` line, followed by a blank line:

```
data: <json>\n\n
```

### Common Frame Fields

Every event frame shares these fields:

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Event type identifier |
| `data` | `object` | Event-specific payload |
| `correlation_id` | `string` | Links events from the same request |
| `sequence` | `number` | Monotonically increasing frame index |
| `final` | `boolean` | `true` on the last frame of a response turn |

### Event Sequence

A typical streaming turn follows this sequence:

```
ack
content.start
content.delta  (repeated)
content.end
result         (final=true)
```

If the AI calls tools:

```
ack
content.start
content.end
tool.call
tool.result
content.start
content.delta  (repeated)
content.end
result         (final=true)
```

If approval is required:

```
ack
...
tool.call
approval.required   ← stream pauses here
                    ← client sends POST /approval
tool.result
...
result              (final=true)
```

### Event Types

#### `ack`

Acknowledges that the prompt was received.

```json
{ "type": "ack", "data": {}, "final": false }
```

#### `content.start`

Marks the start of a content block.

```json
{ "type": "content.start", "data": {}, "final": false }
```

#### `content.delta`

A streamed chunk of the AI's response text.

```json
{
  "type": "content.delta",
  "data": { "delta": "Hello, " },
  "final": false
}
```

#### `content.end`

Marks the end of a content block.

```json
{ "type": "content.end", "data": {}, "final": false }
```

#### `thinking.delta`

A chunk of the AI's internal reasoning (extended thinking models only).

```json
{
  "type": "thinking.delta",
  "data": { "delta": "Let me think about this..." },
  "final": false
}
```

#### `tool.call`

The AI is invoking a tool.

```json
{
  "type": "tool.call",
  "data": {
    "tool_name": "bash",
    "tool_call_id": "tc_xyz",
    "arguments": { "command": "ls -la" }
  },
  "final": false
}
```

#### `tool.result`

The output of a tool invocation.

```json
{
  "type": "tool.result",
  "data": {
    "tool_name": "bash",
    "tool_call_id": "tc_xyz",
    "result": "total 48\ndrwxr-xr-x ...",
    "error": null
  },
  "final": false
}
```

#### `approval.required`

The session is paused waiting for approval. Respond with `POST /v1/session/{id}/approval`.

```json
{
  "type": "approval.required",
  "data": {
    "request_id": "apr_abc123",
    "prompt": "Allow the bash tool to run: rm -rf /tmp/cache?",
    "tool_name": "bash",
    "arguments": { "command": "rm -rf /tmp/cache" }
  },
  "final": false
}
```

#### `agent.spawned`

A sub-agent has been spawned (multi-agent workflows).

```json
{
  "type": "agent.spawned",
  "data": {
    "agent_id": "agent_child_1",
    "agent_name": "code-reviewer",
    "parent_id": "sess_abc123"
  },
  "final": false
}
```

#### `agent.completed`

A sub-agent has finished its task.

```json
{
  "type": "agent.completed",
  "data": {
    "agent_id": "agent_child_1",
    "result": "Review complete. Found 3 issues.",
    "error": null
  },
  "final": false
}
```

#### `result`

The final frame of a turn. Always has `final: true`.

```json
{
  "type": "result",
  "data": {
    "content": "The full assembled response text.",
    "tool_calls": [
      {
        "tool_name": "bash",
        "tool_call_id": "tc_xyz",
        "arguments": { "command": "ls -la" }
      }
    ],
    "turn": 2,
    "state": "ready"
  },
  "final": true
}
```

#### `error`

An error occurred. May be `final: true` (terminates the stream) or `final: false` (recoverable).

```json
{
  "type": "error",
  "data": {
    "error": "Provider rate limit exceeded",
    "code": "RATE_LIMIT",
    "details": {}
  },
  "final": true
}
```

---

## Error Responses

All error responses use standard HTTP status codes and return a JSON body:

```json
{
  "error": "Human-readable error message",
  "details": { ... }
}
```

| Status | Meaning |
|---|---|
| `400` | Bad request — invalid body, missing required fields, or invalid bundle |
| `404` | Resource not found — session, approval request, etc. |
| `409` | Conflict — session is busy (currently processing a prompt) |
| `500` | Internal server error |

---

## Data Models

### `SessionInfo`

```json
{
  "id": "sess_abc123",
  "title": "My session",
  "state": "ready",
  "bundle": "foundation",
  "createdAt": "2024-01-01T12:00:00Z",
  "updatedAt": "2024-01-01T12:01:00Z"
}
```

### Session States

| State | Description |
|---|---|
| `created` | Session created but not yet initialized |
| `ready` | Idle, ready to receive a prompt |
| `running` | Currently processing a prompt |
| `waiting_approval` | Paused at an approval gate |
| `paused` | Paused for another reason |
| `completed` | Session has completed its task |
| `error` | Session encountered an unrecoverable error |
| `cancelled` | Session was cancelled |

### `BundleDefinition`

Used in the `bundle_definition` field of `POST /v1/session`.

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "description": "A custom agent",
  "providers": [
    { "module": "provider-anthropic", "config": { "model": "claude-sonnet-4-5" } }
  ],
  "tools": [
    { "module": "tool-bash" },
    { "module": "tool-filesystem" }
  ],
  "orchestrator": {
    "module": "loop-streaming"
  },
  "context": {
    "module": "context-persistent"
  },
  "hooks": [
    { "module": "hook-logging" }
  ],
  "instructions": "You are a helpful DevOps assistant.",
  "session": {
    "maxTurns": 20,
    "debug": false
  },
  "mcpServers": [
    { "type": "stdio", "command": "my-mcp-server", "args": ["--port", "8080"] }
  ],
  "agents": [
    {
      "name": "code-reviewer",
      "description": "Reviews code for issues",
      "tools": ["tool-filesystem"]
    }
  ],
  "includes": ["foundation"],
  "behaviors": ["code-review"]
}
```

### Module IDs

**Providers**

| ID | Description |
|---|---|
| `provider-anthropic` | Anthropic Claude models |
| `provider-openai` | OpenAI GPT models |
| `provider-azure` | Azure OpenAI |
| `provider-ollama` | Local models via Ollama |
| `provider-google` | Google Gemini models |

**Tools**

| ID | Description |
|---|---|
| `tool-bash` | Execute shell commands |
| `tool-filesystem` | Read/write files |
| `tool-web` | Web search |
| `tool-web-fetch` | Fetch web content |
| `tool-task` | Sub-task delegation |
| `tool-delegate` | Agent delegation |
| `tool-recipes` | Recipe execution |

**Orchestrators**

| ID | Description |
|---|---|
| `loop-basic` | Standard request/response loop |
| `loop-streaming` | Streaming-optimized loop |
| `loop-events` | Event-driven loop |

**Contexts**

| ID | Description |
|---|---|
| `context-simple` | In-memory message history |
| `context-persistent` | Disk-persisted message history |

**Hooks**

| ID | Description |
|---|---|
| `hook-logging` | Log all session events |
| `hook-approval` | Intercept and gate tool calls |
| `hook-shell` | Execute shell commands on lifecycle events |
| `hook-redaction` | Redact sensitive data from events |

---

## cURL Examples

### Health check

```bash
curl http://localhost:4096/v1/health
```

### Create a session

```bash
curl -X POST http://localhost:4096/v1/session \
  -H "Content-Type: application/json" \
  -d '{"bundle": "foundation"}'
```

### Send a streaming prompt

```bash
curl -X POST http://localhost:4096/v1/session/sess_abc123/prompt \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"content": "What is the capital of France?"}' \
  --no-buffer
```

### Send a synchronous prompt

```bash
curl -X POST http://localhost:4096/v1/session/sess_abc123/prompt/sync \
  -H "Content-Type: application/json" \
  -d '{"content": "What is the capital of France?"}'
```

### Approve a tool call

```bash
curl -X POST http://localhost:4096/v1/session/sess_abc123/approval \
  -H "Content-Type: application/json" \
  -d '{"request_id": "apr_abc123", "choice": "approve"}'
```

### Delete a session

```bash
curl -X DELETE http://localhost:4096/v1/session/sess_abc123
```

### List available modules/bundles

```bash
curl http://localhost:4096/v1/modules
```
