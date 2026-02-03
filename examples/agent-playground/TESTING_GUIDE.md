# Agent Playground Testing Guide

Comprehensive guide for testing all SDK features in the Agent Playground.

## Overview

The Agent Playground is a **feature-complete demonstration** of the Amplifier SDK, showcasing all 14 features across 4 development phases:

- ✅ **Phase 1** (3 features): Session CRUD, Streaming, Runtime Bundles
- ✅ **Phase 2** (4 features): Client-side Tools, Approvals, Event Handlers, Session Resume
- ✅ **Phase 3** (4 features): Agent Spawning, Thinking Stream, Behaviors, Sub-agent Config
- ✅ **Phase 4** (3 features): Recipes, Hooks, MCP Servers

**Coverage: 100%** (14/14 features)

---

## Prerequisites

### 1. Start the Runtime Server

```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --http --port 4096
```

**Verify it's running:**
```bash
curl http://localhost:4096/health
# Should return: {"status":"ok"}
```

### 2. Start the Playground

```bash
cd examples/agent-playground
npm install  # First time only
npm run dev
```

The playground will open at `http://localhost:3000` (or next available port).

### 3. Check Connection

Look for the **green "Connected"** status in the top-right header. If disconnected:
- Verify runtime is running on port 4096
- Check browser console for errors
- Refresh the page

---

## Feature Testing Guide

### 📦 Phase 1: Foundation Features

#### ✅ Feature 1: Session CRUD

**What it tests:** Creating, managing, and deleting AI agent sessions.

**Steps:**
1. Go to **Bundle Builder** tab
2. Configure an agent:
   - Name: `test-agent`
   - Instructions: "You are a helpful assistant"
3. Click **"Create Agent"**
4. Observe the session badge in the chat header (e.g., `sess_abc123...`)
5. Go to **Chat** tab and send a test message
6. Return to **Bundle Builder** and click **"Clear Chat"**
7. Change the agent name and click **"Apply Changes"** (deletes old session, creates new)

**Expected Results:**
- ✅ Session created successfully
- ✅ Session ID displayed in header
- ✅ Chat works with the session
- ✅ Old session deleted, new session created on config change

**Verify in Console:**
```
[Session] Created sess_... with bundle: {...}
```

---

#### ✅ Feature 2: Streaming Responses

**What it tests:** Real-time streaming of AI responses via async iterators.

**Steps:**
1. Create an agent (any configuration)
2. Go to **Chat** tab
3. Send a message: "Count from 1 to 10 slowly"
4. Watch the response stream in real-time (letter by letter)

**Expected Results:**
- ✅ Response appears progressively (not all at once)
- ✅ "..." indicator shows while streaming
- ✅ Message completes when streaming ends

**Verify in Code:**
The playground uses `for await (const event of client.prompt(...))` to stream events.

---

#### ✅ Feature 3: Runtime Bundle Definition

**What it tests:** Creating bundles programmatically (not from pre-existing bundle names).

**Steps:**
1. Go to **Bundle Builder** tab
2. Configure an agent with:
   - Custom name: `my-custom-agent`
   - Custom instructions
   - Selected tools: Filesystem, Bash
   - Provider: Anthropic
   - Model: claude-sonnet-4-5
3. Click **"Create Agent"**

**Expected Results:**
- ✅ Session created with custom bundle
- ✅ Tools available to the agent
- ✅ Provider/model configuration applied

**Verify in Console:**
```javascript
[Session] Created sess_... with bundle: {
  name: "my-custom-agent",
  instructions: "...",
  tools: [{module: "tool-filesystem"}, {module: "tool-bash"}],
  providers: [{module: "provider-anthropic", config: {model: "..."}}]
}
```

---

### 🛠️ Phase 2: Client-Side Features

#### ✅ Feature 4: Client-Side Tools

**What it tests:** Tools that run in the browser (not on the server).

