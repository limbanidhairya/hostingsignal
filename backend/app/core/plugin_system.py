"""
HostingSignal Panel — Plugin System
====================================
Plugin loader, manifest parser, hook system, and event bus.
Plugin directory: /usr/local/hostingsignal/plugins/
"""
import os
import json
import importlib
import sys
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

PLUGIN_DIR = "/usr/local/hostingsignal/plugins"
PLUGIN_MANIFEST = "manifest.json"


class EventBus:
    """Pub/sub event system for plugin hooks."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """Register an event listener."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def emit(self, event: str, data: Any = None):
        """Emit an event to all listeners."""
        for callback in self._listeners.get(event, []):
            try:
                callback(data)
            except Exception as e:
                print(f"⚠️  Plugin event error [{event}]: {e}")

    def off(self, event: str, callback: Optional[Callable] = None):
        """Remove a listener."""
        if callback:
            self._listeners.get(event, []).remove(callback)
        else:
            self._listeners.pop(event, None)


# Global event bus
event_bus = EventBus()


AVAILABLE_HOOKS = [
    "panel.startup",
    "panel.shutdown",
    "website.created",
    "website.deleted",
    "website.ssl_issued",
    "database.created",
    "database.deleted",
    "email.account_created",
    "backup.started",
    "backup.completed",
    "security.alert",
    "user.login",
    "user.logout",
    "license.validated",
    "update.available",
    "cron.minutely",
    "cron.hourly",
    "cron.daily",
]


class PluginManifest:
    """Parsed plugin manifest."""

    def __init__(self, data: dict):
        self.name = data.get("name", "Unknown")
        self.version = data.get("version", "0.0.0")
        self.description = data.get("description", "")
        self.author = data.get("author", "Unknown")
        self.category = data.get("category", "utility")
        self.min_panel_version = data.get("min_panel_version", "1.0.0")
        self.entry_point = data.get("entry_point", "main.py")
        self.hooks = data.get("hooks", [])
        self.ui_extensions = data.get("ui_extensions", [])
        self.api_routes = data.get("api_routes", [])
        self.permissions = data.get("permissions", [])
        self.dependencies = data.get("dependencies", [])


class Plugin:
    """A loaded plugin instance."""

    def __init__(self, manifest: PluginManifest, path: str):
        self.manifest = manifest
        self.path = path
        self.module = None
        self.enabled = False

    def load(self):
        """Load the plugin module."""
        entry = os.path.join(self.path, self.manifest.entry_point)
        if not os.path.exists(entry):
            raise FileNotFoundError(f"Plugin entry point not found: {entry}")

        spec = importlib.util.spec_from_file_location(self.manifest.name, entry)
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[self.manifest.name] = self.module
        spec.loader.exec_module(self.module)
        self.enabled = True

        # Register hooks
        if hasattr(self.module, "register_hooks"):
            self.module.register_hooks(event_bus)

        print(f"  ✅ Plugin loaded: {self.manifest.name} v{self.manifest.version}")

    def unload(self):
        """Unload the plugin."""
        if hasattr(self.module, "cleanup"):
            self.module.cleanup()
        sys.modules.pop(self.manifest.name, None)
        self.enabled = False
        print(f"  🛑 Plugin unloaded: {self.manifest.name}")


class PluginManager:
    """Manages loading, unloading, and listing plugins."""

    def __init__(self, plugin_dir: str = PLUGIN_DIR):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Plugin] = {}

    def discover(self) -> List[PluginManifest]:
        """Discover installed plugins."""
        manifests = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)
            return manifests

        for item in os.listdir(self.plugin_dir):
            manifest_path = os.path.join(self.plugin_dir, item, PLUGIN_MANIFEST)
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path) as f:
                        data = json.load(f)
                    manifests.append(PluginManifest(data))
                except Exception as e:
                    print(f"⚠️  Failed to parse manifest: {manifest_path}: {e}")
        return manifests

    def load_all(self):
        """Load all discovered plugins."""
        print("🔌 Loading plugins...")
        for manifest in self.discover():
            try:
                path = os.path.join(self.plugin_dir, manifest.name.replace(" ", "_").lower())
                plugin = Plugin(manifest, path)
                plugin.load()
                self.plugins[manifest.name] = plugin
            except Exception as e:
                print(f"⚠️  Failed to load plugin '{manifest.name}': {e}")

    def get(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)

    def list_plugins(self) -> list:
        return [{"name": p.manifest.name, "version": p.manifest.version, "enabled": p.enabled, "category": p.manifest.category} for p in self.plugins.values()]

    def install(self, archive_path: str):
        """Install a plugin from a tar.gz archive."""
        import tarfile
        with tarfile.open(archive_path) as tar:
            tar.extractall(self.plugin_dir)
        print(f"📦 Plugin installed from {archive_path}")

    def uninstall(self, name: str):
        """Uninstall a plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.unload()
            import shutil
            shutil.rmtree(plugin.path, ignore_errors=True)
            del self.plugins[name]
            print(f"🗑️  Plugin '{name}' uninstalled")


# Singleton
plugin_manager = PluginManager()
