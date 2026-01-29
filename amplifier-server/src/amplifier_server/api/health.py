"""Health check API endpoints."""

from fastapi import APIRouter

from amplifier_server import __version__
from amplifier_server.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    # Try to get core version
    core_version = None
    try:
        from amplifier_core import __version__ as core_ver

        core_version = core_ver
    except ImportError:
        pass

    return HealthResponse(
        status="ok",
        version=__version__,
        core_version=core_version,
    )
