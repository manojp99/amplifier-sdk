"""API endpoint modules."""

from .agents import router as agents_router
from .health import router as health_router
from .recipes import router as recipes_router

__all__ = [
    "agents_router",
    "health_router",
    "recipes_router",
]
