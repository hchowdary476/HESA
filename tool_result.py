"""Standardized ToolResult object returned by every tool in the JARVIS SDK."""

from __future__ import annotations
import time
from typing import Any

class ToolResult:
    """Represents the outcome of a tool execution, including timing and execution logs."""

    def __init__(self, success: bool, output: Any, error: str = "", elapsed_ms: float = 0.0) -> None:
        self.success = success
        self.output = output
        self.error = error
        self.elapsed_ms = elapsed_ms
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp
        }
