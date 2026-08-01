"""JARVIS Tool SDK - Document formats and office parsers."""

from __future__ import annotations
import json
import os
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class JSONDocumentTool(ToolBase):
    """Safely reads and formats JSON database parameters."""

    def __init__(self) -> None:
        super().__init__("JSON Document Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "file_path" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("file_path", "")
        if not os.path.exists(path):
            return ToolResult(False, None, f"Document path '{path}' does not exist.")
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ToolResult(True, {"data": data, "keys": list(data.keys()) if isinstance(data, dict) else []})
        except Exception as e:
            return ToolResult(False, None, f"JSON load error: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 5.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
