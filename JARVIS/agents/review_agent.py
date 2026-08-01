"""Review Agent — final quality gate before output reaches the user.

The Review Agent acts as a "CEO / Security" role:
  - It receives the original user request, all subtask outputs, and test results.
  - It checks that the outputs actually satisfy the request.
  - It flags any security concerns (e.g. shell injection, hardcoded secrets).
  - It produces the final ``summary`` shown to the user.

If the ReviewAgent returns ``approved=False``, the orchestrator marks the run
as "needs_review" but still returns all outputs for user inspection — it does
NOT automatically retry (a human should decide the next step).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Any

from JARVIS.agents.agent_base import AgentBase, AgentError, AgentResult, AgentTask
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.review")

_SYSTEM_PROMPT = """\
You are the Review Agent for HESA — acting as CEO and Security Reviewer.
You receive the original user request and all outputs produced by the planning and coding pipeline.

Your job:
1. Verify that the combined output actually fulfils the original request.
2. Identify any security concerns (hardcoded credentials, shell injection, unsafe file operations, etc.).
3. Provide a concise, user-facing summary of what was accomplished.

Respond ONLY with valid JSON in this exact format:
{
  "approved": true | false,
  "summary": "1-3 sentence plain English summary of what was built and whether it meets the request.",
  "concerns": ["concern 1", "concern 2"]
}

If there are no security concerns, set "concerns" to [].
Be brief. The user will see your "summary" directly in the HESA interface.
"""


@dataclass
class ReviewResult:
    approved: bool
    summary: str
    concerns: list[str] = field(default_factory=list)


def _extract_review(text: str) -> ReviewResult:
    """Parse the JSON verdict from the review agent's response."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        # Fallback: approve with the raw text as summary
        return ReviewResult(approved=True, summary=text[:500], concerns=[])
    try:
        data = json.loads(match.group())
        return ReviewResult(
            approved=bool(data.get("approved", True)),
            summary=str(data.get("summary", "Review complete.")),
            concerns=[str(c) for c in data.get("concerns", [])],
        )
    except Exception:
        return ReviewResult(approved=True, summary=text[:500], concerns=[])


class ReviewAgent(AgentBase):
    name = "review"
    system_prompt = _SYSTEM_PROMPT

    def __init__(self, progress_callback: Callable | None = None) -> None:
        super().__init__(progress_callback)

    def run(self, task: AgentTask) -> AgentResult:
        """Review all pipeline outputs and produce a final approval + summary.

        task.description  = original user request
        task.context      = JSON-serialised dict of all subtask outputs and test results
        task.metadata     = {"subtask_count": N, "all_passed": bool}

        Returns an AgentResult whose ``parsed`` field is a ``ReviewResult``.
        """
        self._emit_progress("Running final review and security check…")
        logger.info("[ReviewAgent] run_id=%s reviewing %d subtasks", task.run_id,
                    task.metadata.get("subtask_count", 0))

        user_prompt = (
            f"Original request:\n{task.description}\n\n"
            f"Pipeline outputs:\n{task.context}"
        )

        model_used = "unknown"
        try:
            response, tokens, elapsed, model_used = self._call_llm(user_prompt)
        except AgentError as exc:
            err = str(exc)
            fallback = ReviewResult(
                approved=True,
                summary="Review agent unavailable — outputs returned without final review.",
                concerns=["ReviewAgent LLM call failed; manual inspection recommended."],
            )
            self._log_to_queue(task, err, "error", 0.0, model_used="unknown")
            logger.error("[ReviewAgent] LLM call failed: %s", err)
            return AgentResult(
                agent=self.name, status="error", output=err,
                parsed=fallback, error=err,
            )

        review = _extract_review(response)

        if review.approved:
            self._emit_progress("✅ Review approved. Pipeline complete.")
            logger.info("[ReviewAgent] APPROVED. Concerns: %d", len(review.concerns))
            status = "success"
        else:
            self._emit_progress("⚠️ Review flagged issues — human review recommended.")
            logger.warning("[ReviewAgent] NOT APPROVED. Concerns: %s", review.concerns)
            status = "error"

        self._log_to_queue(task, response, status, elapsed, model_used=model_used)
        return AgentResult(
            agent=self.name,
            status=status,
            output=response,
            parsed=review,
            elapsed_ms=elapsed,
            tokens_estimate=tokens,
        )

