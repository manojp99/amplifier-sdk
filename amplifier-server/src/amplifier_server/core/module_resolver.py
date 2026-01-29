"""Module resolver for the server - maps module IDs to importable modules."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass


@dataclass
class ModuleSource:
    """Source information for a module."""

    module_id: str
    python_module: str
    path: str | None = None


class ServerModuleResolver:
    """
    Simple module resolver for pre-installed modules.

    Unlike Foundation's resolver which downloads from git URLs,
    this resolver expects modules to already be installed via pip.
    It maps friendly module IDs to Python import paths.
    """

    # Map module IDs to Python package names
    MODULE_MAP: dict[str, str] = {
        # Providers
        "provider-anthropic": "amplifier_module_provider_anthropic",
        "provider-openai": "amplifier_module_provider_openai",
        "provider-azure": "amplifier_module_provider_azure",
        # Tools
        "tool-bash": "amplifier_module_tool_bash",
        "tool-filesystem": "amplifier_module_tool_filesystem",
        "tool-web": "amplifier_module_tool_web",
        # Orchestrators
        "loop-basic": "amplifier_module_loop_basic",
        "loop-streaming": "amplifier_module_loop_streaming",
        # Context managers
        "context-simple": "amplifier_module_context_simple",
        # Hooks
        "hook-logging": "amplifier_module_hook_logging",
    }

    def __init__(self, custom_modules: dict[str, str] | None = None):
        """
        Initialize the resolver.

        Args:
            custom_modules: Additional module mappings (module_id -> python_module)
        """
        self.modules = dict(self.MODULE_MAP)
        if custom_modules:
            self.modules.update(custom_modules)

    def resolve(
        self,
        module_id: str,
        source_hint: str | None = None,
        profile_hint: str | None = None,
    ) -> ModuleSource:
        """
        Resolve a module ID to its source.

        Args:
            module_id: The module identifier (e.g., "provider-anthropic")
            source_hint: Optional source hint (ignored, for compatibility)
            profile_hint: Optional profile hint (ignored, for compatibility)

        Returns:
            ModuleSource with import path

        Raises:
            ModuleNotFoundError: If module is not in registry or not installed
        """
        python_module = self.modules.get(module_id)
        if not python_module:
            raise ModuleNotFoundError(
                f"Unknown module: {module_id}. Available modules: {list(self.modules.keys())}"
            )

        # Verify module is actually installed
        try:
            spec = importlib.util.find_spec(python_module)
            if spec is None:
                raise ModuleNotFoundError(
                    f"Module {module_id} ({python_module}) is not installed. "
                    f"Install it with: pip install {python_module.replace('_', '-')}"
                )
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Module {module_id} ({python_module}) is not installed. "
                f"Install it with: pip install {python_module.replace('_', '-')}"
            ) from e

        return ModuleSource(
            module_id=module_id,
            python_module=python_module,
            path=spec.origin if spec else None,
        )

    def list_available(self) -> dict[str, list[str]]:
        """List available modules by category."""
        result: dict[str, list[str]] = {
            "providers": [],
            "tools": [],
            "orchestrators": [],
            "context_managers": [],
            "hooks": [],
        }

        for module_id in self.modules:
            if module_id.startswith("provider-"):
                result["providers"].append(module_id)
            elif module_id.startswith("tool-"):
                result["tools"].append(module_id)
            elif module_id.startswith("loop-"):
                result["orchestrators"].append(module_id)
            elif module_id.startswith("context-"):
                result["context_managers"].append(module_id)
            elif module_id.startswith("hook-"):
                result["hooks"].append(module_id)

        return result

    def is_available(self, module_id: str) -> bool:
        """Check if a module is available and installed."""
        try:
            self.resolve(module_id)
            return True
        except ModuleNotFoundError:
            return False
