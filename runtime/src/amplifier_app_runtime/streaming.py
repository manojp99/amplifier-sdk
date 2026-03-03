"""Streaming, approval, display, and spawn protocols.

Consolidates: protocols/streaming.py + protocols/approval.py +
              protocols/display.py + protocols/spawn.py

Depends on: .events (Event model)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from amplifier_core.models import HookResult

from .events import Event

logger = logging.getLogger(__name__)


# ============================================================================
# ServerStreamingHook (from protocols/streaming.py)
# ============================================================================


class ServerStreamingHook:
    """Hook that forwards amplifier-core events to the server transport.

    This is registered with the session's hook registry to capture all
    events and forward them to connected clients via the send function.

    Events are also queued so they can be yielded by session.execute().
    This ensures the SDK client receives ALL events (thinking, tools, etc).
    """

    # Events with potentially huge payloads that should not be forwarded
    SKIP_EVENTS = {
        "llm:request:raw",
        "llm:response:raw",
        "llm:request:debug",
        "llm:response:debug",
        "session:start:raw",
        "session:start:debug",
    }

    def __init__(
        self,
        send_fn: Callable[[Event], Awaitable[None]] | None = None,
        show_thinking: bool = True,
    ) -> None:
        """Initialize the streaming hook.

        Args:
            send_fn: Async function to send events to the client
            show_thinking: Whether to forward thinking blocks
        """
        self._send_fn = send_fn
        self._show_thinking = show_thinking
        self._sequence = 0
        self._event_queue: asyncio.Queue[Event | None] = asyncio.Queue()
        self._streaming = False

    def set_send_fn(self, send_fn: Callable[[Event], Awaitable[None]]) -> None:
        """Set the send function after initialization."""
        self._send_fn = send_fn

    def start_streaming(self) -> None:
        """Start collecting events for streaming."""
        self._streaming = True
        # Clear any stale events
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def stop_streaming(self) -> None:
        """Stop streaming and signal completion."""
        self._streaming = False
        self._event_queue.put_nowait(None)

    async def get_events(self) -> AsyncIterator[Event]:
        """Yield events as they arrive during execution."""
        while True:
            event = await self._event_queue.get()
            if event is None:
                break
            yield event

    async def __call__(self, event_type: str, data: dict[str, Any]) -> HookResult:
        """Handle an event from amplifier-core.

        Args:
            event_type: The event type (e.g., "content_block:delta")
            data: The event data

        Returns:
            HookResult with action="continue"
        """
        # Skip raw/debug events with huge payloads
        if event_type in self.SKIP_EVENTS:
            return HookResult(action="continue")

        # Skip thinking events if disabled
        if not self._show_thinking and event_type.startswith("thinking:"):
            return HookResult(action="continue")

        try:
            transport_event = Event(
                type=event_type,
                properties=data,
                sequence=self._sequence,
            )
            self._sequence += 1

            # Queue event for yielding by execute()
            if self._streaming:
                self._event_queue.put_nowait(transport_event)

            # Also send via send_fn if available (for other channels)
            if self._send_fn:
                await self._send_fn(transport_event)

        except Exception as e:
            logger.warning(f"Failed to handle event {event_type}: {e}")

        # Always continue - streaming is observational
        return HookResult(action="continue")

    def reset_sequence(self) -> None:
        """Reset the sequence counter for a new prompt."""
        self._sequence = 0


# Events to capture from amplifier-core
DEFAULT_EVENTS_TO_CAPTURE = [
    # Content streaming
    "content_block:start",
    "content_block:delta",
    "content_block:end",
    # Thinking (extended thinking)
    "thinking:delta",
    "thinking:final",
    # Tool execution
    "tool:pre",
    "tool:post",
    "tool:error",
    # Session lifecycle
    "session:start",
    "session:end",
    "session:fork",
    "session:join",
    "session:resume",
    # Prompt lifecycle
    "prompt:submit",
    "prompt:complete",
    # Provider/LLM
    "provider:request",
    "provider:response",
    "provider:error",
    "llm:request",
    "llm:request:debug",
    "llm:request:raw",
    "llm:response",
    "llm:response:debug",
    "llm:response:raw",
    # Cancellation
    "cancel:requested",
    "cancel:completed",
    # User notifications
    "user:notification",
    # Context
    "context:compaction",
    # Planning
    "plan:start",
    "plan:end",
    # Artifacts
    "artifact:write",
    "artifact:read",
    # Todo updates (amplifier-core todo tool)
    "todo:update",
    # Approval
    "approval:required",
    "approval:granted",
    "approval:denied",
]


def get_events_to_capture() -> list[str]:
    """Get list of events to capture.

    Tries to import ALL_EVENTS from amplifier-core, falls back to default list.
    """
    try:
        from amplifier_core.events import ALL_EVENTS

        return list(ALL_EVENTS)
    except ImportError:
        logger.warning(
            "Could not import ALL_EVENTS from amplifier_core.events, using fallback list"
        )
        return DEFAULT_EVENTS_TO_CAPTURE.copy()


def register_streaming_hook(
    session: Any,
    hook: ServerStreamingHook,
) -> int:
    """Register streaming hook with a session's hook registry.

    Args:
        session: AmplifierSession to register hook on
        hook: The streaming hook instance

    Returns:
        Number of events registered
    """
    hook_registry = session.coordinator.hooks
    if not hook_registry:
        logger.warning("Session has no hook registry")
        return 0

    events = get_events_to_capture()

    # Also try to get auto-discovered module events
    discovered = session.coordinator.get_capability("observability.events") or []
    if discovered:
        events.extend(discovered)
        logger.info(f"Auto-discovered {len(discovered)} additional module events")

    # Register hook for each event
    for event in events:
        hook_registry.register(
            event=event,
            handler=hook,
            priority=100,  # Run early to capture events
            name=f"server-streaming:{event}",
        )

    logger.info(f"Registered streaming hook for {len(events)} events")
    return len(events)


# ============================================================================
# ServerApprovalSystem (from protocols/approval.py)
# ============================================================================


class ApprovalTimeoutError(Exception):
    """Raised when user approval times out."""

    pass


@dataclass
class PendingApproval:
    """A pending approval request waiting for user response."""

    request_id: str
    prompt: str
    options: list[str]
    future: asyncio.Future[str]
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class ServerApprovalSystem:
    """Approval system that sends approval requests to connected clients.

    Implements the ApprovalSystem protocol expected by amplifier-core.
    Approval requests are sent as events to clients, and responses are
    collected via the handle_response method.

    Interface matches CLIApprovalSystem and WebApprovalSystem:
        request_approval(prompt, options, timeout, default) -> str
    """

    def __init__(
        self,
        send_fn: Callable[[Event], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the approval system.

        Args:
            send_fn: Async function to send events to the client
        """
        self._send_fn = send_fn
        self._pending: dict[str, PendingApproval] = {}
        self._cache: dict[int, str] = {}  # Session-scoped approval cache

    def set_send_fn(self, send_fn: Callable[[Event], Awaitable[None]]) -> None:
        """Set the send function after initialization."""
        self._send_fn = send_fn

    async def request_approval(
        self,
        prompt: str,
        options: list[str],
        timeout: float,
        default: Literal["allow", "deny"],
    ) -> str:
        """Request approval from the user.

        This is the interface expected by amplifier-core's approval system.

        Args:
            prompt: Question to ask user (e.g., "Allow tool X to run?")
            options: Available choices (e.g., ["Allow once", "Allow always", "Deny"])
            timeout: Seconds to wait for response
            default: Action to take on timeout ("allow" or "deny")

        Returns:
            The user's chosen option string
        """
        # Check cache for "Allow always" decisions
        cache_key = hash((prompt, tuple(options)))
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug(f"Using cached approval: {cached}")
            return cached

        if not self._send_fn:
            logger.warning("No send function configured, using default")
            return self._resolve_default(default, options)

        request_id = f"approval_{uuid.uuid4().hex[:12]}"

        # Create future for response
        loop = asyncio.get_event_loop()
        future: asyncio.Future[str] = loop.create_future()

        # Store pending request
        pending = PendingApproval(
            request_id=request_id,
            prompt=prompt,
            options=options,
            future=future,
        )
        self._pending[request_id] = pending

        try:
            # Send approval request to client
            event = Event(
                type="approval:required",
                properties={
                    "request_id": request_id,
                    "prompt": prompt,
                    "options": options,
                    "timeout": timeout,
                    "default": default,
                },
            )
            await self._send_fn(event)
            logger.debug(f"Sent approval request {request_id}")

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.debug(f"Received approval response for {request_id}: {result}")

            # Cache "always" decisions
            if "always" in result.lower():
                self._cache[cache_key] = result
                logger.debug(f"Cached 'always' approval: {result}")

            # Send confirmation event
            confirmation_event = Event(
                type="approval:resolved",
                properties={
                    "request_id": request_id,
                    "choice": result,
                },
            )
            await self._send_fn(confirmation_event)

            return result

        except TimeoutError:
            logger.warning(f"Approval request {request_id} timed out")
            if self._send_fn:
                await self._send_fn(
                    Event(
                        type="approval:timeout",
                        properties={
                            "request_id": request_id,
                            "applied_default": default,
                        },
                    )
                )
            return self._resolve_default(default, options)

        finally:
            self._pending.pop(request_id, None)

    def _resolve_default(
        self,
        default: Literal["allow", "deny"],
        options: list[str],
    ) -> str:
        """Find the best matching option for the default action."""
        for option in options:
            option_lower = option.lower()
            if default == "allow" and ("allow" in option_lower or "yes" in option_lower):
                return option
            if default == "deny" and ("deny" in option_lower or "no" in option_lower):
                return option

        # Fall back to last option (typically "deny") or first
        return options[-1] if default == "deny" else options[0]

    def handle_response(self, request_id: str, choice: str) -> bool:
        """Handle an approval response from the client.

        Returns:
            True if the response was handled, False if request not found
        """
        pending = self._pending.get(request_id)
        if not pending:
            logger.warning(f"No pending approval for request {request_id}")
            return False

        if pending.future.done():
            logger.warning(f"Approval {request_id} already completed")
            return False

        # Validate choice
        if choice not in pending.options:
            logger.warning(
                f"Invalid choice '{choice}' for approval {request_id}, "
                f"expected one of {pending.options}"
            )
            # Still accept it but log the warning

        pending.future.set_result(choice)
        logger.debug(f"Handled approval response for {request_id}: {choice}")
        return True

    def get_pending_count(self) -> int:
        """Get the number of pending approval requests."""
        return len(self._pending)

    def get_pending_requests(self) -> list[dict[str, Any]]:
        """Get list of pending approval requests."""
        return [
            {
                "request_id": p.request_id,
                "prompt": p.prompt,
                "options": p.options,
            }
            for p in self._pending.values()
        ]

    def cancel_all(self) -> int:
        """Cancel all pending approval requests.

        Returns:
            Number of requests cancelled
        """
        count = 0
        for pending in list(self._pending.values()):
            if not pending.future.done():
                pending.future.set_result("deny")
                count += 1
        self._pending.clear()
        return count


