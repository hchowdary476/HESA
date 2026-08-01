"""
JARVIS Smart Activation Daemon
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs in background — monitors microphone for:
  • Double/Triple clap patterns
  • Wake words: "Jarvis", "Hey Jarvis", "Friday"

Manages 4-state FSM:
  STANDBY → ACTIVE → SLEEP → EMERGENCY

On activation: fires on_activate(method) callback.
"""

from __future__ import annotations

import difflib
import enum
import logging
import os
import queue
import threading
import time
from collections.abc import Callable

logger = logging.getLogger("jarvis.activation")

# ── Constants ──────────────────────────────────────────────────────────────────
# Import canonical phonetic aliases so smart_activation uses the same set as wake_word.py
from JARVIS.core.voice.wake_word import WAKE_ALIASES as _WAKE_ALIASES  # noqa: E402

WAKE_WORDS: list[str] = list(_WAKE_ALIASES) + ["friday", "wake up", "hesa wake up"]
CLAP_ENERGY_THRESHOLD = float(os.getenv("JARVIS_CLAP_THRESHOLD", "0.18"))
CLAP_SPIKE_DURATION_MAX = 0.12  # seconds — max clap duration
CLAP_WINDOW = 0.85  # seconds — single-clap detection window
DOUBLE_CLAP_WINDOW = 0.85  # seconds — double-clap detection window
TRIPLE_CLAP_WINDOW = 1.5  # seconds — triple-clap detection window
CLAP_MIN_SILENCE = 0.01  # seconds — min gap between claps
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.02  # 20ms chunks
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
WAKE_CONFIDENCE_MIN = 0.72  # fuzzy match threshold


# ── State Machine ──────────────────────────────────────────────────────────────
class ActivationState(enum.Enum):
    STANDBY = "STANDBY"
    ACTIVE = "ACTIVE"
    SLEEP = "SLEEP"
    EMERGENCY = "EMERGENCY"


class ActivationStateManager:
    """Thread-safe 4-state FSM for JARVIS activation."""

    def __init__(self) -> None:
        self._state = ActivationState.STANDBY
        self._lock = threading.Lock()
        self._listeners: list[Callable[[ActivationState], None]] = []

    @property
    def state(self) -> ActivationState:
        with self._lock:
            return self._state

    def transition(self, new_state: ActivationState) -> bool:
        """Transition to new_state. Returns True if state changed."""
        with self._lock:
            if self._state == new_state:
                return False
            old = self._state
            self._state = new_state
        logger.info("Activation state: %s → %s", old.value, new_state.value)
        for cb in self._listeners:
            try:
                cb(new_state)
            except Exception:
                logger.debug("State listener error", exc_info=True)
        return True

    def add_listener(self, fn: Callable[[ActivationState], None]) -> None:
        self._listeners.append(fn)

    def is_listening(self) -> bool:
        return self._state in (ActivationState.STANDBY, ActivationState.EMERGENCY)


