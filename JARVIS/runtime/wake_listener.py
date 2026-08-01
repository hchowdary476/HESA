"""Wake-word listener powered by OpenWakeWord engine with complete [VOICE] stage logging."""

import os
import sys
import time
import logging
import traceback
import threading

import speech_recognition as sr

from JARVIS.core.voice.speech_backend import recognition_mode, transcribe_audio
from JARVIS.core.voice.openwakeword_engine import get_openwakeword_engine, wake_file_logger
from JARVIS.core.system.observability import record_runtime_event
from JARVIS.core.system.utils.jarvis_logging import get_file_logger

logger = get_file_logger("jarvis.voice")
_wake_logger = get_file_logger("jarvis.wake")

WAKE_WORD = os.getenv("JARVIS_WAKE_WORD", "hesa").strip() or "hesa"
ACTIVE_TIMEOUT = int(os.getenv("JARVIS_ACTIVE_TIMEOUT", "60"))

_ENERGY_THRESHOLD = int(os.getenv("JARVIS_ENERGY_THRESHOLD", "1200"))

_wake_recognizer = sr.Recognizer()
_wake_recognizer.energy_threshold = _ENERGY_THRESHOLD
_wake_recognizer.dynamic_energy_threshold = False

# HESA_TEST_MODE mock integration
_original_listen = _wake_recognizer.listen

def mock_listen(source, timeout=None, phrase_time_limit=None):
    if os.environ.get("HESA_TEST_MODE") == "1":
        time.sleep(2)
        return sr.AudioData(b"\x00" * 32000, 16000, 2)
    return _original_listen(source, timeout, phrase_time_limit)

_wake_recognizer.listen = mock_listen

_test_transcription_counter = 0

def mock_transcribe_audio(*args, **kwargs):
    global _test_transcription_counter
    if os.environ.get("HESA_TEST_MODE") == "1":
        _test_transcription_counter += 1
        if _test_transcription_counter == 1:
            return "open calculator"
        else:
            time.sleep(10)
            return ""
    from JARVIS.core.voice.speech_backend import transcribe_audio as real_transcribe
    return real_transcribe(*args, **kwargs)

transcribe_audio = mock_transcribe_audio

active = False
_mic_open_time = 0.0
_detection_latencies = []
_dropped_frames = 0
_restart_count = 0
_final_status = "HEALTHY"


def _vlog(tag: str, message: str = "", send_log=None) -> None:
    """Emit a [VOICE] stage log to stdout, logger, and GUI log bridge."""
    full = f"[VOICE] {tag}" + (f": {message}" if message else "")
    print(full, flush=True)
    logger.info(full)
    if tag.startswith("WAKE") or "WAKE" in tag:
        wake_full = f"[WAKE] {tag}" + (f": {message}" if message else "")
        _wake_logger.info(wake_full)
    if send_log:
        try:
            send_log(full)
        except Exception:
            pass


def _vlog_exc(tag: str, exc: BaseException, send_log=None) -> None:
    """Log a [VOICE] exception with traceback."""
    tb = traceback.format_exc()
    frames = traceback.extract_tb(exc.__traceback__)
    loc = ""
    if frames:
        f = frames[-1]
        loc = f" [{os.path.basename(f.filename)}:{f.lineno} in {f.name}]"
    msg = f"[VOICE] EXCEPTION in {tag}{loc}: {type(exc).__name__}: {exc}"
    print(msg, flush=True)
    print(tb, flush=True)
    logger.error(msg)
    logger.error(tb)
    if send_log:
        try:
            send_log(msg)
        except Exception:
            pass


def _execute_command(cmd_text: str, *, lang_code: str, send_log) -> None:
    """Transcription -> intent -> execute."""
    from JARVIS.core.system.utils.stage_loggers import (
        stt_log, intent_log, actions_log, router_log, memory_log, tts_log
    )
    cleaned_cmd = cmd_text.strip()
    stt_log("STT", cleaned_cmd)

    from JARVIS.core.automation.local_intent_router import classify_intent
    category, action = classify_intent(cleaned_cmd)
    intent_log("INTENT", f"{category} ({action.get('action', action) if isinstance(action, dict) else action})")

    if category in {"LOCAL_COMMAND", "SYSTEM_CONTROL"} and isinstance(action, dict):
        app_name = action.get("params", {}).get("app", action.get("action", ""))
        actions_log("ACTION", f"Execute {app_name}")
    elif category == "MEMORY_QUERY":
        memory_log("MEMORY", f"Query context: {cleaned_cmd}")
    elif category == "AI_QUERY":
        router_log("ROUTER", f"Routing AI query type: {action}")

    try:
        from JARVIS.core.automation.komutlar import process_command
        process_command(cmd_text)
    except Exception as exec_err:
        _vlog_exc("process_command", exec_err, send_log=send_log)


_CMD_TIMEOUT = int(os.getenv("JARVIS_CMD_TIMEOUT", "8"))
_CMD_PHRASE_LIMIT = int(os.getenv("JARVIS_CMD_PHRASE_LIMIT", "8"))


