"""Modules API endpoints."""

from fastapi import APIRouter

from amplifier_server.config import list_available_modules
from amplifier_server.models.responses import ModulesResponse

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=ModulesResponse)
async def get_modules() -> ModulesResponse:
    """List all available modules."""
    modules = list_available_modules()
    return ModulesResponse(
        providers=modules.get("providers", []),
        tools=modules.get("tools", []),
        orchestrators=modules.get("orchestrators", []),
        context_managers=modules.get("context_managers", []),
        hooks=modules.get("hooks", []),
    )
