"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..core.session_manager import get_session_manager
from ..models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns server status, version, and active session count.
    No authentication required.
    """
    manager = get_session_manager()

    return HealthResponse(
        status="ok",
        version=__version__,
        active_sessions=manager.active_count,
    )


@router.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns basic server information.
    """
    return {
        "name": "amplifier-server",
        "version": __version__,
        "docs": "/docs",
    }
