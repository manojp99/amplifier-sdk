# Agent Playground Demo Walkthrough

A step-by-step guide to using every feature in the Agent Playground.

---

## 🎯 Demo 1: Client-Side Tools (THE Killer Feature)

**What you'll see:** Tools that run in your browser, not on the server.

**Why this matters:** No deployment needed. The tool code stays in your app with access to your app's state, databases, and APIs.

### Steps:

1. **Go to Bundle Builder tab**
2. **Click the "demo-client-tools" preset**
   - This loads instructions telling the agent about 3 client-side tools
   - Tools: get-time, calculate, get-random
3. **Click "Create Agent"**
4. **Click "Open Chat"**
5. **Type: "What time is it in Tokyo?"**

**What happens:**
- Agent decides to call the `get-time` tool
- SDK intercepts the tool call
- Tool runs **in your browser** (check console logs!)
- Result sent back to agent
- Agent responds with the time

**Key point:** The `get-time` tool code lives in `App.tsx`. It has access to JavaScript's `Intl.DateTimeFormat`. No server deployment needed!

```typescript
// This runs in YOUR browser
client.registerTool({
  name: "get-time",
  handler: async ({ timezone }) => {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone as string,
      hour: "2-digit",
      minute: "2-digit",
    });
    return { time: formatter.format(new Date()) };
  }
});
```

---

## 🎭 Demo 2: Behaviors (Reusable Capability Packages)

**What you'll see:** Compose multiple behaviors to create a specialized agent.

### Steps:

1. **Go to Behaviors tab**
2. **Click "coding" example**
   - Adds instructions about being an expert programmer
   - Includes filesystem and bash tools
3. **Click "security-minded" example**
   - Adds security review instructions
   - Includes approval hooks
4. **Select both checkboxes**
5. **Go to Bundle Builder**
6. **Click "Create Agent"**
7. **Go to Chat**
8. **Ask: "Review this code for security issues: `app.get('/user/:id', (req, res) => { db.query('SELECT * FROM users WHERE id = ' + req.params.id) })`"**

**What happens:**
- Agent has BOTH behaviors active
- Responds as a coding expert (behavior 1)
- Focuses on security (behavior 2)
- Identifies the SQL injection vulnerability

**Key point:** Behaviors compose. You can mix-and-match capabilities without rewriting instructions.

---

## 📋 Demo 3: Recipes (Multi-Step Workflows)

**What you'll see:** Orchestrate multiple AI agents in a workflow with approval gates.

### Steps:

1. **Go to Recipes tab**
2. **Click "code-review" example**
   - Step 1: zen-architect analyzes code
   - Step 2: modular-builder fixes issues (requires approval)
3. **Add context variable:**
   - Click "+ Add Variable"
   - Name: `file_path`
   - Value: `src/auth.ts`
4. **Click "▶️ Execute Recipe"**

**What happens:**
- SDK creates a session with foundation bundle (has recipes tool)
- Recipe executes step-by-step
- Progress updates show in real-time
- When step 2 needs approval, you see an approval dialog
- You approve/deny the fixes

**Key point:** Multi-agent orchestration with human-in-the-loop approval gates.

---

## 🤖 Demo 4: Sub-Agents Configuration

**What you'll see:** Configure specialized agents that the main agent can spawn.

### Steps:

1. **Go to Bundle Builder**
2. **Click "+ Add Sub-Agent"**
3. **Configure the sub-agent:**
   - Name: `code-reviewer`
   - Instructions: `You are an expert code reviewer. Focus on security and performance.`
   - Tools: Select "Filesystem"
4. **Click "Create Agent"**
5. **Enable "Show Agent Tree" toggle**
6. **Go to Chat**
7. **Ask: "Delegate to a specialist to review the code in src/auth.ts"**

**What happens:**
- Main agent spawns the `code-reviewer` sub-agent
- Agent tree visualizes the hierarchy
- Sub-agent completes its work
- Result bubbles back up

**Key point:** Multi-agent workflows with hierarchy tracking.

---

## 🧠 Demo 5: Thinking Stream

**What you'll see:** AI's reasoning process exposed in real-time.

### Steps:

