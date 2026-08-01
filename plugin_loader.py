"""Plugin Loader for JARVIS - Manifest validation and dynamic imports loading."""

from __future__ import annotations
import os
import json
import time
import importlib.util
from typing import Any
from plugin_registry import PluginRegistry, PluginInfo
from tool_manager import ToolManager
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("plugin_loader")

class PluginLoader:
    """Parses manifest.json specifications, checks permission bounds, and instantiates main classes."""

    def __init__(self) -> None:
        self.registry = PluginRegistry()
        self.tool_manager = ToolManager()

    def load_from_dir(self, plugin_dir: str) -> bool:
        """Read and validate the plugin files under the target directory."""
        manifest_path = os.path.join(plugin_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return False

        try:
            t0 = time.time()
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # 1. Manifest structure check
            required_keys = {"name", "version", "author", "plugin_entry"}
            if not all(key in manifest for key in required_keys):
                logger.error("Invalid manifest schema in: %s", manifest_path)
                return False

            # 2. Permissions check
            for perm in manifest.get("permissions", []):
                if perm not in self.tool_manager.granted_permissions:
                    logger.error("Blocked loading plugin '%s': requires ungranted permission '%s'", manifest["name"], perm)
                    return False

            # 3. Dynamic Import
            entry_file = os.path.join(plugin_dir, manifest["plugin_entry"])
            if not os.path.exists(entry_file):
                logger.error("Entry file not found: %s", entry_file)
                return False

            spec = importlib.util.spec_from_file_location(manifest["name"], entry_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                class_name = manifest.get("class_name", "PluginTool")
                if hasattr(module, class_name):
                    tool_cls = getattr(module, class_name)
                    tool_instance = tool_cls()

                    # Trigger tool initialization hooks
                    if hasattr(tool_instance, "initialize") and not tool_instance.initialize():
                        logger.error("Dynamic tool initialization failed for plugin '%s'", manifest["name"])
                        return False

                    # Register with ToolSDK manager
                    self.tool_manager.register_tool(tool_instance)

                    # Catalog metadata
                    info = PluginInfo(manifest, plugin_dir)
                    info.load_time_ms = (time.time() - t0) * 1000
                    info.status = "running"
                    self.registry.add(info)
                    return True
        except Exception as e:
            logger.error("Error loading plugin from %s: %s", plugin_dir, e)

        return False
