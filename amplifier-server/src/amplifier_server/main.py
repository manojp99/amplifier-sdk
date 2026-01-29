"""Main entry point for the Amplifier Server."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from amplifier_server import __version__
from amplifier_server.api.agents import one_off_router
from amplifier_server.api.agents import router as agents_router
from amplifier_server.api.health import router as health_router
from amplifier_server.api.modules import router as modules_router
from amplifier_server.config import ServerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config: ServerConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = ServerConfig.from_env()

    app = FastAPI(
        title="Amplifier Server",
        description="HTTP API for Amplifier Core capabilities",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(modules_router)
    app.include_router(one_off_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Amplifier Server v{__version__} starting...")
        logger.info(f"Documentation available at http://{config.host}:{config.port}/docs")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Amplifier Server shutting down...")

    return app


def run() -> None:
    """Run the server from command line."""
    config = ServerConfig.from_env()

    logger.info(f"Starting Amplifier Server on {config.host}:{config.port}")

    uvicorn.run(
        "amplifier_server.main:create_app",
        host=config.host,
        port=config.port,
        factory=True,
        log_level=config.log_level,
    )


# For development: `python -m amplifier_server.main`
if __name__ == "__main__":
    run()
