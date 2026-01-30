# Amplifier SDK for Python

Python client for [amplifier-app-runtime](https://github.com/manojp99/amplifier-app-runtime).

## Installation

```bash
pip install amplifier-sdk
```

Or with uv:

```bash
uv add amplifier-sdk
```

## Quick Start

```python
import asyncio
from amplifier_sdk import AmplifierClient

async def main():
    async with AmplifierClient() as client:
        # Create a session
        session = await client.create_session(bundle="foundation")
        
        # Stream a response
        async for event in client.prompt(session.id, "Hello!"):
            if event.type == "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)
        print()  # Newline at end
        
        # Clean up
        await client.delete_session(session.id)

asyncio.run(main())
```

## Usage Patterns

### Streaming Response

```python
async with AmplifierClient() as client:
    session = await client.create_session()
    
    async for event in client.prompt(session.id, "Tell me a story"):
        match event.type:
            case "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)
            case "tool.call":
                print(f"\nUsing tool: {event.data.get('tool_name')}")
            case "thinking.delta":
                print(f"[thinking] {event.data.get('delta', '')}")
            case "content.end":
                print()  # Done
```

### Synchronous Response

```python
async with AmplifierClient() as client:
    session = await client.create_session()
    
    # Wait for complete response
    response = await client.prompt_sync(session.id, "What is 2+2?")
    print(response.content)  # "4"
    print(response.tool_calls)  # List of tool calls made
```

### One-Shot Execution

```python
async with AmplifierClient() as client:
    # Creates session, runs prompt, returns result, cleans up
    response = await client.run("What is the capital of France?")
    print(response.content)
```

### One-Shot Streaming

```python
async with AmplifierClient() as client:
    # Creates session, streams prompt, cleans up
    async for event in client.stream("Tell me about Python"):
        if event.type == "content.delta":
            print(event.data.get("delta", ""), end="")
```

### Handling Approvals

```python
async with AmplifierClient() as client:
    session = await client.create_session()
    
    async for event in client.prompt(session.id, "Delete all files"):
        if event.type == "approval.required":
            # Agent is asking for permission
            request_id = event.data.get("request_id")
            prompt = event.data.get("prompt")
            options = event.data.get("options")
            
            print(f"Approval needed: {prompt}")
            print(f"Options: {options}")
            
            # Respond to approval
            choice = input("Your choice: ")
            await client.respond_approval(session.id, request_id, choice)
```

## API Reference

### AmplifierClient

```python
client = AmplifierClient(
    base_url="http://localhost:4096",  # Server URL
    timeout=300.0,                      # Request timeout
)
```

### Methods

| Method | Description |
|--------|-------------|
| `create_session(bundle, provider, model)` | Create a new session |
| `get_session(session_id)` | Get session info |
| `list_sessions()` | List all sessions |
| `delete_session(session_id)` | Delete a session |
| `prompt(session_id, content)` | Stream a prompt (async iterator) |
| `prompt_sync(session_id, content)` | Wait for complete response |
| `cancel(session_id)` | Cancel ongoing execution |
| `respond_approval(session_id, request_id, choice)` | Respond to approval |
| `ping()` | Check server health |
| `capabilities()` | Get server capabilities |
| `run(content, ...)` | One-shot execution |
| `stream(content, ...)` | One-shot streaming |

### Event Types

| Type | Description |
|------|-------------|
| `content.delta` | Streaming text chunk |
| `content.end` | Content complete |
| `thinking.delta` | Reasoning/thinking chunk |
| `tool.call` | Tool being called |
| `tool.result` | Tool result received |
| `approval.required` | Approval needed |
| `error` | Error occurred |

## Server Setup

Start the amplifier-app-runtime server:

```bash
cd amplifier-app-runtime
uv run python -m amplifier_app_runtime.cli --port 4096
```

## License

MIT
