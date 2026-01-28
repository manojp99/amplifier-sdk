"""Amplifier Server - FastAPI application entry point."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import agents_router, health_router, recipes_router
from .config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("amplifier_server")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()

    app = FastAPI(
        title="Amplifier Server",
        description="HTTP API for Amplifier AI agent capabilities",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(recipes_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting Amplifier Server v{__version__}")
        logger.info(f"Listening on {config.host}:{config.port}")
        if config.require_auth and config.api_key:
            logger.info("API key authentication enabled")
        else:
            logger.warning("API key authentication disabled")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Amplifier Server")

    return app


# Create app instance
app = create_app()


def run() -> None:
    """Run the server (entry point for CLI)."""
    config = get_config()

    uvicorn.run(
        "amplifier_server.main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
