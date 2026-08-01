import os
import json
import time

STATE_FILE = os.path.join("logs", "activity_state.json")

def _read_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        temp_file = STATE_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(state, f)
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        os.rename(temp_file, STATE_FILE)
    except Exception:
        pass

def set_activity(name: str, active: bool):
    """Set activity state for a specific activity (e.g. 'voice_recognition', 'tts_playback', 'face_recognition', 'ui_interaction')."""
    state = _read_state()
    state[name] = {
        "active": active,
        "timestamp": time.time()
    }
    _write_state(state)

def is_activity_active(name: str, max_age: float = 10.0) -> bool:
    """Check if a specific activity is active and hasn't timed out (default 10s timeout to prevent deadlocks)."""
    state = _read_state()
    item = state.get(name)
    if not item:
        return False
    if not item.get("active"):
        return False
    # Check if the active state is fresh to prevent orphaned lockouts on crashes
    if time.time() - item.get("timestamp", 0.0) > max_age:
        return False
    return True

def is_any_trim_prevented() -> bool:
    """Return True if memory trimming should be blocked because a critical task is active."""
    return (
        is_activity_active("voice_recognition") or
        is_activity_active("tts_playback") or
        is_activity_active("face_recognition") or
        is_activity_active("ui_interaction")
    )
