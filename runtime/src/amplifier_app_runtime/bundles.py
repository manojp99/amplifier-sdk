"""Bundle management and module resolution.

Consolidates: bundle_manager.py + resolvers.py

No internal dependencies -- only external packages (amplifier_foundation, yaml).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from amplifier_foundation import Bundle
    from amplifier_foundation.registry import BundleRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Source classes (from resolvers.py)
# ============================================================================


class ModuleResolutionError(Exception):
    """Error during module resolution."""

    pass


class GitSource:
    """Git source that uses foundation's SimpleSourceResolver."""

    def __init__(self, uri: str) -> None:
        """Initialize with git URI (e.g., git+https://github.com/org/repo@ref)."""
        self.uri = uri
        self._resolver = None

    def _get_resolver(self) -> Any:
        """Lazily create the resolver."""
        if self._resolver is None:
            from amplifier_foundation.paths.resolution import get_amplifier_home
            from amplifier_foundation.sources import SimpleSourceResolver

            cache_dir = get_amplifier_home() / "cache"
            self._resolver = SimpleSourceResolver(cache_dir=cache_dir)
        return self._resolver

    def resolve(self) -> Path:
        """Resolve to cached git repository path (sync wrapper).

        Returns:
            Path to cached module directory.

        Raises:
            ModuleResolutionError: Clone/resolution failed.
        """
        from concurrent.futures import ThreadPoolExecutor

        from amplifier_foundation.exceptions import BundleNotFoundError

        resolver = self._get_resolver()

        def _run_async() -> Any:
            """Run the async resolver in a new event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(resolver.resolve(self.uri))
            finally:
                loop.close()

        try:
            try:
                asyncio.get_running_loop()
                # We're in async context - run in thread pool
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_async)
                    result = future.result()
            except RuntimeError:
                # No running loop - we can safely create one directly
                result = _run_async()

            return result.active_path
        except BundleNotFoundError as e:
            raise ModuleResolutionError(str(e)) from e

    def __repr__(self) -> str:
        return f"GitSource({self.uri})"


class FileSource:
    """Local filesystem path source."""

    def __init__(self, path: str | Path) -> None:
        """Initialize with file path."""
        if isinstance(path, str):
            if path.startswith("file://"):
                path = path[7:]
            path = Path(path)
        self.path = path.resolve()

    def resolve(self) -> Path:
        """Resolve to filesystem path."""
        if not self.path.exists():
            raise ModuleResolutionError(f"Module path not found: {self.path}")
        if not self.path.is_dir():
            raise ModuleResolutionError(f"Module path is not a directory: {self.path}")
        return self.path

    def __repr__(self) -> str:
        return f"FileSource({self.path})"


class PackageSource:
    """Installed Python package source."""

    def __init__(self, package_name: str) -> None:
        """Initialize with package name."""
        self.package_name = package_name

    def resolve(self) -> Path:
        """Resolve to installed package path."""
        try:
            dist = metadata.distribution(self.package_name)
            if dist.files:
                package_files = [
                    f
                    for f in dist.files
                    if not any(part.endswith((".dist-info", ".data")) for part in f.parts)
                ]
                if package_files:
                    return Path(str(dist.locate_file(package_files[0]))).parent
                return Path(str(dist.locate_file(dist.files[0]))).parent
            return Path(str(dist.locate_file("")))
        except metadata.PackageNotFoundError as e:
            raise ModuleResolutionError(
                f"Package '{self.package_name}' not installed. "
                f"Install with: uv pip install {self.package_name}"
            ) from e

    def __repr__(self) -> str:
        return f"PackageSource({self.package_name})"


# ============================================================================
# Fallback Resolver (from resolvers.py)
# ============================================================================


class FallbackResolver:
    """Fallback resolver using environment variables and installed packages.

    Resolution order (first match wins):
    1. Environment variable (AMPLIFIER_MODULE_<ID>)
    2. Source hint (from bundle config)
    3. Installed package
    """

    def resolve(
        self, module_id: str, source_hint: str | None = None
    ) -> GitSource | FileSource | PackageSource:
        """Resolve module through fallback chain.

        Args:
            module_id: Module identifier (e.g., "provider-anthropic").
            source_hint: Optional source URI hint.

        Returns:
            Source object.

        Raises:
            ModuleResolutionError: Module not found.
        """
        # Layer 1: Environment variable
        env_key = f"AMPLIFIER_MODULE_{module_id.upper().replace('-', '_')}"
        if env_value := os.getenv(env_key):
            logger.debug(f"[module:resolve] {module_id} -> env var ({env_value})")
            return self._parse_source(env_value)

        # Layer 2: Source hint (from bundle config)
        if source_hint:
            logger.debug(f"[module:resolve] {module_id} -> source_hint")
            return self._parse_source(source_hint)

        # Layer 3: Installed package (fallback)
        logger.debug(f"[module:resolve] {module_id} -> package")
        return self._resolve_package(module_id)

    def _parse_source(self, source: str) -> GitSource | FileSource | PackageSource:
        """Parse source URI into Source instance."""
        if source.startswith("git+"):
            return GitSource(source)
        if source.startswith("file://") or source.startswith("/") or source.startswith("."):
            return FileSource(source)
        # Assume package name
        return PackageSource(source)

    def _resolve_package(self, module_id: str) -> PackageSource:
        """Resolve to installed package using fallback logic."""
        # Try exact ID
        try:
            metadata.distribution(module_id)
            return PackageSource(module_id)
        except metadata.PackageNotFoundError:
            pass

        # Try convention
        convention_name = f"amplifier-module-{module_id}"
        try:
            metadata.distribution(convention_name)
            return PackageSource(convention_name)
        except metadata.PackageNotFoundError:
            pass

        # Both failed
        raise ModuleResolutionError(
            f"Module '{module_id}' not found\n\n"
            f"Resolution attempted:\n"
            f"  1. Environment: AMPLIFIER_MODULE_{module_id.upper().replace('-', '_')} (not set)\n"
            f"  2. Package: Tried '{module_id}' and '{convention_name}' (neither installed)\n\n"
            f"Suggestions:\n"
            f"  - Add source to bundle: source: git+https://...\n"
            f"  - Install package: uv pip install <package-name>"
        )


# ============================================================================
# App Module Resolver (from resolvers.py)
# ============================================================================


class AppModuleResolver:
    """Composes bundle resolver with fallback policy.

    This is app-layer POLICY: when a module isn't in the bundle,
    try to resolve it from environment or installed packages.
    """

    def __init__(
        self,
        bundle_resolver: Any,
        fallback_resolver: FallbackResolver | None = None,
    ) -> None:
        """Initialize with resolvers.

        Args:
            bundle_resolver: Foundation's BundleModuleResolver.
            fallback_resolver: Optional resolver for fallback.
        """
        self._bundle = bundle_resolver
        self._fallback = fallback_resolver or FallbackResolver()

    def resolve(self, module_id: str, source_hint: Any = None, profile_hint: Any = None) -> Any:
        """Resolve module ID with fallback policy.

        Policy: Try bundle first, fall back to environment/packages.
        """
        hint = profile_hint if profile_hint is not None else source_hint

        # Try bundle first (primary source)
        try:
            return self._bundle.resolve(module_id, hint)
        except ModuleNotFoundError:
            pass  # Fall through to fallback resolver

        # Try fallback resolver
        try:
            result = self._fallback.resolve(module_id, hint)
            logger.debug(f"Resolved '{module_id}' from fallback")
            return result
        except ModuleResolutionError as e:
            logger.debug(f"Fallback failed for '{module_id}': {e}")

        # Neither worked - raise informative error
        available = list(getattr(self._bundle, "_paths", {}).keys())
        raise ModuleNotFoundError(
            f"Module '{module_id}' not found in bundle or fallback. "
            f"Bundle contains: {available}. "
            f"Ensure the module is included in the bundle or install the provider."
        )

    def get_module_source(self, module_id: str) -> str | None:
        """Get module source path as string."""
        paths = getattr(self._bundle, "_paths", {})
        if module_id in paths:
            return str(paths[module_id])
        return None

    def __repr__(self) -> str:
        return f"AppModuleResolver(bundle={self._bundle}, fallback={self._fallback})"


# ============================================================================
# BundleInfo dataclass
# ============================================================================


@dataclass
class BundleInfo:
    """Minimal info about a bundle for API responses."""

    name: str
    description: str = ""
    uri: str | None = None
    path: Path | None = None
    source: str | None = None  # "builtin", "git", "local"


# ============================================================================
# BundleManager (from bundle_manager.py)
# ============================================================================


class BundleManager:
    """Thin wrapper around amplifier-foundation's bundle system.

    Responsibilities (app-layer policy):
    - Provide registry instance
    - Compose provider credentials at runtime
    - Auto-detect providers from environment

    NOT responsible for (foundation handles):
    - Bundle discovery, loading, parsing
    - Module activation and resolution
    - Session creation internals
    """

    def __init__(self) -> None:
        """Initialize bundle manager."""
        self._registry: BundleRegistry | None = None
        self._initialized = False

        # Two-tier cache for bundle reuse across sessions
        self._bundle_cache: dict[str, Any] = {}  # uri -> Bundle
        self._prepared_cache: dict[str, Any] = {}  # cache_key -> PreparedBundle

    async def initialize(self) -> None:
        """Initialize by importing foundation and creating registry."""
        if self._initialized:
            return

        try:
            from amplifier_foundation.registry import BundleRegistry

            self._registry = BundleRegistry()
            self._initialized = True
            logger.info("Bundle manager initialized with amplifier-foundation")

        except ImportError as e:
            logger.error(f"Failed to import amplifier-foundation: {e}")
            raise RuntimeError(
                "amplifier-foundation not available. Install with: pip install amplifier-foundation"
            ) from e

    @property
    def registry(self) -> BundleRegistry:
        """Get the bundle registry. Must call initialize() first."""
        if not self._registry:
            raise RuntimeError("BundleManager not initialized. Call initialize() first.")
        return self._registry

    async def load_and_prepare(
        self,
        bundle_name: str,
        behaviors: list[str] | None = None,
        provider_config: dict[str, Any] | None = None,
        working_directory: Path | None = None,
    ) -> Any:  # PreparedBundle
        """Load a bundle, compose behaviors, inject provider config, and prepare.

        Two-tier caching:
        - Level 1: Cache loaded bundles by URI
        - Level 2: Cache prepared bundles by (name, behaviors, provider_hash)
        """
        await self.initialize()

        from amplifier_foundation import Bundle

        # Generate cache key for prepared bundle (L2 cache check)
        cache_key = self._make_cache_key(bundle_name, behaviors, provider_config)

        # Check prepared cache first (fast path)
        if cache_key in self._prepared_cache:
            logger.debug(f"Using cached prepared bundle: {cache_key}")
            return self._prepared_cache[cache_key]

        # Load the base bundle (with L1 cache)
        bundle = await self._load_bundle_cached(bundle_name)
        logger.info(f"Loaded bundle: {bundle_name}")

        # Compose with behaviors if specified
        if behaviors:
            for behavior_name in behaviors:
                behavior_ref = behavior_name
                if ":" not in behavior_name and "/" not in behavior_name:
                    behavior_ref = f"foundation:behaviors/{behavior_name}"

                try:
                    behavior_bundle = await self._load_bundle_cached(behavior_ref)
                    bundle = bundle.compose(behavior_bundle)
                    logger.info(f"Composed behavior: {behavior_name}")
                except Exception as e:
                    logger.warning(f"Failed to load behavior '{behavior_name}': {e}")

        # Enable debug for event visibility
        debug_bundle = Bundle(
            name="server-debug-config",
            version="1.0.0",
            session={"debug": True, "raw_debug": True},
        )
        bundle = bundle.compose(debug_bundle)

        # Compose with provider config if specified
        if provider_config:
            provider_bundle = Bundle(
                name="app-provider-config",
                version="1.0.0",
                providers=[provider_config],
            )
            bundle = bundle.compose(provider_bundle)
            logger.info(f"Injected provider config: {provider_config.get('module')}")
        else:
            # Auto-detect provider from environment
            provider_bundle = await self._auto_detect_provider()
            if provider_bundle:
                bundle = bundle.compose(provider_bundle)

        # Prepare the bundle (expensive: downloads dependencies)
        prepared = await bundle.prepare()

        # Cache the prepared bundle (L2 cache)
        self._prepared_cache[cache_key] = prepared
        logger.info(f"Bundle prepared and cached: {cache_key}")

        return prepared

    async def _auto_detect_provider(self) -> Bundle | None:
        """Auto-detect ALL providers from environment variables.

        Returns:
            Provider Bundle with all detected providers, None if no API keys found.
        """
        from amplifier_foundation import Bundle

        provider_configs = [
            {
                "name": "anthropic",
                "env_var": "ANTHROPIC_API_KEY",
                "module": "provider-anthropic",
                "source": "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
            },
            {
                "name": "openai",
                "env_var": "OPENAI_API_KEY",
                "module": "provider-openai",
                "source": "git+https://github.com/microsoft/amplifier-module-provider-openai@main",
            },
            {
                "name": "azure-openai",
                "env_var": "AZURE_OPENAI_API_KEY",
                "module": "provider-azure-openai",
                "source": "git+https://github.com/microsoft/amplifier-module-provider-azure-openai@main",
            },
            {
                "name": "gemini",
                "env_var": "GOOGLE_API_KEY",
                "module": "provider-gemini",
                "source": "git+https://github.com/microsoft/amplifier-module-provider-gemini@main",
            },
        ]

        detected_providers: list[dict[str, Any]] = []

        for config in provider_configs:
            if os.getenv(config["env_var"]):
                detected_providers.append(
                    {
                        "module": config["module"],
                        "source": config["source"],
                        "config": {
                            "debug": True,
                            "raw_debug": True,
                        },
                    }
                )
                logger.info(f"Auto-detected {config['name']} provider ({config['env_var']} is set)")

        if not detected_providers:
            logger.warning(
                "No provider API keys found in environment. "
                "Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, "
                "AZURE_OPENAI_API_KEY, GOOGLE_API_KEY"
            )
            return None

        try:
            provider_bundle = Bundle(
                name="auto-providers",
                version="1.0.0",
                providers=detected_providers,
            )
            logger.info(f"Created provider bundle with {len(detected_providers)} provider(s)")
            return provider_bundle
        except Exception as e:
            logger.warning(f"Failed to create provider bundle: {e}")
            return None

    async def list_bundles(self) -> list[BundleInfo]:
        """List available bundles."""
        await self.initialize()

        bundles = [
            BundleInfo(
                name="foundation", description="Core foundation bundle with tools and agents"
            ),
            BundleInfo(
                name="amplifier-dev", description="Bundle for Amplifier ecosystem development"
            ),
        ]

        return bundles

    # =========================================================================
    # Bundle Installation & Management
    # =========================================================================

    def _get_bundles_dir(self) -> Path:
        """Get the bundles directory, creating if needed."""
        bundles_dir = Path.home() / ".amplifier-runtime" / "bundles"
        bundles_dir.mkdir(parents=True, exist_ok=True)
        return bundles_dir

    def _get_registry_file(self) -> Path:
        """Get the bundle registry file path."""
        return Path.home() / ".amplifier-runtime" / "bundle-registry.yaml"

    def _load_registry_data(self) -> dict[str, Any]:
        """Load the bundle registry data."""
        import yaml

        registry_file = self._get_registry_file()
        if registry_file.exists():
            with open(registry_file) as f:
                return yaml.safe_load(f) or {"bundles": {}}
        return {"bundles": {}}

    def _save_registry_data(self, data: dict[str, Any]) -> None:
        """Save the bundle registry data."""
        import yaml

        registry_file = self._get_registry_file()
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def name_from_source(self, source: str) -> str:
        """Extract bundle name from source URL."""
        clean = source.replace("git+", "").replace(".git", "")
        name = clean.rstrip("/").split("/")[-1] if "/" in clean else clean
        name = re.sub(r"^amplifier-bundle-", "", name)
        name = re.sub(r"^amplifier-", "", name)
        return name or "unknown"

    async def install_bundle(
        self, source: str, name: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Install a bundle from source. Yields progress events during installation."""
        import shutil

        derived_name = name or self.name_from_source(source)
        bundles_dir = self._get_bundles_dir()
        target_dir = bundles_dir / derived_name

        yield {"stage": "starting", "message": f"Installing bundle: {derived_name}"}

        try:
            if source.startswith("git+") or source.startswith("https://"):
                git_url = source.replace("git+", "")

                yield {"stage": "cloning", "message": f"Cloning from {git_url}"}

                if target_dir.exists():
                    shutil.rmtree(target_dir)

                result = subprocess.run(
                    ["git", "clone", "--depth", "1", git_url, str(target_dir)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Git clone failed: {result.stderr}")

                yield {"stage": "cloned", "message": "Repository cloned successfully"}

            elif Path(source).exists():
                source_path = Path(source).resolve()

                yield {"stage": "linking", "message": f"Linking local bundle from {source_path}"}

                if target_dir.exists() and target_dir.is_symlink():
                    target_dir.unlink()

                target_dir.symlink_to(source_path)

                yield {"stage": "linked", "message": "Local bundle linked"}

            else:
                raise ValueError(f"Invalid source: {source}")

            yield {"stage": "validating", "message": "Validating bundle structure"}

            bundle_file = target_dir / "bundle.md"
            if not bundle_file.exists():
                raise ValueError(f"No bundle.md found in {target_dir}")

            yield {"stage": "validated", "message": "Bundle structure valid"}

            yield {"stage": "registering", "message": "Registering bundle"}

            registry_data = self._load_registry_data()
            registry_data["bundles"][derived_name] = {
                "source": source,
                "path": str(target_dir),
                "installed_at": self._now_iso(),
            }
            self._save_registry_data(registry_data)

            yield {
                "stage": "completed",
                "message": f"Bundle '{derived_name}' installed successfully",
            }

        except Exception as e:
            yield {"stage": "error", "message": str(e)}
            raise

    def _now_iso(self) -> str:
        """Get current time in ISO format."""
        return datetime.now(UTC).isoformat()

    async def add_local_bundle(self, path: str, name: str) -> BundleInfo:
        """Register a local bundle path."""
        source_path = Path(path).resolve()

        if not source_path.exists():
            raise ValueError(f"Path does not exist: {path}")

        bundle_file = source_path / "bundle.md"
        if not bundle_file.exists():
            raise ValueError(f"No bundle.md found in {path}")

        registry_data = self._load_registry_data()
        registry_data["bundles"][name] = {
            "source": "local",
            "path": str(source_path),
            "added_at": self._now_iso(),
        }
        self._save_registry_data(registry_data)

        return BundleInfo(
            name=name,
            description=f"Local bundle from {path}",
            path=source_path,
            source="local",
        )

    async def remove_bundle(self, name: str) -> bool:
        """Remove a bundle registration."""
        registry_data = self._load_registry_data()

        if name not in registry_data["bundles"]:
            return False

        bundle_info = registry_data["bundles"][name]

        del registry_data["bundles"][name]
        self._save_registry_data(registry_data)

        # Optionally remove files (only for git-installed bundles)
        if bundle_info.get("source", "").startswith("git"):
            bundle_path = Path(bundle_info.get("path", ""))
            if bundle_path.exists() and bundle_path.is_relative_to(self._get_bundles_dir()):
                import shutil

                shutil.rmtree(bundle_path)

        return True

    async def get_bundle_info(self, name: str) -> BundleInfo:
        """Get information about a bundle."""
        if name in ("foundation", "amplifier-dev"):
            return BundleInfo(
                name=name,
                description=f"Built-in {name} bundle",
                source="builtin",
            )

        registry_data = self._load_registry_data()

        if name not in registry_data["bundles"]:
            raise ValueError(f"Bundle not found: {name}")

        bundle_data = registry_data["bundles"][name]

        return BundleInfo(
            name=name,
            description=f"Installed bundle: {name}",
            path=Path(bundle_data["path"]) if bundle_data.get("path") else None,
            source=bundle_data.get("source"),
            uri=bundle_data.get("source"),
        )

    async def _load_bundle_cached(self, bundle_uri: str) -> Any:  # Bundle
        """Load bundle with Level 1 caching."""
        if bundle_uri not in self._bundle_cache:
            from amplifier_foundation.registry import load_bundle

            bundle = await load_bundle(bundle_uri, registry=self._registry)
            self._bundle_cache[bundle_uri] = bundle
            logger.debug(f"Loaded and cached bundle: {bundle_uri}")
        else:
            logger.debug(f"Using cached bundle: {bundle_uri}")
        return self._bundle_cache[bundle_uri]

    def _make_cache_key(
        self,
        bundle_name: str,
        behaviors: list[str] | None,
        provider_config: dict[str, Any] | None,
    ) -> str:
        """Generate cache key for prepared bundle."""
        parts = [bundle_name]

        if behaviors:
            behaviors_str = ",".join(sorted(behaviors))
            behaviors_hash = hashlib.md5(behaviors_str.encode()).hexdigest()[:8]  # noqa: S324
            parts.append(behaviors_hash)
        else:
            parts.append("no-behaviors")

        if provider_config:
            config_str = json.dumps(provider_config, sort_keys=True)
            config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]  # noqa: S324
            parts.append(config_hash)
        else:
            parts.append("no-provider")

        return ":".join(parts)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "bundle_cache_size": len(self._bundle_cache),
            "prepared_cache_size": len(self._prepared_cache),
            "bundle_cache_keys": list(self._bundle_cache.keys()),
            "prepared_cache_keys": list(self._prepared_cache.keys()),
        }

    def invalidate_cache(self, bundle_uri: str | None = None) -> None:
        """Invalidate bundle cache."""
        if bundle_uri:
            self._bundle_cache.pop(bundle_uri, None)
            to_remove = [k for k in self._prepared_cache if k.startswith(bundle_uri + ":")]
            for key in to_remove:
                self._prepared_cache.pop(key)
            logger.info(f"Invalidated cache for bundle: {bundle_uri}")
        else:
            self._bundle_cache.clear()
            self._prepared_cache.clear()
            logger.info("Invalidated all bundle caches")

        try:
            if self._registry and hasattr(self._registry, "clear_cache"):
                self._registry.clear_cache()  # type: ignore[attr-defined]
                logger.debug("Cleared bundle registry cache")
        except Exception as e:
            logger.debug(f"Registry cache clear not available: {e}")


# ============================================================================
# Global singleton
# ============================================================================

bundle_manager = BundleManager()
