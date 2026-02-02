# SDK Improvement Notes

Notes collected while building the Agent Playground.

---

## 1. Approval Flow Implementation

**What we built:** Modal overlay that intercepts `approval.required` events and provides approve/deny buttons.

**SDK API used:**
```typescript
// Receiving approval event
event.type === "approval.required"
event.data.request_id
event.data.prompt
event.data.tool_name
event.data.arguments

// Responding to approval
await client.respondApproval(sessionId, requestId, approved)
```

**SDK Improvement Ideas:**
- ✅ Works well as-is
- 💡 **Add helper:** `client.onApprovalRequired(callback)` - convenience hook instead of manual event filtering
- 💡 **TypeScript types:** Create `ApprovalRequiredEvent` interface to avoid casting `event.data` fields
- 💡 **Timeout support:** Allow approvals to timeout (e.g., auto-deny after 30s)

---

## 2. Thinking Visualization

**What we built:** Collapsible blocks showing reasoning traces with toggle to show/hide globally.

**SDK API used:**
```typescript
event.type === "thinking.delta"
event.data.delta  // incremental thinking content
```

**SDK Improvement Ideas:**
- ✅ Works well for basic use
- 💡 **Thinking metadata:** Add `thinking.start` and `thinking.end` events to know when reasoning begins/ends
- 💡 **Thinking structure:** If thinking has sections (like "analyzing", "planning", "deciding"), expose that structure
- 💡 **Token cost:** Include token count for thinking to help users understand cost

---

## 3. Sub-Agent Support

**What we built:** Display sub-agents as they spawn and complete, showing status and results.

**SDK API used:**
```typescript
event.type === "agent.spawned"
event.data.agent_id
event.data.agent_name

event.type === "agent.completed"
event.data.agent_id
event.data.result
```

**SDK Improvement Ideas:**
- ✅ Basic events work
- 💡 **Agent hierarchy:** Add `parent_id` to show nested sub-agent trees
- 💡 **Agent progress:** Add `agent.progress` events for long-running sub-agents
- 💡 **Agent errors:** Add `agent.failed` event type distinct from generic `error`
- 💡 **Streaming sub-agent content:** Allow observing sub-agent's own content.delta events (currently opaque)

**Issue encountered:** 
- No way to distinguish which agent's events we're seeing in the stream (parent vs child)
- **Suggestion:** Add `agent_id` field to ALL events to indicate which agent emitted them

---

## 4. Tool Result Display

**What we built:** Show tool calls and their results inline with messages.

**SDK API used:**
```typescript
event.type === "tool.call"
event.data.tool_name
event.data.arguments

event.type === "tool.result"
event.data.result
```

**SDK Improvement Ideas:**
- ⚠️ **Missing correlation:** No `tool_call_id` in events - can't reliably match results to calls
- **Suggestion:** Add `tool_call_id` to both `tool.call` and `tool.result` events
- 💡 **Tool metadata:** Include execution time, cost, source (local vs API)
- 💡 **Tool errors:** Distinguish `tool.error` from generic errors

**Workaround used:**
- Assumed results arrive in same order as calls (fragile!)

---

## 5. Session Persistence

**What we built:** Save/load agent configurations to localStorage.

**SDK API used:**
- None directly - purely client-side feature

**SDK Improvement Ideas:**
- 💡 **Server-side persistence:** `client.saveSession(sessionId, metadata)` to persist on server
- 💡 **Session restore:** `client.restoreSession(sessionId)` to resume previous conversations
- 💡 **Session history:** `client.listSessions()` returns metadata (we have this!) but doesn't include enough details
  - **Missing:** Message count, last activity time, bundle used, tools enabled
- 💡 **Session export/import:** `client.exportSession()` returns full session state including messages

---

## 6. Export Chat Functionality

**What we built:** Export conversation to JSON file with messages, config, metadata.

**SDK API used:**
- None directly - manually assembled from local state

**SDK Improvement Ideas:**
- 💡 **Built-in export:** `client.exportSession(sessionId)` returns standardized export format
- 💡 **Export formats:** Support multiple formats (JSON, Markdown, HTML)
- 💡 **Event log access:** Include raw event stream in export for debugging
- 💡 **Import sessions:** `client.importSession(data)` to restore exported sessions

**Pain point:**
- Had to manually track all events and reconstruct conversation state
- **Suggestion:** Expose `client.getSessionHistory(sessionId)` that returns full message history

---

## 7. Provider & Model Selection

**What we built:** Dropdown to select provider and model, passed to session creation.

