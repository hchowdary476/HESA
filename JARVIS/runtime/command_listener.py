"""Command listening helpers."""

from __future__ import annotations

import os

import speech_recognition as sr

from JARVIS.core.security.jarvis_admin import format_actionable_message
from JARVIS.core.system.observability import record_runtime_event
from JARVIS.core.voice.speech_backend import recognition_mode, transcribe_audio
from JARVIS.runtime.ui_bridge import send_state

_cmd_recognizer = sr.Recognizer()
_cmd_recognizer.energy_threshold = int(os.getenv("JARVIS_ENERGY_THRESHOLD", "300"))
_cmd_recognizer.dynamic_energy_threshold = False
_cmd_recognizer.pause_threshold = float(os.getenv("JARVIS_PAUSE_THRESHOLD", "1.0"))


def listen_for_command(*, logger, send_log, speak) -> str:
    """Listen for a command and degrade safely when audio input is unavailable."""
    print("[VOICE_STAGE_9] Command listener entered")
    logger.info("[VOICE_STAGE_9] Command listener entered")

    import time

    from JARVIS.core.voice.ses_motoru import VoiceEngine

    while VoiceEngine().speaking:
        time.sleep(0.2)

    from JARVIS.core.system.utils.activity_tracker import set_activity

    set_activity("voice_recognition", True)
    try:
        try:
            from JARVIS.core.voice.microphone import SoundDeviceMicrophone

            with SoundDeviceMicrophone() as source:
                logger.info("Microphone detected")
                logger.info("Listening started")
                logger.info("Listening for command.")
                print("Listening for command...")
                send_log("[VOICE] Listening For Command")
                send_state("LISTENING", "Voice input active")
                try:
                    audio = _cmd_recognizer.listen(source, timeout=10, phrase_time_limit=20)
                except sr.WaitTimeoutError:
                    return ""
        except Exception as exc:
            logger.warning("Microphone not detected while listening for a command: %s", exc)
            record_runtime_event("microphone_missing", "Microphone not detected", "warning", {"mode": recognition_mode()})
            send_log("[ERROR] Microphone not detected. Check input device settings.")
            send_state("ERROR", "Microphone not detected")
            return ""

        try:
            from JARVIS.core.memory.memory_preferences import get_preference

            pref_lang = get_preference("preferred_language")
            lang_code = "te-IN" if pref_lang == "telugu" else "en-US"
            command = transcribe_audio(_cmd_recognizer, audio, language=lang_code)
            if not command:
                if recognition_mode() == "offline":
                    speak(
                        format_actionable_message(
                            "I heard something, but couldn't decode it.",
                            "Offline speech recognition returned an empty transcription.",
                            "Speak a little closer to the microphone and try again.",
                        )
                    )
                return ""
            logger.info("Speech recognized")
            logger.info("SPEECH RECOGNIZED: %s", command)
            logger.info("Recognized command: %s", command)
            print(f"You: {command}")
            print(f"[VOICE] SPEECH RECOGNIZED: {command}")
            send_log(f"[VOICE] Command Recognized: {command}")
            record_runtime_event("command_recognized", command, "info", {"mode": recognition_mode()})
            return command.lower()
        except (OSError, RuntimeError, ValueError):
            record_runtime_event("voice_error", "Speech recognition failure", "warning", {"mode": recognition_mode()})
            speak(
                format_actionable_message(
                    "Voice recognition is unavailable.",
                    "Neither online nor offline speech recognition could transcribe the audio.",
                    "Check your internet connection, microphone, and offline model path.",
                )
            )
            return ""
    finally:
        set_activity("voice_recognition", False)
