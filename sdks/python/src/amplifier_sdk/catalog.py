"""Amplifier Module Catalog.

Hardcoded catalog of known Amplifier modules from the ecosystem.
Updated from: https://github.com/microsoft/amplifier/blob/main/docs/MODULES.md

This catalog ships with the SDK so clients can discover available modules
without needing a runtime API endpoint.

Note: This is a static catalog. New modules won't appear until SDK is updated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ModuleInfo:
    """Information about an Amplifier module."""

    id: str
    """Module identifier (e.g., 'provider-anthropic')"""

    type: Literal["provider", "tool", "orchestrator", "context", "hook"]
    """Module type"""

    name: str
    """Display name"""

    description: str
    """Short description"""

    repository: str | None = None
    """GitHub repository URL"""


# Provider modules - LLM backends
PROVIDERS: list[ModuleInfo] = [
    ModuleInfo(
        id="provider-anthropic",
        type="provider",
        name="Anthropic",
        description="Claude models via Anthropic API",
        repository="https://github.com/microsoft/amplifier-module-provider-anthropic",
    ),
    ModuleInfo(
        id="provider-openai",
        type="provider",
        name="OpenAI",
        description="GPT models via OpenAI API",
        repository="https://github.com/microsoft/amplifier-module-provider-openai",
    ),
    ModuleInfo(
        id="provider-azure",
        type="provider",
        name="Azure OpenAI",
        description="GPT models via Azure OpenAI Service",
        repository="https://github.com/microsoft/amplifier-module-provider-azure",
    ),
    ModuleInfo(
        id="provider-ollama",
        type="provider",
        name="Ollama",
        description="Local LLM inference via Ollama",
        repository="https://github.com/microsoft/amplifier-module-provider-ollama",
    ),
    ModuleInfo(
        id="provider-google",
        type="provider",
        name="Google Gemini",
        description="Gemini models via Google AI API",
        repository="https://github.com/microsoft/amplifier-module-provider-google",
    ),
]

# Tool modules - Agent capabilities
TOOLS: list[ModuleInfo] = [
    ModuleInfo(
        id="tool-bash",
        type="tool",
        name="Bash",
        description="Execute shell commands",
        repository="https://github.com/microsoft/amplifier-module-tool-bash",
    ),
    ModuleInfo(
        id="tool-filesystem",
        type="tool",
        name="Filesystem",
        description="Read/write files and directories",
        repository="https://github.com/microsoft/amplifier-module-tool-filesystem",
    ),
    ModuleInfo(
        id="tool-web",
        type="tool",
        name="Web Search",
        description="Search the web",
        repository="https://github.com/microsoft/amplifier-module-tool-web",
    ),
    ModuleInfo(
        id="tool-web-fetch",
        type="tool",
        name="Web Fetch",
        description="Fetch content from URLs",
        repository="https://github.com/microsoft/amplifier-module-tool-web-fetch",
    ),
    ModuleInfo(
        id="tool-task",
        type="tool",
        name="Task",
        description="Multi-file exploration and search",
        repository="https://github.com/microsoft/amplifier-module-tool-task",
    ),
    ModuleInfo(
        id="tool-delegate",
        type="tool",
        name="Delegate",
        description="Spawn specialized agents",
        repository="https://github.com/microsoft/amplifier-module-tool-delegate",
    ),
    ModuleInfo(
        id="tool-recipes",
        type="tool",
        name="Recipes",
        description="Execute multi-step workflows",
        repository="https://github.com/microsoft/amplifier-module-tool-recipes",
    ),
]

# Orchestrator modules - Execution strategies
ORCHESTRATORS: list[ModuleInfo] = [
    ModuleInfo(
        id="loop-basic",
        type="orchestrator",
        name="Basic Loop",
        description="Simple synchronous execution loop",
        repository="https://github.com/microsoft/amplifier-module-loop-basic",
    ),
    ModuleInfo(
        id="loop-streaming",
        type="orchestrator",
        name="Streaming Loop",
        description="Real-time streaming responses",
        repository="https://github.com/microsoft/amplifier-module-loop-streaming",
    ),
    ModuleInfo(
        id="loop-events",
        type="orchestrator",
        name="Event Loop",
        description="Event-driven execution with rich observability",
        repository="https://github.com/microsoft/amplifier-module-loop-events",
    ),
]

# Context modules - Memory management
CONTEXTS: list[ModuleInfo] = [
    ModuleInfo(
        id="context-simple",
        type="context",
        name="Simple Context",
        description="In-memory conversation history",
        repository="https://github.com/microsoft/amplifier-module-context-simple",
    ),
    ModuleInfo(
        id="context-persistent",
        type="context",
        name="Persistent Context",
        description="Disk-backed conversation history",
        repository="https://github.com/microsoft/amplifier-module-context-persistent",
    ),
]

# Hook modules - Lifecycle observers
HOOKS: list[ModuleInfo] = [
    ModuleInfo(
        id="hook-logging",
        type="hook",
        name="Logging Hook",
        description="Log all events to file/console",
        repository="https://github.com/microsoft/amplifier-module-hook-logging",
    ),
    ModuleInfo(
        id="hook-approval",
        type="hook",
        name="Approval Hook",
        description="Request user approval for sensitive operations",
        repository="https://github.com/microsoft/amplifier-module-hook-approval",
    ),
    ModuleInfo(
        id="hook-shell",
        type="hook",
        name="Shell Hook",
        description="Approve shell commands before execution",
        repository="https://github.com/microsoft/amplifier-module-hook-shell",
    ),
    ModuleInfo(
        id="hook-redaction",
        type="hook",
        name="Redaction Hook",
        description="Redact sensitive information from logs",
        repository="https://github.com/microsoft/amplifier-module-hook-redaction",
    ),
]

# Complete catalog
MODULE_CATALOG = {
    "providers": PROVIDERS,
    "tools": TOOLS,
    "orchestrators": ORCHESTRATORS,
    "contexts": CONTEXTS,
    "hooks": HOOKS,
}


def get_modules_by_type(
    module_type: Literal["provider", "tool", "orchestrator", "context", "hook"]
) -> list[ModuleInfo]:
    """Get modules by type."""
    if module_type == "provider":
        return PROVIDERS
    elif module_type == "tool":
        return TOOLS
    elif module_type == "orchestrator":
        return ORCHESTRATORS
    elif module_type == "context":
        return CONTEXTS
    elif module_type == "hook":
        return HOOKS
    else:
        return []


def find_module(module_id: str) -> ModuleInfo | None:
    """Find module by ID."""
    for module in [*PROVIDERS, *TOOLS, *ORCHESTRATORS, *CONTEXTS, *HOOKS]:
        if module.id == module_id:
            return module
    return None


def get_all_modules() -> list[ModuleInfo]:
    """Get all modules."""
    return [*PROVIDERS, *TOOLS, *ORCHESTRATORS, *CONTEXTS, *HOOKS]