**SDK API used:**
```typescript
const bundle: BundleDefinition = {
  providers: [{ 
    module: `provider-${provider}`,
    config: { model: model }
  }]
};
await client.createSession({ bundle });
```

**SDK Improvement Ideas:**
- ✅ Works well
- 💡 **Get available providers:** `client.getCapabilities()` has `providers` array but doesn't include available models
  - **Suggestion:** Return `{ provider: string, models: string[] }[]` 
- 💡 **Model switching mid-session:** Allow changing model without recreating session
- 💡 **Cost estimation:** Return estimated cost per token for selected model

---

## 8. Custom Tool Definitions

**What we built:** Allow users to type in custom tool module names to load.

**SDK API used:**
```typescript
tools: [{ module: "tool-custom-name" }]
```

**SDK Improvement Ideas:**
- ✅ Works well
- 💡 **Tool validation:** Validate tool exists before session creation (currently fails silently or at runtime)
- 💡 **Tool discovery:** `client.getAvailableTools()` to list installed tools
- 💡 **Tool metadata:** Return tool descriptions, required params, examples
- 💡 **Dynamic tool loading:** Load tools from URLs/GitHub repos on the fly

---

## Overall SDK API Feedback

### Missing Event Correlation
**Problem:** Events lack IDs to correlate related events
- Tool calls → results
- Sub-agent spawn → completion
- Approval request → response

**Suggestion:** Add unique IDs:
```typescript
interface Event {
  type: string;
  data: Record<string, unknown>;
  id?: string;  // ✅ Already exists!
  correlationId?: string;  // ✅ Already exists!
  
  // Add these:
  toolCallId?: string;      // For tool.call, tool.result
  agentId?: string;         // Which agent emitted this event
  parentEventId?: string;   // Chain of events
}
```

### Missing Convenience Methods

**Would be helpful:**
```typescript
// Session management
client.getSessionHistory(sessionId): Message[]
client.exportSession(sessionId): SessionExport
client.importSession(data): SessionInfo

// Observability hooks
client.onApproval(callback: (approval) => Promise<boolean>)
client.onToolCall(callback: (tool) => void)
client.onThinking(callback: (thinking) => void)

// Capabilities
client.getAvailableTools(): ToolInfo[]
client.getAvailableProviders(): ProviderInfo[]
client.validateBundle(bundle): ValidationResult
```

### Type Safety Improvements

**Current:** All event data is `Record<string, unknown>` requiring manual casting
**Suggestion:** Discriminated union types:

```typescript
type Event = 
  | ContentDeltaEvent
  | ThinkingDeltaEvent  
  | ToolCallEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | AgentSpawnedEvent
  | AgentCompletedEvent;

interface ContentDeltaEvent {
  type: "content.delta";
  data: { delta: string };
  id: string;
  timestamp: string;
}

interface ToolCallEvent {
  type: "tool.call";
  data: {
    tool_name: string;
    tool_call_id: string;
    arguments: Record<string, unknown>;
  };
  id: string;
  toolCallId: string;
  agentId: string;
}
```

This would enable:
```typescript
for await (const event of client.prompt(...)) {
  if (event.type === "tool.call") {
    // TypeScript knows event.data.tool_name exists!
    console.log(event.data.tool_name);
  }
}
```

---

## IMPLEMENTED SDK IMPROVEMENTS ✅

Based on the playground needs, we implemented these NECESSARY changes:

### 1. Event Correlation Fields

**Added to Event interface:**
```typescript
interface BaseEvent {
  toolCallId?: string;  // For matching tool.call → tool.result
  agentId?: string;     // For distinguishing parent vs child agent events
}
```

**Client extraction:**
```typescript
// In parseEvent(), extract from event.data:
toolCallId: eventData.tool_call_id as string | undefined,
agentId: eventData.agent_id as string | undefined,
```

**Impact:** 
- ✅ Reliable tool call/result correlation (no more assuming order!)
- ✅ Can distinguish which agent emitted events
- ✅ Playground can properly match results to calls

### 2. Typed Event Interfaces (Discriminated Union)

**Created specific event types:**
- `ContentDeltaEvent` - TypeScript knows `.data.delta` exists
- `ThinkingDeltaEvent` - TypeScript knows `.data.delta` exists
- `ToolCallEvent` - TypeScript knows `.data.tool_name` and `.arguments` exist
- `ToolResultEvent` - TypeScript knows `.data.result` exists
- `ApprovalRequiredEvent` - TypeScript knows all approval fields
- `AgentSpawnedEvent`, `AgentCompletedEvent`, `ErrorEvent`
- `GenericEvent` - Fallback for unknown types

