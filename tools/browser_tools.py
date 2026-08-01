"""JARVIS Tool SDK - Web browser page opener tools."""

from __future__ import annotations
import webbrowser
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class BrowserOpenTool(ToolBase):
    """Safe URL launcher supporting edge, chrome and default clients."""

    def __init__(self) -> None:
        super().__init__("Browser Open Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "url" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url", "")
        try:
            # Safe url validation
            if not url.startswith(("http://", "https://")):
                return ToolResult(False, None, "Invalid protocol prefix. Only HTTP/HTTPS is allowed.")
            
            webbrowser.open(url)
            return ToolResult(True, {"url": url, "launched": True})
        except Exception as e:
            return ToolResult(False, None, f"Failed to load URL: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["browser"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 8.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
