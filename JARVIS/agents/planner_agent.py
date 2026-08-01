"""Planner Agent — decomposes a user request into concrete subtasks.

Input:  A natural-language task description (e.g. "add a button that shows current time").
Output: A list of subtasks, each with an id, title, and description.

The agent enforces a JSON response format.  If the LLM returns malformed
JSON the planner falls back to a single-subtask plan so the pipeline can
continue rather than aborting.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from JARVIS.agents.agent_base import AgentBase, AgentError, AgentResult, AgentTask
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.planner")

_SYSTEM_PROMPT = """\
You are the Planner Agent for HESA, an AI assistant.
Your job is to decompose the user's request into 1-4 concrete, actionable subtasks.

You MUST respond with valid JSON in this exact format (no extra text outside the JSON):
{
  "subtasks": [
    {"id": 1, "title": "Short title", "description": "Clear description of what to do"},
    {"id": 2, "title": "Short title", "description": "Clear description of what to do"}
  ]
}

Rules:
- 1 subtask for trivial requests, up to 4 for complex ones.
- Each description must be specific enough that a coding agent can act on it.
- Do NOT include installation steps — assume the environment is already set up.
- Do NOT include deployment or documentation steps — those come later.
"""


def _extract_subtasks(text: str) -> list[dict[str, Any]]:
    """Parse the JSON block from the LLM response.  Falls back gracefully."""
    # Try to find a JSON object in the response
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in planner response")
    data = json.loads(match.group())
    subtasks = data.get("subtasks", [])
    if not isinstance(subtasks, list) or not subtasks:
        raise ValueError("subtasks list is empty or missing")
    # Normalise each entry
    normalised = []
    for i, st in enumerate(subtasks, start=1):
        normalised.append(
            {
                "id": int(st.get("id", i)),
                "title": str(st.get("title", f"Subtask {i}"))[:80],
                "description": str(st.get("description", "")),
            }
        )
    return normalised


class PlannerAgent(AgentBase):
    name = "planner"
    system_prompt = _SYSTEM_PROMPT

    def __init__(self, progress_callback: Callable | None = None) -> None:
        super().__init__(progress_callback)

    def run(self, task: AgentTask) -> AgentResult:
        """Break the task description into subtasks.

        Returns an AgentResult whose ``parsed`` field is list[dict].
        """
        self._emit_progress("Analysing request and building execution plan…")
        logger.info("[PlannerAgent] run_id=%s task=%r", task.run_id, task.description[:80])

        model_used = "unknown"
        try:
            response, tokens, elapsed, model_used = self._call_llm(task.description)
        except AgentError as exc:
            err = str(exc)
            self._log_to_queue(task, err, "error", 0.0, model_used="unknown")
            logger.error("[PlannerAgent] LLM call failed: %s", err)
            return AgentResult(agent=self.name, status="error", output=err, error=err)

        # Try to parse the JSON plan
        try:
            subtasks = _extract_subtasks(response)
            status = "success"
            parsed = subtasks
            self._emit_progress(f"Plan ready — {len(subtasks)} subtask(s) identified.")
            logger.info("[PlannerAgent] %d subtasks planned.", len(subtasks))
        except (ValueError, json.JSONDecodeError) as exc:
            # Graceful fallback: treat the whole request as one subtask
            logger.warning("[PlannerAgent] JSON parse failed (%s) — using single-subtask fallback.", exc)
            subtasks = [{"id": 1, "title": "Implement request", "description": task.description}]
            status = "success"
            parsed = subtasks
            self._emit_progress("Plan ready (fallback) — 1 subtask.")

        self._log_to_queue(task, response, status, elapsed, model_used=model_used)
        return AgentResult(
            agent=self.name,
            status=status,
            output=response,
            parsed=parsed,
            elapsed_ms=elapsed,
            tokens_estimate=tokens,
        )