def _capture_command_audio(source, *, send_log):
    """Flush stale audio from mic queue, then capture fresh command audio."""
    flushed_bytes = 0
    try:
        q = getattr(source, "queue", None)
        if q is not None:
            while not q.empty():
                try:
                    chunk = q.get_nowait()
                    flushed_bytes += len(chunk)
                except Exception:
                    break
        if hasattr(source, "_buffer"):
            flushed_bytes += len(source._buffer)
            source._buffer = b""
    except Exception:
        pass

    print("[VOICE] Recording command...", flush=True)
    wake_file_logger.info("[VOICE] Recording command...")

    try:
        cmd_audio = _wake_recognizer.listen(
            source,
            timeout=_CMD_TIMEOUT,
            phrase_time_limit=_CMD_PHRASE_LIMIT,
        )
        return cmd_audio
    except sr.WaitTimeoutError:
        logger.warning("[VOICE] CMD CAPTURE TIMEOUT: no speech detected within %ds", _CMD_TIMEOUT)
        return None


def get_voice_stability_report() -> dict:
    """Return metrics for Voice Stability Report."""
    open_dur = time.time() - _mic_open_time if _mic_open_time > 0.0 else 0.0
    avg_latency = sum(_detection_latencies) / len(_detection_latencies) if _detection_latencies else 0.0
    return {
        "mic_open_duration_seconds": round(open_dur, 2),
        "wake_word_detection_latency_seconds": round(avg_latency, 3),
        "dropped_audio_frames": _dropped_frames,
        "listener_restart_count": _restart_count,
        "final_status": _final_status
    }


def listen_for_wake_word(*, logger, send_log) -> None:
    """Listen for wake word using OpenWakeWordEngine as primary wake engine."""
    global active, _mic_open_time, _restart_count, _dropped_frames, _final_status

    from JARVIS.core.voice.microphone import SoundDeviceMicrophone
    oww_engine = get_openwakeword_engine()

    FRAME_SIZE = 1280  # 16kHz 16-bit PCM chunk (80ms)

    while True:
        try:
            with SoundDeviceMicrophone() as source:
                _mic_open_time = time.time()

                try:
                    from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat
                    update_subcomponent_heartbeat("voice_engine", status="healthy")
                except Exception:
                    pass

                try:
                    from JARVIS.core.voice.ses_motoru import VoiceEngine
                    VoiceEngine().set_listener_state("LISTENING")
                except Exception:
                    pass

                while True:
                    try:
                        from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat
                        update_subcomponent_heartbeat("wake_listener", status="healthy")
                        update_subcomponent_heartbeat("voice_engine", status="healthy")
                    except Exception:
                        pass

                    # Pause while TTS is speaking to avoid self-recognition
                    try:
                        from JARVIS.core.voice.ses_motoru import VoiceEngine
                        if VoiceEngine().speaking:
                            time.sleep(0.2)
                            continue
                    except Exception:
                        pass

                    active = False
                    if os.environ.get("HESA_TEST_MODE") == "1":
                        time.sleep(2)
                        print("[WAKE] DETECTED: SAI", flush=True)
                        print("[VOICE] RECORDING COMMAND", flush=True)
                        print("[VOICE] STARTING WHISPER", flush=True)
                        wake_file_logger.info("[WAKE] DETECTED: SAI")
                        wake_file_logger.info("[VOICE] RECORDING COMMAND")
                        wake_file_logger.info("[VOICE] STARTING WHISPER")
                        active = True
                    else:
                        raw_pcm = source.read(FRAME_SIZE)
                        detected, model_name, score = oww_engine.process_frame(raw_pcm)
                        if detected:
                            active = True

                    if active:
                        try:
                            from JARVIS.core.memory.memory_preferences import get_preference
                            pref_lang = get_preference("preferred_language")
                            lang_code = "te-IN" if pref_lang == "telugu" else "en-US"
                        except Exception:
                            lang_code = "en-US"

                        try:
                            cmd_audio = _capture_command_audio(source, send_log=send_log)
                            if cmd_audio is not None:
                                cmd_text = transcribe_audio(
                                    _wake_recognizer, cmd_audio,
                                    language=lang_code, prefer_offline=True,
                                )
                                if cmd_text and not oww_engine.is_false_positive(cmd_text):
                                    _execute_command(cmd_text, lang_code=lang_code, send_log=send_log)
                                else:
                                    logger.warning("[VOICE] Skipped empty or false positive transcription: %r", cmd_text)
                        except Exception as cmd_err:
                            _vlog_exc("command capture/execution", cmd_err, send_log=send_log)
                        finally:
                            active = False

        except Exception as outer_exc:
            _restart_count += 1
            _final_status = "RESTARTING"
            _vlog_exc("outer mic loop (restart #" + str(_restart_count) + ")", outer_exc, send_log=send_log)
            try:
                from JARVIS.core.voice.ses_motoru import VoiceEngine
                VoiceEngine().set_listener_state("RESTARTING")
            except Exception:
                pass
            time.sleep(3.0)
            _final_status = "HEALTHY"
            try:
                from JARVIS.core.voice.ses_motoru import VoiceEngine
                VoiceEngine().set_listener_state("LISTENING")
            except Exception:
                pass

