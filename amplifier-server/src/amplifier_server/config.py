"""Server configuration and module registry."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleSpec:
    """Specification for a module."""

    module: str
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    require_auth: bool = False
    api_keys: list[str] = field(default_factory=list)
    max_agents: int = 100
    log_level: str = "info"

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("AMPLIFIER_SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("AMPLIFIER_SERVER_PORT", "8000")),
            require_auth=os.getenv("AMPLIFIER_REQUIRE_AUTH", "").lower() == "true",
            api_keys=os.getenv("AMPLIFIER_API_KEYS", "").split(",")
            if os.getenv("AMPLIFIER_API_KEYS")
            else [],
            max_agents=int(os.getenv("AMPLIFIER_MAX_AGENTS", "100")),
            log_level=os.getenv("AMPLIFIER_LOG_LEVEL", "info"),
        )


# Module Registry - maps friendly names to module specifications
# Modules must be pre-installed on the server
MODULE_REGISTRY: dict[str, dict[str, ModuleSpec]] = {
    "providers": {
        "anthropic": ModuleSpec(
            module="provider-anthropic",
            config_schema={
                "api_key": {"type": "string", "env": "ANTHROPIC_API_KEY"},
                "model": {"type": "string", "default": "claude-sonnet-4-20250514"},
            },
        ),
        "openai": ModuleSpec(
            module="provider-openai",
            config_schema={
                "api_key": {"type": "string", "env": "OPENAI_API_KEY"},
                "model": {"type": "string", "default": "gpt-4o"},
            },
        ),
        "azure": ModuleSpec(
            module="provider-azure",
            config_schema={
                "endpoint": {"type": "string", "env": "AZURE_OPENAI_ENDPOINT"},
                "api_key": {"type": "string", "env": "AZURE_OPENAI_API_KEY"},
            },
        ),
    },
    "tools": {
        "bash": ModuleSpec(module="tool-bash"),
        "filesystem": ModuleSpec(module="tool-filesystem"),
        "web_search": ModuleSpec(module="tool-web"),
        "web_fetch": ModuleSpec(module="tool-web"),
    },
    "orchestrators": {
        "basic": ModuleSpec(module="loop-basic"),
        "streaming": ModuleSpec(module="loop-streaming"),
    },
    "context_managers": {
        "simple": ModuleSpec(module="context-simple"),
    },
    "hooks": {
        "logging": ModuleSpec(module="hook-logging"),
    },
}


def get_module_spec(category: str, name: str) -> ModuleSpec | None:
    """Get a module specification by category and name."""
    return MODULE_REGISTRY.get(category, {}).get(name)


def list_available_modules() -> dict[str, list[str]]:
    """List all available modules by category."""
    return {category: list(modules.keys()) for category, modules in MODULE_REGISTRY.items()}
