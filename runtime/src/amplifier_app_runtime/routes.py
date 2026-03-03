"""HTTP route handlers for the Amplifier runtime.

Replaces both ``routes/protocol_adapter.py`` and ``protocol/handler.py``.
Route handlers call ``session_manager`` directly — no Command/Event
abstraction layer.

Every handler is a plain async function that receives a Starlette
``Request`` and returns a ``Response``.  The ``routes`` list at the
bottom is mounted by ``app.py`` under the ``/v1/`` prefix.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .events import Bus
from .sessions import SessionConfig, TransportEvent, session_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Event Mapping — session TransportEvents → protocol SSE frames
# =============================================================================

# The protocol event model used by the SDK.  We inline a tiny dict-based
# representation so routes.py has zero coupling to the old protocol/ layer.


def _map_session_event(
    event: TransportEvent,
    correlation_id: str,
    sequence: int,
) -> dict[str, Any] | None:
    """Map a TransportEvent from ManagedSession.execute() into a protocol
    event dict suitable for SSE serialisation.

    Returns ``None`` for events that should be silently skipped.
    """
    etype = event.type
    props = event.properties

    match etype:
        case "content_block:start":
            return _proto(
                "content.start",
                {
                    "block_type": props.get("block_type", "text"),
                    "block_index": props.get("index", 0),
                },
                correlation_id,
                sequence,
            )

        case "content_block:delta":
            delta = props.get("delta", {})
            delta_text = delta.get("text", "") if isinstance(delta, dict) else str(delta)
            return _proto(
                "content.delta",
                {"delta": delta_text, "block_index": props.get("index", 0)},
                correlation_id,
                sequence,
            )

        case "content_block:end":
            block = props.get("block", {})
            content = block.get("text", "") if isinstance(block, dict) else str(block)
            return _proto(
                "content.end",
                {"content": content, "block_index": props.get("index", 0)},
                correlation_id,
                sequence,
            )

        case "tool:pre":
            return _proto(
                "tool.call",
                {
                    "tool_name": props.get("tool_name", "unknown"),
                    "tool_call_id": props.get("tool_call_id", ""),
                    "arguments": props.get("tool_input", {}),
                },
                correlation_id,
                sequence,
            )

        case "tool:post":
            result = props.get("result", {})
            output = result.get("output", "") if isinstance(result, dict) else str(result)
            return _proto(
                "tool.result",
                {
                    "tool_call_id": props.get("tool_call_id", ""),
                    "output": output,
                },
                correlation_id,
                sequence,
            )

        case "approval:required":
            return _proto(
                "approval.required",
                {
                    "request_id": props.get("request_id", ""),
                    "prompt": props.get("prompt", ""),
                    "options": props.get("options", ["yes", "no"]),
                    "timeout": props.get("timeout", 30.0),
                },
                correlation_id,
                sequence,
            )

        case "prompt:submit" | "prompt:complete":
            return None  # handled at higher level

        case "error":
            return _proto(
                "error",
                {
                    "error": props.get("error", "Unknown error"),
                    "code": props.get("error_type", "UNKNOWN"),
                },
                correlation_id,
                sequence,
                final=True,
            )

        case _:
            return _proto(
                etype.replace(":", "."),
                props,
                correlation_id,
                sequence,
            )


def _proto(
    event_type: str,
    data: dict[str, Any],
    correlation_id: str,
    sequence: int,
    *,
    final: bool = False,
) -> dict[str, Any]:
    """Build a protocol event dict."""
    return {
        "type": event_type,
        "data": data,
        "correlation_id": correlation_id,
        "sequence": sequence,
        "final": final,
    }


# =============================================================================
# SSE Helpers
# =============================================================================


async def _events_to_sse(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[bytes]:
    """Convert protocol event dicts to SSE ``data:`` frames (UTF-8)."""
    async for event in events:
        yield f"data: {json.dumps(event)}\n\n".encode()


# =============================================================================
# Route Handlers
# =============================================================================


async def health(request: Request) -> Response:
    """GET /health"""
    return JSONResponse({"status": "ok"})


async def create_session(request: Request) -> Response:
    """POST /session — create a new session.

    Body (JSON):
        bundle: str — bundle name (e.g. "foundation")
        bundle_definition: dict — optional runtime bundle
        config: dict — optional overrides (provider, model, working_directory, …)
        client_tools: list[dict] — optional client-side tool schemas
    """
    try:
        body = await _body(request)

        bundle_name = body.get("bundle")
        bundle_definition = body.get("bundle_definition")
        client_tools = body.get("client_tools") or body.get("clientTools")
        behaviors = body.get("behaviors") or []

        config = SessionConfig(
            bundle=bundle_name if not bundle_definition else None,
            provider=body.get("provider"),
            model=body.get("model"),
            working_directory=body.get("working_directory"),
            storage_directory=body.get("storage_directory"),
            behaviors=behaviors,
        )

        session = await session_manager.create_session(
            config=config,
            client_tools=client_tools,
            bundle_definition=bundle_definition,
        )

        return JSONResponse(
            {
                "session_id": session.session_id,
                "state": session.metadata.state.value,
                "bundle": session.metadata.bundle_name,
            }
        )
    except Exception as e:
        logger.exception("Failed to create session")
        return JSONResponse({"error": str(e), "code": "SESSION_CREATE_ERROR"}, status_code=500)


async def list_sessions(request: Request) -> Response:
    """GET /session — list sessions."""
    try:
        active = await session_manager.list_active()
        saved = session_manager.list_saved()
        return JSONResponse({"active": active, "saved": saved})
    except Exception as e:
        logger.exception("Failed to list sessions")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_session(request: Request) -> Response:
    """GET /session/{session_id}"""
    session_id = request.path_params["session_id"]
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse(session.to_dict())
    except Exception as e:
        logger.exception("Failed to get session")
        return JSONResponse({"error": str(e)}, status_code=500)


async def delete_session(request: Request) -> Response:
    """DELETE /session/{session_id}"""
    session_id = request.path_params["session_id"]
    try:
        deleted = await session_manager.delete_session(session_id)
        if not deleted:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse({"deleted": True, "session_id": session_id})
    except Exception as e:
        logger.exception("Failed to delete session")
        return JSONResponse({"error": str(e)}, status_code=500)


async def send_prompt(request: Request) -> Response:
    """POST /session/{session_id}/prompt — streaming SSE response."""
    session_id = request.path_params["session_id"]
    try:
        body = await _body(request)
        content = body.get("content", "")
        if not content:
            return JSONResponse(
                {"error": "Missing required field: content", "code": "BAD_REQUEST"},
                status_code=400,
            )

        session = await session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )

        correlation_id = f"prompt_{session_id}_{session.metadata.turn_count}"

        async def generate() -> AsyncIterator[dict[str, Any]]:
            seq = 0
            # ACK
            yield _proto("ack", {"message": "Processing prompt"}, correlation_id, seq)
            seq += 1
            try:
                async for event in session.execute(content):
                    mapped = _map_session_event(event, correlation_id, seq)
                    if mapped:
                        yield mapped
                        seq += 1

                # Final result
                yield _proto(
                    "result",
                    {
                        "session_id": session_id,
                        "state": session.metadata.state.value,
                        "turn": session.metadata.turn_count,
                    },
                    correlation_id,
                    seq,
                    final=True,
                )
            except Exception as exc:
                yield _proto(
                    "error",
                    {"error": str(exc), "code": "EXECUTION_ERROR"},
                    correlation_id,
                    seq,
                    final=True,
                )

        # Check Accept header for format preference
        accept = request.headers.get("accept", "text/event-stream")
        if "ndjson" in accept:
            return StreamingResponse(
                _events_to_ndjson(generate()),
                media_type="application/x-ndjson; charset=utf-8",
                headers={"X-Accel-Buffering": "no"},
            )

        return StreamingResponse(
            _events_to_sse(generate()),
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.exception("Failed to send prompt")
        return JSONResponse({"error": str(e), "code": "PROMPT_ERROR"}, status_code=500)


async def send_prompt_sync(request: Request) -> Response:
    """POST /session/{session_id}/prompt/sync — blocking response."""
    session_id = request.path_params["session_id"]
    try:
        body = await _body(request)
        content = body.get("content", "")
        if not content:
            return JSONResponse(
                {"error": "Missing required field: content", "code": "BAD_REQUEST"},
                status_code=400,
            )

        session = await session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )

        content_blocks: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        async for event in session.execute(content):
            if event.type == "content_block:end":
                block = event.properties.get("block", {})
                text = block.get("text", "") if isinstance(block, dict) else str(block)
                content_blocks.append(text)
            elif event.type == "tool:post":
                tool_calls.append(event.properties)
            elif event.type == "error":
                return JSONResponse(
                    {
                        "error": event.properties.get("error", "Unknown error"),
                        "code": event.properties.get("error_type", "UNKNOWN"),
                    },
                    status_code=500,
                )

        return JSONResponse(
            {
                "session_id": session_id,
                "state": session.metadata.state.value,
                "turn": session.metadata.turn_count,
                "content": "".join(content_blocks),
                "tool_calls": tool_calls,
            }
        )
    except Exception as e:
        logger.exception("Failed to send prompt (sync)")
        return JSONResponse({"error": str(e), "code": "PROMPT_ERROR"}, status_code=500)


async def cancel_prompt(request: Request) -> Response:
    """POST /session/{session_id}/cancel"""
    session_id = request.path_params["session_id"]
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )
        await session.cancel()
        return JSONResponse(
            {
                "cancelled": True,
                "session_id": session_id,
                "state": session.metadata.state.value,
            }
        )
    except Exception as e:
        logger.exception("Failed to cancel prompt")
        return JSONResponse({"error": str(e)}, status_code=500)


async def respond_approval(request: Request) -> Response:
    """POST /session/{session_id}/approval"""
    session_id = request.path_params["session_id"]
    try:
        body = await _body(request)
        request_id = body.get("request_id", "")
        choice = body.get("choice", "")

        if not request_id or not choice:
            return JSONResponse(
                {"error": "Missing request_id or choice", "code": "BAD_REQUEST"},
                status_code=400,
            )

        session = await session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session not found: {session_id}", "code": "SESSION_NOT_FOUND"},
                status_code=404,
            )

        handled = await session.handle_approval(request_id, choice)
        if not handled:
            return JSONResponse(
                {
                    "error": f"Approval request not found: {request_id}",
                    "code": "APPROVAL_NOT_FOUND",
                },
                status_code=404,
            )

        return JSONResponse(
            {
                "resolved": True,
                "request_id": request_id,
                "choice": choice,
            }
        )
    except Exception as e:
        logger.exception("Failed to respond to approval")
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_modules(request: Request) -> Response:
    """GET /modules — list installed amplifier modules."""
    try:
        from .bundles import BundleManager

        manager = BundleManager()
        bundles = await manager.list_bundles()
        return JSONResponse(
            {
                "bundles": [
                    {"name": b.name, "description": b.description, "uri": b.uri} for b in bundles
                ],
            }
        )
    except Exception as e:
        logger.exception("Failed to list modules")
        return JSONResponse({"error": str(e)}, status_code=500)


async def global_event_stream(request: Request) -> Response:
    """GET /event — global SSE event stream via Bus."""

    async def generate() -> AsyncIterator[bytes]:
        async for event in Bus.stream():
            yield f"data: {json.dumps(event)}\n\n".encode()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Helpers
# =============================================================================


async def _body(request: Request) -> dict[str, Any]:
    """Parse JSON body, returning empty dict if absent."""
    raw = await request.body()
    if not raw:
        return {}
    return await request.json()  # type: ignore[no-any-return]


async def _events_to_ndjson(
    events: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[bytes]:
    """Convert protocol event dicts to newline-delimited JSON (UTF-8)."""
    async for event in events:
        yield (json.dumps(event) + "\n").encode("utf-8")


# =============================================================================
# Route table — mounted under /v1/ by app.py
# =============================================================================

routes: list[Route] = [
    # Health
    Route("/health", health, methods=["GET"]),
    # Session CRUD
    Route("/session", list_sessions, methods=["GET"]),
    Route("/session", create_session, methods=["POST"]),
    Route("/session/{session_id}", get_session, methods=["GET"]),
    Route("/session/{session_id}", delete_session, methods=["DELETE"]),
    # Execution
    Route("/session/{session_id}/prompt", send_prompt, methods=["POST"]),
    Route("/session/{session_id}/prompt/sync", send_prompt_sync, methods=["POST"]),
    Route("/session/{session_id}/cancel", cancel_prompt, methods=["POST"]),
    # Approval
    Route("/session/{session_id}/approval", respond_approval, methods=["POST"]),
    # Modules
    Route("/modules", list_modules, methods=["GET"]),
    # Global event stream
    Route("/event", global_event_stream, methods=["GET"]),
]
