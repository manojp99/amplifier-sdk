"""Translate SDK configuration to Core mount plan."""

from __future__ import annotations

import os
from typing import Any

from amplifier_server.config import get_module_spec
from amplifier_server.models.requests import (
    AgentConfig,
    ContextManagerConfig,
    HookConfig,
    OrchestratorConfig,
    ProviderConfig,
    ToolConfig,
)


def translate_to_mount_plan(sdk_config: dict[str, Any] | AgentConfig) -> dict[str, Any]:
    """
    Translate SDK-friendly config to Core's mount plan format.

    Supports both simple and advanced configurations:

    Simple SDK Config:
    {
        "instructions": "You are helpful",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "tools": ["bash", "filesystem"],
        "orchestrator": "streaming",
        "context_manager": "simple",
        "hooks": ["logging"],
    }

    Advanced SDK Config:
    {
        "instructions": "You are helpful",
        "providers": [
            {"module": "anthropic", "model": "claude-sonnet-4-20250514", "priority": 1},
            {"module": "openai", "model": "gpt-4o", "priority": 2}
        ],
        "tools": [
            "bash",
            {"module": "filesystem", "config": {"allowed_paths": ["/tmp"]}},
            {"module": "mcp", "server": "github://owner/repo"}
        ],
        "orchestrator": {"module": "agentic-loop", "config": {"max_turns": 20}},
        "context_manager": {"module": "persistent", "config": {"storage": "sqlite"}},
        "hooks": [
            "logging",
            {"module": "approval", "config": {"tools": ["bash"]}}
        ],
        "agents": {...}  # Sub-agent definitions
    }
    """
    # Convert Pydantic model to dict if needed
    if isinstance(sdk_config, AgentConfig):
        sdk_config = sdk_config.model_dump(exclude_none=True)

    # Build providers
    providers = _build_providers(sdk_config)

    # Build orchestrator
    orchestrator = _build_orchestrator(sdk_config)

    # Build context manager
    context = _build_context_manager(sdk_config)

    # Build tools
    tools = _build_tools(sdk_config)

    # Build hooks
    hooks = _build_hooks(sdk_config)

    # Build mount plan
    mount_plan = {
        "session": {
            "orchestrator": orchestrator,
            "context": context,
        },
        "providers": providers,
        "tools": tools,
        "hooks": hooks,
    }

    # Store instructions for later injection into context
    if sdk_config.get("instructions"):
        mount_plan["_instructions"] = sdk_config["instructions"]

    # Store additional config
    if sdk_config.get("config"):
        mount_plan["_extra_config"] = sdk_config["config"]

    # Store sub-agent definitions
    if sdk_config.get("agents"):
        mount_plan["_agents"] = sdk_config["agents"]

    # Store approval config
    if sdk_config.get("approval"):
        mount_plan["_approval"] = sdk_config["approval"]

    return mount_plan