**Steps:**
1. Go to **Bundle Builder** tab
2. Load the **"demo-client-tools"** preset
3. Click **"Create Agent"**
4. Go to **Chat** tab
5. Test each client-side tool:
   - "What time is it in Tokyo?" (uses `get-time`)
   - "Calculate 15 * 23" (uses `calculate`)
   - "Generate a random number between 1 and 100" (uses `get-random`)

**Expected Results:**
- ✅ Agent calls the client-side tools
- ✅ Tools execute in the browser (check Network tab - no server requests for tools)
- ✅ Tool results appear in the response

**Verify in Console:**
```
[Client Tool] Executing get-time with args: {"timezone":"Asia/Tokyo"}
[Client Tool] Result: {"timezone":"Asia/Tokyo","time":"10:30:45 PM",...}
```

---

#### ✅ Feature 5: Approval Flow

**What it tests:** Human-in-the-loop approvals for sensitive operations.

**Steps:**
1. Create an agent with Filesystem tool
2. Go to **Chat** tab
3. Ask: "Delete all files in /tmp" (or any destructive operation)
4. Wait for approval modal to appear

**Expected Results:**
- ✅ Modal appears with approval prompt
- ✅ Tool name and arguments displayed
- ✅ Clicking "Approve" allows operation to proceed
- ✅ Clicking "Deny" cancels the operation

**Note:** The playground uses `client.onApproval()` to handle approval requests automatically.

---

#### ✅ Feature 6: Event Handlers

**What it tests:** Subscribing to specific event types with convenience APIs.

**Steps:**
1. Create any agent
2. Go to **Chat** tab
3. Open browser console
4. Send a message that triggers tools or sub-agents
5. Observe event logs in console

**Expected Results:**
- ✅ `onAgentSpawned` fires when sub-agents are created
- ✅ `onAgentCompleted` fires when sub-agents finish
- ✅ `onThinking` fires and updates thinking display in UI

**Verify in Console:**
```
🤖 [Agent Spawned] foundation:zen-architect (agent_123...)
   Parent: sess_abc...
✅ [Agent Completed] agent_123...
```

**Code Reference:**
- `client.onThinking()` - Thinking stream (Phase 1 refactor)
- `client.onApproval()` - Approval gates (Phase 1 refactor)
- `client.onAgentSpawned()` - Agent spawning
- `client.onAgentCompleted()` - Agent completion

---

#### ✅ Feature 7: Session Resume

**What it tests:** Resuming previous sessions to continue conversations.

**Steps:**
1. Create an agent and have a conversation
2. Note the session ID in the header
3. Refresh the page (or close and reopen)
4. Use `client.getSession(sessionId)` to retrieve session info
5. Use `client.resumeSession(sessionId)` to continue

**Note:** The playground doesn't have UI for this yet, but the SDK APIs are demonstrated via the client methods.

**Test via Console:**
```javascript
const sessionId = "sess_abc123..."; // From header
const session = await client.getSession(sessionId);
console.log(session);
```

---

### 🚀 Phase 3: Advanced Features

#### ✅ Feature 8: Agent Spawning Visibility

**What it tests:** Tracking multi-agent workflows with hierarchy.

**Steps:**
1. Create an agent with "researcher" preset (or any that spawns sub-agents)
2. Go to **Chat** tab
3. Enable **"Show Sub-agents"** and **"Show Agent Tree"** toggles
4. Ask: "Research the latest developments in AI" (triggers delegation)
5. Watch the agent hierarchy panel populate

**Expected Results:**
- ✅ Sub-agent spawning shown in messages
- ✅ Hierarchy tree displays parent-child relationships
- ✅ Agent status (running ⏳ / completed ✅) updates in real-time
- ✅ `client.getAgentHierarchy()` returns the hierarchy tree

**Verify in UI:**
- 🌳 Agent Delegation Tree panel appears
- Tree shows nested agents with status indicators

---

