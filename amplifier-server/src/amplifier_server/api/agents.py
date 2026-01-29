"""Agents API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from amplifier_server.core.session_manager import AgentState, SessionManager
from amplifier_server.models.requests import (
    AgentConfig,
    ApprovalResponse,
    OneOffRunRequest,
    RunRequest,
    SpawnAgentRequest,
)
from amplifier_server.models.responses import (
    AgentListResponse,
    AgentResponse,
    ApprovalListResponse,
    ClearResponse,
    DeleteResponse,
    MessagesResponse,
    RunResponse,
    SpawnResponse,
    SubAgentListResponse,
    ToolCall,
    Usage,
)
from amplifier_server.models.responses import (
    ApprovalRequest as ApprovalRequestResponse,
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
        orchestrator=agent.orchestrator,
        context_manager=agent.context_manager,
        hooks=agent.hooks,
        agents=agent.available_agents,
        message_count=len(agent.messages),
        has_approval_config=agent.has_approval_config,
    )


# =============================================================================
# Agent CRUD Endpoints
# =============================================================================


@router.post("", response_model=AgentResponse)
async def create_agent(
    config: AgentConfig,
    manager: SessionManager = Depends(get_session_manager),
) -> AgentResponse:
    """Create a new agent with full module wiring support."""
    try:
        agent = await manager.create_agent(config.model_dump(exclude_none=True))
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


# =============================================================================
# Execution Endpoints
# =============================================================================


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
        sub_agents_spawned=result.get("sub_agents_spawned", []),
    )


@router.post("/{agent_id}/stream")
async def stream_agent(
    agent_id: str,
    request: RunRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> EventSourceResponse:
    """Stream execution with rich event taxonomy (SSE)."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    async def event_generator():
        async for event in manager.stream(
            agent_id,
            request.prompt,
            request.max_turns,
            event_filter=request.stream_events,
        ):
            yield {"event": event.event, "data": json.dumps(event.data)}

    return EventSourceResponse(event_generator())


# =============================================================================
# Multi-Agent Endpoints
# =============================================================================


@router.post("/{agent_id}/spawn", response_model=SpawnResponse)
async def spawn_sub_agent(
    agent_id: str,
    request: SpawnAgentRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> SpawnResponse:
    """Spawn a sub-agent from a parent agent."""
    parent = await manager.get_agent(agent_id)
    if parent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # Check if agent_name exists in parent's agents config
    if request.agent_name not in parent.available_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Sub-agent '{request.agent_name}' not defined in parent's agents config. "
            f"Available: {parent.available_agents}",
        )

    sub_agent = await manager.spawn_agent(
        parent_id=agent_id,
        agent_name=request.agent_name,
        inherit_context=request.inherit_context,
        inherit_context_turns=request.inherit_context_turns,
    )

    if sub_agent is None:
        raise HTTPException(status_code=500, detail="Failed to spawn sub-agent")

    # Run initial prompt if provided
    if request.prompt:
        await manager.run(sub_agent.agent_id, request.prompt)

    return SpawnResponse(
        agent_id=sub_agent.agent_id,
        parent_id=agent_id,
        agent_name=request.agent_name,
        status=sub_agent.status.value,
    )


@router.get("/{agent_id}/sub-agents", response_model=SubAgentListResponse)
async def list_sub_agents(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> SubAgentListResponse:
    """List sub-agents spawned by a parent agent."""
    parent = await manager.get_agent(agent_id)
    if parent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    sub_agents = await manager.list_sub_agents(agent_id)
    return SubAgentListResponse(
        sub_agents=[
            {
                "agent_id": sa.agent_id,
                "parent_id": sa.parent_id,
                "agent_name": sa.agent_name,
                "created_at": sa.created_at.isoformat(),
            }
            for sa in sub_agents
        ],
        count=len(sub_agents),
    )


# =============================================================================
# Approval Endpoints
# =============================================================================


@router.get("/{agent_id}/approvals", response_model=ApprovalListResponse)
async def list_pending_approvals(
    agent_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> ApprovalListResponse:
    """List pending approval requests for an agent."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    approvals = await manager.list_pending_approvals(agent_id)
    return ApprovalListResponse(
        approvals=[
            ApprovalRequestResponse(
                approval_id=a.approval_id,
                agent_id=a.agent_id,
                tool=a.tool,
                action=a.action,
                args=a.args,
                created_at=a.created_at.isoformat(),
                timeout_at=a.timeout_at.isoformat(),
            )
            for a in approvals
        ],
        count=len(approvals),
    )


@router.post("/{agent_id}/approvals/{approval_id}")
async def respond_to_approval(
    agent_id: str,
    approval_id: str,
    response: ApprovalResponse,
    manager: SessionManager = Depends(get_session_manager),
) -> dict:
    """Respond to an approval request (approve or deny)."""
    agent = await manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    result = await manager.respond_to_approval(
        agent_id=agent_id,
        approval_id=approval_id,
        approved=response.approved,
        reason=response.reason,
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {approval_id}")

    return {
        "approval_id": result.approval_id,
        "approved": result.approved,
        "reason": result.reason,
    }


# =============================================================================
# Message Endpoints
# =============================================================================


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


# =============================================================================
# One-off Execution (Separate Router)
# =============================================================================

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
        providers=None,
        model=request.model,
        tools=request.tools,
        orchestrator="basic",
        context_manager="simple",
        approval=None,
    )

    agent = None
    try:
        agent = await manager.create_agent(config.model_dump(exclude_none=True))
        result = await manager.run(agent.agent_id, request.prompt, request.max_turns)

        return RunResponse(
            content=result.get("content", ""),
            tool_calls=[ToolCall(**tc) for tc in result.get("tool_calls", [])],
            usage=Usage(**result.get("usage", {})),
            turn_count=result.get("turn_count", 1),
            sub_agents_spawned=result.get("sub_agents_spawned", []),
        )
    finally:
        # Clean up temporary agent
        if agent is not None:
            await manager.delete_agent(agent.agent_id)
