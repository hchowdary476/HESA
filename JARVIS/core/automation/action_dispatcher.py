"""Route parsed actions into domain-specific handlers."""

from __future__ import annotations

import os
import time
from typing import Any

from JARVIS.core.automation.action_schema import validate_action_payload
from JARVIS.core.automation.domains.media_actions import handle_media_action
from JARVIS.core.automation.domains.memory_actions import handle_memory_action
from JARVIS.core.automation.domains.runtime_actions import handle_runtime_action
from JARVIS.core.automation.domains.cyber_actions import handle_cyber_action
from JARVIS.core.automation.domains.ai_actions import handle_ai_action

DomainContext = dict[str, Any]

DOMAIN_HANDLERS = (
    handle_runtime_action,
    handle_media_action,
    handle_memory_action,
    handle_cyber_action,
    handle_ai_action,
)


def action_sequence_delay() -> float:
    """Return the delay between multi-action steps."""

    try:
        return max(0.0, float(os.getenv("JARVIS_ACTION_SEQUENCE_DELAY", "0.1")))
    except ValueError:
        return 0.1


def execute_single_action(action: str, params: dict, context: DomainContext) -> bool:
    """Execute one action by delegating to the domain handlers."""

    for handler in DOMAIN_HANDLERS:
        result = handler(action, params, context)
        if result is not None:
            return bool(result)

    logger = context.get("logger")
    if logger is not None:
        logger.warning("Unhandled action: %s", action)
    return True


def execute_action(action: dict, context: DomainContext) -> bool:
    """Execute a single or multi-action payload."""

    speak = context["speak"]
    
    # Graceful Auto-Healing of payload
    if isinstance(action, str):
        action = {
            "action": "talk",
            "params": {},
            "response": action
        }
    elif action is None:
        action = {
            "action": "talk",
            "params": {},
            "response": ""
        }
    elif isinstance(action, dict):
        if "actions" in action:
            actions = action.get("actions")
            if not isinstance(actions, list) or not actions:
                action["action"] = "talk"
                action.pop("actions", None)
        if "actions" not in action:
            act = action.get("action")
            if not isinstance(act, str) or not act.strip():
                action["action"] = "talk"
        if "params" not in action or action.get("params") is None:
            action["params"] = {}
        if "response" not in action or action.get("response") is None:
            action["response"] = ""
        elif not isinstance(action.get("response"), str):
            action["response"] = str(action["response"])

    validation = validate_action_payload(action)
    if not validation.valid:
        logger = context.get("logger")
        if logger is not None:
            logger.warning("Invalid action payload: %s", validation.reason)
        speak(f"Invalid action payload, sir. Reason: {validation.reason}.")
        return False

    if "actions" in action:
        response = action.get("response", "")
        if response:
            speak(response)
        for sub_action in action["actions"]:
            if not isinstance(sub_action, dict) or not sub_action.get("action"):
                logger = context.get("logger")
                if logger is not None:
                    logger.warning("Malformed sub-action payload: %s", sub_action)
                speak("I skipped a malformed action, sir. Reason: it did not include an action name.")
                return False
            result = execute_single_action(
                sub_action["action"],
                sub_action.get("params", {}),
                context,
            )
            if result is False:
                return False
            delay = action_sequence_delay()
            if delay:
                time.sleep(delay)
        return True

    response = action.get("response", "")
    if response:
        speak(response)
    return execute_single_action(action.get("action", "talk"), action.get("params", {}), context)
