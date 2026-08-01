"""Base class for building custom JARVIS tools."""

from __future__ import annotations
from typing import Callable

class BaseTool:
    """Wrapper that developers can use to define new functions for multi-agent use."""

    def __init__(self, name: str, description: str, func: Callable) -> None:
        self.name = name
        self.description = description
        self.func = func

    def execute(self, *args, **kwargs) -> Any:
        """Trigger the tool execution wrapper."""
        return self.func(*args, **kwargs)
