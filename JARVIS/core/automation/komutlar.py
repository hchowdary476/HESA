"""COMMANDS - All HESA OS commands with Local-First Intent Routing & Safety Confirmation."""

from __future__ import annotations

from time import perf_counter

from JARVIS.core.automation.action_dispatcher import execute_action as dispatch_execute_action
from JARVIS.core.automation.groq_router import summarize_text
from JARVIS.core.automation.local_intent_router import classify_intent
from JARVIS.core.memory import add_to_short_term, get_preference, set_preference, track_command
from JARVIS.core.system.utils.jarvis_logging import get_file_logger, get_logger
from JARVIS.core.voice.ses_motoru import speak
from JARVIS.runtime.ui_bridge import send_state

logger = get_logger("commands")
intent_logger = get_file_logger("jarvis.intent")
action_logger = get_file_logger("jarvis.actions")
router_logger = get_file_logger("jarvis.router")


def execute_action(action):
    """Handles single or combo actions via the dispatcher."""
    context = {
        "speak": speak,
        "logger": logger,
        "summarize_text": summarize_text,
    }
    return dispatch_execute_action(action, context)


def process_command(command: str) -> bool:
    """Main command handler with local intent classification, AI routing, and safety confirmation."""
    if not command or not command.strip():
        return True

    t0 = perf_counter()
    logger.info("Received command: %s", command)

    if any(k in command.lower() for k in ["goodbye hesa", "shut down hesa"]):
        speak("Farewell, sir. HESA shutting down.")
        return False

    add_to_short_term("user", command)
    track_command(command)

    # ── 0. Pending Learning Command Intercept ──────────────────────────────────
    learning_cmd = get_preference("learning_command")
    if learning_cmd:
        learned = get_preference("learned_commands") or {}
        learned[learning_cmd] = command
        set_preference("learned_commands", learned)
        set_preference("learning_command", None)
        speak("Sir, ee command ni future kosam gurthupettukunnanu.")
        return True

    # ── 1. Safety Confirmation Guard for Dangerous Commands (Requirement #7) ─
    pending_danger = get_preference("pending_dangerous_action")
    if pending_danger and isinstance(pending_danger, dict):
        cmd_norm = command.lower().strip()
        confirm_words = {"yes", "yep", "sure", "confirm", "do it", "proceed", "sare", "avunu"}
        cancel_words = {"no", "nope", "cancel", "stop", "don't", "dont", "vaddu"}

        if any(w in cmd_norm for w in confirm_words):
            msg = f"[SAFETY] DANGEROUS ACTION CONFIRMED BY USER: {pending_danger.get('action')}"
            print(msg, flush=True)
            intent_logger.info(msg)
            set_preference("pending_dangerous_action", None)
            speak("Confirmation received. Executing command, sir.")
            return bool(execute_action(pending_danger))
        elif any(w in cmd_norm for w in cancel_words):
            msg = f"[SAFETY] DANGEROUS ACTION CANCELLED BY USER: {pending_danger.get('action')}"
            print(msg, flush=True)
            intent_logger.info(msg)
            set_preference("pending_dangerous_action", None)
            speak("Command cancelled, sir.")
            return True

    # ── 2. Intent Detection & Classification (Requirement #2) ──────────────────
    intent_type, payload = classify_intent(command)
    latency_ms = (perf_counter() - t0) * 1000

    intent_msg = f'[INTENT] {intent_type} (latency={latency_ms:.2f}ms command="{command}")'
    print(intent_msg, flush=True)
    intent_logger.info(intent_msg)

    # ── 3. Local Command Execution Path (Requirement #3) ──────────────────────
    if intent_type == "LOCAL_COMMAND" and isinstance(payload, dict):
        act_name = payload.get("action", "talk")
        action_msg = f"[ACTION] {act_name} params={payload.get('params', {})}"
        print(action_msg, flush=True)
        action_logger.info(action_msg)

        # Safety confirmation required check
        if payload.get("requires_confirmation"):
            set_preference("pending_dangerous_action", payload)
            warn_msg = f"[SAFETY] CONFIRMATION REQUIRED for {act_name}"
            print(warn_msg, flush=True)
            intent_logger.warning(warn_msg)
            speak(f"Are you sure you want to {act_name.replace('_', ' ')} the system, sir?")
            return True

        response_text = payload.get("response", "")
        if response_text:
            tts_msg = f"[TTS] {response_text}"
            print(tts_msg, flush=True)
            speak(response_text)
            add_to_short_term("hesa", response_text)

        if act_name == "talk":
            send_state("STANDBY", "Command completed")
            return True

        result = execute_action(payload)
        send_state("STANDBY" if result else "ERROR", "Command completed" if result else "Command failed")
        return bool(result)

    # ── 4. AI Query Routing Path (Requirement #4) ─────────────────────────────
    task_type = payload if isinstance(payload, str) else "general"
    router_msg = f"[ROUTER] CLASSIFIED AS AI_QUERY (task_type={task_type})"
    print(router_msg, flush=True)
    router_logger.info(router_msg)

    try:
        from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

        orchestrator = AIOrchestrator()
        ai_response = orchestrator.query_with_failover(command, task_type=task_type)

        if ai_response:
            print(f"[TTS] {ai_response[:100]}...", flush=True)
            speak(ai_response)
            add_to_short_term("hesa", ai_response)
            action_logger.info(f"[ACTION] AI_RESPONSE_SPOKEN (provider={orchestrator.active_ai})")
            return True
    except Exception as e:
        logger.error("AI Routing failed: %s", e)
        router_logger.error("AI Routing exception: %s", e)
        speak("I encountered an issue querying AI services, sir.")

    return True


komutu_isle = process_command
