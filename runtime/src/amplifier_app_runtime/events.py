"""Events, Bus, and SSE response.

Consolidates: transport/base.py (Event model), bus.py (pub/sub Bus),
events.py (typed event definitions), event_types.py (taxonomy/filters),
and transport/sse.py (server-side SSE response helper).

No internal dependencies -- only external packages (pydantic, starlette).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

# ============================================================================
# Event model (from transport/base.py -- stripped of ABC transport classes)
# ============================================================================


class Event(BaseModel):
    """Base event structure for transport."""

    type: str
    properties: dict[str, Any] = {}
    sequence: int | None = None


# ============================================================================
# Bus (from bus.py)
# ============================================================================

T = TypeVar("T", bound=BaseModel)

EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class EventDefinition(Generic[T]):
    """Typed event definition.

    Usage:
        SessionCreated = Bus.define("session.created", SessionCreatedProps)
        await Bus.publish(SessionCreated, SessionCreatedProps(session_id="..."))
    """

    type: str
    schema: type[T]


class Bus:
    """Simple event bus with wildcard subscription support.

    Thread-safe via asyncio.Lock. All subscriptions and publishes
    are handled asynchronously.
    """

    _subscriptions: dict[str, list[EventCallback]] = {}
    _lock: asyncio.Lock | None = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Get or create the lock (lazy init for event loop safety)."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def define(cls, event_type: str, schema: type[T]) -> EventDefinition[T]:
        """Define a typed event."""
        return EventDefinition(type=event_type, schema=schema)

    @classmethod
    async def publish(cls, event_def: EventDefinition[T], properties: T) -> None:
        """Publish event to all subscribers."""
        payload = {"type": event_def.type, "properties": properties.model_dump()}

        async with cls._get_lock():
            specific_subs = list(cls._subscriptions.get(event_def.type, []))
            wildcard_subs = list(cls._subscriptions.get("*", []))

        for callback in specific_subs:
            try:
                await callback(payload)
            except Exception:
                logger.exception(f"Error in subscriber for {event_def.type}")

        for callback in wildcard_subs:
            try:
                await callback(payload)
            except Exception:
                logger.exception(f"Error in wildcard subscriber for {event_def.type}")

    @classmethod
    async def subscribe(
        cls, event_def: EventDefinition[T], callback: EventCallback
    ) -> Callable[[], None]:
        """Subscribe to a specific event type. Returns unsubscribe function."""
        return await cls._subscribe(event_def.type, callback)

    @classmethod
    async def subscribe_all(cls, callback: EventCallback) -> Callable[[], None]:
        """Subscribe to ALL events (used by SSE endpoint). Returns unsubscribe function."""
        return await cls._subscribe("*", callback)

    @classmethod
    async def _subscribe(cls, key: str, callback: EventCallback) -> Callable[[], None]:
        """Internal subscribe implementation."""
        async with cls._get_lock():
            if key not in cls._subscriptions:
                cls._subscriptions[key] = []
            cls._subscriptions[key].append(callback)

        def unsubscribe() -> None:
            if key in cls._subscriptions and callback in cls._subscriptions[key]:
                cls._subscriptions[key].remove(callback)

        return unsubscribe

    @classmethod
    async def stream(cls) -> AsyncIterator[dict[str, Any]]:
        """Create an async iterator that yields all events.

        Useful for SSE endpoints. Yields events as they are published.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def on_event(payload: dict[str, Any]) -> None:
            await queue.put(payload)

        unsubscribe = await cls.subscribe_all(on_event)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            unsubscribe()

    @classmethod
    def reset(cls) -> None:
        """Reset bus state (for testing)."""
        cls._subscriptions = {}
        cls._lock = None


# ============================================================================
# Typed event definitions (from events.py)
# ============================================================================

# --- Server Lifecycle ---


class ServerConnectedProps(BaseModel):
    """Server connection established."""

    pass


class ServerHeartbeatProps(BaseModel):
    """Heartbeat to keep connection alive."""

    pass


ServerConnected = Bus.define("server.connected", ServerConnectedProps)
ServerHeartbeat = Bus.define("server.heartbeat", ServerHeartbeatProps)

# --- Session Events ---


class SessionCreatedProps(BaseModel):
    """A new session was created."""

    session_id: str
    title: str


class SessionUpdatedProps(BaseModel):
    """Session metadata was updated."""

    session_id: str
    title: str | None = None


class SessionDeletedProps(BaseModel):
    """Session was deleted."""

    session_id: str


class SessionIdleProps(BaseModel):
    """Session finished processing and is idle."""

    session_id: str


class SessionErrorProps(BaseModel):
    """An error occurred in the session."""

    session_id: str
    error: dict


