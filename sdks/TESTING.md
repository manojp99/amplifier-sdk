# SDK Testing Documentation

## Test Coverage Summary

### TypeScript SDK

**Unit Tests:** ✅ 22/22 passing

| Test Category | Tests | Status |
|---------------|-------|--------|
| Connection (ping) | 2 | ✅ Pass |
| Session management | 6 | ✅ Pass |
| Prompt execution | 2 | ✅ Pass |
| Approval flow | 1 | ✅ Pass |
| One-shot helpers | 1 | ✅ Pass |
| **Typed events** | 7 | ✅ Pass |
| **Event correlation** | 3 | ✅ Pass |

**New Features Tested:**
- ✅ Discriminated union event types
- ✅ Type safety on event.data fields
- ✅ toolCallId extraction and correlation
- ✅ agentId extraction for parent/child distinction

**Integration Tests:** ⚠️ Partial (requires runtime configuration)
- ✅ Basic connection and capabilities
- ✅ Session lifecycle
- ✅ Content streaming
- ⏭️ Tool execution (skipped - needs provider setup)

### Python SDK

**Unit Tests:** ✅ 12/12 passing

| Test Category | Tests | Status |
|---------------|-------|--------|
| Connection (ping) | 2 | ✅ Pass |
| Session management | 2 | ✅ Pass |
| Prompt execution | 1 | ✅ Pass |
| Type parsing | 3 | ✅ Pass |
| **Event correlation** | 3 | ✅ Pass |
| **Tool call tracking** | 1 | ✅ Pass |

**New Features Tested:**
- ✅ tool_call_id extraction and correlation
- ✅ agent_id extraction for parent/child events
- ✅ Event.from_dict preserves correlation fields

**Integration Tests:** ❌ Not implemented yet

---

## What We Improved & Tested

### 1. Event Correlation (⭐ Critical Feature)

**TypeScript:**
```typescript
interface BaseEvent {
  toolCallId?: string;  // Correlate tool.call → tool.result
  agentId?: string;     // Track which agent emitted event
}
```

**Python:**
```python
@dataclass
class Event:
    tool_call_id: str | None = None
    agent_id: str | None = None
```

**Tests:**
- ✅ TypeScript: 3 correlation tests in client.test.ts
- ✅ Python: 3 correlation tests in test_client.py

### 2. Typed Event Interfaces (⭐ TypeScript Only)

**TypeScript:**
```typescript
type Event = 
  | ContentDeltaEvent
  | ToolCallEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | AgentSpawnedEvent
  | AgentCompletedEvent
  | ThinkingDeltaEvent
  | ErrorEvent
  | GenericEvent;
```

**Benefits:**
- Full autocomplete on event.data fields
- No manual type casting needed
- Compile-time safety

**Tests:**
- ✅ 7 type safety tests validating each event type

---

## Running Tests

### TypeScript Unit Tests

```bash
cd sdks/typescript
npm test
```

**Result:** 22/22 passing ✅

### Python Unit Tests

```bash
cd sdks/python
uv run pytest tests/
```

**Result:** 12/12 passing ✅

### Integration Tests (Manual)

**Prerequisites:**
1. Start runtime with provider configured:
   ```bash
   cd amplifier-app-runtime
   # Create .amplifier/settings.yaml with provider config
   .venv/bin/python -m amplifier_app_runtime.cli --http --port 4096
   ```

2. Run integration tests:
   ```bash
   cd sdks/typescript
   npm test tests/integration.test.ts
   ```

**Current Status:** 
- Basic tests pass (ping, capabilities, sessions)
- Tool execution tests timeout (provider configuration needed)

---

## Test Strategy

### Unit Tests (Mock-Based)
**What we test:**
- Request/response handling
- Error handling
- Type parsing and serialization
- Event correlation field extraction
- Type discrimination (TypeScript)

**Coverage:**
- All core SDK methods
- All new correlation features
- Type safety for typed events (TypeScript)

### Integration Tests (Real Runtime)
**What we test:**
- Actual HTTP communication
- SSE streaming
- Event structure from real server
- End-to-end workflows

**Limitations:**
- Requires runtime server running
- Requires provider configuration
- Slower execution (real AI calls)

### Playground Testing (Exploratory)
**What it validates:**
- SDK works in real React app
- Streaming UX is smooth
- All event types render correctly
- Complex workflows (approvals, sub-agents, etc.)

**Not automated** - manual verification in browser

---

## Coverage Gaps & Future Work

### Missing Unit Tests
- ❌ Streaming event parsing (TypeScript)
- ❌ Error code mapping
- ❌ Observability hooks (onRequest, onResponse, etc.)
- ❌ Connection state transitions

### Missing Integration Tests
- ❌ Approval flow end-to-end
- ❌ Sub-agent spawning
- ❌ Thinking visualization
- ❌ Python integration tests (none exist)

### Recommended Additions
1. **Snapshot tests** for event parsing
2. **Property-based tests** for type parsing
3. **Load tests** for streaming performance
4. **Multi-session tests** for concurrency

---

## Test Quality Assessment

### What's Well Tested ✅
- Core CRUD operations (sessions)
- Basic request/response flow
- **Event correlation fields** (new!)
- **Type safety** (TypeScript - new!)
- Error handling basics

### What Needs More Testing ⚠️
- Streaming edge cases (connection drops, partial events)
- Complex multi-agent scenarios
- Approval flow timeout handling
- Provider switching mid-session
- Large event payloads

### What's Not Tested ❌
- Performance/load characteristics
- Memory leaks in long-running streams
- Concurrent session handling
- Reconnection logic
- Network failure recovery

---

## Developer Testing Workflow

### Before Committing
```bash
# TypeScript
cd sdks/typescript
npm run build
npm test
npm run typecheck

# Python
cd sdks/python
uv run pytest tests/
uv run pyright
```

### Before Releasing
```bash
# Run integration tests (requires runtime)
cd sdks/typescript
npm test tests/integration.test.ts

# Manual playground testing
cd examples/agent-playground
npm run dev
# Test all features in browser
```

---

## Conclusion

**Unit test coverage:** ✅ Excellent (34 tests, 100% pass rate)

**Features tested:**
- ✅ Event correlation (toolCallId, agentId)
- ✅ Type safety (TypeScript typed events)
- ✅ Core SDK methods
- ✅ Error handling

**Integration testing:** ⚠️ Basic coverage, needs provider configuration

**Recommendation:** Unit tests provide solid foundation. Integration tests should be expanded once runtime provider setup is standardized.
