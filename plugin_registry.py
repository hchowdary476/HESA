"""Plugin Registry for JARVIS - Cataloging loaded plugins and tracking usage metrics."""

from __future__ import annotations
from typing import Any

class PluginInfo:
    """Telemetries and manifest profiles for a single plugin."""

    def __init__(self, manifest: dict[str, Any], path: str) -> None:
        self.name = manifest["name"]
        self.version = manifest["version"]
        self.author = manifest["author"]
        self.category = manifest.get("category", "Utilities")
        self.permissions = manifest.get("permissions", [])
        self.dependencies = manifest.get("dependencies", [])
        self.entry_point = manifest.get("plugin_entry", "plugin.py")
        self.class_name = manifest.get("class_name", "PluginTool")
        self.path = path
        self.status = "registered"
        
        # Telemetry metrics
        self.load_time_ms = 0.0
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.cpu_usage = 0.0
        self.memory_usage = 1.0  # Simulated MBs usage
        self.last_error = ""


class PluginRegistry:
    """Catalog database holding metadata state for all plugins in memory."""

    _instance: PluginRegistry | None = None

    def __new__(cls, *args, **kwargs) -> PluginRegistry:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.registry: dict[str, PluginInfo] = {}

    def add(self, info: PluginInfo) -> None:
        self.registry[info.name.lower()] = info

    def get(self, name: str) -> PluginInfo | None:
        return self.registry.get(name.lower())

    def remove(self, name: str) -> None:
        self.registry.pop(name.lower(), None)
