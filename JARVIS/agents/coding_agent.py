"""Coding Agent — generates code for a given subtask.

Input:  A subtask dict from the PlannerAgent.
Output: The generated code as a string (extracted from fenced code blocks
        if the LLM wraps it, otherwise the raw response).

The Coding Agent:
  - Extracts the first fenced code block (``` … ```) from the response.
  - Falls back to the full response text if no fence is found.
  - Stores both the raw LLM response and the extracted code in AgentResult.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from JARVIS.agents.agent_base import AgentBase, AgentError, AgentResult, AgentTask
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.coding")

_SYSTEM_PROMPT = """\
You are the Coding Agent for HESA, an AI assistant.
You receive a specific subtask and produce clean, working code to implement it.

Rules:
- Produce the most relevant code for the subtask (Python, QML, JSON, etc.).
- Wrap your code in a fenced code block with the appropriate language tag:
    ```python
    # code here
    ```
- If the subtask requires multiple files, separate them with headers like:
    ### filename.py
    ```python
    ...
    ```
- Write only the code and brief inline comments. No lengthy explanations outside the code block.
- Follow existing HESA conventions: use snake_case for Python, camelCase for QML.
- Do NOT include `pip install` commands or import statements for external packages
  that are not in the JARVIS requirements.txt.
"""


def _extract_code(text: str) -> str:
    """Return the content of the first fenced code block, or the raw text."""
    # Match ``` optionally followed by a language tag, then content, then ```
    pattern = re.compile(r"```(?:[a-zA-Z0-9_+\-]*)\n([\s\S]*?)```", re.MULTILINE)
    matches = pattern.findall(text)
    if matches:
        return "\n\n".join(m.strip() for m in matches)
    return text.strip()


class CodingAgent(AgentBase):
    name = "coding"
    system_prompt = _SYSTEM_PROMPT

    def __init__(self, progress_callback: Callable | None = None) -> None:
        super().__init__(progress_callback)

    def run(self, task: AgentTask) -> AgentResult:
        """Generate code for the subtask in task.description.

        ``task.context`` should contain any relevant prior outputs
        (e.g. the planner's subtask list, or error feedback from a tester).

        Returns an AgentResult whose ``parsed`` field is the extracted code string.
        """
        subtask_title = task.metadata.get("subtask_title", "subtask")
        self._emit_progress(f"Writing code for: {subtask_title}…")
        logger.info(
            "[CodingAgent] run_id=%s step=%d subtask=%r",
            task.run_id,
            task.step,
            task.description[:80],
        )

        # Build a focused prompt from the subtask + any error context
        user_prompt = task.description
        if task.context:
            user_prompt = f"Subtask:\n{task.description}\n\nAdditional context / previous error to fix:\n{task.context}"

        model_used = "unknown"
        try:
            response, tokens, elapsed, model_used = self._call_llm(user_prompt)
        except AgentError as exc:
            err = str(exc)
            self._log_to_queue(task, err, "error", 0.0, model_used="unknown")
            logger.error("[CodingAgent] LLM call failed: %s", err)
            return AgentResult(agent=self.name, status="error", output=err, error=err)

        code = _extract_code(response)
        self._emit_progress(f"Code generated ({len(code)} chars). Handing off to Testing Agent…")
        logger.info("[CodingAgent] Generated %d chars of code.", len(code))

        self._log_to_queue(task, response, "success", elapsed, model_used=model_used)
        return AgentResult(
            agent=self.name,
            status="success",
            output=response,
            parsed=code,  # extracted code string
            elapsed_ms=elapsed,
            tokens_estimate=tokens,
        )