# ============================================================================
# ServerDisplaySystem (from protocols/display.py)
# ============================================================================


class ServerDisplaySystem:
    """Display system that sends notifications to connected clients.

    Implements the DisplaySystem protocol expected by amplifier-core.
    Notifications are sent as events to clients via the send function.

    Interface matches CLIDisplaySystem and WebDisplaySystem:
        show_message(message, level, source) -> None
        push_nesting() / pop_nesting() for sub-session hierarchy
    """

    def __init__(
        self,
        send_fn: Callable[[Event], Awaitable[None]] | None = None,
        nesting_depth: int = 0,
    ) -> None:
        """Initialize the display system.

        Args:
            send_fn: Async function to send events to the client
            nesting_depth: Current nesting level for sub-sessions
        """
        self._send_fn = send_fn
        self._nesting_depth = nesting_depth

    def set_send_fn(self, send_fn: Callable[[Event], Awaitable[None]]) -> None:
        """Set the send function after initialization."""
        self._send_fn = send_fn

    async def show_message(
        self,
        message: str,
        level: Literal["info", "warning", "error"] = "info",
        source: str = "hook",
    ) -> None:
        """Display message to user via event stream.

        This is the interface expected by amplifier-core's display system.

        Args:
            message: Message text to display
            level: Severity level (info/warning/error)
            source: Message source for context (e.g., "hook:python-check")
        """
        if not self._send_fn:
            log_fn = getattr(logger, level, logger.info)
            log_fn(f"[{source}] {message}")
            return

        try:
            event = Event(
                type="display:message",
                properties={
                    "message": message,
                    "level": level,
                    "source": source,
                    "nesting_depth": self._nesting_depth,
                },
            )
            await self._send_fn(event)
        except Exception as e:
            logger.warning(f"Failed to send display message: {e}")

    def push_nesting(self) -> ServerDisplaySystem:
        """Create a nested display system for sub-sessions."""
        return ServerDisplaySystem(
            send_fn=self._send_fn,
            nesting_depth=self._nesting_depth + 1,
        )

    def pop_nesting(self) -> ServerDisplaySystem:
        """Create a display system with reduced nesting."""
        return ServerDisplaySystem(
            send_fn=self._send_fn,
            nesting_depth=max(0, self._nesting_depth - 1),
        )

    @property
    def nesting_depth(self) -> int:
        """Current nesting depth for visual hierarchy."""
        return self._nesting_depth

    async def info(self, message: str, source: str = "system") -> None:
        """Send an info message."""
        await self.show_message(message, level="info", source=source)

    async def warning(self, message: str, source: str = "system") -> None:
        """Send a warning message."""
        await self.show_message(message, level="warning", source=source)

    async def error(self, message: str, source: str = "system") -> None:
        """Send an error message."""
        await self.show_message(message, level="error", source=source)


