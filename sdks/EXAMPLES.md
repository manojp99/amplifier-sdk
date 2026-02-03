# Amplifier SDK - Code Examples

Common patterns and use cases for the Amplifier SDK.

**Note:** These examples assume you have the amplifier-app-runtime server running at `http://localhost:4096`. See [GETTING_STARTED.md](GETTING_STARTED.md) for setup instructions.

---

## Basic Usage

### Simple Chat Session

**TypeScript:**
```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();

// Create session
const session = await client.createSession({
  bundle: { 
    name: "assistant",
    instructions: "You are a helpful assistant."
  }
});

// Chat
for await (const event of client.prompt(session.id, "Hello!")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}

// Cleanup
await client.deleteSession(session.id);
```

**Python:**
```python
from amplifier_sdk import AmplifierClient

async with AmplifierClient() as client:
    session = await client.create_session(
        bundle={"name": "assistant", "instructions": "Be helpful"}
    )
    
    async for event in client.prompt(session.id, "Hello!"):
        if event.type == "content.delta":
            print(event.data["delta"], end="", flush=True)
    
    await client.delete_session(session.id)
```

---

## Client-Side Tools

### Database Access

```typescript
// Register a tool that queries YOUR database
client.registerTool({
  name: "get-order",
  description: "Get order information by ID",
  parameters: {
    type: "object",
    properties: {
      orderId: { 
        type: "string",
        description: "Order ID"
      }
    },
    required: ["orderId"]
  },
  handler: async ({ orderId }) => {
    // This runs in YOUR app with YOUR credentials
    const order = await db.orders.findById(orderId);
    return {
      id: order.id,
      status: order.status,
      total: order.total,
      items: order.items
    };
  }
});

// Use in session
const session = await client.createSession({
  bundle: {
    name: "support-agent",
    instructions: "Help customers with their orders",
    clientTools: ["get-order"]
  }
});

// User asks: "What's the status of order #12345?"
// AI calls get-order({ orderId: "12345" })
// Your handler runs locally
// AI responds: "Order #12345 is shipped, arriving Tuesday"
```

### API Integration

```typescript
// Integrate with external APIs
client.registerTool({
  name: "send-notification",
  description: "Send a notification via Slack",
  parameters: {
    type: "object",
    properties: {
      channel: { type: "string" },
      message: { type: "string" }
    },
    required: ["channel", "message"]
  },
  handler: async ({ channel, message }) => {
    const response = await fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.SLACK_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ channel, text: message })
    });
    return await response.json();
  }
});
```

### Browser UI Interaction

```typescript
// React component example
function ChatApp() {
  const [notification, setNotification] = useState(null);
  
  useEffect(() => {
    // Tool can access React state!
    client.registerTool({
      name: "show-notification",
      description: "Show a notification to the user",
      parameters: {
        type: "object",
        properties: {
          message: { type: "string" },
          type: { type: "string", enum: ["info", "success", "error"] }
        }
      },
      handler: async ({ message, type }) => {
        setNotification({ message, type });
        return { displayed: true };
      }
    });
  }, []);
  
  // ... rest of component
}
```

---

## Event Handling

### Tool Visibility

```typescript
// Track tool usage
const toolStats = new Map();

client.on("tool.call", (event) => {
  const tool = event.data.tool_name;
  toolStats.set(tool, (toolStats.get(tool) || 0) + 1);
  console.log(`🔧 ${tool} (used ${toolStats.get(tool)} times)`);
});

client.on("tool.result", (event) => {
  console.log(`✅ Tool completed`);
});
```

### Content Streaming

```typescript
let fullResponse = "";

client.on("content.delta", (event) => {
  fullResponse += event.data.delta;
  updateUI(fullResponse);
});

client.on("content.end", (event) => {
  saveToHistory(fullResponse);
  fullResponse = "";
});
```

### Thinking Visualization

```typescript
let thinkingContent = "";

client.on("thinking.delta", (event) => {
  thinkingContent += event.data.delta;
  updateThinkingPanel(thinkingContent);
});
```

### Agent Hierarchy Tracking

Track multi-agent workflows with hierarchy visualization:

