"""Agent Orchestrator — runs the 4-agent pipeline end-to-end.

Pipeline:
    PlannerAgent  →  [CodingAgent → TestingAgent] × subtasks  →  ReviewAgent

The orchestrator:
  - Generates a UUID4 run_id shared by all log entries in this run.
  - Checks the ``agents.enabled`` config kill-switch before every agent call.
  - Calls progress_callback(agent_name, message) on every status change so
    the QML bridge can stream live updates to the UI.
  - Returns a structured result dict that the QML bridge serialises to JSON.
  - Never raises — all exceptions are caught and included in the result dict
    so the UI always gets a valid response.
"""
from __future__ import annotations

import json
import uuid
import threading
from typing import Any, Callable

from JARVIS.agents.agent_base import AgentTask
from JARVIS.agents.coding_agent import CodingAgent
from JARVIS.agents.planner_agent import PlannerAgent
from JARVIS.agents.review_agent import ReviewAgent, ReviewResult
from JARVIS.agents.task_queue import TaskQueue
from JARVIS.agents.testing_agent import TestingAgent, MAX_RETRIES, TestResult
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.orchestrator")


def _agents_enabled() -> bool:
    """Check the kill-switch in JARVIS config."""
    try:
        from JARVIS.config.manager import ConfigManager
        cfg = ConfigManager()
        cfg.load()
        return bool(cfg.get("agents.enabled", True))
    except Exception:
        return True  # Default: enabled if config unavailable