# ── Clap Detector ──────────────────────────────────────────────────────────────
class ClapDetector:
    """
    Detects single/double clap patterns from a live audio stream.

    Uses sounddevice for streaming. Each 20ms chunk is analyzed for
    an energy spike above threshold followed by rapid silence.
    """

    def __init__(self, on_single_clap: Callable, on_double_clap: Callable) -> None:
        self._on_single = on_single_clap
        self._on_double = on_double_clap
        self._running = False
        self._clap_times: list[float] = []
        self._in_clap = False
        self._clap_start = 0.0
        self._audio_level = 0.0  # exposed for UI
        self._available = False
        self._stream = None

        try:
            import numpy  # noqa: F401
            import sounddevice  # type: ignore  # noqa: F401

            self._available = True
        except ImportError:
            logger.warning("sounddevice/numpy not installed — clap detection disabled.")

    @property
    def audio_level(self) -> float:
        return self._audio_level

    def start(self) -> None:
        if not self._available or self._running:
            return
        self._running = True
        t = threading.Thread(target=self._stream_loop, daemon=True, name="ClapDetector")
        t.start()

    def stop(self) -> None:
        self._running = False

    def _stream_loop(self) -> None:
        try:
            import numpy as np

            from JARVIS.core.voice.microphone import _resolve_best_input_device, _try_open_input_stream

            def _callback(indata, frames, time_info, status):
                if not self._running:
                    return
                chunk = indata[:, 0].astype(np.float32)
                energy = float(np.sqrt(np.mean(chunk**2)))
                self._audio_level = min(1.0, energy * 5.0)
                self._process_energy(energy)

            resolved_device, host_api_name = _resolve_best_input_device()
            stream = _try_open_input_stream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_SIZE,
                device=resolved_device,
                callback=_callback,
                latency="low",
            )
            try:
                while self._running:
                    time.sleep(0.05)
            finally:
                stream.stop()
                stream.close()
        except Exception as exc:
            logger.warning("ClapDetector stream error: %s", exc)

    def _process_energy(self, energy: float) -> None:
        now = time.time()

        # Spike detection
        if energy > CLAP_ENERGY_THRESHOLD and not self._in_clap:
            self._in_clap = True
            self._clap_start = now

        elif energy < CLAP_ENERGY_THRESHOLD * 0.4 and self._in_clap:
            duration = now - self._clap_start
            self._in_clap = False
            if duration < CLAP_SPIKE_DURATION_MAX:
                # Valid clap transient — record timestamp
                self._clap_times.append(now)
                self._evaluate_pattern(now)

    def _evaluate_pattern(self, now: float) -> None:
        # Prune old timestamps — keep within double-clap window
        self._clap_times = [t for t in self._clap_times if now - t < DOUBLE_CLAP_WINDOW]
        count = len(self._clap_times)

        # 2 claps within window → double clap (opens full dashboard)
        if count >= 2:
            span = self._clap_times[-1] - self._clap_times[-2]
            if span <= DOUBLE_CLAP_WINDOW:
                logger.info("👏👏 Double clap detected!")
                self._clap_times.clear()
                try:
                    self._on_double()
                except Exception:
                    logger.debug("Double clap callback error", exc_info=True)
                return

        # 1 clap detected — wait briefly for a potential second clap;
        # fire single-clap after the CLAP_WINDOW expires with only 1 event.
        if count == 1:
            # Schedule a delayed single-clap fire after CLAP_WINDOW elapses
            first_time = self._clap_times[0]

            def _fire_single_if_still_one():
                import time as _t

                _t.sleep(CLAP_WINDOW)
                if len(self._clap_times) == 1 and self._clap_times[0] == first_time:
                    logger.info("👏 Single clap detected!")
                    self._clap_times.clear()
                    try:
                        self._on_single()
                    except Exception:
                        logger.debug("Single clap callback error", exc_info=True)

            import threading as _th

            _th.Thread(target=_fire_single_if_still_one, daemon=True).start()


# ── Wake Word Listener ─────────────────────────────────────────────────────────
class WakeWordListener:
    """
    Continuously listens for wake words using SpeechRecognition.

    Fuzzy matching with confidence scoring allows slight mispronunciations.
    Supports offline Vosk and online Google fallback.
    """

    def __init__(self, on_wake: Callable[[str, float], None]) -> None:
        self._on_wake = on_wake
        self._running = False
        self._last_triggered = 0.0
        self._cooldown = 2.0  # seconds between triggers
        self._available = False

        try:
            import speech_recognition  # type: ignore  # noqa: F401

            self._available = True
        except ImportError:
            logger.warning("SpeechRecognition not installed — voice wake disabled.")

    def start(self) -> None:
        if not self._available or self._running:
            return
        self._running = True
        logger.info("Microphone detected")
        logger.info("Listening started")
        t = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordListener")
        t.start()

    def stop(self) -> None:
        self._running = False

    def _score(self, text: str) -> tuple[str, float]:
        """Fuzzy match text against wake words. Returns (best_match, confidence)."""
        text = text.strip().lower()
        best_word, best_score = "", 0.0
        for wake in WAKE_WORDS:
            # Exact substring check first (fast path)
            if wake in text:
                return wake, 1.0
            ratio = difflib.SequenceMatcher(None, text, wake).ratio()
            if ratio > best_score:
                best_score = ratio
                best_word = wake
        return best_word, best_score

    def _listen_loop(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore

            from JARVIS.core.voice.microphone import SoundDeviceMicrophone

            recognizer = sr.Recognizer()
            recognizer.energy_threshold = int(os.getenv("JARVIS_ENERGY_THRESHOLD", "300"))
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.6

            while self._running:
                try:
                    with SoundDeviceMicrophone() as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.15)
                        audio = recognizer.listen(source, timeout=4, phrase_time_limit=4)

                    text = ""
                    # Try offline first
                    try:
                        text = recognizer.recognize_vosk(audio)  # type: ignore
                    except Exception:
                        pass
                    if not text:
                        try:
                            text = recognizer.recognize_google(audio, language="en-US")
                        except Exception:
                            pass

                    if not text:
                        continue

                    match, confidence = self._score(text)
                    if confidence >= WAKE_CONFIDENCE_MIN:
                        now = time.time()
                        if now - self._last_triggered < self._cooldown:
                            continue
                        self._last_triggered = now
                        logger.info("🎤 Wake word '%s' detected (conf=%.2f)", match, confidence)
                        logger.info("Wake word detected")
                        try:
                            self._on_wake(match, confidence)
                        except Exception:
                            logger.debug("Wake callback error", exc_info=True)

                except Exception:
                    logger.debug("Wake listener cycle error", exc_info=True)
                    time.sleep(0.5)

        except Exception as exc:
            logger.warning("WakeWordListener fatal error: %s", exc)


