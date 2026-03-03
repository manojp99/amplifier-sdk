"""Tests for the Bus event pub/sub system.

The Bus is a pure asyncio pub/sub implementation — no amplifier-core
dependency. These tests verify subscribe/publish/wildcard/reset.
"""

from collections.abc import Generator

import pytest

from amplifier_app_runtime.events import (
    Bus,
    SessionCreated,
    SessionCreatedProps,
    SessionDeleted,
    SessionDeletedProps,
    get_event_category,
    is_debug_event,
    is_ui_safe,
)


@pytest.fixture(autouse=True)
def reset_bus() -> None:
    """Reset Bus state before and after each test."""
    Bus.reset()
    yield
    Bus.reset()


@pytest.mark.asyncio
async def test_subscribe_and_publish_specific_event() -> None:
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    await Bus.subscribe(SessionCreated, handler)
    await Bus.publish(
        SessionCreated,
        SessionCreatedProps(session_id="sess_001", title="Test Session"),
    )

    assert len(received) == 1
    assert received[0]["type"] == "session.created"
    assert received[0]["properties"]["session_id"] == "sess_001"
    assert received[0]["properties"]["title"] == "Test Session"


@pytest.mark.asyncio
async def test_wildcard_subscription_receives_all_events() -> None:
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    await Bus.subscribe_all(handler)

    await Bus.publish(SessionCreated, SessionCreatedProps(session_id="a", title="A"))
    await Bus.publish(SessionDeleted, SessionDeletedProps(session_id="a"))

    assert len(received) == 2
    event_types = {e["type"] for e in received}
    assert "session.created" in event_types
    assert "session.deleted" in event_types


@pytest.mark.asyncio
async def test_reset_clears_all_subscribers() -> None:
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    await Bus.subscribe(SessionCreated, handler)
    Bus.reset()

    await Bus.publish(SessionCreated, SessionCreatedProps(session_id="x", title="X"))

    assert len(received) == 0


@pytest.mark.asyncio
async def test_specific_subscriber_does_not_receive_other_events() -> None:
    created_received: list[dict] = []
    deleted_received: list[dict] = []

    async def on_created(payload: dict) -> None:
        created_received.append(payload)

    async def on_deleted(payload: dict) -> None:
        deleted_received.append(payload)

    await Bus.subscribe(SessionCreated, on_created)
    await Bus.subscribe(SessionDeleted, on_deleted)

    await Bus.publish(SessionCreated, SessionCreatedProps(session_id="s", title="S"))

    assert len(created_received) == 1
    assert len(deleted_received) == 0


@pytest.mark.asyncio
async def test_unsubscribe_stops_receiving_events() -> None:
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    unsubscribe = await Bus.subscribe(SessionCreated, handler)

    await Bus.publish(SessionCreated, SessionCreatedProps(session_id="1", title="1"))
    assert len(received) == 1

    unsubscribe()

    await Bus.publish(SessionCreated, SessionCreatedProps(session_id="2", title="2"))
    assert len(received) == 1  # Still 1 — unsubscribed


def test_get_event_category_parses_prefix() -> None:
    from amplifier_app_runtime.events import EventCategory

    assert get_event_category("session:start") == EventCategory.SESSION
    assert get_event_category("tool:pre") == EventCategory.TOOL
    assert get_event_category("no-colon") is None


def test_is_debug_event() -> None:
    assert is_debug_event("llm:request:debug") is True
    assert is_debug_event("llm:request:raw") is True
    assert is_debug_event("llm:request") is False
    assert is_debug_event("content_block:start") is False


def test_is_ui_safe() -> None:
    assert is_ui_safe("session:start") is True
    assert is_ui_safe("llm:request:debug") is False
    assert is_ui_safe("llm:response:raw") is False
    assert is_ui_safe("content_block:start") is True
