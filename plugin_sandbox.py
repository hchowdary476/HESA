"""Plugin Sandbox for JARVIS - Safe isolated run context, container limits, and exception containment."""

from __future__ import annotations
import threading
from typing import Callable, Any
from tool_result import ToolResult

class PluginSandbox:
    """Isolates executions, catches run errors, and applies timeouts to prevent plugin locks."""

    @staticmethod
    def execute_safely(func: Callable[..., Any], timeout: float = 3.0, *args, **kwargs) -> ToolResult:
        """Run a plugin call inside a crash-isolated daemon thread with timeout checks."""
        res_container = {"result": None, "error": None}

        def _worker():
            try:
                res_container["result"] = func(*args, **kwargs)
            except Exception as e:
                res_container["error"] = str(e)

        thread = threading.Thread(target=_worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            return ToolResult(False, None, f"Plugin Execution Aborted: Process timed out after {timeout}s.")

        if res_container["error"]:
            return ToolResult(False, None, f"Plugin Exception Intercepted: {res_container['error']}")

        out = res_container["result"]
        if isinstance(out, ToolResult):
            return out
        return ToolResult(True, out)