#### ✅ Feature 9: Thinking Stream

**What it tests:** Exposing AI reasoning process in real-time.

**Steps:**
1. Create any agent
2. Go to **Chat** tab
3. Enable **"Show Thinking"** toggle
4. Send a complex message: "Explain step by step how to implement a binary search tree"
5. Watch thinking blocks appear before responses

**Expected Results:**
- ✅ Purple thinking blocks appear with 💭 icon
- ✅ Thinking content streams in real-time
- ✅ Thinking is shown before the main response
- ✅ Toggling "Show Thinking" hides/shows the blocks

**Code Reference:**
The playground uses `client.onThinking()` (Phase 1 refactor) to capture thinking deltas.

---

#### ✅ Feature 10: Client-Side Behaviors

**What it tests:** Reusable capability packages that can be composed.

**Steps:**
1. Go to **Behaviors** tab
2. Load example behaviors:
   - Click **"coding"** - Adds filesystem and bash tools
   - Click **"security-minded"** - Adds approval hooks
   - Click **"research"** - Adds web tools
3. Check the checkboxes to select behaviors
4. Return to **Bundle Builder** tab
5. Click **"Create Agent"** (applies selected behaviors)
6. Go to **Chat** tab and test the combined capabilities

**Expected Results:**
- ✅ Selected behaviors applied to agent
- ✅ Tools from behaviors are available
- ✅ Instructions from behaviors merged
- ✅ Hooks from behaviors active

**Verify in Console:**
```
[Session] Applied behaviors: ["coding", "security-minded"]
```

**Test Custom Behavior:**
1. In **Behaviors** tab, click **"+ Create Custom Behavior"**
2. Name: `my-behavior`
3. Instructions: "Always respond in bullet points"
4. Select it and create agent
5. Verify behavior is applied

---

#### ✅ Feature 11: Sub-Agent Configuration

**What it tests:** Configuring spawnable agents within bundles.

**Steps:**
1. Go to **Bundle Builder** tab
2. Scroll to **"Sub-Agents"** section
3. Click **"+ Add Sub-Agent"**
4. Configure sub-agent:
   - Name: `code-reviewer`
   - Instructions: "Review code for bugs and suggest improvements"
5. Click **"Create Agent"**
6. Go to **Chat** tab
7. Ask: "Spawn a code-reviewer agent to review this function" (provide code)

**Expected Results:**
- ✅ Sub-agent definition included in bundle
- ✅ Agent can spawn the configured sub-agent
- ✅ Sub-agent appears in hierarchy tree
- ✅ Sub-agent uses its specific instructions

**Verify in Console:**
```javascript
[Session] Created sess_... with bundle: {
  // ...
  agents: [{
    name: "code-reviewer",
    instructions: "Review code for bugs..."
  }]
}
```

---

### 🎯 Phase 4: Enterprise Features

#### ✅ Feature 12: Recipe Management & Execution

**What it tests:** Multi-step workflow orchestration with approval gates.

**Steps:**
1. Go to **Recipes** tab
2. Load example recipe:
   - Click **"code-review"**
3. Review the recipe:
   - Step 1: `analyze` - foundation:zen-architect analyzes code
   - Step 2: `fix` - foundation:modular-builder applies fixes (requires approval)
4. Add context variable:
   - Click **"+ Add Variable"**
   - Key: `file_path`
   - Value: `src/example.ts`
5. Click **"▶️ Execute Recipe"**
6. Watch execution progress below

**Expected Results:**
- ✅ Recipe steps execute in sequence
- ✅ Progress indicators update (pending → running → completed)
- ✅ Approval gate halts execution until approved
- ✅ Step outputs displayed
- ✅ Failed steps show error messages

**Test Custom Recipe:**
1. In **Recipes** tab, enter:
   - Name: `my-workflow`
   - Description: "Custom multi-step workflow"