```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();

// Track agent lifecycle
client.onAgentSpawned((info) => {
  console.log(`\n🤖 Agent spawned: ${info.agentName}`);
  if (info.parentId) {
    console.log(`   Delegated by: ${info.parentId}`);
  }
});

client.onAgentCompleted((info) => {
  console.log(`\n✅ Agent completed: ${info.agentId}`);
  if (info.result) {
    console.log(`   Result: ${info.result.substring(0, 100)}...`);
  }
});

// Run a task that uses multiple agents
const session = await client.createSession({ bundle: "foundation" });

for await (const event of client.prompt(session.id, "Analyze this project")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}

// Print the agent tree
const hierarchy = client.getAgentHierarchy();
printAgentTree(hierarchy);

function printAgentTree(hierarchy: Map<string, AgentNode>) {
  // Find root agents
  const roots = Array.from(hierarchy.values())
    .filter(node => node.parentId === null);
  
  console.log("\n\n📊 Agent Delegation Tree:");
  roots.forEach(root => printNode(root, hierarchy, 0));
}

function printNode(node: AgentNode, hierarchy: Map<string, AgentNode>, depth: number) {
  const indent = "  ".repeat(depth);
  const status = node.completedAt ? "✅" : "⏳";
  console.log(`${indent}${status} ${node.agentName}`);
  
  node.children.forEach(childId => {
    const child = hierarchy.get(childId);
    if (child) printNode(child, hierarchy, depth + 1);
  });
}
```

**Python:**
```python
from amplifier_sdk import AmplifierClient

async with AmplifierClient() as client:
    # Track agent lifecycle
    def handle_spawn(info):
        print(f"\n🤖 Agent spawned: {info['agent_name']}")
        if info['parent_id']:
            print(f"   Delegated by: {info['parent_id']}")
    
    def handle_completion(info):
        print(f"\n✅ Agent completed: {info['agent_id']}")
        if info.get('result'):
            print(f"   Result: {info['result'][:100]}...")
    
    client.on_agent_spawned(handle_spawn)
    client.on_agent_completed(handle_completion)
    
    # Run task
    session = await client.create_session(bundle="foundation")
    async for event in client.prompt(session.id, "Analyze this project"):
        if event.type == "content.delta":
            print(event.data["delta"], end="", flush=True)
    
    # Print hierarchy
    hierarchy = client.get_agent_hierarchy()
    print_agent_tree(hierarchy)

def print_agent_tree(hierarchy: dict):
    roots = [node for node in hierarchy.values() if node.parent_id is None]
    
    print("\n\n📊 Agent Delegation Tree:")
    for root in roots:
        print_node(root, hierarchy, 0)

def print_node(node, hierarchy, depth):
    indent = "  " * depth
    status = "✅" if node.completed_at else "⏳"
    print(f"{indent}{status} {node.agent_name}")
    
    for child_id in node.children:
        child = hierarchy.get(child_id)
        if child:
            print_node(child, hierarchy, depth + 1)
```

---

## Approval Flows

### Interactive Approval

```typescript
client.onApproval(async (request) => {
  // Show modal to user
  const dialog = document.createElement('dialog');
  dialog.innerHTML = `
    <h3>Permission Required</h3>
    <p>${request.prompt}</p>
    <p>Tool: ${request.toolName}</p>
    <button id="approve">Approve</button>
    <button id="deny">Deny</button>
  `;
  
  document.body.appendChild(dialog);
  dialog.showModal();
  
  return new Promise((resolve) => {
    dialog.querySelector('#approve').onclick = () => {
      dialog.close();
      resolve(true);
    };
    dialog.querySelector('#deny').onclick = () => {
      dialog.close();
      resolve(false);
    };
  });
});
```

### Conditional Auto-Approval

```typescript
const SAFE_TOOLS = new Set(['read-file', 'list-directory']);
const DANGEROUS_TOOLS = new Set(['delete-file', 'run-command']);

client.onApproval(async (request) => {
  // Auto-approve safe tools
  if (SAFE_TOOLS.has(request.toolName)) {
    return true;
  }
  
  // Always ask for dangerous tools
  if (DANGEROUS_TOOLS.has(request.toolName)) {
    return await showUserDialog(request);
  }
  
  // Default: approve
  return true;
});
```

## Visualizing Multi-Agent Workflows

Track and visualize complex agent delegation patterns:

### React Component Example

