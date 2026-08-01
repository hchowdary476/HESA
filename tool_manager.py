"""ToolManager for JARVIS - Dynamic tool discovery, registry, permission validation, and health checks."""

from __future__ import annotations
import os
import json
import time
import importlib.util
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("tool_manager")

class ToolManager:
    """Manages discoverability, permissions authorization, execution safety, and plugins loading."""

    _instance: ToolManager | None = None

    def __new__(cls, *args, **kwargs) -> ToolManager:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.tools: dict[str, ToolBase] = {}
        self.enabled_tools: dict[str, bool] = {}
        
        # Simulated authorized permissions whitelist
        self.granted_permissions = {
            "filesystem", "network", "clipboard", "browser", 
            "microphone", "camera", "notifications", "settings"
        }

    def register_tool(self, tool: ToolBase) -> bool:
        """Initialize and register a tool into the system directory."""
        if not tool.initialize():
            logger.error("Failed to initialize tool: %s", tool.name)
            tool.is_healthy = False
            return False
        
        key = tool.name.lower().replace(" ", "_")
        self.tools[key] = tool
        self.enabled_tools[key] = True
        logger.info("Successfully registered tool: %s (v%s)", tool.name, tool.version)
        return True

    def disable_tool(self, name: str) -> None:
        key = name.lower().replace(" ", "_")
        if key in self.tools:
            self.enabled_tools[key] = False
            logger.info("Disabled tool: %s", name)

    def enable_tool(self, name: str) -> None:
        key = name.lower().replace(" ", "_")
        if key in self.tools:
            self.enabled_tools[key] = True
            logger.info("Enabled tool: %s", name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Evaluate permissions, validate arguments, execute, and verify rollback hooks on failures."""
        key = name.lower().replace(" ", "_")
        tool = self.tools.get(key)
        if not tool:
            return ToolResult(False, None, f"Tool '{name}' is not registered.")

        if not self.enabled_tools.get(key, False):
            return ToolResult(False, None, f"Tool '{name}' is currently disabled.")

        # 1. PERMISSION CHECK
        for perm in tool.permissions():
            if perm not in self.granted_permissions:
                logger.warning("Blocked tool '%s' execution: missing '%s' permission.", name, perm)
                return ToolResult(False, None, f"Permission Denied: Tool requires missing permission '{perm}'.")

        # 2. VALIDATION CHECK
        if not tool.validate(**kwargs):
            return ToolResult(False, None, f"Validation Block: Arguments failed syntax constraints for '{name}'.")

        # 3. EXECUTE
        t0 = time.time()
        tool.run_count += 1
        try:
            res = tool.execute(**kwargs)
            elapsed = (time.time() - t0) * 1000
            res.elapsed_ms = elapsed
            
            if res.success:
                tool.success_count += 1
                try:
                    from knowledge_graph import ProductionKnowledgeGraph
                    kg = ProductionKnowledgeGraph()
                    tool_node_id = f"tool:{key}"
                    kg.add_node(tool_node_id, "TOOL", tool.name, {"version": tool.version})
                    run_node_id = f"run:{key}:{int(t0)}"
                    kg.add_node(run_node_id, "TASK", f"Executed {tool.name}", {"success": True, "elapsed_ms": elapsed})
                    kg.add_edge(run_node_id, tool_node_id, "USES")
                except Exception:
                    pass
            else:
                tool.failure_count += 1
                logger.warning("Tool '%s' returned failure result. Triggering rollback hook.", name)
                tool.rollback()
            
            tool.total_time_ms += elapsed
            return res
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            tool.failure_count += 1
            tool.total_time_ms += elapsed
            logger.error("Execution error inside tool '%s': %s", name, e)
            tool.rollback()
            return ToolResult(False, None, f"Runtime Error: {e}", elapsed_ms=elapsed)

    def load_plugin(self, manifest_path: str) -> bool:
        """Dynamically load third-party tool plugins via manifest specification."""
        if not os.path.exists(manifest_path):
            logger.error("Manifest file not found: %s", manifest_path)
            return False

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            plugin_dir = os.path.dirname(manifest_path)
            entry_file = os.path.join(plugin_dir, manifest.get("plugin_entry", "plugin.py"))

            if not os.path.exists(entry_file):
                logger.error("Plugin entry file not found: %s", entry_file)
                return False

            # Verify permissions
            for req_perm in manifest.get("permissions", []):
                if req_perm not in self.granted_permissions:
                    logger.warning("Rejected plugin load '%s': requires ungranted permission '%s'", manifest.get("name"), req_perm)
                    return False

            spec = importlib.util.spec_from_file_location(manifest["name"], entry_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Assume module defines a Class that matches the manifest key or defines a standard PluginTool class
                class_name = manifest.get("class_name", "PluginTool")
                if hasattr(module, class_name):
                    tool_cls = getattr(module, class_name)
                    tool_instance = tool_cls()
                    return self.register_tool(tool_instance)
        except Exception as e:
            logger.error("Failed to load plugin manifest: %s, error: %s", manifest_path, e)

        return False

    def shutdown(self) -> None:
        """Call shutdown hook on all registered tools to release connections and handles."""
        for t in self.tools.values():
            try:
                t.shutdown()
            except Exception:
                pass
