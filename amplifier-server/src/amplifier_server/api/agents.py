"""Agent API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..core.auth import verify_api_key
from ..core.session_manager import get_session_manager
from ..models import (
    AgentResponse,
    CreateAgentRequest,
    RunPromptRequest,
    RunResponse,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> AgentResponse:
    """Create a new agent.

    Creates an agent with the specified configuration. The agent
    maintains conversation state until deleted.
    """
    manager = get_session_manager()

    try:
        agent_id = await manager.create_agent(
            instructions=request.instructions,
            tools=request.tools,
            provider=request.provider,
            model=request.model,
            bundle_path=request.bundle_path,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}") from e

    return AgentResponse(
        agent_id=agent_id,
        created_at=datetime.utcnow().isoformat() + "Z",
    )


@router.post("/{agent_id}/run", response_model=RunResponse)
async def run_prompt(
    agent_id: str,
    request: RunPromptRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> RunResponse:
    """Run a prompt on an agent.

    Executes the prompt and returns the complete response.
    For streaming responses, use the /stream endpoint.
    """
    manager = get_session_manager()

    try:
        response = await manager.run(
            agent_id=agent_id,
            prompt=request.prompt,
            max_turns=request.max_turns,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}") from e

    return response


@router.post("/{agent_id}/stream")
async def stream_prompt(
    agent_id: str,
    request: RunPromptRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> EventSourceResponse:
    """Stream execution events for a prompt.

    Returns a Server-Sent Events stream with execution events:
    - message_start: Start of response
    - content_delta: Text content chunk
    - tool_use: Tool being called
    - tool_result: Tool execution result
    - message_end: End of response with usage stats
    """
    manager = get_session_manager()

    # Verify agent exists
    if manager.get_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    async def event_generator():
        try:
            async for event in manager.stream(
                agent_id=agent_id,
                prompt=request.prompt,
                max_turns=request.max_turns,
            ):
                yield {
                    "event": event.get("event", "message"),
                    "data": event.get("data", {}),
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": {"message": str(e)},
            }

    return EventSourceResponse(event_generator())


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """Get agent information.

    Returns the agent's current state and statistics.
    """
    manager = get_session_manager()
    state = manager.get_agent(agent_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    return {
        "agent_id": state.agent_id,
        "created_at": state.created_at.isoformat() + "Z",
        "instructions": state.instructions[:100] + "..."
        if len(state.instructions) > 100
        else state.instructions,
        "tools": state.tools,
        "provider": state.provider,
        "model": state.model,
        "message_count": state.message_count,
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """Delete an agent.

    Cleans up all resources associated with the agent.
    """
    manager = get_session_manager()
    deleted = await manager.delete_agent(agent_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    return {"deleted": True, "agent_id": agent_id}


@router.get("")
async def list_agents(
    _api_key: str | None = Depends(verify_api_key),
) -> dict:
    """List all active agents.

    Returns a list of agent IDs and summary statistics.
    """
    manager = get_session_manager()

    return {
        "agents": manager.list_agents(),
        "count": manager.active_count,
    }