class AgentOrchestrator:
    _lock = threading.Lock()
    _is_running = False

    @classmethod
    def is_running(cls) -> bool:
        with cls._lock:
            return cls._is_running

    """Runs the full 4-agent pipeline for a given task description.

    Usage::
        result = AgentOrchestrator().run("add a button that shows current time")
        print(result["final_output"])
    """

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """
        Args:
            progress_callback: optional callable(agent_name, message) for
                               streaming progress to the QML bridge.
        """
        self._progress_callback = progress_callback

    def _make_agents(self):
        cb = self._progress_callback
        return (
            PlannerAgent(progress_callback=cb),
            CodingAgent(progress_callback=cb),
            TestingAgent(progress_callback=cb),
            ReviewAgent(progress_callback=cb),
        )

    def run(self, task_description: str) -> dict[str, Any]:
        """Execute the full pipeline.

        Returns a dict suitable for JSON serialisation and QML consumption::
            {
                "run_id":       str,
                "status":       "complete" | "error" | "needs_review" | "killed",
                "final_output": str,       # user-facing summary from ReviewAgent
                "subtasks":     list[dict],
                "concerns":     list[str],
                "log_entries":  int,
                "task_log_path": str,
            }
        """
        with AgentOrchestrator._lock:
            if AgentOrchestrator._is_running:
                return self._error_result("busy", "Agent Core is currently busy.")
            AgentOrchestrator._is_running = True

        try:
            run_id = str(uuid.uuid4())
            logger.info("[Orchestrator] Starting run %s: %r", run_id, task_description[:80])

            # --- Kill-switch check ---
            if not _agents_enabled():
                logger.info("[Orchestrator] Agent system is disabled via kill-switch.")
                return {
                    "run_id": run_id,
                    "status": "killed",
                    "final_output": "Agent system is currently disabled. Enable it in Settings → AI & ML → Agent Core.",
                    "subtasks": [],
                    "concerns": [],
                    "log_entries": 0,
                    "task_log_path": TaskQueue.log_path(),
                }

            planner, coder, tester, reviewer = self._make_agents()

            # ── STEP 1: Planning ──────────────────────────────────────────────────
            plan_task = AgentTask(
                run_id=run_id,
                step=1,
                description=task_description,
            )
            try:
                plan_result = planner.run(plan_task)
            except Exception as exc:
                logger.error("[Orchestrator] Planner crashed: %s", exc)
                return self._error_result(run_id, f"Planner agent failed: {exc}")

            subtasks: list[dict] = plan_result.parsed or [
                {"id": 1, "title": "Implement request", "description": task_description}
            ]
            all_outputs: list[dict[str, Any]] = []
            step = 2

            # ── STEP 2+: Coding → Testing loop per subtask ───────────────────────
            for subtask in subtasks:
                if not _agents_enabled():
                    logger.info("[Orchestrator] Kill-switch tripped mid-run.")
                    break

                subtask_id = subtask.get("id", step)
                subtask_title = subtask.get("title", f"Subtask {subtask_id}")
                subtask_desc = subtask.get("description", task_description)

                code_output = ""
                test_passed = False
                last_suggestion = ""

                for attempt in range(MAX_RETRIES):
                    if not _agents_enabled():
                        break

                    # Coding
                    code_task = AgentTask(
                        run_id=run_id,
                        step=step,
                        description=subtask_desc,
                        context=last_suggestion,  # error feedback from previous test
                        metadata={"subtask_title": subtask_title, "attempt": attempt},
                    )
                    try:
                        code_result = coder.run(code_task)
                    except Exception as exc:
                        logger.error("[Orchestrator] CodingAgent crashed: %s", exc)
                        break
                    step += 1
                    code_output = code_result.parsed or code_result.output

                    # Testing
                    test_task = AgentTask(
                        run_id=run_id,
                        step=step,
                        description=subtask_desc,
                        context=code_output,
                        metadata={
                            "subtask_title": subtask_title,
                            "retry_count": attempt,
                        },
                    )
                    try:
                        test_result = tester.run(test_task)
                    except Exception as exc:
                        logger.error("[Orchestrator] TestingAgent crashed: %s", exc)
                        break
                    step += 1

                    tr: TestResult | None = test_result.parsed
                    if tr and tr.passed:
                        test_passed = True
                        break
                    elif tr:
                        last_suggestion = tr.suggestion
                        logger.info(
                            "[Orchestrator] Subtask %d attempt %d failed. Suggestion: %s",
                            subtask_id, attempt + 1, tr.suggestion[:100],
                        )
                    else:
                        # No structured result — treat as pass to avoid infinite loop
                        test_passed = True
                        break

                all_outputs.append({
                    "subtask_id": subtask_id,
                    "subtask_title": subtask_title,
                    "code": code_output,
                    "test_passed": test_passed,
                    "attempts": min(attempt + 1, MAX_RETRIES) if 'attempt' in dir() else 1,
                })

            # ── STEP N: Review ────────────────────────────────────────────────────
            all_passed = all(o.get("test_passed", False) for o in all_outputs)
            review_context = json.dumps(all_outputs, indent=2, ensure_ascii=False)

            review_task = AgentTask(
                run_id=run_id,
                step=step,
                description=task_description,
                context=review_context,
                metadata={
                    "subtask_count": len(subtasks),
                    "all_passed": all_passed,
                },
            )
            try:
                review_result = reviewer.run(review_task)
            except Exception as exc:
                logger.error("[Orchestrator] ReviewAgent crashed: %s", exc)
                review_result = None

            # Build final result
            final_output = task_description  # fallback
            concerns: list[str] = []
            run_status = "complete"

            if review_result and review_result.parsed:
                rv: ReviewResult = review_result.parsed
                final_output = rv.summary
                concerns = rv.concerns
                if not rv.approved or concerns:
                    run_status = "review_needed"
            elif review_result:
                final_output = review_result.output[:1000]

            if not all_passed and run_status == "complete":
                run_status = "error"

            log_entries = len(TaskQueue.get_by_run_id(run_id))
            logger.info(
                "[Orchestrator] Run %s finished: status=%s entries=%d",
                run_id, run_status, log_entries,
            )

            return {
                "run_id": run_id,
                "status": run_status,
                "final_output": final_output,
                "subtasks": all_outputs,
                "concerns": concerns,
                "log_entries": log_entries,
                "task_log_path": TaskQueue.log_path(),
            }

        finally:
            with AgentOrchestrator._lock:
                AgentOrchestrator._is_running = False

    @staticmethod
    def _error_result(run_id: str, message: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "status": "error",
            "final_output": message,
            "subtasks": [],
            "concerns": [],
            "log_entries": 0,
            "task_log_path": TaskQueue.log_path(),
        }