1. **Ensure "Show Thinking" toggle is ON**
2. **Go to Chat (with any agent)**
3. **Ask a complex question: "Explain the difference between async/await and Promises, then write a comparison table"**

**What happens:**
- As the agent thinks, you see its reasoning
- Thinking content appears in gray italic text
- You understand HOW it's approaching the problem
- Final response appears after thinking completes

**Key point:** Educational - see the AI's reasoning process.

---

## 🔧 Demo 6: Hooks Configuration

**What you'll see:** Add lifecycle observers to your agent.

### Steps:

1. **Go to Bundle Builder**
2. **Scroll to "Hooks" section**
3. **Click "+ Add Hook"**
4. **Enter: `hook-logging`**
5. **Click "Create Agent"**
6. **Go to Chat**
7. **Send any message**
8. **Check browser console**

**What would happen (if runtime supported):**
- `hook-logging` observes all events
- Logs tool calls, approvals, thinking
- Pure observation - doesn't block execution

**Key point:** Enterprise observability and event handling.

---

## 🔌 Demo 7: MCP Servers

**What you'll see:** Configure external tool servers via Model Context Protocol.

### Steps:

1. **Go to Bundle Builder**
2. **Scroll to "MCP Servers" section**
3. **Click "+ Add MCP Server"**
4. **Configure:**
   - Type: `stdio`
   - Command: `/path/to/mcp-server`
5. **Click "Create Agent"**

**What would happen (if you had an MCP server):**
- Runtime spawns the MCP server as a child process
- Server exposes additional tools
- Agent can use MCP tools alongside SDK tools

**Key point:** Integrate external tool ecosystems.

---

## 🎬 Full Feature Showcase (5-Minute Demo)

**The complete SDK feature tour:**

1. **Start: Bundle Builder**
   - Load "demo-client-tools" preset
   - Add a sub-agent: "researcher" 
   - Add hook: "hook-logging"
   - Create Agent

2. **Behaviors Tab**
   - Load "coding" behavior
   - Load "security-minded" behavior
   - Select both

3. **Recipes Tab**
   - Load "code-review" example
   - Add context: file_path = "src/app.ts"
   - Execute Recipe (watch progress)

4. **Chat Tab**
   - Test client-side tool: "What time is it in Paris?"
   - Test sub-agent: "Delegate research to a specialist"
   - Watch thinking stream
   - Watch agent hierarchy tree

**Result:** You've seen all 14 SDK features in action!

---

## 📊 Feature Checklist

After the demo, you'll have seen:

- ✅ Session CRUD (Create Agent button)
- ✅ Streaming (live chat updates)
- ✅ Runtime Bundles (bundle builder)
- ✅ Client-Side Tools (get-time, calculate, get-random)
- ✅ Event Handlers (automatic in SDK)
- ✅ Approval Flow (in recipes)
- ✅ Session Resume (implicit)
- ✅ Agent Spawning (sub-agents)
- ✅ Thinking Stream (toggle on/off)
- ✅ Behaviors (composition)
- ✅ Sub-Agent Config (bundle builder)
- ✅ Recipes (recipe tab)
- ✅ Hooks (bundle builder)
- ✅ MCP (bundle builder)

**All 14 features, 100% coverage!**

---

## 🎓 Learning Objectives

**After using the playground, you'll understand:**

1. **Why SDK exists** - Client-side tools are impossible with Foundation alone
2. **Event streaming** - Real-time UI updates during agent execution
3. **Multi-agent workflows** - Orchestration and hierarchy
4. **Enterprise features** - Hooks, MCP, recipes for production deployments

---

## 🐛 Troubleshooting

**"Create Agent" does nothing:**
- Check browser console for errors
- Ensure runtime is running: `curl http://localhost:4096/health`

**Recipe execution fails:**
- SDK creates a session with "foundation" bundle automatically
- Foundation bundle includes the recipes tool
- Error likely means runtime isn't configured properly

**Tools don't execute:**
- Client-side tools require the preset "demo-client-tools"
- Tools are registered on app load (check console logs)

---

**Ready to try it?** Open http://localhost:3001 and start with Demo 1!
