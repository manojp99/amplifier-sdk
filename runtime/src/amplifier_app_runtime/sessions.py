"""Session management for Amplifier HTTP server.

Consolidates session lifecycle, execution, and management:
- ManagedSession: wraps amplifier-core AmplifierSession with streaming,
  approval, display, and spawn wiring.
- SessionManager: singleton that manages all active/saved sessions.

All amplifier-core integration (PreparedBundle, create_session, coordinator
setup, hook wiring) is preserved from the original session.py.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Event types that the backend stats route parses from events.jsonl
_PERSISTED_EVENT_TYPES = frozenset(
    {
        "session:start",
        "execution:start",
        "execution:end",
        "llm:request",
        "llm:response",
        "content_block:start",
        "content_block:end",
    }
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class SessionState(str, Enum):
    """Session lifecycle states."""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class SessionMetadata:
    """Metadata for a session."""

    session_id: str
    state: SessionState = SessionState.CREATED
    bundle_name: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    turn_count: int = 0
    cwd: str = field(default_factory=lambda: str(Path.cwd()))
    parent_session_id: str | None = None
    error: str | None = None


@dataclass
class SessionConfig:
    """Configuration for session creation."""

    bundle: str | None = None
    provider: str | None = None
    model: str | None = None
    max_turns: int = 100
    timeout: float = 300.0
    working_directory: str | None = None
    storage_directory: str | None = None
    behaviors: list[str] = field(default_factory=list)
    show_thinking: bool = True
    environment: dict[str, str] = field(default_factory=dict)
    approval_system: Any | None = None


# =============================================================================
# Transport Event — lightweight carrier used by streaming hook / approval / display
# =============================================================================


class TransportEvent:
    """Lightweight event object yielded by ManagedSession.execute().

    This replaces the old ``transport.base.Event`` Pydantic model with a
    plain object so the session layer has zero dependency on transport
    infrastructure.  The routes layer maps these into protocol Events or
    SSE frames as needed.
    """

    __slots__ = ("type", "properties", "sequence")

    def __init__(
        self,
        type: str,
        properties: dict[str, Any] | None = None,
        sequence: int | None = None,
    ) -> None:
        self.type = type
        self.properties = properties or {}
        self.sequence = sequence


# =============================================================================
# ManagedSession
# =============================================================================


class ManagedSession:
    """A managed Amplifier session with streaming integration.

    Wraps an AmplifierSession with:
    - Event streaming via ServerStreamingHook
    - Approval handling via ServerApprovalSystem
    - Display notifications via ServerDisplaySystem
    - Agent spawning via ServerSpawnManager
    - State management and persistence
    - Transcript persistence
    """

    def __init__(
        self,
        session_id: str,
        config: SessionConfig,
        store: Any | None = None,
    ) -> None:
        self.session_id = session_id
        self.config = config
        self.metadata = SessionMetadata(
            session_id=session_id,
            bundle_name=config.bundle,
            cwd=config.working_directory or str(Path.cwd()),
        )

        # Protocol handlers (created during initialization)
        self._approval: Any = None
        self._display: Any = None
        self._streaming_hook: Any = None
        self._spawn_manager: Any = None

        # Persistence
        self._store = store

        # Conversation history (for persistence)
        self._messages: list[dict[str, Any]] = []

        # Internal state
        self._amplifier_session: Any = None  # AmplifierSession when loaded
        self._prepared_bundle: Any = None  # PreparedBundle when loaded
        self._lock = asyncio.Lock()
        self._cancel_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.session_id

    @property
    def created_at(self) -> datetime:
        return self.metadata.created_at

    @property
    def status(self) -> str:
        return self.metadata.state.value

    @property
    def transcript(self) -> list[dict[str, Any]]:
        return list(self._messages)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(
        self,
        prepared_bundle: Any = None,
        initial_transcript: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the Amplifier session.

        Args:
            prepared_bundle: Optional pre-prepared bundle to use
            initial_transcript: Optional transcript to restore (for resume)
        """
        from .streaming import (
            ServerApprovalSystem,
            ServerDisplaySystem,
            ServerSpawnManager,
            ServerStreamingHook,
        )

        async with self._lock:
            if self.metadata.state != SessionState.CREATED:
                raise RuntimeError(f"Cannot initialize session in state {self.metadata.state}")

            try:
                # Create protocol handlers — no send_fn needed; the
                # streaming hook queues events for execute() to yield.
                if self.config.approval_system is not None:
                    self._approval = self.config.approval_system
                else:
                    self._approval = ServerApprovalSystem(send_fn=None)
                self._display = ServerDisplaySystem(send_fn=None)
                self._streaming_hook = ServerStreamingHook(
                    send_fn=None,
                    show_thinking=self.config.show_thinking,
                )
                self._spawn_manager = ServerSpawnManager()

                # Create real AmplifierSession
                if prepared_bundle:
                    self._prepared_bundle = prepared_bundle
                    await self._create_amplifier_session(
                        prepared_bundle,
                        initial_transcript,
                    )
                elif self.config.bundle:
                    try:
                        from .bundles import BundleManager

                        manager = BundleManager()
                        prepared = await manager.load_and_prepare(
                            bundle_name=self.config.bundle,
                            behaviors=self.config.behaviors,
                            working_directory=(
                                Path(self.metadata.cwd) if self.metadata.cwd else None
                            ),
                        )
                        self._prepared_bundle = prepared
                        await self._create_amplifier_session(prepared, initial_transcript)
                    except Exception as e:
                        logger.error(
                            f"Session {self.session_id} failed to load bundle "
                            f"'{self.config.bundle}': {e}"
                        )
                        raise RuntimeError(
                            f"Failed to load bundle '{self.config.bundle}'. "
                            f"Ensure the bundle exists and providers are configured "
                            f"(ANTHROPIC_API_KEY or OPENAI_API_KEY). Error: {e}"
                        ) from e
                else:
                    raise RuntimeError(
                        f"Session {self.session_id} requires a bundle to be specified. "
                        "Pass a bundle name in SessionConfig or a prepared_bundle."
                    )

                # Restore transcript if provided and not already restored
                if initial_transcript and not self._messages:
                    self._messages = list(initial_transcript)
                    self.metadata.turn_count = sum(
                        1 for m in initial_transcript if m.get("role") == "user"
                    )
                    logger.info(
                        f"Restored {len(initial_transcript)} messages for session {self.session_id}"
                    )

                self.metadata.state = SessionState.READY
                self.metadata.updated_at = datetime.now(UTC)

                # Save initial metadata
                self._persist_metadata()

            except Exception as e:
                self.metadata.state = SessionState.ERROR
                self.metadata.error = str(e)
                logger.error(f"Failed to initialize session {self.session_id}: {e}")
                raise

    async def _create_amplifier_session(
        self,
        prepared_bundle: Any,
        initial_transcript: list[dict[str, Any]] | None = None,
    ) -> None:
        """Create AmplifierSession from prepared bundle."""
        from .bundles import AppModuleResolver, FallbackResolver
        from .streaming import register_spawn_capability, register_streaming_hook

        try:
            # Wrap bundle resolver with app-layer fallback
            fallback_resolver = FallbackResolver()
            prepared_bundle.resolver = AppModuleResolver(
                bundle_resolver=prepared_bundle.resolver,
                fallback_resolver=fallback_resolver,
            )

            # Create session via foundation's factory method
            session = await prepared_bundle.create_session(
                session_id=self.session_id,
                approval_system=self._approval,
                display_system=self._display,
                session_cwd=Path(self.metadata.cwd) if self.metadata.cwd else None,
                is_resumed=initial_transcript is not None,
            )

            # Register streaming hook for all events
            register_streaming_hook(session, self._streaming_hook)

            # Register spawn capability for agent delegation
            register_spawn_capability(session, prepared_bundle, self._spawn_manager)

            # Register host-defined tools
            await self._register_host_tools(session)

            # Restore transcript if provided
            if initial_transcript:
                await self._restore_transcript(session, initial_transcript)

            self._amplifier_session = session
            logger.info(f"Session {self.session_id} initialized with amplifier-core")

        except ImportError as e:
            logger.error(
                f"Session {self.session_id} failed: amplifier-core/foundation not available: {e}"
            )
            raise RuntimeError(
                f"Failed to create AmplifierSession: {e}. "
                "Ensure amplifier-core and amplifier-foundation are installed."
            ) from e

    async def _restore_transcript(
        self,
        session: Any,
        transcript: list[dict[str, Any]],
    ) -> None:
        """Restore conversation transcript into a session."""
        try:
            context = session.coordinator.get("context")
            if context and hasattr(context, "set_messages"):
                # Preserve fresh system message if present
                fresh_system_msg = None
                if hasattr(context, "get_messages"):
                    current_msgs = await context.get_messages()
                    system_msgs = [m for m in current_msgs if m.get("role") == "system"]
                    if system_msgs:
                        fresh_system_msg = system_msgs[0]

                filtered = [msg for msg in transcript if msg.get("role") in ("user", "assistant")]
                await context.set_messages(filtered)

                if fresh_system_msg:
                    restored_msgs = await context.get_messages()
                    has_system = any(m.get("role") == "system" for m in restored_msgs)
                    if not has_system:
                        await context.set_messages([fresh_system_msg] + restored_msgs)

                self._messages = list(transcript)
                logger.info(f"Restored {len(filtered)} messages via context.set_messages()")
            else:
                logger.warning("Context module not found or doesn't support set_messages()")
        except Exception as e:
            logger.error(f"Failed to restore transcript: {e}")

    async def _register_host_tools(self, session: Any) -> None:
        """Register host-defined tools on this session.

        Host tools are not used in the thin HTTP runtime.
        """
        logger.debug(f"Host tools not available in HTTP-only runtime for session {self.session_id}")

    async def _register_client_tools(
        self,
        client_tools: list[dict[str, Any]],
    ) -> list[str]:
        """Register client-side proxy tools on this session.

        Client tools have their schema sent from the SDK but execute
        client-side. The runtime creates proxy tools that the LLM can
        call; actual execution happens via tool.call / tool.result
        events over the wire.
        """
        if not client_tools or not self._amplifier_session:
            return []

        # Client tools (SDK-provided proxy tools) not yet supported in thin runtime
        logger.debug(
            "Client tool registration skipped in HTTP-only runtime (%d tools)",
            len(client_tools),
        )
        return []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, prompt: str) -> AsyncIterator[TransportEvent]:
        """Execute a prompt and stream results.

        Yields TransportEvent objects as they occur during execution.
        """
        async with self._lock:
            if self.metadata.state not in (SessionState.READY, SessionState.PAUSED):
                raise RuntimeError(f"Cannot execute in state {self.metadata.state}")

            self.metadata.state = SessionState.RUNNING
            self.metadata.turn_count += 1
            self.metadata.updated_at = datetime.now(UTC)
            self._cancel_event.clear()

        # Reset streaming hook sequence
        if self._streaming_hook:
            self._streaming_hook.reset_sequence()

        # Emit session:start on first turn, execution:start on every turn
        if self.metadata.turn_count == 1:
            self._persist_event("session:start")
        self._persist_event("execution:start", {"turn": self.metadata.turn_count})

        # Record user message
        self._messages.append(
            {
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Emit prompt submit event
        yield TransportEvent(
            type="prompt:submit",
            properties={
                "session_id": self.session_id,
                "prompt": prompt,
                "turn": self.metadata.turn_count,
            },
        )

        response_text = ""

        try:
            if not self._amplifier_session:
                raise RuntimeError(
                    f"Session {self.session_id} not properly initialized. "
                    "AmplifierSession is required for execution."
                )

            async for event in self._execute_with_amplifier(prompt):
                # Persist events for stats (llm:request, llm:response, etc.)
                self._persist_event(event.type, event.properties)

                # Capture response text from content blocks
                if event.type == "content_block:end":
                    block = event.properties.get("block", {})
                    if "text" in block:
                        response_text += block["text"]
                yield event

            # Record assistant message
            if response_text:
                self._messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

            # Update state on completion
            async with self._lock:
                self.metadata.state = SessionState.READY
                self.metadata.updated_at = datetime.now(UTC)

            # Emit execution:end for stats
            self._persist_event("execution:end", {"turn": self.metadata.turn_count})

            # Persist after each turn
            self._persist_transcript()
            self._persist_metadata()

            # Emit completion event
            yield TransportEvent(
                type="prompt:complete",
                properties={
                    "session_id": self.session_id,
                    "turn": self.metadata.turn_count,
                },
            )

        except asyncio.CancelledError:
            async with self._lock:
                self.metadata.state = SessionState.CANCELLED
            self._persist_metadata()
            yield TransportEvent(
                type="cancel:completed",
                properties={"session_id": self.session_id},
            )
            raise

        except Exception as e:
            async with self._lock:
                self.metadata.state = SessionState.ERROR
                self.metadata.error = str(e)
            self._persist_metadata()

            yield TransportEvent(
                type="error",
                properties={
                    "session_id": self.session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def _execute_with_amplifier(self, prompt: str) -> AsyncIterator[TransportEvent]:
        """Execute prompt using real Amplifier session.

        Uses the streaming hook's event queue to yield ALL events
        (thinking, tools, content, etc.) as they occur.
        """
        if not self._streaming_hook:
            logger.warning("No streaming hook configured, events will be limited")
            result = await self._amplifier_session.execute(prompt)
            if result:
                yield TransportEvent(
                    type="content_block:start",
                    properties={
                        "session_id": self.session_id,
                        "block_type": "text",
                        "index": 0,
                    },
                )
                yield TransportEvent(
                    type="content_block:end",
                    properties={
                        "session_id": self.session_id,
                        "index": 0,
                        "block": {"text": str(result)},
                    },
                )
            return

        # Start streaming mode — hook will queue events
        self._streaming_hook.start_streaming()

        async def run_execute():
            try:
                return await self._amplifier_session.execute(prompt)
            finally:
                self._streaming_hook.stop_streaming()

        exec_task = asyncio.create_task(run_execute())

        try:
            # Yield events as they arrive from the hook
            async for event in self._streaming_hook.get_events():
                # Re-wrap as TransportEvent (hook yields transport.base.Event)
                yield TransportEvent(
                    type=event.type,
                    properties=event.properties,
                    sequence=event.sequence,
                )

            # Wait for execution to complete
            result = await exec_task
            if result:
                logger.debug(f"Execution completed with result: {str(result)[:100]}...")

        except asyncio.CancelledError:
            exec_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await exec_task
            raise
        except Exception as e:
            logger.error(f"Execution error in session {self.session_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}, full traceback:", exc_info=True)
            exec_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await exec_task
            raise

    # ------------------------------------------------------------------
    # Cancel / Approval
    # ------------------------------------------------------------------

    async def cancel(self) -> None:
        """Cancel the current execution."""
        self._cancel_event.set()

        if self._approval:
            self._approval.cancel_all()

        if self._amplifier_session and hasattr(self._amplifier_session, "cancel"):
            await self._amplifier_session.cancel()

        async with self._lock:
            if self.metadata.state == SessionState.RUNNING:
                self.metadata.state = SessionState.CANCELLED

        self._persist_metadata()

    async def handle_approval(self, request_id: str, choice: str) -> bool:
        """Handle an approval response from the client."""
        if not self._approval:
            return False
        return self._approval.handle_response(request_id, choice)

    # ------------------------------------------------------------------
    # Serialization & Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize session metadata."""
        return {
            "session_id": self.session_id,
            "state": self.metadata.state.value,
            "bundle": self.metadata.bundle_name,
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
            "turn_count": self.metadata.turn_count,
            "cwd": self.metadata.cwd,
            "parent_session_id": self.metadata.parent_session_id,
            "error": self.metadata.error,
        }

    def _persist_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Persist a single event to events.jsonl in the format the stats route expects.

        Format: {"event": "<type>", "data": {...}, "ts": "<iso>", "session_id": "<id>"}
        """
        if not self._store or event_type not in _PERSISTED_EVENT_TYPES:
            return
        try:
            self._store.append_event(
                self.session_id,
                {
                    "event": event_type,
                    "data": data or {},
                    "ts": datetime.now(UTC).isoformat(),
                    "session_id": self.session_id,
                },
            )
        except Exception:
            logger.debug("Failed to persist event %s", event_type, exc_info=True)

    def _persist_metadata(self) -> None:
        """Persist session metadata to storage."""
        if not self._store:
            return
        self._store.save_metadata(
            session_id=self.session_id,
            bundle_name=self.metadata.bundle_name,
            turn_count=self.metadata.turn_count,
            created_at=self.metadata.created_at,
            updated_at=self.metadata.updated_at,
            cwd=self.metadata.cwd,
            parent_session_id=self.metadata.parent_session_id,
            state=self.metadata.state.value,
            error=self.metadata.error,
        )

    def _persist_transcript(self) -> None:
        """Persist conversation transcript to storage."""
        if not self._store or not self._messages:
            return
        self._store.save_transcript(self.session_id, self._messages)

    def get_transcript(self) -> list[dict[str, Any]]:
        """Get the conversation transcript."""
        return list(self._messages)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Clean up session resources."""
        if self._amplifier_session:
            try:
                if hasattr(self._amplifier_session, "__aexit__"):
                    await self._amplifier_session.__aexit__(None, None, None)
                elif hasattr(self._amplifier_session, "cleanup"):
                    await self._amplifier_session.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up session {self.session_id}: {e}")


# =============================================================================
# SessionManager
# =============================================================================


class SessionManager:
    """Manager for all active and saved sessions.

    Provides:
    - Session creation and lookup
    - Session lifecycle management
    - Concurrent session support
    - Session persistence via SessionStore
    - Bundle management via BundleManager
    """

    def __init__(
        self,
        store: Any | None = None,
    ) -> None:
        import os

        no_persist = os.environ.get("AMPLIFIER_NO_PERSIST") == "1"
        storage_dir = os.environ.get("AMPLIFIER_STORAGE_DIR")

        if store:
            self._store = store
        elif no_persist:
            self._store = None
        elif storage_dir:
            from .store import SessionStore

            self._store = SessionStore(storage_dir=Path(storage_dir))
        else:
            from .store import SessionStore

            self._store = SessionStore()

        self._active: dict[str, ManagedSession] = {}
        self._bundle_manager: Any = None
        self._lock = asyncio.Lock()

    async def _get_bundle_manager(self) -> Any:
        """Get or create the bundle manager."""
        if self._bundle_manager is None:
            from .bundles import BundleManager

            self._bundle_manager = BundleManager()
            await self._bundle_manager.initialize()
        return self._bundle_manager

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self,
        config: SessionConfig | None = None,
        session_id: str | None = None,
        client_tools: list[dict[str, Any]] | None = None,
        prepared_bundle: Any = None,
        bundle_definition: dict[str, Any] | None = None,
    ) -> ManagedSession:
        """Create a new session.

        Args:
            config: Session configuration
            session_id: Optional session ID (generated if not provided)
            client_tools: Optional client-side tool definitions from SDK
            prepared_bundle: Optional pre-prepared bundle
            bundle_definition: Optional runtime bundle definition from SDK

        Returns:
            The created ManagedSession (already initialized)
        """
        config = config or SessionConfig()
        session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"

        # Handle runtime bundle definition from SDK
        if bundle_definition and not prepared_bundle:
            prepared_bundle = await self._prepare_runtime_bundle(bundle_definition)

        # Use a per-session store so sessions are written to a deterministic
        # location.  storage_directory (canonical) is preferred; fall back to
        # working_directory for backwards-compat.
        store = self._store
        storage_dir = config.storage_directory or config.working_directory
        if storage_dir and self._store is not None:
            from .store import SessionStore

            store = SessionStore(working_directory=storage_dir)

        session = ManagedSession(
            session_id=session_id,
            config=config,
            store=store,
        )

        async with self._lock:
            self._active[session_id] = session

        # Initialize with bundle
        await session.initialize(prepared_bundle=prepared_bundle)

        # Register client-side tools after initialization
        if client_tools:
            await session._register_client_tools(client_tools)

        logger.info(f"Created session {session_id} with bundle {config.bundle}")
        return session

    async def _prepare_runtime_bundle(self, bundle_definition: dict[str, Any]) -> Any:
        """Prepare a bundle from a runtime definition sent by the SDK."""
        from amplifier_foundation import Bundle, load_bundle

        from .bundles import BundleManager

        # Ensure session defaults
        session_config = bundle_definition.get("session", {})
        if "orchestrator" not in session_config:
            session_config["orchestrator"] = "loop-streaming"
        if "context" not in session_config:
            session_config["context"] = "context-simple"

        bundle = Bundle(
            name=bundle_definition.get("name", "runtime-bundle"),
            version=bundle_definition.get("version", "1.0.0"),
            description=bundle_definition.get("description", ""),
            providers=bundle_definition.get("providers", []),
            tools=bundle_definition.get("tools", []),
            hooks=bundle_definition.get("hooks", []),
            agents=bundle_definition.get("agents", {}),
            instruction=(
                bundle_definition.get("instructions") or bundle_definition.get("instruction")
            ),
            session=session_config,
        )

        # Process includes — each included bundle is loaded and composed as a base
        # so the inline bundle's values win. This mirrors BundleRegistry._compose_includes()
        # and is required to bring in hooks, context files, and any other capabilities
        # declared in the included bundle (e.g. behaviors/engram.yaml brings in both
        # hooks-protocol-reminder/hooks-memory-tracker AND the 8 Engram context files).
        # NOTE: bundle.prepare() does NOT process includes — it only activates Python
        # modules already present in the bundle, so we must resolve includes here.
        for include_entry in bundle_definition.get("includes", []):
            # Each include entry may be a plain string URI or a dict with a 'bundle' key
            # (the YAML format used by engramBundle.ts writes `- bundle: git+https://...`)
            if isinstance(include_entry, dict):
                include_uri = include_entry.get("bundle", "")
            else:
                include_uri = include_entry
            if not include_uri:
                continue
            try:
                included = await load_bundle(include_uri)
                bundle = included.compose(bundle)
            except Exception as e:
                logger.warning("Failed to load included bundle '%s': %s", include_uri, e)

        # Compose on top of base bundle if requested
        if "base" in bundle_definition:
            base = await load_bundle(bundle_definition["base"])
            bundle = base.compose(bundle)

        # Auto-detect provider if not specified
        if not bundle_definition.get("providers"):
            manager = BundleManager()
            await manager.initialize()
            provider_bundle = await manager._auto_detect_provider()
            if provider_bundle:
                bundle = bundle.compose(provider_bundle)

        return await bundle.prepare()

    async def get_session(self, session_id: str) -> ManagedSession | None:
        """Get an active session by ID."""
        return self._active.get(session_id)

    async def list_sessions(
        self,
        limit: int = 50,
        include_completed: bool = False,
    ) -> list[dict[str, Any]]:
        """List all sessions (active + saved)."""
        sessions = []

        for session in self._active.values():
            info = session.to_dict()
            info["is_active"] = True
            sessions.append(info)

        if self._store:
            saved = self._store.list_sessions(limit=limit)
            for saved_info in saved:
                sid = saved_info.get("session_id")
                if sid not in self._active:
                    saved_info["is_active"] = False
                    if include_completed or saved_info.get("state") != "completed":
                        sessions.append(saved_info)

        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions[:limit]

    async def list_active(self) -> list[dict[str, Any]]:
        """List all active sessions."""
        return [{**session.to_dict(), "active": True} for session in self._active.values()]

    def list_saved(self, min_turns: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """List saved sessions from storage."""
        if not self._store:
            return []
        return self._store.list_sessions(min_turns=min_turns, limit=limit)

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get info about a session (active or saved)."""
        if session_id in self._active:
            info = self._active[session_id].to_dict()
            info["active"] = True
            return info

        if self._store:
            saved = self._store.load_metadata(session_id)
            if saved:
                saved["active"] = False
                return saved

        return None

    async def delete_session(self, session_id: str, delete_saved: bool = True) -> bool:
        """Delete a session.

        Returns True if deleted, False if not found.
        """
        async with self._lock:
            session = self._active.pop(session_id, None)

        if session:
            await session.cleanup()

        deleted = False
        if delete_saved and self._store:
            deleted = self._store.delete_session(session_id)

        if deleted:
            logger.info(f"Deleted session {session_id}")

        return deleted or session is not None

    async def resume_session(
        self,
        session_id: str,
        force_bundle: str | None = None,
    ) -> ManagedSession | None:
        """Resume a saved session.

        Returns the resumed session, or None if not found.
        """
        # Already active?
        if session_id in self._active:
            return self._active[session_id]

        if not self._store:
            return None

        metadata = self._store.load_metadata(session_id)
        if not metadata:
            return None

        transcript = self._store.load_transcript(session_id)

        bundle_name = force_bundle or metadata.get("bundle_name")
        working_dir = metadata.get("cwd")
        config = SessionConfig(
            bundle=bundle_name,
            working_directory=working_dir,
        )

        # Use a store derived from the session's working directory so we
        # look in the same location where create_session() stored the data.
        store = self._store
        if working_dir and self._store is not None:
            from .store import SessionStore

            store = SessionStore(working_directory=working_dir)

        session = ManagedSession(
            session_id=session_id,
            config=config,
            store=store,
        )

        # Restore metadata
        session.metadata.turn_count = metadata.get("turn_count", 0)
        session.metadata.created_at = metadata.get("created_at", datetime.now(UTC))

        # Load and prepare bundle
        prepared_bundle = None
        if bundle_name:
            try:
                manager = await self._get_bundle_manager()
                prepared_bundle = await manager.load_and_prepare(
                    bundle_name=bundle_name,
                    working_directory=(
                        Path(config.working_directory) if config.working_directory else None
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to prepare bundle '{bundle_name}' for resume: {e}")
                if self._bundle_manager:
                    await self._bundle_manager.invalidate_cache()
                raise

        async with self._lock:
            self._active[session_id] = session

        await session.initialize(
            prepared_bundle=prepared_bundle,
            initial_transcript=transcript,
        )

        logger.info(f"Resumed session {session_id}")
        return session

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def active_count(self) -> int:
        """Count of active (ready/running) sessions."""
        return sum(
            1
            for s in self._active.values()
            if s.metadata.state in (SessionState.READY, SessionState.RUNNING)
        )

    @property
    def total_count(self) -> int:
        """Total count of sessions in memory."""
        return len(self._active)

    @property
    def store(self) -> Any | None:
        """Get the session store (None if persistence disabled)."""
        return self._store

    async def cleanup_completed(self, max_age_seconds: int = 86400) -> int:
        """Clean up old completed sessions from memory."""
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
        to_remove = []

        async with self._lock:
            for session_id, session in self._active.items():
                if (
                    session.metadata.state in (SessionState.COMPLETED, SessionState.ERROR)
                    and session.metadata.updated_at < cutoff
                ):
                    to_remove.append(session_id)

            for session_id in to_remove:
                session = self._active.pop(session_id)
                await session.cleanup()

        return len(to_remove)


# =============================================================================
# Global singleton
# =============================================================================

session_manager = SessionManager()
