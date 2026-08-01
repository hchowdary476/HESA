"""Common Abstract Base Class (ABC) for all tools in the JARVIS SDK."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from tool_result import ToolResult

class ToolBase(ABC):
    """Abstract interface enforcing standardized behaviors across all agent capabilities."""

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time_ms = 0.0
        self.is_healthy = True

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool core logic."""
        pass

    @abstractmethod
    def validate(self, **kwargs) -> bool:
        """Validate input arguments before execution."""
        pass

    @abstractmethod
    def rollback(self) -> bool:
        """Revert changes if execution failed or was aborted."""
        pass

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Report current health telemetry."""
        pass

    @abstractmethod
    def permissions(self) -> list[str]:
        """Declare permissions needed to run (e.g. 'filesystem', 'network')."""
        pass

    @abstractmethod
    def metrics(self) -> dict[str, Any]:
        """Expose run duration and usage details."""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """Run setup tasks, check executables, or map dependencies on startup."""
        pass

    @abstractmethod
    def shutdown(self) -> bool:
        """Clean up handles, close sockets, and release resources on shutdown."""
        pass