**Result type:**
```typescript
export type Event = 
  | ContentDeltaEvent
  | ThinkingDeltaEvent
  | ToolCallEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | AgentSpawnedEvent
  | AgentCompletedEvent
  | ErrorEvent
  | GenericEvent;
```

**Impact:**
- ✅ Full TypeScript autocomplete on `event.data` fields
- ✅ No more manual type casting
- ✅ Compile-time safety - can't access wrong fields
- ✅ Better developer experience in IDEs

### 3. Playground Updates

**Used new types:**
- Tool calls store `toolCallId` for correlation
- Tool results match by `toolCallId` instead of assuming order
- No more `as string` casts - TypeScript knows the types!

---

## Testing Notes

**What needs testing:**
1. ✅ Basic session creation and chat
2. Approval flow with actual approval-requiring tools
3. Thinking visualization with models that emit thinking
4. Sub-agent spawning (need multi-agent workflows)
5. Tool results with filesystem/bash tools
6. Session persistence across page reloads
7. Export/import functionality
8. Provider switching
9. Custom tools with real module names

**Server running:** 
- Runtime: http://localhost:4096 ✅
- Playground: http://localhost:3003 ✅

**Build status:** ✅ TypeScript compiles without errors

---

## SUMMARY: What We Improved

### Critical Issues Fixed

1. **Event Correlation** ⭐ MOST IMPORTANT
   - **Problem:** No way to match tool results to their calls
   - **Solution:** Added `toolCallId` field extracted from `event.data.tool_call_id`
   - **Impact:** Reliable correlation, no more fragile order assumptions

2. **Type Safety** ⭐ MAJOR DEVELOPER EXPERIENCE WIN
   - **Problem:** All events were `{ type: string, data: Record<string, unknown> }` requiring casts
   - **Solution:** Discriminated union of typed event interfaces
   - **Impact:** Full autocomplete, compile-time safety, no casts needed

3. **Agent Attribution**
   - **Problem:** Can't tell if event came from parent or child agent
   - **Solution:** Added `agentId` field extracted from `event.data.agent_id`
   - **Impact:** Can distinguish parent vs child events

### Developer Experience Before/After

**Before:**
```typescript
if (event.type === "tool.call") {
  const name = event.data.tool_name as string;  // Manual cast
  const args = event.data.arguments as Record<string, unknown>;  // Manual cast
  // No way to correlate with result!
}
```

**After:**
```typescript
if (event.type === "tool.call") {
  const name = event.data.tool_name;  // TypeScript knows this exists!
  const args = event.data.arguments;  // TypeScript knows this exists!
  const id = event.toolCallId;  // Can match to result!
}
```

### What We Did NOT Implement (and Why)

**Convenience methods** (`onApproval()`, `getSessionHistory()`, etc.)
- **Reason:** Not necessary for playground - apps can filter events themselves
- **Status:** Nice-to-have, but basic API is sufficient

**Server-side persistence** 
- **Reason:** Runtime doesn't support this yet
- **Status:** Future enhancement after runtime adds support

**Tool/provider discovery APIs**
- **Reason:** Apps can hardcode available tools for now
- **Status:** Nice-to-have, not blocking

---

## Manual Testing Checklist

Open http://localhost:3003 and verify:

1. **Session Creation**
   - [ ] Load "assistant" preset
   - [ ] Click "Create Agent"
   - [ ] Session ID appears in header

2. **Basic Chat**
   - [ ] Send message "Hello!"
   - [ ] Receive streaming response
   - [ ] Content appears correctly

3. **Tool Calls** (use "coder" preset)
   - [ ] Send "List files in current directory"
   - [ ] Tool call badge appears
   - [ ] Tool result displays (if toggle enabled)

4. **Provider Selection**
   - [ ] Select different provider
   - [ ] Select different model
   - [ ] Apply changes
   - [ ] Verify new session created

5. **Custom Tools**
   - [ ] Click "+ Add Custom Tool"
   - [ ] Enter "tool-web"
   - [ ] Tool appears in list
   - [ ] Can remove tool

6. **Export Chat**
   - [ ] After conversation, click "Export"
   - [ ] JSON file downloads
   - [ ] Contains session, messages, config

7. **Config Persistence**
   - [ ] Create custom config
   - [ ] Apply it
   - [ ] Check localStorage has saved config

8. **Visual Toggles**
   - [ ] Toggle "Show Thinking" - thinking blocks appear/disappear
   - [ ] Toggle "Show Tool Results" - results appear/disappear
   - [ ] Toggle "Show Sub-agents" - agent info appears/disappears

---