2. Click **"+ Add Step"** twice:
   - Step 1: `gather-info` - Agent: `foundation:explorer` - Prompt: "Find all {{file_type}} files"
   - Step 2: `summarize` - Agent: `foundation:technical-writer` - Prompt: "Summarize findings"
3. Add context variable: `file_type` = `*.ts`
4. Execute and watch progress

**Verify Recipe Builder API:**
```javascript
const builder = new RecipeBuilder("my-workflow")
  .description("...")
  .step("gather-info", (s) => s.agent("foundation:explorer").prompt("..."))
  .step("summarize", (s) => s.agent("foundation:technical-writer").prompt("..."))
  .build();
```

---

#### ✅ Feature 13: Hooks Configuration

**What it tests:** Adding hook modules for event handling.

**Steps:**
1. Go to **Bundle Builder** tab
2. Scroll to **"Hooks"** section
3. Click **"+ Add Hook"**
4. Enter hook module name: `hook-logging` (or `hook-approval`)
5. Click **"Create Agent"**

**Expected Results:**
- ✅ Hook module included in bundle
- ✅ Hook receives events from the session
- ✅ Hook can modify behavior (e.g., logging, approval gates)

**Verify in Console:**
```javascript
[Session] Created sess_... with bundle: {
  // ...
  hooks: [{module: "hook-logging"}]
}
```

**Note:** The actual hook behavior depends on the runtime server having the hook module installed. The playground demonstrates the **configuration** - the runtime handles the **execution**.

---

#### ✅ Feature 14: MCP Server Integration

**What it tests:** Connecting to Model Context Protocol servers.

**Steps:**
1. Go to **Bundle Builder** tab
2. Scroll to **"MCP Servers"** section
3. Click **"+ Add MCP Server"**
4. Configure an MCP server:
   - **Type: stdio**
     - Command: `/usr/local/bin/my-mcp-server`
   - **Type: http**
     - URL: `http://localhost:8080`
   - **Type: sse**
     - URL: `http://localhost:8080/events`
5. Click **"Create Agent"**

**Expected Results:**
- ✅ MCP server configuration included in bundle
- ✅ Agent can use tools from MCP server
- ✅ MCP server connection handled by runtime

**Verify in Console:**
```javascript
[Session] Created sess_... with bundle: {
  // ...
  mcpServers: [
    {type: "stdio", command: "/usr/local/bin/my-mcp-server", args: [], env: {}},
    {type: "http", url: "http://localhost:8080", headers: {}}
  ]
}
```

**Note:** Like hooks, MCP server behavior depends on the runtime. The playground demonstrates the **SDK configuration API**.

---

## UI Feature Testing

### Tab Navigation

**Test:**
1. Click each tab: **Bundle Builder**, **Behaviors**, **Recipes**, **Chat**
2. Verify content changes
3. Active tab highlighted with blue underline
4. Chat preview button appears when session exists and not on chat tab

**Expected:** Smooth tab switching, no broken UI.

---

### Toggle Controls

**Test each toggle:**
- **Show Thinking** - Hides/shows purple thinking blocks
- **Show Sub-agents** - Hides/shows green sub-agent panels
- **Show Tool Results** - Hides/shows tool result details
- **Show Agent Tree** - Hides/shows hierarchy tree panel

**Expected:** Toggles affect only their respective features, chat continues working.

---

### Export Chat

**Test:**
1. Have a conversation with tool calls, thinking, sub-agents
2. Click **"Export"** button in Bundle Builder
3. Opens save dialog for JSON file

**Expected:** JSON file contains session ID, config, and full message history.

---

## Troubleshooting

### Connection Issues

**Problem:** "Disconnected" status in header

**Solutions:**
1. Check runtime is running: `curl http://localhost:4096/health`
2. Check port conflicts: `lsof -i :4096`
3. Clear browser cache and reload
4. Check browser console for errors

---

### Approval Modal Stuck

**Problem:** Approval modal doesn't disappear after clicking approve/deny

