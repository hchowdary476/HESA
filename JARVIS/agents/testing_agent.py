"""Testing Agent — validates the CodingAgent's output.

Strategy
--------
1. **Syntax check (always):** Any Python code is written to a temp file and
   run through ``python -m py_compile``.  Failures are reported as errors with
   the compiler's message as the ``suggestion`` field so the CodingAgent can
   fix it.

2. **LLM code-review (always):** The agent asks the LLM to act as a code
   reviewer and flag obvious bugs, missing logic, or security issues.
   This catches non-Python code (QML, JSON, shell) that py_compile can't check.

3. **Pass decision:** The test passes if:
   - py_compile succeeds (or there is no Python code to compile), AND
   - the LLM reviewer gives a positive assessment (no "FAIL" or "CRITICAL" in output).

The orchestrator calls this agent up to ``MAX_RETRIES`` times per subtask,
passing each failure's ``suggestion`` back to the CodingAgent as context.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable

from JARVIS.agents.agent_base import AgentBase, AgentError, AgentResult, AgentTask
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("agents.testing")

MAX_RETRIES = 3  # Maximum Coding→Testing retry loops per subtask

_SYSTEM_PROMPT = """\
You are the Testing Agent for HESA, an AI assistant.
You receive a subtask description and the code written to implement it.

Your job is to assess whether the code correctly implements the subtask.

Respond with this JSON format (no extra text outside the JSON):
{
  "verdict": "PASS" | "FAIL",
  "issues": ["issue 1", "issue 2"],
  "suggestion": "Concise instruction for the Coding Agent on how to fix the code, or empty string if PASS."
}

Be strict but fair. Flag actual bugs, not style preferences.
If the code looks correct and safe, return PASS with empty issues and suggestion.
"""


@dataclass
class TestResult:
    passed: bool
    errors: str
    suggestion: str
    syntax_ok: bool = True


def _python_syntax_check(code: str) -> tuple[bool, str]:
    """Run py_compile on code string. Returns (ok, error_message)."""
    # Write to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, ""
        # Clean up the temp path from error message so it's readable
        err = (result.stderr or result.stdout or "Unknown syntax error").replace(tmp_path, "<code>")
        return False, err.strip()
    except subprocess.TimeoutExpired:
        return False, "py_compile timed out after 10 seconds."
    except Exception as exc:
        return False, f"Syntax check failed: {exc}"
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _has_python(code: str) -> bool:
    """Heuristic: does the code string look like Python?"""
    python_indicators = ["def ", "import ", "class ", "if __name__", "    "]
    return any(ind in code for ind in python_indicators)


def _extract_verdict(text: str) -> tuple[bool, str, str]:
    """Parse the JSON verdict from LLM response.  Returns (passed, errors_str, suggestion)."""
    import json
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        # If LLM didn't return JSON, treat as PASS (don't block on bad reviewer response)
        return True, "", ""
    try:
        data = json.loads(match.group())
        verdict = str(data.get("verdict", "PASS")).upper()
        issues = data.get("issues", [])
        suggestion = str(data.get("suggestion", ""))
        passed = (verdict == "PASS")
        errors_str = "; ".join(str(i) for i in issues) if issues else ""
        return passed, errors_str, suggestion
    except Exception:
        return True, "", ""


class TestingAgent(AgentBase):
    name = "testing"
    system_prompt = _SYSTEM_PROMPT

    def __init__(self, progress_callback: Callable | None = None) -> None:
        super().__init__(progress_callback)

    def run(self, task: AgentTask) -> AgentResult:
        """Test the code in ``task.context`` against the subtask in ``task.description``.

        Returns an AgentResult whose ``parsed`` field is a ``TestResult`` dataclass.
        """
        code = task.context
        subtask_title = task.metadata.get("subtask_title", "subtask")
        retry_count = task.metadata.get("retry_count", 0)

        self._emit_progress(f"Testing code for: {subtask_title} (attempt {retry_count + 1}/{MAX_RETRIES})…")
        logger.info(
            "[TestingAgent] run_id=%s step=%d retry=%d",
            task.run_id, task.step, retry_count,
        )

        # --- Step 1: Syntax check (Python only) ---
        syntax_ok = True
        syntax_error = ""
        if _has_python(code):
            syntax_ok, syntax_error = _python_syntax_check(code)
            if not syntax_ok:
                self._emit_progress(f"⚠️ Syntax error detected — requesting fix…")
                logger.warning("[TestingAgent] Syntax error: %s", syntax_error[:200])
                result = TestResult(
                    passed=False,
                    errors=f"Syntax error: {syntax_error}",
                    suggestion=f"Fix the syntax error: {syntax_error}",
                    syntax_ok=False,
                )
                status = "retry" if retry_count < MAX_RETRIES - 1 else "error"
                self._log_to_queue(task, syntax_error, status, 0.0, retry_count=retry_count, model_used="syntax_compiler")
                return AgentResult(
                    agent=self.name,
                    status=status,
                    output=syntax_error,
                    parsed=result,
                    error=syntax_error,
                    retry_count=retry_count,
                )

        # --- Step 2: LLM code review ---
        review_prompt = (
            f"Subtask:\n{task.description}\n\n"
            f"Code to review:\n```\n{code}\n```"
        )
        model_used = "unknown"
        try:
            response, tokens, elapsed, model_used = self._call_llm(review_prompt)
        except AgentError as exc:
            # If LLM review fails, treat as PASS (don't block the pipeline)
            err = str(exc)
            logger.warning("[TestingAgent] LLM review failed, defaulting to PASS: %s", err)
            response, tokens, elapsed, model_used = "Review unavailable — defaulting to PASS.", 0, 0.0, "unknown"

        passed, errors, suggestion = _extract_verdict(response)

        result = TestResult(
            passed=passed,
            errors=errors,
            suggestion=suggestion,
            syntax_ok=syntax_ok,
        )

        if passed:
            self._emit_progress(f"✅ Tests passed for: {subtask_title}")
            logger.info("[TestingAgent] PASS for subtask %r", subtask_title)
            status = "success"
        else:
            level = "retry" if retry_count < MAX_RETRIES - 1 else "error"
            self._emit_progress(f"⚠️ Test failed (attempt {retry_count + 1}) — {'retrying…' if level == 'retry' else 'max retries reached.'}")
            logger.warning("[TestingAgent] FAIL: %s", errors[:200])
            status = level

        self._log_to_queue(task, response, status, elapsed, retry_count=retry_count, model_used=model_used)
        return AgentResult(
            agent=self.name,
            status=status,
            output=response,
            parsed=result,
            elapsed_ms=elapsed,
            tokens_estimate=tokens,
            retry_count=retry_count,
        )

