---
title: "Building on Amplifier Just Got a Whole Lot Easier"
date: 2026-01-30
author: Amplifier Team
tags: [sdk, announcement, developer-experience]
---

# Building on Amplifier Just Got a Whole Lot Easier

We've all been there. You're building an application that needs to integrate with a powerful platform. You crack open the API documentation, fire up your HTTP client, and start writing request handlers. Before long, you're neck-deep in connection pooling, error handling, retry logic, and parsing streaming responses. What you wanted to build—a great application—has taken a back seat to wrestling with API plumbing.

**That ends today.**

We're excited to announce the **Amplifier SDK**—TypeScript and Python client libraries that make building applications on top of Amplifier's AI capabilities as simple as a few lines of code.

## The Problem: Raw APIs Are Nobody's Friend

Amplifier's `amplifier-app-runtime` exposes a powerful HTTP + Server-Sent Events (SSE) API that gives you access to:
- AI agent sessions with full context management
- Real-time streaming responses  
- Multi-provider AI model support (OpenAI, Anthropic, local models)
- Tool execution with approval flows
- Sub-agent orchestration

But here's the thing: **HTTP APIs are a starting point, not a solution.**

Without a proper SDK, developers face:

- **Type chaos**: No IntelliSense, no autocomplete, just string soup and crossed fingers
- **Streaming headaches**: SSE parsing, connection management, error recovery—all on you
- **Protocol complexity**: Session lifecycle, event types, approval flows—learn it all from scratch  
- **Language mismatch**: The API speaks JSON over HTTP; your Python/TypeScript app speaks objects and promises
- **Error-prone code**: Every developer reinvents the wheel, each with their own bugs

Even worse, direct API calls meant we weren't testing what developers would actually use. We needed to eat our own dog food.

## The Solution: SDKs That Feel Like Home

The Amplifier SDK provides idiomatic, fully-typed client libraries for TypeScript and Python. They handle all the HTTP/SSE complexity so you can focus on building your application.

Here's what you get:

### 🎯 **Type Safety**
Full TypeScript types and Python type hints. Your IDE knows what `event.type` can be. Your code editor autocompletes `client.createSession()`. Bugs caught at compile time, not runtime.

### 🌊 **Streaming Built-In**
Async iterators (Python) and async generators (TypeScript) make streaming responses feel natural. No manual SSE parsing, no connection juggling.

### 🧩 **Ergonomic APIs**
The SDK speaks your language. Python developers get `async with` context managers and snake_case methods. TypeScript developers get promises, camelCase, and `for await...of` loops.

### 🚀 **Simple Session Management**
Create a session, send prompts, get responses, clean up. The SDK handles the lifecycle.

### ✅ **Approval Flows**
When an agent needs permission to do something, the SDK surfaces it as an event. Respond with one method call.

## How It Works: The 30-Second Demo

**TypeScript:**
```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();

// Create a session
const session = await client.createSession({ bundle: "foundation" });

// Stream a response
for await (const event of client.prompt(session.id, "Write a haiku about coding")) {
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta as string);
  }
}

// Clean up
await client.deleteSession(session.id);
```

**Python:**
```python
import asyncio
from amplifier_sdk import AmplifierClient

async def main():
    async with AmplifierClient() as client:
        # Create a session
        session = await client.create_session(bundle="foundation")
        
        # Stream a response
        async for event in client.prompt(session.id, "Write a haiku about coding"):
            if event.type == "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)
        
        # Clean up
        await client.delete_session(session.id)

asyncio.run(main())
```

That's it. No HTTP clients, no SSE parsers, no protocol documentation. Just clean, readable code.

## Real-World Patterns

### One-Shot Execution
Need a quick answer? The SDK handles session creation and cleanup for you:

```python
async with AmplifierClient() as client:
    response = await client.run("What's the weather in Paris?")
    print(response.content)
```

### Handling Tool Calls
See what the agent is doing in real-time:

