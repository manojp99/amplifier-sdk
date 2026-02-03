"""Amplifier SDK - Python client for amplifier-app-runtime.

Simple, typed Python client for interacting with Amplifier runtime server.

Example:
    ```python
    from amplifier_sdk import AmplifierClient

    async with AmplifierClient() as client:
        # Create a session
        session = await client.create_session(bundle="foundation")

        # Send a prompt and stream the response
        async for event in client.prompt(session.id, "Hello!"):
            if event.type == "content.delta":
                print(event.data.get("delta", ""), end="", flush=True)

        # Or get the complete response
        response = await client.prompt_sync(session.id, "What is 2+2?")
        print(response.content)
    ```
"""

from .client import AmplifierClient
from .recipes import (
    RateLimitingConfig,
    RecipeApprovalGate,
    RecipeBuilder,
    RecipeDefinition,
    RecipeExecution,
    RecipeSession,
    RecipeStep,
    RecipeStepEvent,
    RecursionConfig,
    StepBuilder,
)
from .types import (
    AgentNode,
    ApprovalRequest,
    BehaviorDefinition,
    BundleDefinition,
    ClientTool,
    Event,
    EventType,
    ModuleConfig,
    PromptResponse,
    SessionConfig,
    SessionInfo,
    ToolCall,
)

__version__ = "0.1.0"

__all__ = [
    "AgentNode",
    "AmplifierClient",
    "Event",
    "EventType",
    "SessionInfo",
    "PromptResponse",
    "ToolCall",
    "ApprovalRequest",
    "BehaviorDefinition",
    "ClientTool",
    "BundleDefinition",
    "ModuleConfig",
    "SessionConfig",
    # Recipe types
    "RecipeBuilder",
    "StepBuilder",
    "RecipeDefinition",
    "RecipeStep",
    "RecipeSession",
    "RecipeStepEvent",
    "RecipeApprovalGate",
    "RecipeExecution",
    "RecursionConfig",
    "RateLimitingConfig",
]
