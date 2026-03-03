"""Amplifier Runtime CLI.

Usage:
    amplifier-runtime                  # Start HTTP server (default port 4096)
    amplifier-runtime --port 8080      # Custom port
    amplifier-runtime --host 0.0.0.0   # Bind to all interfaces
    amplifier-runtime --log-level debug  # Enable debug logging
    LOG_LEVEL=debug amplifier-runtime    # Same via env var
"""

from __future__ import annotations

import logging
import os

import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=4096, type=int, help="Bind port")
@click.option("--reload", is_flag=True, help="Auto-reload on code changes")
@click.option(
    "--log-level",
    default=None,
    help="Log level: debug, info, warning, error (overrides LOG_LEVEL env var)",
)
def main(host: str, port: int, reload: bool, log_level: str | None) -> None:
    """Start the Amplifier HTTP runtime server."""
    # Resolve log level: CLI flag > LOG_LEVEL env var > default "info"
    resolved_level = (log_level or os.environ.get("LOG_LEVEL", "info")).lower()

    # Configure Python root logger — without this, debug/info logs are silently dropped
    logging.basicConfig(
        level=resolved_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    click.echo(f"Starting Amplifier runtime on http://{host}:{port} (log-level={resolved_level})")
    click.echo("Press Ctrl+C to stop")
    uvicorn.run(
        "amplifier_app_runtime.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        log_level=resolved_level,
    )


if __name__ == "__main__":
    main()
