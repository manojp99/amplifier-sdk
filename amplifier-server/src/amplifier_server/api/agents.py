"""Agents API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from amplifier_server.core.session_manager import AgentState, SessionManager
from amplifier_server.models.requests import AgentConfig, OneOffRunRequest, RunRequest
from amplifier_server.models.responses import (
    AgentListResponse,
    AgentResponse,
    ClearResponse,
    DeleteResponse,
    MessagesResponse,
    RunResponse,
    ToolCall,
    Usage,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# Global session manager instance (injected via dependency)
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def set_session_manager(manager: SessionManager) -> None:
    """Set the session manager instance (for testing)."""
    global _session_manager
    _session_manager = manager


def _agent_to_response(agent: AgentState) -> AgentResponse:
    """Convert AgentState to AgentResponse."""
    return AgentResponse(
        agent_id=agent.agent_id,
        created_at=agent.created_at.isoformat(),
        status=agent.status.value,
        instructions=agent.instructions,
        provider=agent.provider,
        model=agent.model,
        tools=agent.tools,
        message_count=len(agent.messages),
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    config: AgentConfig,
    manager: SessionManager = Depends(get_session_manager),
) -> AgentResponse:
    """Create a new agent."""
    try:
        agent = await manager.create_agent(config.model_dump())
        return _agent_to_response(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=AgentListResponse)
async def list_agents(
    manager: SessionManager = Depends(get_session_manager),
) -> AgentListResponse:
    """List all agents."""
    agents = await manager.list_agents()
    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> AgentResponse:
    """Get an agent by ID."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return _agent_to_response(agent)


@router.delete("/{agent_id}", response_model=DeleteResponse)
async def delete_agent(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> DeleteResponse:
    """Delete an agent."""
    deleted = await manager.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return DeleteResponse(deleted=True)


@router.post("/{agent_id}/run", response_model=RunResponse)
async def run_agent(
    agent_id: str,
    request: RunRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> RunResponse:
    """Run a prompt on an agent (non-streaming)."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    result = await manager.run(agent_id, request.prompt, request.max_turns)

    # Check for error
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return RunResponse(
        content=result.get("content", ""),
        tool_calls=[ToolCall(**tc) for tc in result.get("tool_calls", [])],
        usage=Usage(**result.get("usage", {})),
        turn_count=result.get("turn_count", 1),
    )


@router.post("/{agent_id}/stream")
async def stream_agent(
    agent_id: str,
    request: RunRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> EventSourceResponse:
    """Stream execution of a prompt on an agent (SSE)."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    async def event_generator():
        async for event in manager.stream(agent_id, request.prompt, request.max_turns):
            yield {"event": event.event, "data": json.dumps(event.data)}

    return EventSourceResponse(event_generator())


@router.get("/{agent_id}/messages", response_model=MessagesResponse)
async def get_messages(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> MessagesResponse:
    """Get conversation messages for an agent."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    messages = await manager.get_messages(agent_id)
    return MessagesResponse(messages=messages)


@router.delete("/{agent_id}/messages", response_model=ClearResponse)
async def clear_messages(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> ClearResponse:
    """Clear conversation messages for an agent."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    await manager.clear_messages(agent_id)
    return ClearResponse(cleared=True)


# One-off execution endpoint (no persistent agent)
one_off_router = APIRouter(tags=["execution"])


@one_off_router.post("/run", response_model=RunResponse)
async def run_once(
    request: OneOffRunRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> RunResponse:
    """Run a prompt without a persistent agent (creates and destroys agent)."""
    # Create temporary agent
    config = AgentConfig(
        instructions=request.instructions,
        provider=request.provider,
        model=request.model,
        tools=request.tools,
        orchestrator="basic",
        context_manager="simple",
    )

    agent = None
    try:
        agent = await manager.create_agent(config.model_dump())
        result = await manager.run(agent.agent_id, request.prompt, request.max_turns)

        return RunResponse(
            content=result.get("content", ""),
            tool_calls=[ToolCall(**tc) for tc in result.get("tool_calls", [])],
            usage=Usage(**result.get("usage", {})),
            turn_count=result.get("turn_count", 1),
        )
    finally:
        # Clean up temporary agent
        if agent is not None:
            await manager.delete_agent(agent.agent_id)
