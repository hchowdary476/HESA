"""AI Orchestrator action execution domain for JARVIS."""

from __future__ import annotations

import logging
from typing import Any

from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator
from JARVIS.runtime.ui_bridge import send_log

logger = logging.getLogger("jarvis.ai_actions")


def handle_ai_action(action: str, params: dict[str, Any], context: dict[str, Any]) -> bool | None:
    """Execute AI Orchestrator routing, failover, and debate actions."""
    if not action.startswith("ai_"):
        return None

    speak = context.get("speak", print)
    orchestrator = AIOrchestrator()
    prompt = params.get("prompt", "") or params.get("query", "")

    try:
        if action == "ai_query":
            provider = params.get("provider", "chatgpt")
            if not prompt:
                prompt = "Introduce yourself and state your active parameters."

            # Update active status variables on orchestrator
            orchestrator.active_ai = provider.title()
            orchestrator.active_model = (
                "gpt-4o-mini"
                if provider == "chatgpt"
                else "gemini-1.5-flash"
                if provider == "gemini"
                else "grok-beta"
                if provider == "grok"
                else "claude-3-5"
                if provider == "claude"
                else "deepseek-chat"
                if provider == "deepseek"
                else "qwen2"
            )

            res = orchestrator.query_provider(provider, prompt)
            send_log(f"[{provider.upper()}] {res}")
            speak(res)
            return True

        elif action == "ai_failover":
            if not prompt:
                prompt = "Perform system validation query."
            res = orchestrator.query_with_failover(prompt)
            send_log(f"[AI ROUTER] Result: {res}")
            speak(res)
            return True

        elif action == "ai_debate":
            if not prompt:
                prompt = "What are the security implications of container root access?"

            speak("Dispatched parallel queries to ChatGPT, Gemini, and Claude, sir. Conducting debate analysis.")
            res = orchestrator.run_debate_mode(prompt)
            send_log(res["unified"])

            # Set context properties on the bridge if available
            try:
                # We can also store debate results in cache or expose to bridge slots
                pass
            except Exception:
                pass

            speak("Analysis complete, sir. Unified debated answer is posted on screen.")
            return True

        else:
            return False

    except Exception as e:
        logger.error("Failed to execute AI action %s: %s", action, e)
        send_log(f"⚠️ AI Orchestrator Error: {e}")
        return False