```typescript
for await (const event of client.prompt(session.id, "Analyze this codebase")) {
  if (event.type === "tool.call") {
    console.log(`🔧 Using tool: ${event.data.tool_name}`);
  }
  if (event.type === "content.delta") {
    process.stdout.write(event.data.delta as string);
  }
}
```

### Approval Flows
Let users control what agents can do:

```python
async for event in client.prompt(session.id, "Delete old logs"):
    if event.type == "approval.required":
        choice = input(f"Allow? {event.data['prompt']} (y/n): ")
        await client.respond_approval(session.id, event.data["request_id"], choice)
```

## The Architecture: Clean Separation

```
┌─────────────────────────────────────────────────────────────┐
│  Your App (chat-app, automation tool, agent interface)     │
│      ↓ Uses SDK                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  SDK (TypeScript/Python)                             │  │
│  │    • Type-safe client methods                        │  │
│  │    • Streaming abstraction                           │  │
│  │    • Session lifecycle management                    │  │
│  └───────────────────────────────────────────────────────┘  │
│      ↓ HTTP + SSE                                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  amplifier-app-runtime (localhost:4096)              │  │
│  │    • REST API + SSE streaming                        │  │
│  │    • Session management                              │  │
│  │    • Protocol handling                               │  │
│  └───────────────────────────────────────────────────────┘  │
│      ↓                                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  amplifier-foundation + amplifier-core               │  │
│  │    • AI agents and tools                             │  │
│  │    • Provider integrations                           │  │
│  │    • Core capabilities                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

The SDK sits between your application and the runtime, handling all the protocol details. You work with clean, typed interfaces. The runtime handles the heavy lifting.

## Getting Started in 3 Steps

### 1. Start the Runtime

```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --port 4096
```

### 2. Install the SDK

**TypeScript:**
```bash
npm install amplifier-sdk
```

**Python:**
```bash
pip install amplifier-sdk
```

### 3. Build Something Cool

```typescript
import { AmplifierClient } from "amplifier-sdk";

const client = new AmplifierClient();
const session = await client.createSession();

for await (const event of client.prompt(session.id, "Your prompt here")) {
  // Handle events
}
```

## What's Next?

This is just the beginning. We're actively developing:

- 🔄 **More language SDKs** (Go, Rust, Java—tell us what you need!)
- 📦 **Richer event types** (progress tracking, cost monitoring, debug traces)
- 🔌 **Webhook support** (async execution patterns)
- 🎨 **UI components** (drop-in React/Vue components for common patterns)
- 📚 **More examples** (chat apps, automation tools, agent orchestrators)

## We Want Your Feedback

The SDK is **ready to use today**, but it's still early days. We're building this for you, the community. Here's how you can help:

- **Try it out**: Build something, break something, tell us what's missing
- **Share patterns**: Found a great way to use the SDK? Show us!
- **Report issues**: [GitHub Issues](https://github.com/manojp99/amplifier-sdk) for bugs and feature requests  
- **Contribute**: Both SDKs are open source—PRs welcome!

## Resources

- 📦 **Repository**: [github.com/manojp99/amplifier-sdk](https://github.com/manojp99/amplifier-sdk)
- 📖 **TypeScript Docs**: [sdks/typescript/README.md](https://github.com/manojp99/amplifier-sdk/tree/main/sdks/typescript)
- 📖 **Python Docs**: [sdks/python/README.md](https://github.com/manojp99/amplifier-sdk/tree/main/sdks/python)
- 💬 **Discussion**: Join us on [GitHub Discussions](https://github.com/manojp99/amplifier-sdk/discussions)
- 🎯 **Examples**: Check out [examples/](https://github.com/manojp99/amplifier-sdk/tree/main/examples) for full applications

---

Building on Amplifier used to mean wrestling with HTTP and SSE. Now it means writing a few lines of clean, typed code and shipping your application.

**The SDK is ready. What will you build?**

— The Amplifier Team
