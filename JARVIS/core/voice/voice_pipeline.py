"""
JARVIS/HESA Voice Pipeline Bridge — Layer 3: Voice ↔ CognitiveCore Integration.

Connects Speech-to-Text (Faster-Whisper), Voice Activity Detection (MicrophonePipeline),
Wake Word (SAI), AI Router (AutonomousExecutor), PronunciationEngine, and Edge TTS (ses_motoru)
into a seamless, responsive, full-duplex-like voice communication system.

States:
  IDLE -> LISTENING -> TRANSCRIBING -> THINKING -> SPEAKING -> IDLE/LISTENING
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Optional

from JARVIS.core.system.utils.jarvis_logging import get_logger, get_file_logger
from JARVIS.core.voice.voice_state import VoiceState, VoiceStateMachine

logger = get_logger("voice_pipeline")
_voice_logger = get_file_logger("jarvis.voice")


# ---------------------------------------------------------------------------
# Conversational Follow-up Classifier
# ---------------------------------------------------------------------------

_CLARIFICATION_PHRASES = frozenset([
    "what do you mean", "can you clarify", "i don't understand",
    "explain that", "be more specific", "what exactly", "which one",
    "are you sure", "confirm that", "what did you say",
])

_CANCELLATION_PHRASES = frozenset([
    "cancel", "stop", "abort", "never mind", "forget it",
    "halt", "pause", "hold on", "wait", "ignore that",
])


def _is_clarification(text: str) -> bool:
    t = text.lower().strip()
    return any(p in t for p in _CLARIFICATION_PHRASES)


def _is_cancellation(text: str) -> bool:
    t = text.lower().strip()
    return any(p in t for p in _CANCELLATION_PHRASES)


# ---------------------------------------------------------------------------
# Voice Pipeline
# ---------------------------------------------------------------------------

class VoicePipeline:
    """
    Central bridge between hardware voice I/O, Faster-Whisper, Pronunciation Engine,
    Edge TTS, and HESA AI Router.
    """

    _instance: Optional[VoicePipeline] = None
    _lock = threading.Lock()

    def __new__(cls) -> VoicePipeline:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.state_machine = VoiceStateMachine()
        self._active_execution: Optional[threading.Thread] = None
        self._exec_lock = threading.Lock()

        # Configuration options
        self.barge_in_enabled: bool = os.getenv("JARVIS_BARGE_IN_ENABLED", "1") not in ("0", "false", "no")
        self.continuous_conversation_enabled: bool = os.getenv("JARVIS_CONTINUOUS_CONVERSATION", "0") in ("1", "true", "yes")
        self.wake_word_enabled: bool = os.getenv("JARVIS_WAKE_WORD_ENABLED", "1") not in ("0", "false", "no")

        # Callbacks registered by the GUI bridge or other consumers
        self._on_state_change: list[Callable[[str], None]] = []
        self._on_response: list[Callable[[str], None]] = []
        self._on_transcription: list[Callable[[str], None]] = []

        # Context chaining
        self._last_response: str = ""
        self._pending_clarification: str = ""

        logger.info("VoicePipeline initialized — SAI voice communication bridge active.")

    # ── Registration ──────────────────────────────────────────────────────────

    def on_state_change(self, cb: Callable[[str], None]) -> None:
        """Register a callback for pipeline state changes (for UI updates)."""
        self._on_state_change.append(cb)

    def on_response(self, cb: Callable[[str], None]) -> None:
        """Register a callback when SAI produces a response."""
        self._on_response.append(cb)

    def on_transcription(self, cb: Callable[[str], None]) -> None:
        """Register a callback when speech is transcribed."""
        self._on_transcription.append(cb)

    # ── Interruption & Barge-in ────────────────────────────────────────────────

    def handle_user_interruption(self) -> None:
        """Stop current speech output and active execution instantly when user speaks during TTS."""
        if not self.barge_in_enabled:
            return

        _voice_logger.info("[BARGE_IN] Genuine user speech detected during speech output — interrupting")
        print("[VOICE] BARGE-IN TRIGGERED — Stopping TTS playback", flush=True)

        try:
            from JARVIS.core.voice.ses_motoru import stop_playback
            stop_playback()
        except Exception as exc:
            logger.warning("Failed to stop playback during barge-in: %s", exc)

        self._interrupt_if_running()
        self.set_state(VoiceState.LISTENING, detail="barge_in")

    # ── Main Entry Points ─────────────────────────────────────────────────────

    def set_state(self, state: VoiceState | str, detail: str = "") -> None:
        """Transition state machine and broadcast to registered UI listeners."""
        res = self.state_machine.transition(state, detail=detail)
        if not res.get("ok"):
            res = self.state_machine.force(state, detail=detail)

        ui_state = self.state_machine.state.value
        _voice_logger.info("[VOICE_STATE] %s (detail=%s)", ui_state, detail)
        self._emit_state(ui_state)

    def process_audio_data(self, audio_data: Any, language: Optional[str] = None) -> None:
        """
        Transcribe recorded microphone AudioData via Faster-Whisper and dispatch to AI Router.
        """
        self.set_state(VoiceState.TRANSCRIBING, detail="whisper_stt")

        def _transcribe_and_dispatch():
            try:
                from JARVIS.core.voice.speech_backend import transcribe_audio
                import speech_recognition as sr

                rec = sr.Recognizer()
                text = transcribe_audio(rec, audio_data, language=language or "en-US")
                if text:
                    self.process_transcription(text)
                else:
                    _voice_logger.warning("[VOICE] STT produced no text result")
                    self.set_state(VoiceState.IDLE, detail="empty_stt")
            except Exception as exc:
                _voice_logger.error("[VOICE] STT processing error: %s", exc, exc_info=True)
                self.set_state(VoiceState.ERROR, detail=str(exc))

        threading.Thread(target=_transcribe_and_dispatch, daemon=True, name="voice-stt-dispatch").start()

    def process_transcription(self, text: str) -> None:
        """
        Called when a phrase is transcribed into text.
        """
        text = text.strip()
        if not text:
            self.set_state(VoiceState.IDLE, detail="empty_text")
            return

        print(f"[VOICE] TRANSCRIBED TEXT: '{text}'", flush=True)
        _voice_logger.info("[VOICE] Intent received: '%s'", text)
        self._emit_transcription(text)

        # Cancellation check
        if _is_cancellation(text):
            self._handle_cancellation()
            return

        # Clarification check
        if _is_clarification(text) and self._last_response:
            self._handle_clarification(text)
            return

        # Interrupt any running workflow if user provides new command
        self._interrupt_if_running()

        # Dispatch command to HESA AI Router
        self._dispatch_command(text)

    def handle_wake_word_detected(self) -> None:
        """Called by wake word detector when 'SAI' / 'Hey SAI' is heard."""
        _voice_logger.info("Wake word detected ('SAI') — entering LISTENING state.")
        self.set_state(VoiceState.WAKE_WORD_DETECTED, detail="wake_word")
        self.set_state(VoiceState.LISTENING, detail="listening_for_command")
        self._speak_notification("Hello Hemanth. How can I help you?")

    def handle_push_to_talk_start(self) -> None:
        """Called when Push-to-Talk button is pressed."""
        self.set_state(VoiceState.LISTENING, detail="push-to-talk")

    def handle_push_to_talk_end(self, transcribed_text: str) -> None:
        """Called when Push-to-Talk button is released with captured text."""
        self.process_transcription(transcribed_text)

    # ── Private Execution Dispatch ────────────────────────────────────────────

    def _dispatch_command(self, command: str) -> None:
        """Execute command through AutonomousExecutor and output response via Edge TTS."""
        def _run():
            self.set_state(VoiceState.THINKING, detail="ai_router")

            try:
                executor = self._get_executor()
                result = executor.handle_voice_command(command)
                response = result.response or ""

                print(f"[VOICE] AI RESPONSE: '{response[:100]}...'", flush=True)
                _voice_logger.info("AI Router produced response length=%d", len(response))

                self._last_response = response
                self._pending_clarification = ""

                self.set_state(VoiceState.SPEAKING, detail="tts_synthesis")
                self._emit_response(response)

                # Speak response through VoiceEngine (uses PronunciationEngine + Edge TTS)
                from JARVIS.core.voice.ses_motoru import VoiceEngine
                VoiceEngine().speak(response)

            except Exception as e:
                logger.error("VoicePipeline dispatch error: %s", e, exc_info=True)
                err_msg = "I encountered an internal fault. Please try again."
                self.set_state(VoiceState.ERROR, detail=str(e))
                self._speak_notification(err_msg)
                self._emit_response(err_msg)
            finally:
                if self.continuous_conversation_enabled:
                    self.set_state(VoiceState.LISTENING, detail="continuous_conversation")
                else:
                    self.set_state(VoiceState.IDLE, detail="ready")

        with self._exec_lock:
            t = threading.Thread(target=_run, daemon=True, name="voice_pipeline_exec")
            self._active_execution = t
            t.start()

    def _interrupt_if_running(self) -> None:
        """Cancel any in-flight workflow when a new command arrives."""
        with self._exec_lock:
            if self._active_execution and self._active_execution.is_alive():
                logger.info("Interrupting active workflow for new voice command.")
                try:
                    executor = self._get_executor()
                    executor.cancel()
                except Exception:
                    pass

    def _handle_cancellation(self) -> None:
        """User said 'stop' / 'cancel'."""
        self._interrupt_if_running()
        try:
            from JARVIS.core.voice.ses_motoru import stop_playback
            stop_playback()
        except Exception:
            pass
        self.set_state(VoiceState.IDLE, detail="cancelled")
        _voice_logger.info("Voice pipeline: cancellation processed.")

    def _handle_clarification(self, text: str) -> None:
        """User asked for clarification on the last response."""
        clarification_prompt = (
            f"The user wants clarification about your previous response: "
            f"'{self._last_response[:200]}'. "
            f"User question: '{text}'"
        )
        self._dispatch_command(clarification_prompt)

    # ── Notification Helpers ──────────────────────────────────────────────────

    def _speak_notification(self, text: str) -> None:
        """Speak a short system notification (non-blocking)."""
        def _s():
            try:
                from JARVIS.core.voice.ses_motoru import VoiceEngine
                VoiceEngine().speak(text)
            except Exception as e:
                logger.warning("TTS notification failed: %s", e)
        threading.Thread(target=_s, daemon=True).start()

    def _emit_state(self, state: str) -> None:
        for cb in self._on_state_change:
            try:
                cb(state)
            except Exception:
                pass

    def _emit_response(self, response: str) -> None:
        for cb in self._on_response:
            try:
                cb(response)
            except Exception:
                pass

    def _emit_transcription(self, text: str) -> None:
        for cb in self._on_transcription:
            try:
                cb(text)
            except Exception:
                pass

    # ── Lazy executor access ──────────────────────────────────────────────────

    @staticmethod
    def _get_executor():
        from JARVIS.core.system.autonomous_executor import get_executor
        return get_executor()

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self.state_machine.state.name,
            "barge_in_enabled": self.barge_in_enabled,
            "continuous_conversation": self.continuous_conversation_enabled,
            "wake_word_enabled": self.wake_word_enabled,
            "last_response_length": len(self._last_response),
            "pending_clarification": bool(self._pending_clarification),
            "active_execution": self._active_execution is not None
            and self._active_execution.is_alive(),
        }


def get_voice_pipeline() -> VoicePipeline:
    """Return the global singleton VoicePipeline."""
    return VoicePipeline()
