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
    ClientTool,
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
        self._client_tools: dict[str, ClientTool] = {}
        self._event_handlers: dict[str, list[Any]] = {}
        self._approval_handler: Any = None

    # =========================================================================
    # Client-Side Tools
    # =========================================================================

    def register_tool(self, tool: ClientTool) -> None:
        """Register a client-side tool.

        Client-side tools run in your app (not on the server) and give the AI
        access to your local APIs, databases, and services.

        Args:
            tool: ClientTool instance to register

        Raises:
            ValueError: If tool is invalid

        Example:
            ```python
            client.register_tool(ClientTool(
                name="get-customer",
                description="Get customer information by ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "customerId": {"type": "string"}
                    },
                    "required": ["customerId"]
                },
                handler=lambda args: get_customer(args["customerId"])
            ))
            ```
        """
        if not isinstance(tool, ClientTool):
            raise ValueError("Tool must be a ClientTool instance")
        if not tool.name or not isinstance(tool.name, str):
            raise ValueError("Tool name is required and must be a string")
        if not tool.description or not isinstance(tool.description, str):
            raise ValueError("Tool description is required and must be a string")
        if not callable(tool.handler):
            raise ValueError("Tool handler must be callable")

        self._client_tools[tool.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a client-side tool.

        Args:
            name: Tool name to remove

        Returns:
            True if tool was removed, False if not found
        """
        return self._client_tools.pop(name, None) is not None

    def get_client_tools(self) -> list[ClientTool]:
        """Get all registered client-side tools.

        Returns:
            List of registered client tools
        """
        return list(self._client_tools.values())

    async def _execute_client_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Execute a client-side tool handler.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result

        Raises:
            KeyError: If tool not found
            Exception: If tool execution fails
        """
        tool = self._client_tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Client tool not found: {tool_name}")

        # Execute the handler (may be async or sync)
        result = tool.handler(args)
        if hasattr(result, "__await__"):
            return await result
        return result

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
    # Event Handlers (Convenience API)
    # =========================================================================

    def on(self, event_type: str, handler: Any) -> None:
        """Register an event handler.

        Example:
            ```python
            client.on("tool.call", lambda event: print(f"Tool: {event.data['tool_name']}"))
            client.on("content.delta", lambda event: print(event.data["delta"], end=""))
            ```
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Any) -> None:
        """Unregister an event handler."""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass

    def once(self, event_type: str, handler: Any) -> None:
        """Register a one-time event handler."""

        def wrapped_handler(event: Event) -> None:
            handler(event)
            self.off(event_type, wrapped_handler)

        self.on(event_type, wrapped_handler)

    async def _emit_event(self, event: Event) -> None:
        """Emit event to registered handlers."""
        handlers = self._event_handlers.get(event.type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception as err:
                print(f"Event handler error for {event.type}: {err}")

    def on_approval(self, handler: Any) -> None:
        """Register approval handler (convenience method).

        When the AI requests approval, your handler will be called automatically.
        Return True to approve, False to deny.

        Example:
            ```python
            async def handle_approval(request):
                user_choice = await show_dialog(request["prompt"])
                return user_choice

            client.on_approval(handle_approval)
            ```
        """
        self._approval_handler = handler

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

        Raises:
            ValueError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")

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

        Raises:
            ValueError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")

        client = await self._get_client()
        response = await client.delete(f"/v1/session/{session_id}")
        return response.status_code == 200

    async def cancel(self, session_id: str) -> bool:
        """Cancel ongoing execution.

        Args:
            session_id: Session ID

        Returns:
            True if cancelled successfully

        Raises:
            ValueError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")

        client = await self._get_client()
        try:
            response = await client.post(f"/v1/session/{session_id}/cancel")
            return response.status_code == 200
        except Exception:
            return False

    async def resume_session(self, session_id: str) -> dict[str, Any]:
        """Resume a previous session (convenience method).

        This is a convenience wrapper that fetches session info and provides
        helper methods for continuing the conversation.

        Args:
            session_id: Session ID to resume

        Returns:
            Session object with helper methods

        Raises:
            ValueError: If session_id is invalid

        Example:
            ```python
            session = await client.resume_session("sess_abc123")

            # Continue the conversation
            async for event in session["send"]("Where were we?"):
                if event.type == "content.delta":
                    print(event.data.get("delta", ""), end="", flush=True)
            ```
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")

        info = await self.get_session(session_id)

        return {
            "id": info.id,
            "title": info.title,
            "state": info.state,
            "created_at": info.created_at,
            "updated_at": info.updated_at,
            "send": lambda content: self.prompt(session_id, content),
            "send_sync": lambda content: self.prompt_sync(session_id, content),
            "cancel": lambda: self.cancel(session_id),
            "delete": lambda: self.delete_session(session_id),
        }

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

        Raises:
            ValueError: If session_id or content is invalid

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
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")
        if not content or not isinstance(content, str):
            raise ValueError("Prompt content is required and must be a string")

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
                            event = Event.from_dict(data)

                            # Intercept client-side tool calls
                            if event.type == "tool.call":
                                tool_name = event.data.get("tool_name", "")
                                tool_call_id = event.tool_call_id or event.data.get("tool_call_id")

                                # Check if this is a client-side tool
                                if tool_name in self._client_tools:
                                    # Execute tool locally
                                    try:
                                        args = event.data.get("arguments", {})
                                        result = await self._execute_client_tool(tool_name, args)

                                        # Send result back to server
                                        await client.post(
                                            f"/v1/session/{session_id}/tool-result",
                                            json={
                                                "tool_call_id": tool_call_id,
                                                "result": result,
                                            },
                                        )
                                    except Exception as err:
                                        # Send error back to server
                                        await client.post(
                                            f"/v1/session/{session_id}/tool-result",
                                            json={
                                                "tool_call_id": tool_call_id,
                                                "error": str(err),
                                            },
                                        )

                                    # Don't yield the tool.call event - it's handled
                                    continue

                            # Handle approval requests with registered handler
                            if event.type == "approval.required" and self._approval_handler:
                                request_id = event.data.get("request_id", "")
                                prompt = event.data.get("prompt", "")
                                tool_name = event.data.get("tool_name")
                                args = event.data.get("arguments")

                                try:
                                    request_data = {
                                        "requestId": request_id,
                                        "prompt": prompt,
                                        "toolName": tool_name,
                                        "arguments": args,
                                    }

                                    # Call approval handler
                                    approved = self._approval_handler(request_data)
                                    if hasattr(approved, "__await__"):
                                        approved = await approved

                                    # Auto-respond to approval
                                    await self.respond_approval(
                                        session_id, request_id, str(approved).lower()
                                    )
                                except Exception as err:
                                    print(f"Approval handler error: {err}")

                            # Emit to registered event handlers
                            await self._emit_event(event)

                            yield event
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

        Raises:
            ValueError: If session_id or content is invalid

        Example:
            ```python
            response = await client.prompt_sync(session_id, "What is 2+2?")
            print(response.content)  # "4"
            ```
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")
        if not content or not isinstance(content, str):
            raise ValueError("Prompt content is required and must be a string")

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

        Raises:
            ValueError: If any parameter is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID is required and must be a string")
        if not request_id or not isinstance(request_id, str):
            raise ValueError("Request ID is required and must be a string")
        if not choice or not isinstance(choice, str):
            raise ValueError("Choice is required and must be a string")

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
