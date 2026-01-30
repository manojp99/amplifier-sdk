"""Amplifier SDK Client.

HTTP client for communicating with amplifier-app-runtime server.
Supports both streaming (SSE) and synchronous request modes.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .types import (
    Event,
    PromptResponse,
    SessionConfig,
    SessionInfo,
)


class AmplifierClient:
    """HTTP client for amplifier-app-runtime server.

    Example:
        ```python
        async with AmplifierClient() as client:
            # Create session
            session = await client.create_session(bundle="foundation")

            # Stream a prompt
            async for event in client.prompt(session.id, "Hello!"):
                if event.type == "content.delta":
                    print(event.data.get("delta", ""), end="")

            # Or use synchronous mode
            response = await client.prompt_sync(session.id, "What is 2+2?")
            print(response.content)

            # Clean up
            await client.delete_session(session.id)
        ```
    """

    def __init__(
        self,
        base_url: str = "http://localhost:4096",
        timeout: float = 300.0,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Server URL (default: http://localhost:4096)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AmplifierClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # =========================================================================
    # Health & Capabilities
    # =========================================================================

    async def ping(self) -> bool:
        """Check if server is alive.

        Returns:
            True if server responds to ping
        """
        try:
            client = await self._get_client()
            response = await client.get("/v1/ping")
            return response.status_code == 200
        except Exception:
            return False

    async def capabilities(self) -> dict[str, Any]:
        """Get server capabilities.

        Returns:
            Server capabilities dictionary
        """
        client = await self._get_client()
        response = await client.get("/v1/capabilities")
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Session Management
    # =========================================================================

    async def create_session(
        self,
        bundle: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        working_directory: str | None = None,
    ) -> SessionInfo:
        """Create a new session.

        Args:
            bundle: Bundle name (e.g., "foundation", "amplifier-dev")
            provider: Provider name (e.g., "anthropic", "openai")
            model: Model name (e.g., "claude-sonnet-4-20250514")
            working_directory: Working directory for the session

        Returns:
            SessionInfo with the new session ID
        """
        client = await self._get_client()
        config = SessionConfig(
            bundle=bundle,
            provider=provider,
            model=model,
            working_directory=working_directory,
        )
        response = await client.post("/v1/session", json=config.to_dict())
        response.raise_for_status()
        return SessionInfo.from_dict(response.json())

    async def get_session(self, session_id: str) -> SessionInfo:
        """Get session information.

        Args:
            session_id: Session ID

        Returns:
            SessionInfo
        """
        client = await self._get_client()
        response = await client.get(f"/v1/session/{session_id}")
        response.raise_for_status()
        return SessionInfo.from_dict(response.json())

    async def list_sessions(self) -> list[SessionInfo]:
        """List all sessions.

        Returns:
            List of SessionInfo
        """
        client = await self._get_client()
        response = await client.get("/v1/session")
        response.raise_for_status()
        data = response.json()
        sessions = data.get("sessions", [])
        return [SessionInfo.from_dict(s) for s in sessions]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()
        response = await client.delete(f"/v1/session/{session_id}")
        return response.status_code == 200

    # =========================================================================
    # Prompt Execution
    # =========================================================================

    async def prompt(
        self,
        session_id: str,
        content: str,
        stream: bool = True,
    ) -> AsyncIterator[Event]:
        """Send a prompt and stream the response.

        This is the primary method for interacting with the agent.
        Events are streamed as they arrive from the server.

        Args:
            session_id: Session ID
            content: Prompt content
            stream: Whether to stream (default: True)

        Yields:
            Event objects as they arrive

        Example:
            ```python
            async for event in client.prompt(session_id, "Hello!"):
                if event.type == "content.delta":
                    print(event.data.get("delta", ""), end="", flush=True)
                elif event.type == "tool.call":
                    print(f"\\nCalling tool: {event.data.get('tool_name')}")
                elif event.type == "content.end":
                    print()  # Newline at end
            ```
        """
        client = await self._get_client()

        async with client.stream(
            "POST",
            f"/v1/session/{session_id}/prompt",
            json={"content": content, "stream": stream},
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                # Parse SSE format: "data: {...}"
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            yield Event.from_dict(data)
                        except json.JSONDecodeError:
                            continue

    async def prompt_sync(
        self,
        session_id: str,
        content: str,
    ) -> PromptResponse:
        """Send a prompt and wait for complete response.

        Use this when you want to wait for the full response
        instead of streaming events.

        Args:
            session_id: Session ID
            content: Prompt content

        Returns:
            PromptResponse with complete content and tool calls

        Example:
            ```python
            response = await client.prompt_sync(session_id, "What is 2+2?")
            print(response.content)  # "4"
            ```
        """
        client = await self._get_client()
        response = await client.post(
            f"/v1/session/{session_id}/prompt/sync",
            json={"content": content},
        )
        response.raise_for_status()
        return PromptResponse.from_dict(response.json())

    async def cancel(self, session_id: str) -> bool:
        """Cancel ongoing execution.

        Args:
            session_id: Session ID

        Returns:
            True if cancelled successfully
        """
        client = await self._get_client()
        response = await client.post(f"/v1/session/{session_id}/cancel")
        return response.status_code == 200

    # =========================================================================
    # Approval System
    # =========================================================================

    async def respond_approval(
        self,
        session_id: str,
        request_id: str,
        choice: str,
    ) -> bool:
        """Respond to an approval request.

        When the agent requires approval (e.g., for dangerous operations),
        use this to approve or deny the request.

        Args:
            session_id: Session ID
            request_id: Approval request ID (from approval.required event)
            choice: One of the options from the approval request

        Returns:
            True if response was accepted
        """
        client = await self._get_client()
        response = await client.post(
            f"/v1/session/{session_id}/approval",
            json={"request_id": request_id, "choice": choice},
        )
        return response.status_code == 200

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def run(
        self,
        content: str,
        bundle: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> PromptResponse:
        """One-shot execution: create session, run prompt, return response.

        Convenience method for quick interactions that don't need
        session persistence.

        Args:
            content: Prompt content
            bundle: Bundle name (optional)
            provider: Provider name (optional)
            model: Model name (optional)

        Returns:
            PromptResponse with the result

        Example:
            ```python
            response = await client.run("What is the capital of France?")
            print(response.content)
            ```
        """
        session = await self.create_session(
            bundle=bundle,
            provider=provider,
            model=model,
        )
        try:
            return await self.prompt_sync(session.id, content)
        finally:
            await self.delete_session(session.id)

    async def stream(
        self,
        content: str,
        bundle: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[Event]:
        """One-shot streaming: create session, stream prompt, cleanup.

        Convenience method for streaming interactions that don't need
        session persistence.

        Args:
            content: Prompt content
            bundle: Bundle name (optional)
            provider: Provider name (optional)
            model: Model name (optional)

        Yields:
            Event objects as they arrive

        Example:
            ```python
            async for event in client.stream("Tell me a story"):
                if event.type == "content.delta":
                    print(event.data.get("delta", ""), end="")
            ```
        """
        session = await self.create_session(
            bundle=bundle,
            provider=provider,
            model=model,
        )
        try:
            async for event in self.prompt(session.id, content):
                yield event
        finally:
            await self.delete_session(session.id)


# Convenience function for simple usage
async def run(
    content: str,
    base_url: str = "http://localhost:4096",
    bundle: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> PromptResponse:
    """Quick one-shot execution.

    Example:
        ```python
        from amplifier_sdk import run

        response = await run("What is 2+2?")
        print(response.content)
        ```
    """
    async with AmplifierClient(base_url=base_url) as client:
        return await client.run(content, bundle=bundle, provider=provider, model=model)
