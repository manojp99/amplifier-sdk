"""Tests for SessionManager lifecycle and state management.

All tests use AMPLIFIER_NO_PERSIST=1 (set in conftest.py) so no
files are written to disk. Tests that call create_session() will
fail fast because amplifier-core is required to initialize a
real session — we test the failure behaviour and book-keeping only.
"""

import pytest

from amplifier_app_runtime.sessions import (
    SessionConfig,
    SessionManager,
    SessionState,
)


@pytest.fixture
def manager() -> SessionManager:
    """Fresh SessionManager with no persistence for each test."""
    return SessionManager()


def test_new_manager_is_empty(manager: SessionManager) -> None:
    assert manager.active_count == 0
    assert manager.total_count == 0


def test_new_manager_has_no_store(manager: SessionManager) -> None:
    # AMPLIFIER_NO_PERSIST=1 means no store
    assert manager.store is None


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_none(manager: SessionManager) -> None:
    result = await manager.get_session("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session_returns_false(manager: SessionManager) -> None:
    result = await manager.delete_session("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_create_session_without_bundle_raises(manager: SessionManager) -> None:
    """Sessions require a bundle — fail clearly if none provided."""
    with pytest.raises(RuntimeError, match="bundle"):
        await manager.create_session(config=SessionConfig(bundle=None))


@pytest.mark.asyncio
async def test_list_sessions_returns_empty_when_none(manager: SessionManager) -> None:
    result = await manager.list_sessions()
    assert result == []


def test_session_states_enum_values() -> None:
    """Verify SessionState enum has expected values."""
    assert SessionState.CREATED == "created"
    assert SessionState.READY == "ready"
    assert SessionState.RUNNING == "running"
    assert SessionState.COMPLETED == "completed"
    assert SessionState.ERROR == "error"
