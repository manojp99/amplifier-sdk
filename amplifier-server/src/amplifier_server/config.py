"""Server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuration for the Amplifier server."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"

    # Authentication
    api_key: str | None = None
    require_auth: bool = True

    # Provider defaults
    default_provider: str = "anthropic"
    default_model: str | None = None

    # Session limits
    max_sessions: int = 100
    session_timeout_seconds: int = 3600  # 1 hour

    # Request limits
    max_tokens_per_request: int | None = None
    max_turns_per_request: int = 50

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("AMPLIFIER_HOST", "0.0.0.0"),
            port=int(os.getenv("AMPLIFIER_PORT", "8080")),
            log_level=os.getenv("AMPLIFIER_LOG_LEVEL", "info"),
            api_key=os.getenv("AMPLIFIER_API_KEY"),
            require_auth=os.getenv("AMPLIFIER_REQUIRE_AUTH", "true").lower() == "true",
            default_provider=os.getenv("AMPLIFIER_DEFAULT_PROVIDER", "anthropic"),
            default_model=os.getenv("AMPLIFIER_DEFAULT_MODEL"),
            max_sessions=int(os.getenv("AMPLIFIER_MAX_SESSIONS", "100")),
            session_timeout_seconds=int(os.getenv("AMPLIFIER_SESSION_TIMEOUT", "3600")),
        )


# Global config instance
_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get the current server configuration."""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
    return _config


def set_config(config: ServerConfig) -> None:
    """Set the server configuration (for testing)."""
    global _config
    _config = config
