"""Runtime startup readiness and degraded-mode reporting."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping

import speech_recognition as sr

from JARVIS.runtime.config_runtime import resolved_env


def _env_flag_enabled(values: Mapping[str, str], name: str, default: bool = True) -> bool:
    value = values.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


_mic_ready_cached = None
_mic_check_thread_started = False

def microphone_available() -> bool:
    """Return whether a microphone source can be opened asynchronously without blocking startup."""
    global _mic_ready_cached, _mic_check_thread_started
    if _mic_ready_cached is not None:
        return _mic_ready_cached
        
    if not _mic_check_thread_started:
        _mic_check_thread_started = True
        
        def _check():
            global _mic_ready_cached
            try:
                from JARVIS.core.voice.microphone import SoundDeviceMicrophone
                with SoundDeviceMicrophone():
                    _mic_ready_cached = True
            except Exception:
                _mic_ready_cached = False
                
        import threading
        t = threading.Thread(target=_check, name="jarvis_mic_probe", daemon=True)
        t.start()
        
    return True  # Non-blocking default


def emit_startup_readiness(
    *,
    env: Mapping[str, str] | None = None,
    send_log: Callable[[str], None],
    microphone_probe: Callable[[], bool] = microphone_available,
    recognition_mode: Callable[[], str] | None = None,
) -> dict[str, bool | str]:
    """Send one startup readiness snapshot to the UI without blocking runtime startup."""

    values = resolved_env(os.environ) if env is None else env
    groq_enabled = _env_flag_enabled(values, "JARVIS_ENABLE_GROQ", default=False)
    spotify_enabled = _env_flag_enabled(values, "JARVIS_ENABLE_SPOTIFY", default=True)
    groq_ready = groq_enabled and bool(values.get("GROQ_API_KEY"))
    spotify_ready = spotify_enabled and bool(values.get("SPOTIFY_CLIENT_ID") and values.get("SPOTIFY_CLIENT_SECRET"))
    mic_ready = microphone_probe()
    stt_mode = recognition_mode() if recognition_mode is not None else "unknown"

    if not groq_ready:
        send_log("[WARN] Groq API key not found. Running local backup routing, sir.")
    if not spotify_ready:
        send_log("[WARN] Spotify credentials not found. Spotify integration disabled.")
    if not mic_ready:
        send_log("[ERROR] Microphone not detected.")
    else:
        import logging
        logging.getLogger("jarvis.audio").info("Microphone detected")
        send_log("Microphone detected")
    send_log(f"[INFO] Speech recognition mode: {stt_mode}")
    return {"groq": groq_ready, "spotify": spotify_ready, "microphone": mic_ready, "recognition_mode": stt_mode}
