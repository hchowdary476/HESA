"""Abstract base class for all JARVIS agents.

Every agent:
  1. Has a ``name`` and a structured ``system_prompt``.
  2. Calls ``_call_llm()`` which delegates to AIOrchestrator — so
     whichever model is configured in JARVIS is used automatically.
  3. Writes a structured entry to the TaskQueue after every LLM call.
  4. Never swallows exceptions silently — it raises ``AgentError``
     with context so the orchestrator can decide whether to retry.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from JARVIS.agents.task_queue import TaskQueue
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.base")


class AgentError(RuntimeError):
    """Raised when an agent call fails after all retries."""


@dataclass
class AgentTask:
    """Inputs passed to an agent."""

    run_id: str
    step: int
    description: str  # The specific task for this agent
    context: str = ""  # Prior outputs / additional context
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Structured output from an agent."""

    agent: str
    status: str  # "success" | "error" | "retry"
    output: str  # Raw text output from LLM
    parsed: Any = None  # Structured parsed value (agent-specific)
    elapsed_ms: float = 0.0
    tokens_estimate: int = 0
    retry_count: int = 0
    error: str = ""


class AgentBase(ABC):
    """Base class for all JARVIS multi-agents."""

    name: str = "base"
    system_prompt: str = "You are a helpful AI agent."

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """
        Args:
            progress_callback: optional callable(agent_name, message) for
                               streaming progress updates to the QML bridge.
        """
        self._progress_callback = progress_callback

    def _emit_progress(self, message: str) -> None:
        if self._progress_callback:
            try:
                self._progress_callback(self.name, message)
            except Exception:
                pass

    def _call_llm(self, user_prompt: str) -> tuple[str, int, float, str]:
        """Call the active JARVIS LLM via AIOrchestrator.

        Returns:
            (response_text, token_estimate, elapsed_ms, model_used)
        """
        import concurrent.futures

        from JARVIS.config.manager import ConfigManager
        from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

        try:
            cfg = ConfigManager()
            cfg.load()
            timeout = float(cfg.get("ai.timeout", 30.0))
        except Exception:
            timeout = 30.0

        orch = AIOrchestrator()
        full_prompt = f"[SYSTEM]\n{self.system_prompt}\n\n[USER]\n{user_prompt}"
        start = time.perf_counter()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(orch.query_with_failover, full_prompt)
                try:
                    response = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError as exc:
                    elapsed = (time.perf_counter() - start) * 1000
                    raise AgentError(f"{self.name}: LLM call timed out after {timeout}s") from exc
        except Exception as exc:
            if "timed out" in str(exc):
                raise AgentError(f"{self.name}: LLM call timed out after {timeout}s") from exc
            raise AgentError(f"{self.name}: LLM call failed — {exc}") from exc
        elapsed = (time.perf_counter() - start) * 1000
        tokens = int((len(full_prompt.split()) + len(response.split())) * 1.3)
        model_used = getattr(orch, "active_model", "unknown")
        return response, tokens, elapsed, model_used

    def _log_to_queue(
        self,
        task: AgentTask,
        output: str,
        status: str,
        elapsed_ms: float,
        retry_count: int = 0,
        model_used: str = "",
    ) -> None:
        """Write this agent's result to the shared task log."""
        try:
            TaskQueue.append_entry(
                run_id=task.run_id,
                agent=self.name,
                step=task.step,
                input_text=task.description + ("\n\nContext:\n" + task.context if task.context else ""),
                output_text=output,
                elapsed_ms=elapsed_ms,
                status=status,
                retry_count=retry_count,
                model_used=model_used,
            )
        except Exception as exc:
            logger.warning("TaskQueue write failed for agent %s: %s", self.name, exc)

    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult:
        """Execute this agent on the given task. Must be implemented by subclasses."""
        ...
