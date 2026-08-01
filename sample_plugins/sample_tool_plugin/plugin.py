"""Sample tool plugin entry point for JARVIS."""

from __future__ import annotations
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class PluginTool(ToolBase):
    """Demonstration plugin tool class inheriting from ToolBase."""

    def __init__(self) -> None:
        super().__init__("Sample Tool Plugin", "1.0")

    def validate(self, **kwargs) -> bool:
        return True

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(True, {"message": "Hello from the Sandbox Sample Plugin, sir."})

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem"]

    def metrics(self) -> dict[str, Any]:
        return {"run_time": 2.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
