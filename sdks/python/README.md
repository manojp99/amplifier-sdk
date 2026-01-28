# Amplifier SDK for Python

Python client for Amplifier AI agents.

## Installation

```bash
pip install amplifier-sdk
```

## Quick Start

```python
from amplifier_sdk import Agent

# Create an agent
agent = Agent(
    instructions="You are a helpful coding assistant.",
    tools=["filesystem", "bash"],
)

# Run a prompt
response = await agent.run("List all Python files in the current directory")
print(response.content)

# Multi-turn conversation (session state maintained)
await agent.run("Remember my name is Alice")
response = await agent.run("What's my name?")
print(response.content)  # "Your name is Alice"

# Clean up
await agent.delete()
```

## Streaming

```python
from amplifier_sdk import Agent

agent = Agent(instructions="You are a poet.")

async for event in agent.stream("Write a haiku about coding"):
    print(event.content, end="", flush=True)
```

## Context Manager

```python
from amplifier_sdk import Agent

async with Agent(instructions="You help with code.") as agent:
    response = await agent.run("Hello!")
    print(response.content)
# Agent automatically deleted on exit
```

## One-Shot Usage

```python
from amplifier_sdk.agent import run

response = await run("What is 2+2?")
print(response.content)
```

## Low-Level Client

```python
from amplifier_sdk import AmplifierClient

client = AmplifierClient(base_url="http://localhost:8080")

# Create agent
agent_id = await client.create_agent(
    instructions="You are helpful.",
    tools=["bash"],
)

# Run prompt
response = await client.run(agent_id, "Hello!")
print(response.content)

# Stream
async for event in client.stream(agent_id, "Write a poem"):
    print(event.content, end="")

# Delete
await client.delete_agent(agent_id)
await client.close()
```

## Recipes

```python
from amplifier_sdk import AmplifierClient

client = AmplifierClient()

# Execute recipe
execution_id = await client.execute_recipe(
    recipe_yaml="""
name: code-review
steps:
  - id: analyze
    prompt: Analyze the code structure
  - id: review
    prompt: Review based on {{steps.analyze.result}}
""",
    context={"project": "my-app"}
)

# Check status
execution = await client.get_recipe_execution(execution_id)
print(execution.status)

# Approve gate
await client.approve_gate(execution_id, "review-gate")
```

## Configuration

```python
from amplifier_sdk import Agent

agent = Agent(
    instructions="You are helpful.",
    tools=["filesystem", "bash", "web_search"],
    provider="anthropic",           # LLM provider
    model="claude-sonnet-4-20250514",  # Model name
    base_url="http://localhost:8080",  # Server URL
    api_key="your-api-key",         # Optional auth
)
```

## Response Types

```python
from amplifier_sdk import RunResponse, StreamEvent

# RunResponse
response: RunResponse = await agent.run("Hello")
response.content      # str - The response text
response.tool_calls   # list[ToolCall] - Tools that were called
response.usage        # Usage - Token usage (input_tokens, output_tokens)
response.stop_reason  # str | None - Why generation stopped

# StreamEvent
async for event in agent.stream("Hello"):
    event.event    # str - Event type
    event.content  # str - Content from delta events
    event.is_done  # bool - True if final event
```

## Requirements

- Python 3.10+
- Amplifier server running at localhost:8080

## License

MIT