```typescript
import { useState, useEffect } from "react";
import { AmplifierClient, type AgentNode } from "amplifier-sdk";

function AgentTreeVisualization() {
  const [client] = useState(() => new AmplifierClient());
  const [hierarchy, setHierarchy] = useState<Map<string, AgentNode>>(new Map());
  const [activeAgents, setActiveAgents] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Update hierarchy when agents spawn
    client.onAgentSpawned((info) => {
      setActiveAgents(prev => new Set(prev).add(info.agentId));
      setHierarchy(client.getAgentHierarchy());
    });

    // Update when agents complete
    client.onAgentCompleted((info) => {
      setActiveAgents(prev => {
        const next = new Set(prev);
        next.delete(info.agentId);
        return next;
      });
      setHierarchy(client.getAgentHierarchy());
    });
  }, []);

  const rootAgents = Array.from(hierarchy.values())
    .filter(node => node.parentId === null);

  return (
    <div className="agent-tree">
      <h3>Agent Activity</h3>
      <p>Active: {activeAgents.size}</p>
      {rootAgents.map(root => (
        <AgentNodeComponent 
          key={root.agentId} 
          node={root} 
          hierarchy={hierarchy}
          activeAgents={activeAgents}
        />
      ))}
    </div>
  );
}

function AgentNodeComponent({ node, hierarchy, activeAgents, depth = 0 }) {
  const isActive = activeAgents.has(node.agentId);
  const status = node.completedAt ? "✅" : isActive ? "⏳" : "⏸️";
  
  return (
    <div style={{ marginLeft: `${depth * 20}px` }}>
      <div className={`agent-node ${isActive ? "active" : ""}`}>
        <span className="status">{status}</span>
        <span className="name">{node.agentName}</span>
        {node.error && <span className="error">❌ {node.error}</span>}
      </div>
      {node.children.map(childId => {
        const child = hierarchy.get(childId);
        return child ? (
          <AgentNodeComponent
            key={childId}
            node={child}
            hierarchy={hierarchy}
            activeAgents={activeAgents}
            depth={depth + 1}
          />
        ) : null;
      })}
    </div>
  );
}
```

### Analytics and Monitoring

```typescript
// Track agent performance
const agentMetrics = new Map();

client.onAgentSpawned((info) => {
  agentMetrics.set(info.agentId, {
    name: info.agentName,
    startTime: Date.now(),
    parentId: info.parentId
  });
});

client.onAgentCompleted((info) => {
  const metrics = agentMetrics.get(info.agentId);
  if (metrics) {
    const duration = Date.now() - metrics.startTime;
    
    // Send to analytics
    analytics.track("agent_execution", {
      agentName: metrics.name,
      duration,
      success: !info.error,
      error: info.error
    });
    
    console.log(`📊 ${metrics.name}: ${duration}ms`);
  }
});
```

### Memory Management

```typescript
// Clear hierarchy between major tasks to prevent memory growth
const session = await client.createSession({ bundle: "foundation" });

// Task 1
await runPrompt(session.id, "First task");
client.clearAgentHierarchy();

// Task 2
await runPrompt(session.id, "Second task");
client.clearAgentHierarchy();

// Task 3
await runPrompt(session.id, "Third task");
```

---

## Session Management

### Session Resume

```typescript
// List all sessions
const sessions = await client.listSessions();

// Show to user
console.log("Previous conversations:");
sessions.forEach((s, i) => {
  console.log(`${i + 1}. ${s.title || s.id} (${s.state})`);
});

// Let user choose
const choice = await getUserChoice();
const session = sessions[choice];

// Resume
const resumed = await client.resumeSession(session.id);

for await (const event of resumed.send("Let's continue where we left off")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta);
  }
}
```

### Session Persistence

```typescript
// Save session ID for later
localStorage.setItem('currentSession', session.id);

// Later... resume the session
const sessionId = localStorage.getItem('currentSession');
if (sessionId) {
  const session = await client.resumeSession(sessionId);
  // Continue conversation
}
```

---

## Event Correlation

### Tool Call Tracking

```typescript
const toolExecutions = new Map();

for await (const event of client.prompt(sessionId, "Analyze this repo")) {
  if (event.type === "tool.call") {
    toolExecutions.set(event.toolCallId, {
      name: event.data.tool_name,
      args: event.data.arguments,
      startTime: Date.now()
    });
    console.log(`⏳ ${event.data.tool_name} started...`);
  }
  
  if (event.type === "tool.result") {
    const call = toolExecutions.get(event.toolCallId);
    const duration = Date.now() - call.startTime;
    console.log(`✅ ${call.name} completed in ${duration}ms`);
    
    // Show result
    console.log(`Result: ${JSON.stringify(event.data.result)}`);
  }
}
```

