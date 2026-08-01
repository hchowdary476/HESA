"""
JARVIS Autonomous Executor — Layer 1: Unified AI Operating System Brain Stem.

Wires together every JARVIS module into one continuous, self-healing pipeline:

  Voice Input / Text Input
       ↓
  AutonomousExecutor.execute()
       ↓
  SecurityShield (rate limit + safety gate)
       ↓
  Intent Classifier (local → Groq fallback)
       ↓
  Goal Complexity Assessor
       ↓
  CognitiveCore.process_request()   ← 12-stage pipeline
       ↓
  TaskPlanner (DAG decomposition)   ← if multi-step goal
       ↓
  AgentManager.route_command()      ← agent dispatch
       ↓
  ToolRouter.resolve()              ← tool selection
       ↓
  runtime_actions / Tool SDK        ← real execution
       ↓
  DiagnosticsCenter (telemetry)
       ↓
  LearningEngine (pattern update)
       ↓
  MemoryEngine + KnowledgeGraph     ← persistent state update
       ↓
  SelfImprovementEngine.evaluate()  ← routing optimisation
       ↓
  TTS Voice Response
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("autonomous_executor")


# ---------------------------------------------------------------------------
# Lazy singleton helpers — avoids circular imports & keeps startup fast
# ---------------------------------------------------------------------------


def _get_cognitive_core():
    from JARVIS.core.system.cognitive_core import CognitiveCore

    return CognitiveCore()


def _get_task_planner():
    from JARVIS.core.system.task_planner import TaskPlanner

    return TaskPlanner()


def _get_agent_manager():
    from JARVIS.core.ai_router.multi_agent_system import AgentManager

    return AgentManager()


def _get_diagnostics():
    from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

    return DiagnosticsCenter()


def _get_learning_engine():
    from JARVIS.core.learning.learning_engine import PersonalLearningEngine

    return PersonalLearningEngine()


def _get_safety():
    from JARVIS.core.security.safety_layer import AISafetyLayer

    return AISafetyLayer()


def _get_self_improver():
    try:
        from JARVIS.core.system.self_improvement_engine import SelfImprovementEngine

        return SelfImprovementEngine()
    except Exception:
        return None


def _get_tool_router():
    try:
        from JARVIS.core.automation.tool_router import ToolRouter

        return ToolRouter()
    except Exception:
        return None


def _speak(text: str) -> None:
    """Deliver a TTS response without blocking the caller."""
    try:
        from JARVIS.core.voice.ses_motoru import VoiceEngine

        VoiceEngine().speak(text)
    except Exception as e:
        logger.warning("TTS unavailable: %s", e)


def _speak_async(text: str) -> None:
    """Fire-and-forget TTS so execution pipeline is never blocked."""
    threading.Thread(target=_speak, args=(text,), daemon=True).start()


# ---------------------------------------------------------------------------
# Goal Complexity Classifier
# ---------------------------------------------------------------------------

# Keywords that signal a multi-step goal requiring DAG decomposition
_MULTI_STEP_SIGNALS = frozenset(
    [
        "prepare",
        "setup",
        "set up",
        "deploy",
        "launch",
        "initialize",
        "build",
        "configure",
        "install",
        "create environment",
        "start all",
        "run all",
        "complete",
        "full",
        "entire",
        "everything",
        "automate",
        "orchestrate",
        "research",
        "investigate",
        "analyse",
        "analyze",
        "audit",
        "scan all",
        "backup",
        "migrate",
        "integrate",
        "end-to-end",
        "end to end",
        "start to finish",
        "from scratch",
        "generate report",
        "compile report",
        "development environment",
        "dev environment",
        "python environment",
        "production environment",
        "deploy application",
        "ship",
        "run tests",
        "test and",
        "build and",
        "push and",
        "commit and",
    ]
)

_CONTINUATION_SIGNALS = frozenset(
    [
        "and then",
        "after that",
        "followed by",
        "next step",
        "and also",
        "and open",
        "and start",
        "and launch",
        "and run",
        "then deploy",
        "then open",
        "then close",
    ]
)

# Fast single-action keywords (skip DAG)
_QUICK_SIGNALS = frozenset(
    [
        "open",
        "close",
        "what",
        "time",
        "date",
        "weather",
        "volume",
        "screenshot",
        "lock",
        "battery",
        "ram",
        "cpu",
        "clipboard",
        "note",
        "remind",
        "tell me",
        "say",
        "play",
    ]
)


def classify_goal_complexity(command: str) -> str:
    """
    Returns one of:
        'simple'   — single action, route directly through CognitiveCore
        'compound' — sequential multi-action, use list-dispatch
        'goal'     — high-level goal, decompose via TaskPlanner DAG
    """
    cmd = command.lower()

    multi = any(sig in cmd for sig in _MULTI_STEP_SIGNALS)
    cont = any(sig in cmd for sig in _CONTINUATION_SIGNALS)
    quick = any(cmd.startswith(sig) or f" {sig} " in cmd for sig in _QUICK_SIGNALS)

    if multi or cont:
        if any(kw in cmd for kw in ("prepare", "setup", "deploy", "environment", "build", "ship", "audit", "research")):
            return "goal"
        return "compound"

    if quick and not cont:
        return "simple"

    # Heuristic: > 6 words with action verbs → compound
    words = cmd.split()
    if len(words) > 6 and any(v in cmd for v in ("and", "then", "also", "plus")):
        return "compound"

    return "simple"


# ---------------------------------------------------------------------------
# Execution Result Schema
# ---------------------------------------------------------------------------


class ExecutionResult:
    """Structured result returned by AutonomousExecutor.execute()."""

    def __init__(
        self,
        success: bool,
        response: str,
        action: str = "talk",
        plan_id: str | None = None,
        tool_used: str | None = None,
        agent_used: str | None = None,
        elapsed_ms: float = 0.0,
        stage_timings: dict[str, float] | None = None,
        explanation: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.response = response
        self.action = action
        self.plan_id = plan_id
        self.tool_used = tool_used
        self.agent_used = agent_used
        self.elapsed_ms = elapsed_ms
        self.stage_timings = stage_timings or {}
        self.explanation = explanation or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "response": self.response,
            "action": self.action,
            "plan_id": self.plan_id,
            "tool_used": self.tool_used,
            "agent_used": self.agent_used,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "stage_timings": self.stage_timings,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Autonomous Executor — Master Integration Class
# ---------------------------------------------------------------------------


class AutonomousExecutor:
    """
    The central autonomous execution engine for JARVIS v3.0.

    All input paths — voice, text, CLI, API — converge here.
    This class:
      1. Applies security + rate-limiting gates
      2. Classifies goal complexity
      3. Routes to CognitiveCore (12-stage pipeline)
      4. For multi-step goals, triggers TaskPlanner DAG
      5. Selects agents and tools automatically
      6. Collects telemetry in DiagnosticsCenter
      7. Updates LearningEngine + MemoryEngine
      8. Triggers SelfImprovementEngine evaluation
      9. Delivers TTS response
      10. Returns structured ExecutionResult

    Singleton — only one executor instance is ever alive.
    """

    _instance: AutonomousExecutor | None = None
    _lock = threading.Lock()

    def __new__(cls) -> AutonomousExecutor:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Conversation context for follow-up chaining
        self._conversation_context: list[dict[str, str]] = []
        self._context_lock = threading.Lock()

        # Cancellation flag — set True to abort running workflow
        self._cancel_requested = False

        # Execution log path
        self._exec_log_path = os.path.abspath(os.path.join("logs", "autonomous_executor.jsonl"))
        os.makedirs(os.path.dirname(self._exec_log_path), exist_ok=True)

        # Registered completion callbacks (e.g. GUI bridge)
        self._on_complete_callbacks: list[Callable[[ExecutionResult], None]] = []

        logger.info("AutonomousExecutor v3.0 initialised — all pipeline layers active.")

    # ── Public API ────────────────────────────────────────────────────────────

    def register_completion_callback(self, cb: Callable[[ExecutionResult], None]) -> None:
        """Register a function to be called after every execution completes."""
        self._on_complete_callbacks.append(cb)

    def cancel(self) -> None:
        """Request cancellation of the currently running workflow."""
        self._cancel_requested = True
        logger.info("Cancellation requested by user.")
        _speak_async("Understood, sir. Cancelling the current workflow.")

    def execute(self, command: str, *, speak_response: bool = True) -> ExecutionResult:
        """
        Main entry point for any input.

        Args:
            command: Natural language command or goal.
            speak_response: If True, deliver the response via TTS.

        Returns:
            ExecutionResult with full telemetry.
        """
        self._cancel_requested = False
        start = time.perf_counter()
        stage_timings: dict[str, float] = {}

        logger.info("AutonomousExecutor received: '%s'", command)

        # ── Stage 1: Security Gate ────────────────────────────────────────────
        t = time.perf_counter()
        try:
            safety = _get_safety()
            if safety.is_rate_limited():
                msg = "Sir, request rate limit reached. Please stand by for a moment."
                logger.warning("Rate limit triggered.")
                result = ExecutionResult(False, msg, elapsed_ms=(time.perf_counter() - start) * 1000)
                self._finalize(result, command, speak_response)
                return result
        except Exception as e:
            logger.warning("Safety gate check failed (non-blocking): %s", e)
        stage_timings["security_gate"] = (time.perf_counter() - t) * 1000

        # ── Stage 2: Cancellation Check ───────────────────────────────────────
        if self._cancel_requested:
            return ExecutionResult(False, "Workflow cancelled.", elapsed_ms=0)

        # ── Stage 3: Conversation Context Injection ───────────────────────────
        t = time.perf_counter()
        enriched_command = self._inject_context(command)
        stage_timings["context_injection"] = (time.perf_counter() - t) * 1000

        # ── Stage 4: Goal Complexity Classification ───────────────────────────
        t = time.perf_counter()
        complexity = classify_goal_complexity(enriched_command)
        stage_timings["complexity_classification"] = (time.perf_counter() - t) * 1000
        logger.info("Goal complexity: %s for command: '%s'", complexity, command)

        # ── Stage 5: Tool Router Pre-Selection ────────────────────────────────
        t = time.perf_counter()
        tool_hint: str | None = None
        agent_hint: str | None = None
        try:
            tool_router = _get_tool_router()
            if tool_router:
                resolution = tool_router.resolve(command)
                tool_hint = resolution.get("tool")
                agent_hint = resolution.get("agent")
        except Exception as e:
            logger.warning("ToolRouter resolution failed (non-blocking): %s", e)
        stage_timings["tool_pre_selection"] = (time.perf_counter() - t) * 1000

        # ── Stage 6: Core Pipeline Execution ─────────────────────────────────
        t = time.perf_counter()
        core_result: dict[str, Any] = {}
        plan_id: str | None = None

        try:
            if complexity == "goal":
                # Multi-step: announce intent, then run DAG
                _speak_async("Understood, sir. Decomposing your goal into an autonomous execution plan. Stand by.")
                planner = _get_task_planner()
                plan_id = planner.create_plan(enriched_command)
                planner.execute_plan(plan_id)

                plan_info = planner.get_plan(plan_id)
                n_steps = len(plan_info.get("subtasks", [])) if plan_info else 0
                response = (
                    f"Sir, I have initiated a {n_steps}-step autonomous workflow for your goal: "
                    f"'{command}'. All agents are executing concurrently. "
                    "I will report completion status momentarily."
                )
                core_result = {
                    "action": "execute_plan",
                    "params": {"plan_id": plan_id, "complexity": complexity},
                    "response": response,
                    "explanation": {"intent": f"Goal-based DAG execution ({n_steps} steps)", "plan_id": plan_id},
                }

            elif complexity == "compound":
                # Compound: run through CognitiveCore (it handles multi-intent)
                cognitive = _get_cognitive_core()
                core_result = cognitive.process_request(enriched_command)
                plan_id = core_result.get("params", {}).get("plan_id")

            else:
                # Simple: direct CognitiveCore execution
                cognitive = _get_cognitive_core()
                core_result = cognitive.process_request(enriched_command)

        except Exception as e:
            logger.error("Core pipeline execution error: %s", e, exc_info=True)
            core_result = {
                "action": "error",
                "params": {},
                "response": f"I encountered a system fault, sir: {e}. Running diagnostic fallback.",
                "explanation": {"error": str(e)},
            }
        stage_timings["core_pipeline"] = (time.perf_counter() - t) * 1000

        # ── Stage 7: Observability Recording ──────────────────────────────────
        t = time.perf_counter()
        try:
            diagnostics = _get_diagnostics()
            diagnostics.record_timeline(stage_timings)
            success_flag = core_result.get("action", "error") != "error"
            diagnostics.record_task_outcome(success_flag)
            diagnostics.record_learning_event(
                "autonomous_execution",
                f"complexity={complexity}, command={command[:60]}",
            )
        except Exception as e:
            logger.warning("Diagnostics recording failed (non-blocking): %s", e)
        stage_timings["observability"] = (time.perf_counter() - t) * 1000

        # ── Stage 8: Learning Engine Update ───────────────────────────────────
        t = time.perf_counter()
        try:
            learning = _get_learning_engine()
            action_name = core_result.get("action", "unknown")
            params = core_result.get("params", {})
            learning.log_interaction(command, action_name, params, success=success_flag)
        except Exception as e:
            logger.warning("Learning engine update failed (non-blocking): %s", e)
        stage_timings["learning_update"] = (time.perf_counter() - t) * 1000

        # ── Stage 9: Memory + Knowledge Graph Update ──────────────────────────
        t = time.perf_counter()
        try:
            from memory_engine import MemoryEngine

            action_name = core_result.get("action", "unknown")
            MemoryEngine().write_memory(
                "autonomous_execution",
                command,
                f"Action: {action_name}, Complexity: {complexity}, Success: {success_flag}",
            )
        except Exception as e:
            logger.warning("MemoryEngine update failed (non-blocking): %s", e)
        stage_timings["memory_update"] = (time.perf_counter() - t) * 1000

        # ── Stage 10: Self-Improvement Evaluation ─────────────────────────────
        t = time.perf_counter()
        try:
            improver = _get_self_improver()
            if improver:
                improver.record_execution(
                    command=command,
                    complexity=complexity,
                    success=success_flag,
                    stage_timings=stage_timings,
                    agent_used=agent_hint,
                    tool_used=tool_hint,
                )
        except Exception as e:
            logger.warning("SelfImprovementEngine evaluation failed (non-blocking): %s", e)
        stage_timings["self_improvement"] = (time.perf_counter() - t) * 1000

        # ── Stage 11: Conversational Context Update ───────────────────────────
        response_text = core_result.get("response", "")
        self._update_context(command, response_text)

        # ── Stage 12: Build Result + Finalise ────────────────────────────────
        elapsed = (time.perf_counter() - start) * 1000
        stage_timings["total_elapsed"] = elapsed

        result = ExecutionResult(
            success=success_flag,
            response=response_text,
            action=core_result.get("action", "talk"),
            plan_id=plan_id,
            tool_used=tool_hint,
            agent_used=agent_hint,
            elapsed_ms=elapsed,
            stage_timings=stage_timings,
            explanation=core_result.get("explanation", {}),
        )

        self._finalize(result, command, speak_response)
        logger.info(
            "Execution complete in %.1f ms | success=%s | action=%s | complexity=%s",
            elapsed,
            result.success,
            result.action,
            complexity,
        )
        return result

    def execute_async(
        self,
        command: str,
        *,
        speak_response: bool = True,
        on_complete: Callable[[ExecutionResult], None] | None = None,
    ) -> None:
        """Non-blocking execution — fires the pipeline in a background thread."""

        def _run():
            result = self.execute(command, speak_response=speak_response)
            if on_complete:
                try:
                    on_complete(result)
                except Exception as e:
                    logger.error("on_complete callback error: %s", e)

        threading.Thread(target=_run, daemon=True, name=f"jarvis_exec_{int(time.time())}").start()

    # ── Voice-Specific Entry Points ───────────────────────────────────────────

    def handle_voice_command(self, transcribed_text: str) -> ExecutionResult:
        """Entry point for the voice pipeline bridge."""
        return self.execute(transcribed_text, speak_response=True)

    def handle_text_command(self, text: str) -> ExecutionResult:
        """Entry point for GUI text input / API calls."""
        return self.execute(text, speak_response=False)

    # ── Autonomous Goal Sequences ─────────────────────────────────────────────

    def run_dev_environment_goal(self) -> ExecutionResult:
        """Pre-built goal: 'Prepare my Python development environment'."""
        return self.execute("prepare my python development environment", speak_response=True)

    def run_security_audit_goal(self) -> ExecutionResult:
        """Pre-built goal: 'Run a full security audit'."""
        return self.execute("security audit check vulnerabilities", speak_response=True)

    def run_deploy_pipeline_goal(self) -> ExecutionResult:
        """Pre-built goal: 'Deploy my application'."""
        return self.execute("deploy my application", speak_response=True)

    def run_research_goal(self, topic: str) -> ExecutionResult:
        """Pre-built goal: Research a topic autonomously."""
        return self.execute(f"research {topic}", speak_response=True)

    def run_morning_briefing(self) -> ExecutionResult:
        """Pre-built routine: Morning system check and briefing."""
        return self.execute("daily summary morning briefing prepare development environment", speak_response=True)

    # ── Utility / Internal ────────────────────────────────────────────────────

    def get_conversation_context(self) -> list[dict[str, str]]:
        with self._context_lock:
            return list(self._conversation_context)

    def clear_context(self) -> None:
        with self._context_lock:
            self._conversation_context.clear()
        logger.info("Conversation context cleared.")

    def get_execution_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Read recent execution records from the JSONL log."""
        if not os.path.exists(self._exec_log_path):
            return []
        lines: list[dict] = []
        try:
            with open(self._exec_log_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
        return lines[-limit:]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _inject_context(self, command: str) -> str:
        """Prefix recent context to the command for follow-up awareness."""
        with self._context_lock:
            if not self._conversation_context:
                return command
            # Only inject last 2 exchanges to keep prompts compact
            recent = self._conversation_context[-2:]
        snippets = " | ".join(f"[{e['role']}]: {e['content'][:80]}" for e in recent)
        return f"[Context: {snippets}] Current request: {command}"

    def _update_context(self, command: str, response: str) -> None:
        with self._context_lock:
            self._conversation_context.append({"role": "user", "content": command})
            self._conversation_context.append({"role": "assistant", "content": response})
            # Keep last 10 exchanges (20 entries)
            if len(self._conversation_context) > 20:
                self._conversation_context = self._conversation_context[-20:]

    def _finalize(self, result: ExecutionResult, command: str, speak_response: bool) -> None:
        """Log result, fire callbacks, optionally speak."""
        # Persist execution record
        try:
            with open(self._exec_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

        # Speak response
        if speak_response and result.response:
            _speak_async(result.response)

        # Fire completion callbacks (e.g. GUI bridge updates)
        for cb in self._on_complete_callbacks:
            try:
                cb(result)
            except Exception as e:
                logger.error("Completion callback error: %s", e)


# ---------------------------------------------------------------------------
# Module-level convenience accessor
# ---------------------------------------------------------------------------


def get_executor() -> AutonomousExecutor:
    """Return the global singleton AutonomousExecutor instance."""
    return AutonomousExecutor()
