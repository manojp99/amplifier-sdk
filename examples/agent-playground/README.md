# Agent Playground

Interactive playground for building and testing Amplifier agents with the SDK.

## Features

### 🎨 Agent Configuration
- **Presets**: Pre-configured agents (assistant, coder, researcher, tutor, demo-client-tools)
- **Custom Configuration**: Build your own agent with custom name, instructions, and tools
- **Provider Selection**: Choose between Anthropic and OpenAI with model selection
- **Tool Selection**: Enable server-side tools (filesystem, bash, web, web-fetch)
- **Custom Tools**: Add your own tool modules by name

### 💬 Chat Interface
- **Streaming Responses**: Real-time streaming of AI responses
- **Tool Visibility**: See when AI uses tools and their results
- **Thinking Visualization**: View AI's reasoning process (toggle on/off)
- **Sub-Agent Tracking**: Monitor when AI delegates to specialist agents

### 🔧 Client-Side Tools (NEW!)
- **Zero Deployment**: Define tools that run in your browser
- **Instant Execution**: No server roundtrip, instant results
- **Demo Tools Included**:
  - `get-time`: Get current time in any timezone
  - `calculate`: Perform math calculations
  - `get-random`: Generate random numbers

### 🛠️ Advanced Features
- **Approval Flow**: Handle AI approval requests with modal UI
- **Session Persistence**: Saves agent configs to localStorage
- **Export Chat**: Download conversation history as JSON
- **Visual Toggles**: Control what information is displayed

## Prerequisites

The playground requires the **amplifier-app-runtime server** running separately.

**Note:** The runtime is a separate Python application, not part of this package.

## Quick Start

### 1. Install and Start the Runtime (Separate Repository)

```bash
# Clone runtime repository (private - requires access)
git clone git@github.com:manojp99/amplifier-app-runtime.git
cd amplifier-app-runtime

# Install and configure
uv sync
mkdir -p .amplifier
cat > .amplifier/settings.yaml << EOF
providers:
  - module: provider-anthropic
    config:
      priority: 1
EOF

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Start server
uv run python -m amplifier_app_runtime.cli --http --port 4096
```

Keep this server running (localhost:4096).

### 2. Start the Playground

```bash
cd examples/agent-playground
npm install
npm run dev
```

### 3. Open in Browser

Navigate to http://localhost:3001 (or whichever port Vite assigns)

## Testing Client-Side Tools

1. Select **"demo-client-tools"** preset
2. Click **"Create Agent"**
3. Try these prompts:
   - "What time is it in Tokyo?"
   - "Calculate 42 * 17"
   - "Give me a random number between 1 and 100"

**Check the browser console** - you'll see `[Amplifier] Intercepting client-side tool: {name}` proving they run locally!

## SDK Features Demonstrated

### Runtime Bundle Creation
```typescript
const session = await client.createSession({
  bundle: {
    name: "my-agent",
    instructions: "You are a helpful assistant",
    tools: [{ module: "tool-bash" }],
    clientTools: ["get-time", "calculate"],  // Run in browser!
  }
});
```

### Event Streaming
```typescript
for await (const event of client.prompt(sessionId, "Hello!")) {
  if (event.type === "content.delta") {
    // TypeScript knows event.data.delta exists!
    console.log(event.data.delta);
  }
}
```

### Client-Side Tools
```typescript
client.registerTool({
  name: "get-time",
  description: "Get current time",
  handler: async ({ timezone }) => {
    return { time: new Date().toLocaleString("en-US", { timeZone: timezone }) };
  }
});
```

### Typed Events
```typescript
// Full TypeScript type safety
if (event.type === "tool.call") {
  // No casting needed - TypeScript knows these fields exist!
  console.log(event.data.tool_name);
  console.log(event.toolCallId);  // For correlation
}
```

### Event Correlation
```typescript
// Reliable tool call → result matching
const toolCalls = new Map();

if (event.type === "tool.call") {
  toolCalls.set(event.toolCallId, event.data.tool_name);
}

if (event.type === "tool.result") {
  const toolName = toolCalls.get(event.toolCallId);
  console.log(`${toolName} completed!`);
}
```

## Architecture

```
Agent Playground (React App)
    ↓ Uses
amplifier-sdk (TypeScript)
    ↓ HTTP + SSE
amplifier-app-runtime (localhost:4096)
    ↓
amplifier-foundation + amplifier-core
```

## Development

### Build
```bash
npm run build
```

### Lint
```bash
npm run lint
```

### Type Check
```bash
npm run typecheck  # If you have this script
```

## Notes

- The playground uses the local SDK via `file:../../sdks/typescript`
- Changes to the SDK require rebuilding: `cd ../../sdks/typescript && npm run build`
- The playground demonstrates all major SDK features in a real React app
