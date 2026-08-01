"""Preference detection, storage, and natural language memory query helpers."""

from __future__ import annotations

import time
import re
from JARVIS.core.memory.memory_store import load_memory, save_memory
from JARVIS.core.memory.privacy_mode import memory_reads_enabled, memory_writes_enabled
from JARVIS.core.system.utils.jarvis_logging import get_file_logger

memory_logger = get_file_logger("jarvis.memory")


def set_preference(key: str, value, *, config_manager=None):
    """Save a user preference with structured logging."""
    if not memory_writes_enabled(config_manager):
        return
    t0 = time.perf_counter()
    memory = load_memory()
    if key in memory["preferences"]:
        memory["preferences"][key] = value
    else:
        if "custom" not in memory["preferences"]:
            memory["preferences"]["custom"] = {}
        memory["preferences"]["custom"][key] = value
    save_memory(memory)
    latency_ms = (time.perf_counter() - t0) * 1000
    msg = f"[MEMORY_WRITE] key=\"{key}\" value=\"{value}\" latency={latency_ms:.2f}ms"
    print(msg, flush=True)
    memory_logger.info(msg)


def get_preference(key: str, *, config_manager=None):
    """Get a user preference with latency tracking (< 50ms requirement)."""
    if not memory_reads_enabled(config_manager):
        return None
    t0 = time.perf_counter()
    memory = load_memory()
    res = None
    if key in memory.get("preferences", {}):
        res = memory["preferences"][key]
    else:
        res = memory.get("preferences", {}).get("custom", {}).get(key)
    latency_ms = (time.perf_counter() - t0) * 1000
    msg = f"[MEMORY_LOOKUP] key=\"{key}\" result=\"{res}\" latency={latency_ms:.2f}ms"
    print(msg, flush=True)
    memory_logger.info(msg)
    return res


def detect_and_save_preference(command: str):
    """Detect and save preferences from natural language, or query stored memories."""
    cmd_lower = command.lower().strip()

    # ── 1. Query stored facts (Instant response < 50ms) ──────────────────────
    if "what is my favorite language" in cmd_lower or "what's my favorite language" in cmd_lower or "favorite programming language" in cmd_lower:
        lang = get_preference("favorite_language")
        if lang:
            return f"Your favorite language is {lang.capitalize()}."
        return "I haven't saved your favorite language yet, sir."

    if "what is my name" in cmd_lower or "what's my name" in cmd_lower or "who am i" in cmd_lower:
        name = get_preference("user_name")
        if name:
            return f"Your name is {name.capitalize()}, sir."
        return "I haven't saved your name yet, sir."

    if "what is my favorite app" in cmd_lower or "what's my favorite app" in cmd_lower:
        app = get_preference("favorite_app")
        if app:
            return f"Your favorite app is {app.title()}, sir."
        return "I haven't recorded a favorite app yet, sir."

    # ── 2. Detect and save new facts ─────────────────────────────────────────
    if "favorite language" in cmd_lower or "favourite language" in cmd_lower:
        for trigger in ["favorite language is", "favourite language is", "favorite programming language is"]:
            if trigger in cmd_lower:
                lang = cmd_lower.split(trigger)[-1].strip().rstrip(".")
                if lang:
                    set_preference("favorite_language", lang.title())
                    return f"Got it, sir. I'll remember that your favorite language is {lang.title()}."

    if "my name is" in cmd_lower or "call me" in cmd_lower:
        for trigger in ["my name is", "call me"]:
            if trigger in cmd_lower:
                name = cmd_lower.split(trigger)[-1].strip().rstrip(".")
                if name:
                    set_preference("user_name", name.title())
                    return f"Pleasure to meet you, {name.title()}. I'll remember your name."

    if "always play" in cmd_lower or "favorite music" in cmd_lower or "favorite artist" in cmd_lower:
        for trigger in ["always play", "favorite music is", "favorite artist is"]:
            if trigger in cmd_lower:
                artist = cmd_lower.split(trigger)[-1].strip().rstrip(".")
                if artist:
                    set_preference("favorite_music", artist.title())
                    return f"Got it, sir. I'll remember that you love {artist.title()}."

    if "default volume" in cmd_lower or "always volume" in cmd_lower:
        numbers = re.findall(r"\d+", cmd_lower)
        if numbers:
            volume = int(numbers[0])
            set_preference("preferred_volume", volume)
            return f"Noted, sir. Default volume set to {volume} percent."

    if "always open" in cmd_lower or "favorite app" in cmd_lower:
        apps = ["chrome", "spotify", "steam", "epic", "vscode", "discord", "calculator"]
        for app in apps:
            if app in cmd_lower:
                set_preference("favorite_app", app)
                return f"Understood, sir. I'll remember you prefer {app.title()}."

    return None