### Parent vs Child Agent Events

```typescript
const agentOutputs = new Map();

for await (const event of client.prompt(sessionId, "Complex task")) {
  // Events have agentId to distinguish parent vs child
  if (event.type === "content.delta") {
    const agentId = event.agentId || "parent";
    
    if (!agentOutputs.has(agentId)) {
      agentOutputs.set(agentId, "");
    }
    
    agentOutputs.set(agentId, agentOutputs.get(agentId) + event.data.delta);
  }
}

// agentOutputs now has separate content for each agent
console.log("Parent output:", agentOutputs.get("parent"));
console.log("Child agents:", Array.from(agentOutputs.keys()).filter(k => k !== "parent"));
```

---

## Advanced Patterns

### Multi-Tool Agent

```typescript
// Agent with multiple server-side tools
const session = await client.createSession({
  bundle: {
    name: "developer-assistant",
    instructions: "You are a coding assistant with access to filesystem and shell.",
    tools: [
      { module: "tool-filesystem" },
      { module: "tool-bash" },
      { module: "tool-web" }
    ]
  }
});
```

### Mixed Tools (Server + Client)

```typescript
// Register client-side tools
client.registerTool({
  name: "query-jira",
  description: "Query Jira for issues",
  handler: async ({ jql }) => {
    return await jiraClient.search(jql);
  }
});

// Create session with BOTH server and client tools
const session = await client.createSession({
  bundle: {
    name: "project-manager",
    instructions: "Help manage development projects",
    tools: [
      { module: "tool-bash" },      // Server-side
      { module: "tool-filesystem" }  // Server-side
    ],
    clientTools: ["query-jira"]     // Client-side (your app!)
  }
});

// AI can now use both server tools AND your local Jira API!
```

---

## Error Handling

### Retry Logic

```typescript
import { AmplifierError, ErrorCode } from "amplifier-sdk";

async function createSessionWithRetry(maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await client.createSession({
        bundle: { name: "assistant", instructions: "Be helpful" }
      });
    } catch (err) {
      if (err instanceof AmplifierError && err.isRetryable) {
        console.log(`Attempt ${attempt} failed, retrying...`);
        await sleep(1000 * attempt);  // Exponential backoff
        continue;
      }
      throw err;  // Not retryable, give up
    }
  }
  throw new Error("Max retries exceeded");
}
```

### Graceful Degradation

```typescript
let client: AmplifierClient;

try {
  client = new AmplifierClient();
  const available = await client.ping();
  
  if (!available) {
    throw new Error("Runtime not available");
  }
} catch (err) {
  // Fallback: show error message, use cached responses, etc.
  console.error("AI features unavailable:", err.message);
  return showStaticContent();
}
```

---

## React Integration

### Custom Hook

```typescript
import { useState, useEffect } from "react";
import { AmplifierClient, type Event } from "amplifier-sdk";

export function useAmplifierSession(bundleConfig) {
  const [client] = useState(() => new AmplifierClient());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function createSession() {
      const session = await client.createSession({ bundle: bundleConfig });
      setSessionId(session.id);
    }
    createSession();
    
    return () => {
      if (sessionId) {
        client.deleteSession(sessionId);
      }
    };
  }, []);

  const sendMessage = async (content: string) => {
    if (!sessionId) return;
    
    setMessages(prev => [...prev, { role: "user", content }]);
    setIsLoading(true);

    let response = "";
    for await (const event of client.prompt(sessionId, content)) {
      if (event.type === "content.delta") {
        response += event.data.delta;
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { role: "assistant", content: response }];
          }
          return [...prev, { role: "assistant", content: response }];
        });
      }
    }
    
    setIsLoading(false);
  };

  return { messages, sendMessage, isLoading, sessionId };
}

// Usage in component
function ChatComponent() {
  const { messages, sendMessage, isLoading } = useAmplifierSession({
    name: "chat-assistant",
    instructions: "Be concise and friendly"
  });

  return (
    <div>
      {messages.map((msg, i) => (
        <div key={i} className={msg.role}>
          {msg.content}
        </div>
      ))}
      <input onSubmit={(e) => sendMessage(e.target.value)} disabled={isLoading} />
    </div>
  );
}
```

---

## Python Async Patterns

### Context Manager Pattern

