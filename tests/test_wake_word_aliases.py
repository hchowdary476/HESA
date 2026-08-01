import pytest
import os
from unittest.mock import MagicMock, patch

from JARVIS.core.voice.wake_word import (
    wake_word_detected,
    extract_inline_command,
    WAKE_ALIASES,
)
from JARVIS.core.automation.local_intent_router import route_local_intent
from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator


def test_allowed_wake_aliases_detection():
    """Verify that all allowed wake word aliases are matched successfully."""
    cfg = {"wake_word": "hesa", "enabled": True, "cooldown_seconds": 0.0}
    
    # Exact allowed aliases from spec
    for alias in WAKE_ALIASES:
        assert wake_word_detected(alias, config=cfg) is True
        assert wake_word_detected(f"hey {alias} open chrome", config=cfg) is True


def test_false_positive_prevention():
    """Verify that false-positive phrases do not trigger the wake-word listener."""
    cfg = {"wake_word": "hesa", "enabled": True, "cooldown_seconds": 0.0}
    
    false_positives = [
        "hey hey sir",
        "he zhan will",
        "hey he's open grown",
        "he is here",
        "here he is",
        "where is his clipboard",
        "he's out today",
        "esa method",
    ]
    for fp in false_positives:
        assert wake_word_detected(fp, config=cfg) is False


def test_wake_anchoring():
    """Verify that wake word detection requires the alias to appear near the start."""
    cfg = {"wake_word": "hesa", "enabled": True, "cooldown_seconds": 0.0}
    
    # Valid starts
    assert wake_word_detected("hesa open calculator", config=cfg) is True
    assert wake_word_detected("hey hesa open calculator", config=cfg) is True
    
    # Mid-sentence should NOT match
    assert wake_word_detected("could you open settings hesa", config=cfg) is False
    assert wake_word_detected("please run hessa now", config=cfg) is False


def test_inline_command_extraction():
    """Verify inline command extraction for both exact and fuzzy inputs."""
    cfg = {"wake_word": "hesa", "enabled": True, "cooldown_seconds": 0.0}
    
    # Exact
    assert extract_inline_command("hey hesa open calculator", config=cfg) == "open calculator"
    assert extract_inline_command("hessa play music", config=cfg) == "play music"
    assert extract_inline_command("hey heysa start settings", config=cfg) == "start settings"
    
    # Empty commands
    assert extract_inline_command("hey hesa", config=cfg) is None
    assert extract_inline_command("hessa", config=cfg) is None
    
    # Fuzzy
    assert extract_inline_command("hey heesa write note", config=cfg) == "write note"


def test_local_command_bypass():
    """Verify that the local commands are resolved by the local intent router."""
    # List of bypass commands from the objective
    local_cmds = [
        ("open calculator", "open_app", "calculator"),
        ("open chrome", "open_app", "chrome"),
        ("open notepad", "open_app", "notepad"),
        ("open explorer", "open_app", "explorer"),
        ("open settings", "open_app", "settings"),
        ("volume up", "press_key", "volumeup"),
        ("volume down", "press_key", "volumedown"),
        ("mute", "control_volume", "mute"),
        ("lock pc", "lock_screen", None),
        ("sleep pc", "sleep", None),
        ("shutdown", "shutdown", None),
        ("restart", "restart", None),
        ("take screenshot", "screenshot", None),
    ]
    
    for cmd, expected_action, expected_param in local_cmds:
        payload = route_local_intent(cmd)
        assert payload is not None, f"Failed to route local command: {cmd}"
        assert payload.get("action") == expected_action
        if expected_param:
            # Check app parameter or volume action parameter
            params = payload.get("params", {})
            param_val = params.get("app") or params.get("action") or params.get("key")
            assert param_val == expected_param


def test_claude_model_configuration():
    """Verify Claude is configured with the correct production model and priority."""
    orchestrator = AIOrchestrator()
    
    # Must use "claude-sonnet-4-20250514"
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hello, sir."}],
            "usage": {"total_tokens": 10}
        }
        mock_post.return_value = mock_response
        
        # Test Claude querying
        res = orchestrator.query_provider("claude", "ping")
        assert "Hello" in res
        
        # Verify model name sent in payload
        called_args, called_kwargs = mock_post.call_args
        payload = called_kwargs.get("json", {})
        assert payload.get("model") == "claude-sonnet-4-20250514"
        
        headers = called_kwargs.get("headers", {})
        assert headers.get("anthropic-version") == "2023-06-01"
        assert headers.get("Content-Type") == "application/json"
