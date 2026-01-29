"""Translate SDK configuration to Core mount plan."""

from __future__ import annotations

import os
from typing import Any

from amplifier_server.config import get_module_spec


def translate_to_mount_plan(sdk_config: dict[str, Any]) -> dict[str, Any]:
    """
    Translate SDK-friendly config to Core's mount plan format.

    SDK Config (user-friendly):
    {
        "instructions": "You are helpful",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "tools": ["bash", "filesystem"],
        "orchestrator": "streaming",
        "context_manager": "simple",
        "hooks": ["logging"],
        "config": {"max_turns": 10}
    }

    Mount Plan (Core's format):
    {
        "session": {
            "orchestrator": {"module": "loop-streaming", "config": {}},
            "context": {"module": "context-simple", "config": {}}
        },
        "providers": [
            {"module": "provider-anthropic", "config": {"model": "..."}}
        ],
        "tools": [
            {"module": "tool-bash", "config": {}},
            {"module": "tool-filesystem", "config": {}}
        ],
        "hooks": [
            {"module": "hook-logging", "config": {}}
        ]
    }
    """
    # Get orchestrator spec
    orchestrator_name = sdk_config.get("orchestrator", "basic")
    orchestrator_spec = get_module_spec("orchestrators", orchestrator_name)
    if not orchestrator_spec:
        raise ValueError(f"Unknown orchestrator: {orchestrator_name}")

    # Get context manager spec
    context_name = sdk_config.get("context_manager", "simple")
    context_spec = get_module_spec("context_managers", context_name)
    if not context_spec:
        raise ValueError(f"Unknown context manager: {context_name}")

    # Get provider spec
    provider_name = sdk_config.get("provider")
    if not provider_name:
        raise ValueError("Provider is required")
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
    if sdk_config.get("model"):
        provider_config["model"] = sdk_config["model"]

    # Build tools list
    tools = []
    for tool_name in sdk_config.get("tools", []):
        tool_spec = get_module_spec("tools", tool_name)
        if not tool_spec:
            raise ValueError(f"Unknown tool: {tool_name}")
        tools.append({"module": tool_spec.module, "config": {}})

    # Build hooks list
    hooks = []
    for hook_name in sdk_config.get("hooks", []):
        hook_spec = get_module_spec("hooks", hook_name)
        if not hook_spec:
            raise ValueError(f"Unknown hook: {hook_name}")
        hooks.append({"module": hook_spec.module, "config": {}})

    # Build mount plan
    mount_plan = {
        "session": {
            "orchestrator": {"module": orchestrator_spec.module, "config": {}},
            "context": {"module": context_spec.module, "config": {}},
        },
        "providers": [{"module": provider_spec.module, "config": provider_config}],
        "tools": tools,
        "hooks": hooks,
    }

    # Store instructions for later injection into context
    if sdk_config.get("instructions"):
        mount_plan["_instructions"] = sdk_config["instructions"]

    # Store additional config
    if sdk_config.get("config"):
        mount_plan["_extra_config"] = sdk_config["config"]

    return mount_plan