```python
from amplifier_sdk import AmplifierClient

async def chat():
    async with AmplifierClient() as client:
        session = await client.create_session(bundle="foundation")
        
        async for event in client.prompt(session.id, "Hello"):
            if event.type == "content.delta":
                print(event.data["delta"], end="", flush=True)
        
        # Client auto-closes, session auto-deletes
```

### Manual Management

```python
client = AmplifierClient()

try:
    session = await client.create_session(bundle="foundation")
    
    async for event in client.prompt(session.id, "Hello"):
        if event.type == "content.delta":
            print(event.data["delta"], end="", flush=True)
            
finally:
    await client.close()
```

---

## Advanced Features

### Multi-Turn Conversation

```typescript
const session = await client.createSession({
  bundle: { name: "assistant", instructions: "Remember context" }
});

// Turn 1
await streamPrompt(session.id, "My name is Alice");

// Turn 2
await streamPrompt(session.id, "What's my name?");
// Response: "Your name is Alice"

async function streamPrompt(sessionId: string, content: string) {
  let response = "";
  for await (const event of client.prompt(sessionId, content)) {
    if (event.type === "content.delta") {
      response += event.data.delta;
      process.stdout.write(event.data.delta);
    }
  }
  console.log("\n");
  return response;
}
```

### Provider and Model Selection

```typescript
// Use specific provider and model
const session = await client.createSession({
  bundle: {
    name: "fast-assistant",
    instructions: "Be very concise",
    providers: [
      { 
        module: "provider-anthropic",
        config: { model: "claude-haiku-3-5-20250307" }  // Fast, cheap model
      }
    ]
  }
});

// Different session with different model
const smartSession = await client.createSession({
  bundle: {
    name: "smart-assistant",
    instructions: "Think deeply about complex problems",
    providers: [
      {
        module: "provider-anthropic",
        config: { model: "claude-opus-4-20250514" }  // Best reasoning
      }
    ]
  }
});
```

---

## Observability

### Request Logging

```typescript
const client = new AmplifierClient({
  onRequest: (req) => {
    console.log(`→ [${req.requestId}] ${req.method} ${req.url}`);
    console.log(`  Headers:`, req.headers);
    console.log(`  Body:`, req.body);
  },
  
  onResponse: (res) => {
    console.log(`← [${res.requestId}] ${res.status} in ${res.durationMs}ms`);
  },
  
  onError: (err) => {
    console.error(`✗ [${err.requestId}] ${err.code}: ${err.message}`);
    
    // Send to error tracking service
    if (typeof Sentry !== 'undefined') {
      Sentry.captureException(err);
    }
  }
});
```

### Analytics Tracking

```typescript
client.on("tool.call", (event) => {
  analytics.track("ai_tool_used", {
    tool: event.data.tool_name,
    sessionId: currentSessionId
  });
});

client.on("content.end", (event) => {
  analytics.track("ai_response_complete", {
    sessionId: currentSessionId
  });
});
```

---

## Real-World Use Cases

### Customer Support Bot

```typescript
// Register customer data tools
client.registerTool({
  name: "get-customer",
  description: "Get customer information",
  handler: async ({ email }) => await customerDB.findByEmail(email)
});

client.registerTool({
  name: "get-orders",
  description: "Get customer orders",
  handler: async ({ customerId }) => await orderDB.findByCustomer(customerId)
});

client.registerTool({
  name: "create-ticket",
  description: "Create support ticket",
  handler: async ({ title, description }) => await ticketSystem.create({ title, description })
});

// Create support agent
const session = await client.createSession({
  bundle: {
    name: "support-agent",
    instructions: `You are a customer support agent. Help customers with:
    - Order status inquiries
    - Account information
    - Creating support tickets
    
    Be empathetic and professional.`,
    clientTools: ["get-customer", "get-orders", "create-ticket"]
  }
});
```

### Code Review Assistant

```typescript
client.registerTool({
  name: "get-pr-diff",
  description: "Get pull request diff",
  handler: async ({ prNumber }) => {
    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}`,
      { headers: { Authorization: `token ${GITHUB_TOKEN}` } }
    );
    return await response.json();
  }
});

