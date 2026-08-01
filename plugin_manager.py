"""Plugin Manager for JARVIS - Dynamic marketplace installation, removals, and hot unloads."""

from __future__ import annotations
import os
import shutil
from typing import Any
from plugin_loader import PluginLoader
from plugin_registry import PluginRegistry
from tool_manager import ToolManager

class PluginManager:
    """Manages installation, walks directories to discover plugins, and handles resource unloads."""

    def __init__(self, plugins_root: str = "plugins") -> None:
        self.plugins_root = os.path.abspath(plugins_root)
        os.makedirs(self.plugins_root, exist_ok=True)
        self.loader = PluginLoader()
        self.registry = PluginRegistry()

    def discover_plugins(self) -> int:
        """Scan folder for any plugin manifest and load them."""
        count = 0
        if not os.path.exists(self.plugins_root):
            return count

        for entry in os.listdir(self.plugins_root):
            p_dir = os.path.join(self.plugins_root, entry)
            if os.path.isdir(p_dir):
                if self.loader.load_from_dir(p_dir):
                    count += 1
        return count

    def install_plugin(self, src_dir: str) -> bool:
        """Register, copy, and load plugin into the system."""
        if not os.path.exists(src_dir):
            return False

        manifest_path = os.path.join(src_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return False

        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            dest_name = manifest["name"].lower().replace(" ", "_")
            dest_dir = os.path.join(self.plugins_root, dest_name)
            
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(src_dir, dest_dir)

            return self.loader.load_from_dir(dest_dir)
        except Exception:
            return False

    def remove_plugin(self, name: str) -> bool:
        """Unload registered tool, clean registry, and delete local asset directories."""
        info = self.registry.get(name)
        if not info:
            return False

        t_mgr = ToolManager()
        key = name.lower().replace(" ", "_")
        t_mgr.tools.pop(key, None)
        t_mgr.enabled_tools.pop(key, None)

        try:
            if os.path.exists(info.path):
                shutil.rmtree(info.path)
            self.registry.remove(name)
            return True
        except Exception:
            return False

    def get_plugin_metrics(self) -> list[dict[str, Any]]:
        """Collect usage statistics for all registered plugins."""
        metrics = []
        for info in self.registry.registry.values():
            metrics.append({
                "name": info.name,
                "version": info.version,
                "status": info.status,
                "load_time_ms": info.load_time_ms,
                "run_count": info.run_count,
                "success_rate": 100.0 if info.run_count == 0 else (info.success_count / info.run_count * 100.0),
                "cpu_usage": info.cpu_usage,
                "memory_usage": info.memory_usage
            })
        return metrics
