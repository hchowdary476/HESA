"""
Robust Microphone & VAD Pipeline for HESA / SAI.

Replaces fixed-duration recording windows with dynamic Voice Activity Detection (VAD)
and end-of-speech silence detection.

Pipeline flow:
Microphone -> Audio Stream -> VAD / Energy Filter -> Audio Chunk -> Faster-Whisper
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from JARVIS.core.system.utils.jarvis_logging import get_file_logger
from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat

logger = logging.getLogger("jarvis.audio")
_audio_logger = get_file_logger("jarvis.audio")


class MicrophonePipeline:
    """
    Microphone Stream Handler with dynamic VAD and End-of-Speech Detection.

    Parameters:
    - device_index: sounddevice device ID (None for default input device)
    - sample_rate: 16000 Hz
    - chunk_size: 512 frames per block (~32ms)
    - silence_threshold_rms: RMS threshold above which speech is detected
    - max_speech_duration: Maximum duration in seconds before forcing transcription (default 15.0)
    - silence_duration_seconds: Silence duration after speech to trigger end-of-speech (default 0.8s)
    """

    def __init__(
        self,
        device_index: int | None = None,
        sample_rate: int = 16000,
        chunk_size: int = 512,
        silence_threshold_rms: float = 300.0,
        max_speech_duration: float = 15.0,
        silence_duration_seconds: float = 0.8,
    ) -> None:
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold_rms = silence_threshold_rms
        self.max_speech_duration = max_speech_duration
        self.silence_duration_seconds = silence_duration_seconds

        self._stream: sd.InputStream | None = None
        self._is_listening = False
        self._cancel_flag = threading.Event()
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._worker_thread: threading.Thread | None = None

        self._on_speech_captured: list[Callable[[sr.AudioData], None]] = []
        self._on_speech_start: list[Callable[[], None]] = []
        self._on_speech_end: list[Callable[[], None]] = []

    def add_speech_captured_callback(self, cb: Callable[[sr.AudioData], None]) -> None:
        self._on_speech_captured.append(cb)

    def add_speech_start_callback(self, cb: Callable[[], None]) -> None:
        self._on_speech_start.append(cb)

    def add_speech_end_callback(self, cb: Callable[[], None]) -> None:
        self._on_speech_end.append(cb)

    @staticmethod
    def calculate_rms(pcm_data: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy of 16-bit PCM audio block."""
        if not pcm_data:
            return 0.0
        shorts = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        if len(shorts) == 0:
            return 0.0
        mean_sq = np.mean(shorts**2)
        return float(np.sqrt(mean_sq))

    def start_listening(self) -> bool:
        """Start non-blocking background audio listener loop."""
        if self._is_listening:
            return True

        self._cancel_flag.clear()
        self._audio_queue = queue.Queue()

        def audio_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            if status:
                _audio_logger.warning("[MIC_PIPELINE] Audio stream status: %s", status)
            if self._is_listening:
                self._audio_queue.put(indata.tobytes())

        try:
            # Resolve the best input device (prefers WASAPI on Windows)
            from JARVIS.core.voice.microphone import _resolve_best_input_device, _try_open_input_stream

            resolved_device, host_api_name = _resolve_best_input_device(self.device_index)

            self._stream = _try_open_input_stream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_size,
                device=resolved_device,
                callback=audio_callback,
            )
            self._is_listening = True

            self._worker_thread = threading.Thread(
                target=self._vad_listener_loop,
                daemon=True,
                name="mic-vad-pipeline",
            )
            self._worker_thread.start()

            _audio_logger.info("[MIC_PIPELINE] Listening active (device=%s, host_api=%s)", resolved_device, host_api_name)
            print(f"[VOICE] MIC PIPELINE STARTED (host_api={host_api_name})", flush=True)
            update_subcomponent_heartbeat("microphone_pipeline", status="healthy")
            return True

        except Exception as exc:
            self._is_listening = False
            _audio_logger.error("[MIC_PIPELINE] Failed to start microphone: %s", exc, exc_info=True)
            print(f"[VOICE_ERROR] Microphone start failed: {exc}", flush=True)
            update_subcomponent_heartbeat("microphone_pipeline", status="error", details={"error": str(exc)})
            return False

    def stop_listening(self) -> None:
        """Stop audio input stream and background worker loop."""
        self._is_listening = False
        self._cancel_flag.set()

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        _audio_logger.info("[MIC_PIPELINE] Listening stopped")
        print("[VOICE] MIC PIPELINE STOPPED", flush=True)
        update_subcomponent_heartbeat("microphone_pipeline", status="stopped")

    def cancel_current_speech(self) -> None:
        """Cancel current speech accumulation buffer instantly."""
        self._cancel_flag.set()

    def capture_single_phrase(self, max_timeout: float = 10.0) -> sr.AudioData | None:
        """
        Synchronous utility: record audio from speech start until silence end.
        """
        if not self._is_listening:
            if not self.start_listening():
                return None
            should_stop_after = True
        else:
            should_stop_after = False

        audio_chunks: list[bytes] = []
        is_speaking = False
        speech_start_time = 0.0
        silence_start_time = 0.0
        start_wait_time = time.time()

        try:
            while time.time() - start_wait_time < max_timeout:
                if self._cancel_flag.is_set():
                    break
                try:
                    chunk = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                rms = self.calculate_rms(chunk)

                if not is_speaking:
                    if rms > self.silence_threshold_rms:
                        is_speaking = True
                        speech_start_time = time.time()
                        audio_chunks.append(chunk)
                        _audio_logger.info("[MIC_PIPELINE] Speech detected (RMS=%.1f)", rms)
                else:
                    audio_chunks.append(chunk)
                    curr_time = time.time()

                    # Max duration timeout check
                    if curr_time - speech_start_time > self.max_speech_duration:
                        _audio_logger.info("[MIC_PIPELINE] Max speech duration reached")
                        break

                    # End of speech silence check
                    if rms <= self.silence_threshold_rms:
                        if silence_start_time == 0.0:
                            silence_start_time = curr_time
                        elif curr_time - silence_start_time >= self.silence_duration_seconds:
                            _audio_logger.info("[MIC_PIPELINE] End of speech silence detected (%.1fs)", curr_time - silence_start_time)
                            break
                    else:
                        silence_start_time = 0.0

            if audio_chunks:
                full_raw = b"".join(audio_chunks)
                return sr.AudioData(full_raw, self.sample_rate, 2)
            return None

        finally:
            if should_stop_after:
                self.stop_listening()

    def _vad_listener_loop(self) -> None:
        """Continuous background VAD loop processing incoming PCM audio chunks."""
        audio_chunks: list[bytes] = []
        is_speaking = False
        speech_start_time = 0.0
        silence_start_time = 0.0

        while self._is_listening:
            if self._cancel_flag.is_set():
                audio_chunks.clear()
                is_speaking = False
                self._cancel_flag.clear()

            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            rms = self.calculate_rms(chunk)
            now = time.time()

            if not is_speaking:
                if rms > self.silence_threshold_rms:
                    is_speaking = True
                    speech_start_time = now
                    silence_start_time = 0.0
                    audio_chunks = [chunk]

                    for cb in self._on_speech_start:
                        try:
                            cb()
                        except Exception:
                            pass
            else:
                audio_chunks.append(chunk)

                # Check max speech duration
                if now - speech_start_time > self.max_speech_duration:
                    self._emit_speech_captured(audio_chunks)
                    audio_chunks = []
                    is_speaking = False
                    continue

                # Check end of speech silence
                if rms <= self.silence_threshold_rms:
                    if silence_start_time == 0.0:
                        silence_start_time = now
                    elif now - silence_start_time >= self.silence_duration_seconds:
                        self._emit_speech_captured(audio_chunks)
                        audio_chunks = []
                        is_speaking = False
                else:
                    silence_start_time = 0.0

    def _emit_speech_captured(self, chunks: list[bytes]) -> None:
        if not chunks:
            return
        full_raw = b"".join(chunks)
        audio_data = sr.AudioData(full_raw, self.sample_rate, 2)

        for cb in self._on_speech_end:
            try:
                cb()
            except Exception:
                pass

        for cb in self._on_speech_captured:
            try:
                cb(audio_data)
            except Exception as exc:
                _audio_logger.error("[MIC_PIPELINE] Callback error: %s", exc)


def get_microphone_pipeline() -> MicrophonePipeline:
    """Return a MicrophonePipeline instance."""
    return MicrophonePipeline()