def _build_providers(sdk_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build providers list from SDK config."""
    providers = []

    # Check for advanced providers config first
    if sdk_config.get("providers"):
        for p in sdk_config["providers"]:
            if isinstance(p, dict):
                provider_module = p.get("module") or p.get("provider")
                if not provider_module:
                    raise ValueError("Provider module is required in providers list")
                provider_config = _build_single_provider(
                    provider_module,
                    p.get("model"),
                    p.get("config", {}),
                    p.get("priority", 1),
                )
                providers.append(provider_config)
            elif isinstance(p, ProviderConfig):
                provider_config = _build_single_provider(p.module, p.model, p.config, p.priority)
                providers.append(provider_config)
        return providers

    # Simple provider config
    provider_name = sdk_config.get("provider")
    if not provider_name:
        raise ValueError("Provider is required (either 'provider' or 'providers')")

    provider_config = _build_single_provider(provider_name, sdk_config.get("model"), {}, 1)
    providers.append(provider_config)
    return providers


def _build_single_provider(
    provider_name: str,
    model: str | None,
    extra_config: dict[str, Any],
    priority: int,
) -> dict[str, Any]:
    """Build a single provider config."""
    provider_spec = get_module_spec("providers", provider_name)
    if not provider_spec:
        raise ValueError(f"Unknown provider: {provider_name}")

    # Build provider config with API key from environment
    provider_config: dict[str, Any] = {}
    for key, schema in provider_spec.config_schema.items():
        if "env" in schema:
            env_value = os.getenv(schema["env"])
            if env_value:
                provider_config[key] = env_value
        if "default" in schema and key not in provider_config:
            provider_config[key] = schema["default"]

    # Override model if specified
    if model:
        provider_config["model"] = model

    # Merge extra config
    provider_config.update(extra_config)

    return {
        "module": provider_spec.module,
        "config": provider_config,
        "priority": priority,
    }


def _build_orchestrator(sdk_config: dict[str, Any]) -> dict[str, Any]:
    """Build orchestrator config from SDK config."""
    orch = sdk_config.get("orchestrator", "basic")

    if isinstance(orch, str):
        orchestrator_name = orch
        orchestrator_config = {}
    elif isinstance(orch, dict):
        orchestrator_name = orch.get("module", "basic")
        orchestrator_config = orch.get("config", {})
    elif isinstance(orch, OrchestratorConfig):
        orchestrator_name = orch.module
        orchestrator_config = orch.config
    else:
        raise ValueError(f"Invalid orchestrator config: {orch}")

    orchestrator_spec = get_module_spec("orchestrators", orchestrator_name)
    if not orchestrator_spec:
        raise ValueError(f"Unknown orchestrator: {orchestrator_name}")

    return {"module": orchestrator_spec.module, "config": orchestrator_config}


def _build_context_manager(sdk_config: dict[str, Any]) -> dict[str, Any]:
    """Build context manager config from SDK config."""
    ctx = sdk_config.get("context_manager", "simple")

    if isinstance(ctx, str):
        context_name = ctx
        context_config = {}
    elif isinstance(ctx, dict):
        context_name = ctx.get("module", "simple")
        context_config = ctx.get("config", {})
    elif isinstance(ctx, ContextManagerConfig):
        context_name = ctx.module
        context_config = ctx.config
    else:
        raise ValueError(f"Invalid context manager config: {ctx}")

    context_spec = get_module_spec("context_managers", context_name)
    if not context_spec:
        raise ValueError(f"Unknown context manager: {context_name}")

    return {"module": context_spec.module, "config": context_config}


def _build_tools(sdk_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build tools list from SDK config."""
    tools = []

    for tool in sdk_config.get("tools", []):
        if isinstance(tool, str):
            # Simple tool name
            tool_spec = get_module_spec("tools", tool)
            if not tool_spec:
                raise ValueError(f"Unknown tool: {tool}")
            tools.append({"module": tool_spec.module, "config": {}})

        elif isinstance(tool, dict):
            tool_name = tool.get("module")
            tool_config = tool.get("config", {})

            # Handle special tool types
            if tool_name == "mcp":
                # MCP server tool
                tools.append(
                    {
                        "module": "tool-mcp",
                        "config": {
                            "server": tool.get("server"),
                            **tool_config,
                        },
                    }
                )
            elif tool_name == "custom":
                # Custom tool from path
                tools.append(
                    {
                        "module": "tool-custom",
                        "config": {
                            "path": tool.get("path"),
                            **tool_config,
                        },
                    }
                )
            else:
                # Standard tool with config
                if not tool_name:
                    raise ValueError("Tool module name is required")
                tool_spec = get_module_spec("tools", tool_name)
                if not tool_spec:
                    raise ValueError(f"Unknown tool: {tool_name}")
                tools.append({"module": tool_spec.module, "config": tool_config})

        elif isinstance(tool, ToolConfig):
            if tool.module == "mcp":
                tools.append(
                    {
                        "module": "tool-mcp",
                        "config": {"server": tool.server, **tool.config},
                    }
                )
            elif tool.module == "custom":
                tools.append(
                    {
                        "module": "tool-custom",
                        "config": {"path": tool.path, **tool.config},
                    }
                )
            else:
                tool_spec = get_module_spec("tools", tool.module)
                if not tool_spec:
                    raise ValueError(f"Unknown tool: {tool.module}")
                tools.append({"module": tool_spec.module, "config": tool.config})

    return tools


def _build_hooks(sdk_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build hooks list from SDK config."""
    hooks = []

    for hook in sdk_config.get("hooks", []):
        if isinstance(hook, str):
            # Simple hook name
            hook_spec = get_module_spec("hooks", hook)
            if not hook_spec:
                raise ValueError(f"Unknown hook: {hook}")
            hooks.append({"module": hook_spec.module, "config": {}})

        elif isinstance(hook, dict):
            hook_name = hook.get("module")
            hook_config = hook.get("config", {})

            if hook_name == "custom":
                # Custom hook from path
                hooks.append(
                    {
                        "module": "hook-custom",
                        "config": {
                            "path": hook.get("path"),
                            **hook_config,
                        },
                    }
                )
            else:
                if not hook_name:
                    raise ValueError("Hook module name is required")
                hook_spec = get_module_spec("hooks", hook_name)
                if not hook_spec:
                    raise ValueError(f"Unknown hook: {hook_name}")
                hooks.append({"module": hook_spec.module, "config": hook_config})

        elif isinstance(hook, HookConfig):
            if hook.module == "custom":
                hooks.append(
                    {
                        "module": "hook-custom",
                        "config": {"path": hook.path, **hook.config},
                    }
                )
            else:
                hook_spec = get_module_spec("hooks", hook.module)
                if not hook_spec:
                    raise ValueError(f"Unknown hook: {hook.module}")
                hooks.append({"module": hook_spec.module, "config": hook.config})

    return hooks


def translate_sub_agent_config(
    parent_config: dict[str, Any],
    sub_agent_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Translate sub-agent config, inheriting from parent where not specified.
    """
    # Start with parent's provider/model if not specified
    merged = {
        "instructions": sub_agent_config.get("instructions"),
        "provider": sub_agent_config.get("provider") or parent_config.get("provider"),
        "model": sub_agent_config.get("model") or parent_config.get("model"),
        "tools": sub_agent_config.get("tools", []),
        "orchestrator": sub_agent_config.get("orchestrator", "basic"),
        "context_manager": sub_agent_config.get("context_manager", "simple"),
        "hooks": sub_agent_config.get("hooks", []),
        "config": sub_agent_config.get("config", {}),
    }

    return translate_to_mount_plan(merged)
