"""Runtime loop for JARVIS."""

from __future__ import annotations

import threading
import time

from JARVIS.core.voice.ses_motoru import speak
from JARVIS.core.voice.speech_backend import recognition_mode
from JARVIS.core.automation.komutlar import process_command
from JARVIS.core.system.observability import record_runtime_event
from JARVIS.runtime import orchestrator as runtime_orchestrator
from JARVIS.runtime import readiness as runtime_readiness
from JARVIS.runtime import timer as timer_runtime
from JARVIS.runtime import ui_bridge
from JARVIS.runtime import voice_personality as personality_runtime
from JARVIS.runtime import wake_listener as wake_state
from JARVIS.runtime import wake_word as voice_runtime
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("main")

_state = {"command_count": 0, "joke_interval": 5}


def set_ui_callback(fn):
    ui_bridge.set_ui_callback(fn)


def send_log(message):
    ui_bridge.send_log(message)


def maybe_tell_joke():
    personality_runtime.maybe_tell_joke(
        speak=speak,
        send_log=send_log,
        logger=logger,
        state=_state,
    )


def say_goodbye():
    personality_runtime.say_goodbye(speak=speak, send_log=send_log, logger=logger)


def parse_duration(command):
    return timer_runtime.parse_duration(command)


def start_timer(seconds, message="Time is up, sir."):
    return timer_runtime.start_timer(seconds, message, speak=speak, send_log=send_log, logger=logger)


def handle_timer_command(command):
    return timer_runtime.handle_timer_command(command, speak=speak, send_log=send_log, logger=logger)


def listen_for_wake_word():
    return wake_state.listen_for_wake_word(logger=logger, send_log=send_log)


def listen_for_command():
    return voice_runtime.listen_for_command(speak=speak, send_log=send_log, logger=logger)


def greet():
    personality_runtime.greet(speak=speak, send_log=send_log, logger=logger)


def start_jarvis():
    """Run the main voice loop with async background pipeline initialization."""

    print(
        """
=================================================
             JARVIS  Starting...                 
=================================================
        """
    )

    logger.info("JARVIS startup sequence initiated.")

    # ── Non-blocking background voice pipeline initialization & watchdog protection ──
    try:
        from JARVIS.core.voice.voice_pipeline_manager import get_voice_pipeline_manager
        vpm = get_voice_pipeline_manager()
        vpm.initialize_pipeline_async(timeout_seconds=10.0)
    except Exception as e:
        logger.error(f"Failed to trigger VoicePipelineManager async init: {e}")

    try:
        from JARVIS.core.system.utils.camera_tracker import generate_startup_report
        report_str = generate_startup_report()
        print("=================================================")
        print(report_str)
        print("=================================================")
        logger.info(f"Camera Health Report at startup:\n{report_str}")
    except Exception as e:
        logger.error(f"Failed to generate startup camera diagnostic: {e}")

    record_runtime_event("startup", "JARVIS startup sequence initiated", "info", {"offline_stt": recognition_mode()})
    runtime_readiness.emit_startup_readiness(send_log=send_log, recognition_mode=recognition_mode)
    threading.Thread(target=greet, daemon=True).start()

    # ── STAGE: WAKE THREAD CREATED ───────────────────────────────────────────
    print("[VOICE] WAKE THREAD CREATED", flush=True)
    logger.info("[VOICE] WAKE THREAD CREATED")
    threading.Thread(target=listen_for_wake_word, daemon=True).start()
    logger.info("Wake word listener thread started.")
    print(f'Standby mode -- say "{voice_runtime.WAKE_WORD}" to activate...')

    from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat
    update_subcomponent_heartbeat("voice_listener", status="healthy")

    running = True
    from JARVIS.core.voice.ses_motoru import VoiceEngine
    while running:
        update_subcomponent_heartbeat("voice_listener", status="healthy")
        if not wake_state.active:
            VoiceEngine().set_listener_state("LISTENING")
            time.sleep(0.2)
            continue

        VoiceEngine().set_listener_state("ACTIVE")
        active_start = time.time()
        print("[VOICE] COMMAND LISTEN STARTED", flush=True)
        logger.info("[VOICE] COMMAND LISTEN STARTED")
        command = listen_for_command()

        if command:
            print(f"[VOICE] COMMAND RECOGNIZED: {command}", flush=True)
            logger.info("[VOICE] COMMAND RECOGNIZED: %s", command)
            print("[VOICE] INTENT DETECTED", flush=True)
            logger.info("[VOICE] INTENT DETECTED")
            running = runtime_orchestrator.handle_runtime_command(
                command,
                logger=logger,
                process_command=process_command,
                handle_timer_command=handle_timer_command,
                say_goodbye=say_goodbye,
                maybe_tell_joke=maybe_tell_joke,
                record_runtime_event=record_runtime_event,
                wake_state=wake_state,
            )
            if not running:
                continue

        if runtime_orchestrator.should_return_to_standby(active_start, voice_runtime.ACTIVE_TIMEOUT):
            wake_state.active = False
            logger.info("Returned to standby mode.")
            print(f'💤 Returned to standby — say "{voice_runtime.WAKE_WORD}" to activate...')
        else:
            wake_state.active = False
