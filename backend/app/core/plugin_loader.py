"""Plugin Loader Engine — Core plugin system for HostingSignal Panel"""
import os
import sys
import json
import importlib
import importlib.util
import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PLUGIN_DIR = "/usr/local/hostingsignal/plugins"
REQUIRED_MANIFEST_FIELDS = ["name", "version", "entry_point"]


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    category: str = "utility"
    min_panel_version: str = "1.0.0"
    entry_point: str = "main.py"
    hooks: List[str] = field(default_factory=list)
    ui_extensions: List[dict] = field(default_factory=list)
    api_routes: List[dict] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class LoadedPlugin:
    manifest: PluginManifest
    module: Any = None
    path: str = ""
    active: bool = False
    error: Optional[str] = None


class EventBus:
    """Publish-subscribe event system for plugin hooks."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._plugin_handlers: Dict[str, List[str]] = {}  # plugin_name -> [event_names]

    def on(self, event: str, handler: Callable, plugin_name: str = None):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        if plugin_name:
            if plugin_name not in self._plugin_handlers:
                self._plugin_handlers[plugin_name] = []
            self._plugin_handlers[plugin_name].append(event)
        logger.debug(f"Handler registered for event: {event}")

    def off(self, event: str, handler: Callable):
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def remove_plugin_handlers(self, plugin_name: str):
        """Remove all handlers registered by a specific plugin."""
        if plugin_name in self._plugin_handlers:
            for event in self._plugin_handlers[plugin_name]:
                if event in self._handlers:
                    self._handlers[event] = []
            del self._plugin_handlers[plugin_name]

    async def emit(self, event: str, data: dict = None):
        if event not in self._handlers:
            return
        for handler in self._handlers[event]:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    await handler(data or {})
                else:
                    handler(data or {})
            except Exception as e:
                logger.error(f"Plugin handler error for event '{event}': {e}")
                traceback.print_exc()

    def list_events(self) -> List[str]:
        return list(self._handlers.keys())

    def handler_count(self, event: str) -> int:
        return len(self._handlers.get(event, []))


class PluginLoader:
    """Manages the lifecycle of plugins: load, activate, deactivate, uninstall."""

    def __init__(self, plugin_dir: str = PLUGIN_DIR):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, LoadedPlugin] = {}
        self.event_bus = EventBus()
        os.makedirs(plugin_dir, exist_ok=True)

    def discover_plugins(self) -> List[str]:
        """Find all plugin directories with valid manifest.json."""
        discovered = []
        if not os.path.exists(self.plugin_dir):
            return discovered

        for entry in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, entry)
            manifest_path = os.path.join(plugin_path, "manifest.json")
            if os.path.isdir(plugin_path) and os.path.exists(manifest_path):
                discovered.append(entry)
        return discovered

    def parse_manifest(self, plugin_name: str) -> Optional[PluginManifest]:
        manifest_path = os.path.join(self.plugin_dir, plugin_name, "manifest.json")
        if not os.path.exists(manifest_path):
            logger.error(f"No manifest.json for plugin: {plugin_name}")
            return None

        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)

            for field_name in REQUIRED_MANIFEST_FIELDS:
                if field_name not in data:
                    logger.error(f"Missing required field '{field_name}' in {plugin_name}/manifest.json")
                    return None

            return PluginManifest(**{k: v for k, v in data.items() if k in PluginManifest.__dataclass_fields__})
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {plugin_name}/manifest.json: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing manifest for {plugin_name}: {e}")
            return None

    def load_plugin(self, plugin_name: str) -> bool:
        """Load a plugin module without activating it."""
        if plugin_name in self.plugins and self.plugins[plugin_name].active:
            logger.warning(f"Plugin {plugin_name} is already loaded and active")
            return True

        manifest = self.parse_manifest(plugin_name)
        if not manifest:
            return False

        plugin_path = os.path.join(self.plugin_dir, plugin_name)
        entry_file = os.path.join(plugin_path, manifest.entry_point)

        if not os.path.exists(entry_file):
            logger.error(f"Entry point not found: {entry_file}")
            self.plugins[plugin_name] = LoadedPlugin(
                manifest=manifest, path=plugin_path, error=f"Entry point not found: {manifest.entry_point}"
            )
            return False

        try:
            spec = importlib.util.spec_from_file_location(f"hs_plugin_{manifest.name}", entry_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"hs_plugin_{manifest.name}"] = module
            spec.loader.exec_module(module)

            self.plugins[plugin_name] = LoadedPlugin(
                manifest=manifest, module=module, path=plugin_path, active=False
            )
            logger.info(f"Plugin loaded: {plugin_name} v{manifest.version}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            traceback.print_exc()
            self.plugins[plugin_name] = LoadedPlugin(
                manifest=manifest, path=plugin_path, error=str(e)
            )
            return False

    async def activate_plugin(self, plugin_name: str) -> bool:
        """Activate a loaded plugin by calling its register_hooks function."""
        if plugin_name not in self.plugins:
            if not self.load_plugin(plugin_name):
                return False

        plugin = self.plugins[plugin_name]
        if plugin.active:
            return True
        if plugin.error:
            logger.error(f"Cannot activate {plugin_name}: {plugin.error}")
            return False

        try:
            register_fn = getattr(plugin.module, "register_hooks", None)
            if register_fn:
                import asyncio
                if asyncio.iscoroutinefunction(register_fn):
                    await register_fn(self.event_bus)
                else:
                    register_fn(self.event_bus)

            plugin.active = True
            await self.event_bus.emit("plugin.activated", {"plugin": plugin_name, "version": plugin.manifest.version})
            logger.info(f"Plugin activated: {plugin_name}")
            return True
        except Exception as e:
            plugin.error = str(e)
            logger.error(f"Failed to activate {plugin_name}: {e}")
            traceback.print_exc()
            return False

    async def deactivate_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.plugins:
            return False

        plugin = self.plugins[plugin_name]
        if not plugin.active:
            return True

        try:
            cleanup_fn = getattr(plugin.module, "cleanup", None)
            if cleanup_fn:
                import asyncio
                if asyncio.iscoroutinefunction(cleanup_fn):
                    await cleanup_fn()
                else:
                    cleanup_fn()

            self.event_bus.remove_plugin_handlers(plugin_name)
            plugin.active = False
            await self.event_bus.emit("plugin.deactivated", {"plugin": plugin_name})
            logger.info(f"Plugin deactivated: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating {plugin_name}: {e}")
            return False

    async def uninstall_plugin(self, plugin_name: str) -> bool:
        """Deactivate and remove a plugin."""
        await self.deactivate_plugin(plugin_name)
        plugin_path = os.path.join(self.plugin_dir, plugin_name)
        if os.path.exists(plugin_path):
            import shutil
            shutil.rmtree(plugin_path)

        if plugin_name in self.plugins:
            mod_name = f"hs_plugin_{self.plugins[plugin_name].manifest.name}"
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            del self.plugins[plugin_name]

        logger.info(f"Plugin uninstalled: {plugin_name}")
        return True

    async def load_all(self):
        """Discover and activate all plugins."""
        discovered = self.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins")
        for plugin_name in discovered:
            self.load_plugin(plugin_name)
            await self.activate_plugin(plugin_name)

    def get_status(self) -> List[dict]:
        return [{
            "name": name,
            "version": p.manifest.version,
            "description": p.manifest.description,
            "author": p.manifest.author,
            "category": p.manifest.category,
            "active": p.active,
            "error": p.error,
            "hooks": p.manifest.hooks,
            "ui_extensions": p.manifest.ui_extensions,
        } for name, p in self.plugins.items()]

    def get_ui_extensions(self) -> List[dict]:
        """Get all UI extensions from active plugins."""
        extensions = []
        for name, plugin in self.plugins.items():
            if plugin.active:
                for ext in plugin.manifest.ui_extensions:
                    extensions.append({**ext, "plugin": name})
        return extensions

    def get_api_routes(self) -> List[dict]:
        """Get all API routes from active plugins."""
        routes = []
        for name, plugin in self.plugins.items():
            if plugin.active:
                for route in plugin.manifest.api_routes:
                    routes.append({**route, "plugin": name})
        return routes


# Singleton instance
plugin_loader = PluginLoader()