**Solutions:**
1. Check browser console for errors
2. Verify `client.onApproval()` is registered
3. Refresh page and try again

---

### Recipe Execution Fails

**Problem:** Recipe progress shows "failed" status

**Solutions:**
1. Check step configuration (agent names must be valid)
2. Verify context variables are provided
3. Check if required agents exist in runtime
4. Look at error message in progress panel

---

### Sub-Agents Not Spawning

**Problem:** Agent hierarchy tree stays empty

**Solutions:**
1. Ensure the agent has delegation capabilities
2. Ask questions that require sub-tasks
3. Check that "Show Agent Tree" toggle is enabled
4. Verify runtime supports agent delegation

---

### Thinking Stream Not Showing

**Problem:** No purple thinking blocks appear

**Solutions:**
1. Enable "Show Thinking" toggle
2. Verify model supports thinking (Claude Sonnet 4.5+)
3. Check browser console for `onThinking` events
4. Send a complex question that requires reasoning

---

## Performance Testing

### Load Test

**Test many messages:**
1. Create agent
2. Send 20+ messages rapidly
3. Monitor for:
   - Memory leaks (check browser DevTools Memory)
   - UI lag
   - Message ordering issues

**Expected:** Smooth performance, messages in correct order.

---

### Large Agent Hierarchy

**Test deep delegation:**
1. Create agent that delegates heavily
2. Ask: "Research 5 different topics in parallel"
3. Watch hierarchy tree grow to 10+ nodes

**Expected:** Tree renders correctly, scrollable, no UI crashes.

---

### Long-Running Recipe

**Test recipe with multiple steps:**
1. Create recipe with 5+ steps
2. Execute with approval gates
3. Progress through each approval
4. Monitor execution time (should be several minutes)

**Expected:** Progress updates smoothly, no timeouts, all steps complete.

---

## Feature Coverage Checklist

Use this checklist to verify 100% feature coverage:

### Phase 1: Foundation
- [ ] Session CRUD (create, delete)
- [ ] Streaming responses
- [ ] Runtime bundle definition

### Phase 2: Client-Side
- [ ] Client-side tools (get-time, calculate, get-random)
- [ ] Approval flow (modal, approve/deny)
- [ ] Event handlers (onThinking, onApproval, onAgentSpawned)
- [ ] Session resume (via getSession/resumeSession)

### Phase 3: Advanced
- [ ] Agent spawning visibility (hierarchy tree)
- [ ] Thinking stream (purple blocks)
- [ ] Client-side behaviors (load, select, apply)
- [ ] Sub-agent configuration (add, configure, use)

### Phase 4: Enterprise
- [ ] Recipe management (create, load examples)
- [ ] Recipe execution (run, monitor progress)
- [ ] Hooks configuration (add, apply)
- [ ] MCP server integration (stdio, http, sse)

### UI Features
- [ ] Tab navigation (4 tabs working)
- [ ] Toggle controls (4 toggles working)
- [ ] Export chat (JSON download)
- [ ] Presets (5 presets loadable)
- [ ] Custom tools (add/remove)
- [ ] Connection status (connected/disconnected)

**Target:** 14/14 SDK features + 6/6 UI features = 100% coverage ✅

---

## Next Steps

After testing all features:

1. **Report Issues:** If you find bugs, note the feature, steps to reproduce, and expected vs actual behavior.

2. **Suggest Improvements:** Ideas for better UX, missing features, or documentation gaps.

3. **Create Tutorials:** Use this testing guide as a basis for user tutorials.

4. **Performance Benchmarks:** Measure response times, memory usage, and scalability limits.

5. **Integration Tests:** Automate some of these tests with Playwright or similar tools.

---

## Summary

The Agent Playground demonstrates **100% of the SDK's features** across all development phases. Use this guide to systematically test each feature and verify the SDK is working correctly in your environment.

**Happy testing! 🎉**