# ============================================================================
# ServerSpawnManager (from protocols/spawn.py)
# ============================================================================


class ServerSpawnManager:
    """Manages spawning of sub-sessions for agent delegation.

    This enables the task tool to spawn sub-agents. Events from child
    sessions are forwarded to the parent session's hooks for streaming.
    """

    def __init__(self) -> None:
        """Initialize the spawn manager."""
        self._active_spawns: dict[str, Any] = {}

    async def spawn(
        self,
        agent_name: str,
        instruction: str,
        parent_session: Any,
        agent_configs: dict[str, dict],
        prepared_bundle: Any,  # PreparedBundle from amplifier_foundation
        parent_tool_call_id: str | None = None,
        sub_session_id: str | None = None,
        tool_inheritance: dict[str, list[str]] | None = None,
        hook_inheritance: dict[str, list[str]] | None = None,
        orchestrator_config: dict | None = None,
        parent_messages: list[dict] | None = None,
        provider_override: str | None = None,
        model_override: str | None = None,
    ) -> dict:
        """Spawn a sub-session for agent delegation.

        Args:
            agent_name: Name of the agent to spawn
            instruction: Task instruction for the agent
            parent_session: The parent AmplifierSession
            agent_configs: Agent configurations from the bundle
            prepared_bundle: The PreparedBundle for creating sessions
            parent_tool_call_id: Optional tool call ID for correlation
            sub_session_id: Optional session ID to use
            tool_inheritance: Tools to inherit from parent
            hook_inheritance: Hooks to inherit from parent
            orchestrator_config: Optional orchestrator configuration
            parent_messages: Optional context messages to pass
            provider_override: Optional provider to use
            model_override: Optional model to use

        Returns:
            Result dict with status, result, and session_id
        """
        if not sub_session_id:
            sub_session_id = f"sub_{uuid.uuid4().hex[:12]}"

        logger.info(f"Spawning agent '{agent_name}' with session {sub_session_id}")

        parent_hooks = parent_session.coordinator.hooks

        try:
            agent_config = agent_configs.get(agent_name)
            if not agent_config:
                return {
                    "status": "error",
                    "error": f"Unknown agent: {agent_name}",
                    "session_id": sub_session_id,
                }

            # Emit session:fork event BEFORE creating child session
            if parent_hooks:
                logger.info(
                    f"Emitting session:fork: child={sub_session_id}, "
                    f"tool_call_id={parent_tool_call_id}, agent={agent_name}"
                )
                await parent_hooks.emit(
                    "session:fork",
                    {
                        "parent_id": parent_session.session_id,
                        "child_id": sub_session_id,
                        "parent_tool_call_id": parent_tool_call_id,
                        "agent": agent_name,
                    },
                )

            # Create event forwarder to parent hooks
            def create_event_forwarder():
                """Create a hook that forwards events to parent session."""

                async def forward_event(event_type: str, data: dict) -> dict:
                    data = dict(data)
                    data["child_session_id"] = sub_session_id
                    data["parent_tool_call_id"] = parent_tool_call_id
                    data["agent_name"] = agent_name
                    data["nesting_depth"] = data.get("nesting_depth", 0) + 1

                    if parent_hooks:
                        await parent_hooks.emit(event_type, data)
                    return {}

                return forward_event

            # Create child session
            child_session = await prepared_bundle.create_session(
                session_id=sub_session_id,
                parent_id=parent_session.session_id,
                agent_name=agent_name,
            )

            # Register event forwarder
            forwarder = create_event_forwarder()
            child_hooks = child_session.coordinator.hooks
            if child_hooks:
                for event in [
                    "content_block:start",
                    "content_block:delta",
                    "content_block:end",
                    "tool:pre",
                    "tool:post",
                    "tool:error",
                ]:
                    child_hooks.register(
                        event=event,
                        handler=forwarder,
                        priority=50,
                        name=f"parent-forward:{event}",
                    )

            # Track active spawn
            self._active_spawns[sub_session_id] = child_session

            # Execute the instruction
            logger.info(f"Executing instruction in spawned session {sub_session_id}")
            result = await child_session.execute(instruction)

            # Clean up
            self._active_spawns.pop(sub_session_id, None)

            # Emit session:join event when spawn completes
            if parent_hooks:
                await parent_hooks.emit(
                    "session:join",
                    {
                        "parent_id": parent_session.session_id,
                        "child_id": sub_session_id,
                        "parent_tool_call_id": parent_tool_call_id,
                        "agent": agent_name,
                        "status": "success",
                    },
                )

            return {
                "status": "success",
                "result": result,
                "session_id": sub_session_id,
            }

        except Exception as e:
            logger.error(f"Spawn failed for agent '{agent_name}': {e}")
            self._active_spawns.pop(sub_session_id, None)

            # Emit session:join event with error status
            if parent_hooks:
                await parent_hooks.emit(
                    "session:join",
                    {
                        "parent_id": parent_session.session_id,
                        "child_id": sub_session_id,
                        "parent_tool_call_id": parent_tool_call_id,
                        "agent": agent_name,
                        "status": "error",
                        "error": str(e),
                    },
                )

            return {
                "status": "error",
                "error": str(e),
                "session_id": sub_session_id,
            }

    def get_active_spawns(self) -> list[str]:
        """Get list of active spawn session IDs."""
        return list(self._active_spawns.keys())

    async def cancel_spawn(self, session_id: str) -> bool:
        """Cancel an active spawn.

        Returns:
            True if cancelled, False if not found
        """
        session = self._active_spawns.get(session_id)
        if not session:
            return False

        try:
            if hasattr(session, "cancel"):
                await session.cancel()
            return True
        except Exception as e:
            logger.warning(f"Error cancelling spawn {session_id}: {e}")
            return False


