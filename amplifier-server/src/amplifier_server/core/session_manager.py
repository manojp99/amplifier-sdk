"""Session manager for handling Amplifier sessions."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config import get_config
from ..models import RunResponse, ToolCall, Usage

logger = logging.getLogger(__name__)

# Check if foundation is available
try:
    from amplifier_foundation import Bundle, load_bundle

    FOUNDATION_AVAILABLE = True
except ImportError:
    FOUNDATION_AVAILABLE = False
    Bundle = None
    load_bundle = None


@dataclass
class AgentState:
    """State for a managed agent."""

    agent_id: str
    created_at: datetime
    instructions: str
    tools: list[str]
    provider: str
    model: str | None
    session: Any = None  # AmplifierSession
    prepared: Any = None  # PreparedBundle for session management
    message_count: int = 0
    working_dir: Path | None = None


@dataclass
class SessionManager:
    """Manages Amplifier sessions for the API.

    This class handles:
    - Creating and destroying agent sessions
    - Executing prompts on sessions
    - Streaming execution events
    - Session lifecycle management
    """

    _agents: dict[str, AgentState] = field(default_factory=dict)
    _prepared_bundles: dict[str, Any] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def create_agent(
        self,
        instructions: str,
        tools: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
        bundle_path: str | None = None,
        working_dir: str | None = None,
    ) -> str:
        """Create a new agent session.

        Args:
            instructions: System prompt for the agent
            tools: List of tool names to enable
            provider: LLM provider name
            model: Model name
            bundle_path: Optional path to bundle file
            working_dir: Working directory for the session

        Returns:
            Agent ID

        Raises:
            RuntimeError: If session limit reached or creation fails
        """
        config = get_config()

        async with self._lock:
            if len(self._agents) >= config.max_sessions:
                raise RuntimeError(f"Maximum session limit reached ({config.max_sessions})")

        agent_id = str(uuid4())
        provider = provider or config.default_provider
        model = model or config.default_model
        work_path = Path(working_dir) if working_dir else Path.cwd()

        # Create session using foundation
        session, prepared = await self._create_foundation_session(
            instructions=instructions,
            tools=tools or [],
            provider=provider,
            model=model,
            bundle_path=bundle_path,
            working_dir=work_path,
        )

        state = AgentState(
            agent_id=agent_id,
            created_at=datetime.utcnow(),
            instructions=instructions,
            tools=tools or [],
            provider=provider,
            model=model,
            session=session,
            prepared=prepared,
            working_dir=work_path,
        )

        async with self._lock:
            self._agents[agent_id] = state

        logger.info(f"Created agent {agent_id} with provider={provider}, model={model}")
        return agent_id

    async def _create_foundation_session(
        self,
        instructions: str,
        tools: list[str],
        provider: str,
        model: str | None,
        bundle_path: str | None,
        working_dir: Path,
    ) -> tuple[Any, Any]:
        """Create a foundation session.

        Returns:
            Tuple of (session, prepared_bundle)
        """
        if not FOUNDATION_AVAILABLE or load_bundle is None:
            logger.warning("amplifier-foundation not available, using mock mode")
            return None, None

        try:
            if bundle_path:
                # Load existing bundle
                bundle = await load_bundle(bundle_path)
                logger.info(f"Loaded bundle from {bundle_path}")
            else:
                # Create inline bundle config
                bundle = self._create_inline_bundle(
                    instructions=instructions,
                    tools=tools,
                    provider=provider,
                    model=model,
                )
                logger.info("Created inline bundle")

            # Prepare the bundle (downloads modules)
            prepared = await bundle.prepare()

            # Create session
            session = await prepared.create_session(session_cwd=working_dir)

            return session, prepared

        except Exception as e:
            logger.error(f"Failed to create foundation session: {e}")
            raise RuntimeError(f"Failed to create session: {e}") from e

    def _create_inline_bundle(
        self,
        instructions: str,
        tools: list[str],
        provider: str,
        model: str | None,
    ) -> Any:
        """Create an inline bundle from configuration."""
        if not FOUNDATION_AVAILABLE or Bundle is None:
            return None

        # Map tool names to module sources
        tool_configs = []
        for tool in tools:
            # Normalize tool name (e.g., "filesystem" -> "tool-filesystem")
            module_name = tool if tool.startswith("tool-") else f"tool-{tool}"
            tool_configs.append(
                {
                    "module": module_name,
                    "source": f"git+https://github.com/microsoft/amplifier-module-{module_name}@main",
                }
            )

        # Create provider config
        provider_module = provider if provider.startswith("provider-") else f"provider-{provider}"
        provider_config = {
            "module": provider_module,
            "source": f"git+https://github.com/microsoft/amplifier-module-{provider_module}@main",
            "config": {},
        }
        if model:
            provider_config["config"]["default_model"] = model

        # Build the bundle
        bundle = Bundle(
            name="api-agent",
            version="1.0.0",
            session={
                "orchestrator": {
                    "module": "loop-basic",
                    "source": "git+https://github.com/microsoft/amplifier-module-loop-basic@main",
                },
                "context": {
                    "module": "context-simple",
                    "source": "git+https://github.com/microsoft/amplifier-module-context-simple@main",
                },
            },
            providers=[provider_config],
            tools=tool_configs,
            instruction=instructions,
        )

        return bundle

    async def run(self, agent_id: str, prompt: str, max_turns: int = 10) -> RunResponse:
        """Execute a prompt on an agent.

        Args:
            agent_id: Agent identifier
            prompt: User prompt
            max_turns: Maximum turns for agentic loop

        Returns:
            RunResponse with content and tool calls

        Raises:
            KeyError: If agent not found
        """
        state = self._get_agent(agent_id)

        if state.session is None:
            # Mock mode - return placeholder response
            logger.info(f"Mock mode: executing prompt for agent {agent_id}")
            return RunResponse(
                content=f"[Mock] Received prompt: {prompt}",
                tool_calls=[],
                usage=Usage(input_tokens=10, output_tokens=20, total_tokens=30),
            )

        # Execute on foundation session
        logger.info(f"Executing prompt for agent {agent_id}")
        result = await state.session.execute(prompt)
        state.message_count += 1

        return self._to_run_response(result)

    async def stream(
        self,
        agent_id: str,
        prompt: str,
        max_turns: int = 10,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream execution events for a prompt.

        Uses hooks to capture streaming events from the foundation session.

        Args:
            agent_id: Agent identifier
            prompt: User prompt
            max_turns: Maximum turns

        Yields:
            SSE event dictionaries
        """
        state = self._get_agent(agent_id)

        if state.session is None:
            # Mock mode - yield placeholder events
            yield {"event": "message_start", "data": {"id": str(uuid4())}}
            yield {"event": "content_delta", "data": {"text": f"[Mock] {prompt}"}}
            yield {
                "event": "message_end",
                "data": {"usage": {"input_tokens": 10, "output_tokens": 20}},
            }
            return

        # Create event queue for streaming
        event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        # Register hooks to capture events
        async def on_content_delta(event: str, data: dict) -> Any:
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                await event_queue.put(
                    {"event": "content_delta", "data": {"text": delta.get("text", "")}}
                )
            # Import here to avoid circular imports
            from amplifier_core.models import HookResult

            return HookResult(action="continue")

        async def on_tool_pre(event: str, data: dict) -> Any:
            await event_queue.put(
                {
                    "event": "tool_use",
                    "data": {
                        "tool": data.get("tool_name"),
                        "input": data.get("tool_input"),
                    },
                }
            )
            from amplifier_core.models import HookResult

            return HookResult(action="continue")

        async def on_tool_post(event: str, data: dict) -> Any:
            await event_queue.put(
                {
                    "event": "tool_result",
                    "data": {
                        "tool": data.get("tool_name"),
                        "result": str(data.get("tool_result", ""))[:1000],
                    },
                }
            )
            from amplifier_core.models import HookResult

            return HookResult(action="continue")

        # Register hooks
        coordinator = state.session.coordinator
        coordinator.hooks.register("content_block:delta", on_content_delta, priority=100)
        coordinator.hooks.register("tool:pre", on_tool_pre, priority=100)
        coordinator.hooks.register("tool:post", on_tool_post, priority=100)

        # Start execution in background
        async def run_execution():
            try:
                await state.session.execute(prompt)
                state.message_count += 1
            finally:
                await event_queue.put(None)  # Signal completion

        task = asyncio.create_task(run_execution())

        # Yield message start
        yield {"event": "message_start", "data": {"id": str(uuid4())}}

        # Stream events from queue
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            # Cleanup
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Yield message end
        yield {
            "event": "message_end",
            "data": {"session_id": state.agent_id},
        }

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and cleanup resources.

        Args:
            agent_id: Agent identifier

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            state = self._agents.pop(agent_id, None)

        if state is None:
            return False

        # Cleanup session
        if state.session is not None:
            with contextlib.suppress(Exception):
                # Session cleanup if available
                if hasattr(state.session, "__aexit__"):
                    await state.session.__aexit__(None, None, None)

        logger.info(f"Deleted agent {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Get agent state by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentState or None if not found
        """
        return self._agents.get(agent_id)

    def _get_agent(self, agent_id: str) -> AgentState:
        """Get agent state, raising if not found."""
        state = self._agents.get(agent_id)
        if state is None:
            raise KeyError(f"Agent not found: {agent_id}")
        return state

    def list_agents(self) -> list[str]:
        """List all active agent IDs."""
        return list(self._agents.keys())

    @property
    def active_count(self) -> int:
        """Number of active agents."""
        return len(self._agents)

    def _to_run_response(self, result: Any) -> RunResponse:
        """Convert foundation result to RunResponse."""
        # Handle string result (most common)
        if isinstance(result, str):
            return RunResponse(content=result, tool_calls=[], usage=Usage())

        # Extract content, tool calls, and usage from foundation result
        content = getattr(result, "content", str(result))
        tool_calls = []
        usage = Usage()

        if hasattr(result, "tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.name,
                    input=tc.input,
                    output=getattr(tc, "output", None),
                )
                for tc in result.tool_calls
            ]

        if hasattr(result, "usage"):
            usage = Usage(
                input_tokens=getattr(result.usage, "input_tokens", 0),
                output_tokens=getattr(result.usage, "output_tokens", 0),
                total_tokens=getattr(result.usage, "total_tokens", 0),
            )

        return RunResponse(content=content, tool_calls=tool_calls, usage=usage)


# Global session manager instance
_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
