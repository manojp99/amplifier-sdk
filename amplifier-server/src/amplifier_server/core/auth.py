"""Authentication middleware and utilities."""

from __future__ import annotations

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from ..config import get_config

# API key header
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str | None:
    """Verify the API key from the Authorization header.

    Args:
        request: FastAPI request
        api_key: API key from header

    Returns:
        The verified API key or None if auth not required

    Raises:
        HTTPException: If authentication fails
    """
    config = get_config()

    # If auth not required, allow all requests
    if not config.require_auth:
        return None

    # Check if API key is configured
    if not config.api_key:
        # No API key configured, allow all requests
        return None

    # Validate the provided key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide 'Authorization: Bearer <key>' header.",
        )

    # Handle "Bearer <key>" format
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]

    if api_key != config.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    return api_key


class AuthMiddleware:
    """Middleware for API key authentication.

    Can be used as a dependency or middleware.
    """

    def __init__(self, required: bool = True):
        """Initialize the middleware.

        Args:
            required: Whether authentication is required
        """
        self.required = required

    async def __call__(
        self,
        request: Request,
        api_key: str | None = Security(api_key_header),
    ) -> str | None:
        """Verify authentication.

        Args:
            request: FastAPI request
            api_key: API key from header

        Returns:
            Verified API key or None
        """
        if not self.required:
            return None
        return await verify_api_key(request, api_key)
