"""Plugin API for JARVIS - Safe core interface access for third-party plug-in scripts."""

from __future__ import annotations
from typing import Any
from tool_manager import ToolManager
from tool_base import ToolBase
from JARVIS.core.memory.knowledge_graph import KnowledgeGraph
from JARVIS.core.system.utils.jarvis_logging import get_logger

class PluginAPI:
    """Controlled abstraction interface providing safe core system capabilities exposure."""

    def __init__(self) -> None:
        self.tool_manager = ToolManager()
        self.kg = KnowledgeGraph()
        self.logger = get_logger("plugin_api")

    def register_tool(self, tool: ToolBase) -> bool:
        """Expose dynamic tool registries to plugin tools."""
        return self.tool_manager.register_tool(tool)

    def add_memory_node(self, node_id: str, node_type: str, label: str, properties: dict | None = None) -> None:
        """Allow additions to Knowledge Graph nodes."""
        self.kg.add_node(node_id, node_type, label, properties)

    def get_memory_context(self, query: str) -> str:
        """Expose search lookups to the Knowledge Graph context matching."""
        return self.kg.get_context_for_query(query)

    def log_notification(self, message: str, level: str = "info") -> None:
        """Allow plugins to print debug parameters to standard log outputs."""
        if level.lower() == "error":
            self.logger.error("[Plugin] %s", message)
        else:
            self.logger.info("[Plugin] %s", message)