const session = await client.createSession({
  bundle: {
    name: "code-reviewer",
    instructions: `Review code for:
    - Security vulnerabilities
    - Performance issues
    - Best practices
    - Code style`,
    tools: [{ module: "tool-filesystem" }],  // Read local files
    clientTools: ["get-pr-diff"]              // Fetch from GitHub
  }
});
```

### Data Analysis Assistant

```typescript
client.registerTool({
  name: "query-database",
  description: "Query analytics database",
  parameters: {
    type: "object",
    properties: {
      metric: { type: "string" },
      startDate: { type: "string" },
      endDate: { type: "string" }
    }
  },
  handler: async ({ metric, startDate, endDate }) => {
    const results = await analyticsDB.query({
      metric,
      dateRange: { start: startDate, end: endDate }
    });
    return results;
  }
});

client.registerTool({
  name: "create-chart",
  description: "Create a chart visualization",
  handler: async ({ data, chartType }) => {
    const chartUrl = await chartingService.create({ data, type: chartType });
    return { url: chartUrl };
  }
});

const session = await client.createSession({
  bundle: {
    name: "data-analyst",
    instructions: "Analyze data and create visualizations",
    clientTools: ["query-database", "create-chart"]
  }
});
```

---

## Testing

### Mocking for Unit Tests

```typescript
import { vi } from 'vitest';

// Mock the client
const mockClient = {
  createSession: vi.fn().mockResolvedValue({ id: "sess_123" }),
  prompt: vi.fn().mockImplementation(async function* () {
    yield { type: "content.delta", data: { delta: "Hello" } };
    yield { type: "content.end", data: {} };
  })
};

// Use in tests
test("handles streaming response", async () => {
  for await (const event of mockClient.prompt("sess_123", "Hi")) {
    expect(event.type).toBeDefined();
  }
});
```

---

## Performance Optimization

### Batch Requests

```typescript
// Create multiple sessions concurrently
const [session1, session2, session3] = await Promise.all([
  client.createSession({ bundle: "assistant" }),
  client.createSession({ bundle: "coder" }),
  client.createSession({ bundle: "researcher" })
]);
```

### Reuse Sessions

```typescript
// Don't create new session for every message
const session = await client.createSession({ bundle: "assistant" });

// Reuse the same session for multiple prompts
await client.prompt(session.id, "First question");
await client.prompt(session.id, "Second question");
await client.prompt(session.id, "Third question");

// Only delete when done
await client.deleteSession(session.id);
```

---

## Security Examples

See [SECURITY.md](SECURITY.md) for comprehensive security guidance.

### Input Sanitization

```typescript
client.registerTool({
  name: "search-users",
  handler: async ({ query }) => {
    // Sanitize input
    const sanitized = query.replace(/[^a-zA-Z0-9\s]/g, '');
    
    // Use parameterized query
    return await db.users.where('name', 'LIKE', `%${sanitized}%`).limit(10);
  }
});
```

### Rate Limiting

```typescript
const rateLimits = new Map<string, number>();

client.registerTool({
  name: "expensive-api-call",
  handler: async (args) => {
    const lastCall = rateLimits.get("expensive-api-call") || 0;
    const now = Date.now();
    
    if (now - lastCall < 5000) {  // Max once per 5 seconds
      throw new Error("Rate limit exceeded. Please wait.");
    }
    
    rateLimits.set("expensive-api-call", now);
    return await expensiveAPI.call(args);
  }
});
```

---

## Troubleshooting Examples

### Connection Issues

```typescript
const client = new AmplifierClient({
  onError: (err) => {
    if (err.code === "CONNECTION_REFUSED") {
      showError("Runtime server not available. Please start it.");
    }
  }
});

const available = await client.ping();
if (!available) {
  console.error("Runtime not reachable at http://localhost:4096");
  console.log("Start it with: cd amplifier-app-runtime && uv run python -m amplifier_app_runtime.cli --http --port 4096");
}
```

### Provider Configuration

```typescript
try {
  const session = await client.createSession({ bundle: "foundation" });
} catch (err) {
  if (err.message.includes("no providers configured")) {
    console.error("No AI provider configured!");
    console.log("Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable");
  }
}
```

---

## More Examples

Check out the example applications:

- **[Agent Playground](../examples/agent-playground/)** - Interactive agent builder
- **[Chat App](../examples/chat-app/)** - Simple chat interface

---

## See Also

- **[Getting Started](GETTING_STARTED.md)** - Installation and basics
- **[API Reference](API_REFERENCE.md)** - Complete API docs
- **[Security](SECURITY.md)** - Security best practices
