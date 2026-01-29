"""API routes for the Amplifier Server."""

from amplifier_server.api.agents import router as agents_router
from amplifier_server.api.health import router as health_router
from amplifier_server.api.modules import router as modules_router

__all__ = ["health_router", "agents_router", "modules_router"]