SessionCreated = Bus.define("session.created", SessionCreatedProps)
SessionUpdated = Bus.define("session.updated", SessionUpdatedProps)
SessionDeleted = Bus.define("session.deleted", SessionDeletedProps)
SessionIdle = Bus.define("session.idle", SessionIdleProps)
SessionError = Bus.define("session.error", SessionErrorProps)

# --- Message Events ---


class MessageCreatedProps(BaseModel):
    """A new message was created."""

    session_id: str
    message_id: str
    role: str  # "user" | "assistant"


class MessagePartUpdatedProps(BaseModel):
    """A message part was updated (streaming)."""

    session_id: str
    message_id: str
    part: dict


MessageCreated = Bus.define("message.created", MessageCreatedProps)
MessagePartUpdated = Bus.define("message.part.updated", MessagePartUpdatedProps)

# --- Tool Events ---


class ToolStartedProps(BaseModel):
    """A tool execution started."""

    session_id: str
    tool_name: str
    tool_call_id: str
    input: dict


class ToolCompletedProps(BaseModel):
    """A tool execution completed."""

    session_id: str
    tool_name: str
    tool_call_id: str
    output: str | None = None
    error: str | None = None


ToolStarted = Bus.define("tool.started", ToolStartedProps)
ToolCompleted = Bus.define("tool.completed", ToolCompletedProps)

# --- Approval Events ---


class ApprovalRequestedProps(BaseModel):
    """An approval was requested."""

    session_id: str
    approval_id: str
    tool_name: str
    description: str
    input: dict


class ApprovalResolvedProps(BaseModel):
    """An approval was resolved."""

    session_id: str
    approval_id: str
    approved: bool
    reason: str | None = None


ApprovalRequested = Bus.define("approval.requested", ApprovalRequestedProps)
ApprovalResolved = Bus.define("approval.resolved", ApprovalResolvedProps)


# ============================================================================
# Event taxonomy constants (from event_types.py)
# ============================================================================


class EventCategory(str, Enum):
    """Event categories for filtering and routing."""

    SESSION = "session"
    PROMPT = "prompt"
    CONTENT = "content_block"
    THINKING = "thinking"
    TOOL = "tool"
    PROVIDER = "provider"
    LLM = "llm"
    APPROVAL = "approval"
    CONTEXT = "context"
    CANCEL = "cancel"
    USER = "user"
    PLAN = "plan"
    ARTIFACT = "artifact"
    TRANSPORT = "transport"


# Canonical event names (aligned with amplifier-core)
SESSION_START = "session:start"
SESSION_END = "session:end"
SESSION_FORK = "session:fork"
SESSION_RESUME = "session:resume"

PROMPT_SUBMIT = "prompt:submit"
PROMPT_COMPLETE = "prompt:complete"

CONTENT_BLOCK_START = "content_block:start"
CONTENT_BLOCK_DELTA = "content_block:delta"
CONTENT_BLOCK_END = "content_block:end"

THINKING_DELTA = "thinking:delta"
THINKING_FINAL = "thinking:final"

TOOL_PRE = "tool:pre"
TOOL_POST = "tool:post"
TOOL_ERROR = "tool:error"

PROVIDER_REQUEST = "provider:request"
PROVIDER_RESPONSE = "provider:response"
PROVIDER_ERROR = "provider:error"

LLM_REQUEST = "llm:request"
LLM_REQUEST_DEBUG = "llm:request:debug"
LLM_REQUEST_RAW = "llm:request:raw"
LLM_RESPONSE = "llm:response"
LLM_RESPONSE_DEBUG = "llm:response:debug"
LLM_RESPONSE_RAW = "llm:response:raw"

APPROVAL_REQUIRED = "approval:required"
APPROVAL_GRANTED = "approval:granted"
APPROVAL_DENIED = "approval:denied"

CONTEXT_COMPACTION = "context:compaction"

CANCEL_REQUESTED = "cancel:requested"
CANCEL_COMPLETED = "cancel:completed"

USER_NOTIFICATION = "user:notification"

PLAN_START = "plan:start"
PLAN_END = "plan:end"

ARTIFACT_WRITE = "artifact:write"
ARTIFACT_READ = "artifact:read"

TRANSPORT_ERROR = "transport:error"
TRANSPORT_CONNECTED = "transport:connected"
TRANSPORT_DISCONNECTED = "transport:disconnected"


ALL_EVENTS: list[str] = [
    SESSION_START,
    SESSION_END,
    SESSION_FORK,
    SESSION_RESUME,
    PROMPT_SUBMIT,
    PROMPT_COMPLETE,
    CONTENT_BLOCK_START,
    CONTENT_BLOCK_DELTA,
    CONTENT_BLOCK_END,
    THINKING_DELTA,
    THINKING_FINAL,
    TOOL_PRE,
    TOOL_POST,
    TOOL_ERROR,
    PROVIDER_REQUEST,
    PROVIDER_RESPONSE,
    PROVIDER_ERROR,
    LLM_REQUEST,
    LLM_REQUEST_DEBUG,
    LLM_REQUEST_RAW,
    LLM_RESPONSE,
    LLM_RESPONSE_DEBUG,
    LLM_RESPONSE_RAW,
    APPROVAL_REQUIRED,
    APPROVAL_GRANTED,
    APPROVAL_DENIED,
    CONTEXT_COMPACTION,
    CANCEL_REQUESTED,
    CANCEL_COMPLETED,
    USER_NOTIFICATION,
    PLAN_START,
    PLAN_END,
    ARTIFACT_WRITE,
    ARTIFACT_READ,
]

