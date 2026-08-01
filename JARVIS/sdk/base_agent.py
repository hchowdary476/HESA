"""Base class for building custom JARVIS AI Agents."""

from __future__ import annotations
import queue
import time
from typing import Any, Callable

class BaseAgent:
    """Base class that custom developer agents must inherit from to attach to the Cognitive Core."""

    def __init__(self, name: str, model: str = "Ollama-Qwen2") -> None:
        self.name = name
        self.model = model
        self.task_queue: queue.Queue = queue.Queue()
        self.tools: dict[str, Callable] = {}
        self.status = "IDLE"

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a custom tool callable."""
        self.tools[name] = func

    def run_task(self, prompt: str) -> str:
        """Execute task prompt. To be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement run_task method.")

    def run_loop(self) -> None:
        """Standard task consumer loop running in a daemon thread."""
        import threading
        def _loop():
            while True:
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    self.status = "BUSY"
                    try:
                        res = self.run_task(task["prompt"])
                        if task["callback"]:
                            task["callback"](res)
                    except Exception as e:
                        if task["callback"]:
                            task["callback"](f"Error: {e}")
                    self.status = "IDLE"
                    self.task_queue.task_done()
                time.sleep(0.1)
        threading.Thread(target=_loop, daemon=True).start()