def register_spawn_capability(
    session: Any,
    prepared_bundle: Any,  # PreparedBundle from amplifier_foundation
    spawn_manager: ServerSpawnManager | None = None,
) -> ServerSpawnManager:
    """Register session spawning capability on a session.

    Args:
        session: The AmplifierSession to register on
        prepared_bundle: The PreparedBundle for creating sessions
        spawn_manager: Optional existing spawn manager to use

    Returns:
        The spawn manager instance
    """
    if spawn_manager is None:
        spawn_manager = ServerSpawnManager()

    async def spawn_capability(
        agent_name: str,
        instruction: str,
        parent_session: Any,
        agent_configs: dict[str, dict],
        sub_session_id: str | None = None,
        tool_inheritance: dict[str, list[str]] | None = None,
        hook_inheritance: dict[str, list[str]] | None = None,
        orchestrator_config: dict | None = None,
        parent_messages: list[dict] | None = None,
        provider_override: str | None = None,
        model_override: str | None = None,
        parent_tool_call_id: str | None = None,
    ) -> dict:
        return await spawn_manager.spawn(
            agent_name=agent_name,
            instruction=instruction,
            parent_session=parent_session,
            agent_configs=agent_configs,
            prepared_bundle=prepared_bundle,
            parent_tool_call_id=parent_tool_call_id,
            sub_session_id=sub_session_id,
            tool_inheritance=tool_inheritance,
            hook_inheritance=hook_inheritance,
            orchestrator_config=orchestrator_config,
            parent_messages=parent_messages,
            provider_override=provider_override,
            model_override=model_override,
        )

    session.coordinator.register_capability("session.spawn", spawn_capability)
    logger.info("Registered session spawn capability (session.spawn)")

    return spawn_manager