UI_EVENTS: list[str] = [
    SESSION_START,
    SESSION_END,
    SESSION_FORK,
    PROMPT_COMPLETE,
    CONTENT_BLOCK_START,
    CONTENT_BLOCK_DELTA,
    CONTENT_BLOCK_END,
    THINKING_DELTA,
    THINKING_FINAL,
    TOOL_PRE,
    TOOL_POST,
    TOOL_ERROR,
    PROVIDER_REQUEST,
    PROVIDER_RESPONSE,
    APPROVAL_REQUIRED,
    APPROVAL_GRANTED,
    APPROVAL_DENIED,
    CONTEXT_COMPACTION,
    CANCEL_REQUESTED,
    CANCEL_COMPLETED,
    USER_NOTIFICATION,
]


# Event data models


class AmplifierEvent(BaseModel):
    """Base event structure."""

    type: str
    session_id: str | None = None
    timestamp: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    child_session_id: str | None = None
    parent_tool_call_id: str | None = None
    nesting_depth: int = 0


class ContentBlockEvent(AmplifierEvent):
    """Content streaming event."""

    block_type: str = "text"
    block_index: int = 0
    delta: str | None = None
    content: str | None = None


class ToolEvent(AmplifierEvent):
    """Tool execution event."""

    tool_name: str
    tool_call_id: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None


class ApprovalEvent(AmplifierEvent):
    """Approval request/response event."""

    request_id: str
    prompt: str | None = None
    options: list[str] = Field(default_factory=list)
    timeout: float = 30.0
    default: str | None = None
    choice: str | None = None


class ProviderEvent(AmplifierEvent):
    """Provider interaction event."""

    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None


# Event utility functions


def get_event_category(event_type: str) -> EventCategory | None:
    """Get the category for an event type."""
    if ":" not in event_type:
        return None
    prefix = event_type.split(":")[0]
    try:
        return EventCategory(prefix)
    except ValueError:
        return None


def is_debug_event(event_type: str) -> bool:
    """Check if event is a debug/raw event (high volume, may contain sensitive data)."""
    return ":debug" in event_type or ":raw" in event_type


def is_ui_safe(event_type: str) -> bool:
    """Check if event is safe to stream to UI."""
    return event_type in UI_EVENTS


def filter_events(
    events: list[str],
    categories: list[EventCategory] | None = None,
    exclude_debug: bool = True,
) -> list[str]:
    """Filter events by category and debug status."""
    result = events
    if exclude_debug:
        result = [e for e in result if not is_debug_event(e)]
    if categories:
        category_prefixes = [c.value for c in categories]
        result = [e for e in result if any(e.startswith(p + ":") for p in category_prefixes)]
    return result


# ============================================================================
# Server-side SSE response helper (from transport/sse.py)
# ============================================================================


async def sse_response(
    request: Request,
    event_iterator: AsyncIterator[Event],
    heartbeat_interval: float = 30.0,
) -> StreamingResponse:
    """Create an SSE streaming response.

    Args:
        request: The incoming request (for disconnect detection)
        event_iterator: Async iterator yielding Events
        heartbeat_interval: Seconds between heartbeat pings
    """

    async def generate():
        # Send initial connected event
        yield f"data: {json.dumps({'type': 'server.connected', 'properties': {}})}\n\n"

        heartbeat_task = None
        event_queue: asyncio.Queue[Event | None] = asyncio.Queue()

        async def heartbeat():
            """Send periodic heartbeats to keep connection alive."""
            while True:
                await asyncio.sleep(heartbeat_interval)
                await event_queue.put(Event(type="server.heartbeat", properties={}))

        async def collect_events():
            """Collect events from the iterator into the queue."""
            try:
                async for event in event_iterator:
                    await event_queue.put(event)
            finally:
                await event_queue.put(None)  # Signal completion

        heartbeat_task = asyncio.create_task(heartbeat())
        collector_task = asyncio.create_task(collect_events())

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    if event is None:
                        break  # Iterator exhausted

                    payload = {"type": event.type, "properties": event.properties}
                    yield f"data: {json.dumps(payload)}\n\n"

                except TimeoutError:
                    continue  # Check disconnect and try again

        finally:
            heartbeat_task.cancel()
            collector_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            with contextlib.suppress(asyncio.CancelledError):
                await collector_task

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
