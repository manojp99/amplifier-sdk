"""Pytest configuration and shared fixtures."""

import os

import pytest

# Disable filesystem persistence for all tests — no writes to disk
os.environ["AMPLIFIER_NO_PERSIST"] = "1"


@pytest.fixture(scope="module")
def anyio_backend():
    """Configure anyio to use asyncio backend."""
    return "asyncio"