# ── Smart Activation Daemon ────────────────────────────────────────────────────
class SmartActivationDaemon(threading.Thread):
    """
    Top-level activation daemon.

    Manages ClapDetector + WakeWordListener.
    Fires on_activate(method, state_manager) callbacks.

    Usage::

        daemon = SmartActivationDaemon(on_activate=my_callback)
        daemon.start()
    """

    def __init__(
        self,
        on_activate: Callable[[str], None] | None = None,
        on_double_clap: Callable[[], None] | None = None,
        on_state_change: Callable[[ActivationState], None] | None = None,
    ) -> None:
        super().__init__(daemon=True, name="SmartActivationDaemon")
        self._on_activate = on_activate
        self._on_double = on_double_clap
        self._on_state_change = on_state_change
        self._state_mgr = ActivationStateManager()
        self._event_queue: queue.Queue[tuple[str, str | float]] = queue.Queue()
        self._stop_event = threading.Event()

        if on_state_change:
            self._state_mgr.add_listener(on_state_change)

        self._clap_detector = ClapDetector(
            on_single_clap=self._handle_single_clap,
            on_double_clap=self._handle_double_clap,
        )
        self._wake_listener = WakeWordListener(
            on_wake=self._handle_wake_word,
        )

    # ── Public API ────────────────────────────────────────────────────────────
    @property
    def state(self) -> ActivationState:
        return self._state_mgr.state

    @property
    def audio_level(self) -> float:
        return self._clap_detector.audio_level

    @property
    def clap_available(self) -> bool:
        return self._clap_detector._available

    @property
    def voice_available(self) -> bool:
        return self._wake_listener._available

    def set_state(self, state: ActivationState) -> None:
        self._state_mgr.transition(state)

    def stop(self) -> None:
        self._stop_event.set()
        self._clap_detector.stop()
        self._wake_listener.stop()

    # ── Internal callbacks ────────────────────────────────────────────────────
    def _handle_single_clap(self) -> None:
        """Single clap → activate JARVIS."""
        if self._state_mgr.is_listening():
            self._event_queue.put(("activate", "single_clap"))

    def _handle_double_clap(self) -> None:
        """Double clap → open full dashboard."""
        self._event_queue.put(("double_clap", "double_clap"))

    def _handle_wake_word(self, word: str, confidence: float) -> None:
        if self._state_mgr.is_listening():
            self._event_queue.put(("activate", f"wake_word:{word}"))

    def _fire_activate(self, method: str) -> None:
        self._state_mgr.transition(ActivationState.ACTIVE)
        if self._on_activate:
            try:
                self._on_activate(method)
            except Exception:
                logger.debug("on_activate callback error", exc_info=True)

    def _fire_double(self) -> None:
        if self._on_double:
            try:
                self._on_double()
            except Exception:
                logger.debug("on_double callback error", exc_info=True)

    # ── Thread run ────────────────────────────────────────────────────────────
    def run(self) -> None:
        logger.info("SmartActivationDaemon started.")
        self._clap_detector.start()
        self._wake_listener.start()

        while not self._stop_event.is_set():
            try:
                event_type, payload = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if event_type == "activate":
                self._fire_activate(str(payload))
            elif event_type == "double_clap":
                self._fire_double()

        logger.info("SmartActivationDaemon stopped.")


# ── Convenience factory ───────────────────────────────────────────────────────
def create_activation_daemon(
    on_activate: Callable[[str], None],
    on_double_clap: Callable[[], None] | None = None,
    on_state_change: Callable[[ActivationState], None] | None = None,
) -> SmartActivationDaemon:
    """Create and return a configured SmartActivationDaemon (not yet started)."""
    return SmartActivationDaemon(
        on_activate=on_activate,
        on_double_clap=on_double_clap,
        on_state_change=on_state_change,
    )


__all__ = [
    "ActivationState",
    "ActivationStateManager",
    "ClapDetector",
    "WakeWordListener",
    "SmartActivationDaemon",
    "create_activation_daemon",
]
