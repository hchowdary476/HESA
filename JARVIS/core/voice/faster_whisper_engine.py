"""
Faster-Whisper Speech-to-Text Engine for HESA / SAI.

Provides non-blocking background initialization, singleton model caching,
automatic language detection (en, te, hi, ta, ml, kn), CPU/GPU inference,
and first-run download handling without freezing the HESA GUI.
"""

from __future__ import annotations

import io
import os
import sys
import time
import wave
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from JARVIS.core.system.utils.jarvis_logging import get_file_logger
from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat

logger = logging.getLogger("jarvis.stt")
_stt_logger = get_file_logger("jarvis.stt")
_voice_logger = get_file_logger("jarvis.voice")


class FasterWhisperEngine:
    """
    Singleton Manager for Faster-Whisper local Speech-to-Text model.

    Features:
    - Lazy / background non-blocking model initialization (no GUI freeze)
    - Model reuse (load once, transcribe many)
    - CPU (int8) inference default, optional GPU (cuda/float16)
    - Language auto-detection + multi-language support (en, te, hi, ta, ml, kn)
    - Graceful error handling & fallback availability checks
    """

    _instance: Optional[FasterWhisperEngine] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> FasterWhisperEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized_attributes = False
            return cls._instance

    def __init__(
        self,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[str] = None,
    ) -> None:
        if getattr(self, "_initialized_attributes", False):
            return
        self._initialized_attributes = True

        self.model_name = os.getenv("JARVIS_WHISPER_MODEL", model_name)
        self.device = os.getenv("JARVIS_WHISPER_DEVICE", device)
        self.compute_type = os.getenv("JARVIS_WHISPER_COMPUTE_TYPE", compute_type)
        self.download_root = download_root or os.getenv("JARVIS_WHISPER_CACHE")

        self.status = "UNINITIALIZED"
        self.last_error: Optional[str] = None
        self._model: Any = None
        self._init_lock = threading.Lock()
        self._init_thread: Optional[threading.Thread] = None

    def initialize_async(self) -> threading.Thread:
        """Launch non-blocking background initialization thread."""
        with self._init_lock:
            if self.status in ("READY", "LOADING"):
                return self._init_thread or threading.Thread()

            self.status = "LOADING"
            self._init_thread = threading.Thread(
                target=self._load_model_worker,
                daemon=True,
                name="faster-whisper-init",
            )
            self._init_thread.start()
            return self._init_thread

    def _load_model_worker(self) -> None:
        start_time = time.perf_counter()
        _stt_logger.info(
            "[FASTER-WHISPER] Starting model load: model=%s device=%s compute=%s",
            self.model_name,
            self.device,
            self.compute_type,
        )
        print(
            f"[STT] Loading Faster-Whisper model '{self.model_name}' on {self.device} ({self.compute_type})...",
            flush=True,
        )

        try:
            from faster_whisper import WhisperModel

            # Determine device & compute_type safely
            target_device = self.device
            target_compute = self.compute_type

            if target_device == "cuda":
                try:
                    import torch
                    if not torch.cuda.is_available():
                        _stt_logger.warning("[FASTER-WHISPER] CUDA requested but not available — falling back to CPU")
                        target_device = "cpu"
                        target_compute = "int8"
                except ImportError:
                    target_device = "cpu"
                    target_compute = "int8"

            model_kwargs: Dict[str, Any] = {
                "device": target_device,
                "compute_type": target_compute,
            }
            if self.download_root:
                model_kwargs["download_root"] = self.download_root

            self._model = WhisperModel(self.model_name, **model_kwargs)
            load_ms = (time.perf_counter() - start_time) * 1000

            self.status = "READY"
            self.last_error = None
            _stt_logger.info(
                "[FASTER-WHISPER] Model READY model=%s latency=%.0fms",
                self.model_name,
                load_ms,
            )
            _voice_logger.info(
                "[VOICE] Faster-Whisper STT engine READY (%s, %.0fms)",
                self.model_name,
                load_ms,
            )
            print(f"[STT] Faster-Whisper READY ({load_ms:.0f} ms)", flush=True)

            update_subcomponent_heartbeat(
                "faster_whisper",
                status="healthy",
                details={"model": self.model_name, "device": target_device},
            )

        except Exception as exc:
            self.status = "ERROR"
            self.last_error = str(exc)
            _stt_logger.error(
                "[FASTER-WHISPER] Failed to load model %s: %s", self.model_name, exc, exc_info=True
            )
            _voice_logger.error("[VOICE] Faster-Whisper model load failed: %s", exc)
            print(f"[STT_ERROR] Faster-Whisper model load failed: {exc}", flush=True)

            update_subcomponent_heartbeat(
                "faster_whisper",
                status="error",
                details={"error": str(exc)},
            )

    def is_ready(self) -> bool:
        return self.status == "READY" and self._model is not None

    def ensure_loaded(self, timeout: float = 15.0) -> bool:
        """Block until model is ready (used if transcription requested before background init finishes)."""
        if self.is_ready():
            return True

        if self.status == "UNINITIALIZED":
            t = self.initialize_async()
            t.join(timeout=timeout)
        elif self.status == "LOADING" and self._init_thread:
            self._init_thread.join(timeout=timeout)

        return self.is_ready()

    def transcribe(
        self,
        audio: Any,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Faster-Whisper.

        Accepts:
        - numpy float32 array (16000Hz PCM)
        - speech_recognition.AudioData
        - file path / str / Path
        - raw bytes (16-bit PCM wav)

        Returns dict:
        {"text": str, "language": str, "probability": float, "latency_ms": float}
        """
        if not self.ensure_loaded():
            _stt_logger.warning("[FASTER-WHISPER] Cannot transcribe: model not ready (status=%s)", self.status)
            return None

        t0 = time.perf_counter()

        try:
            audio_input = self._prepare_audio_input(audio)
            if audio_input is None:
                _stt_logger.warning("[FASTER-WHISPER] Audio preparation failed or empty audio payload")
                return None

            # Prepare language parameter (None for auto-detection)
            lang_code = language
            if lang_code:
                lang_code = lang_code.split("-")[0].lower()
                if lang_code not in ("en", "te", "hi", "ta", "ml", "kn"):
                    # Fall back to auto-detect for unhandled codes
                    lang_code = None

            segments, info = self._model.transcribe(
                audio_input,
                language=lang_code,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=False,
            )

            text_parts = []
            for segment in segments:
                if segment.text:
                    text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts).strip()
            lat_ms = (time.perf_counter() - t0) * 1000

            detected_lang = getattr(info, "language", "en")
            lang_prob = getattr(info, "language_probability", 1.0)

            _stt_logger.info(
                "[FASTER-WHISPER] SUCCESS lang=%s prob=%.2f lat=%.0fms result=\"%s\"",
                detected_lang,
                lang_prob,
                lat_ms,
                full_text[:80],
            )
            _voice_logger.info("[VOICE] Faster-Whisper transcribed (%s): '%s'", detected_lang, full_text)

            return {
                "text": full_text,
                "language": detected_lang,
                "probability": lang_prob,
                "duration": getattr(info, "duration", 0.0),
                "latency_ms": lat_ms,
            }

        except Exception as exc:
            _stt_logger.error("[FASTER-WHISPER] Transcription error: %s", exc, exc_info=True)
            _voice_logger.error("[VOICE] Faster-Whisper transcription error: %s", exc)
            return None

    def _prepare_audio_input(self, audio: Any) -> Any:
        """Convert input audio formats to numpy array or file object for Faster-Whisper."""
        import numpy as np

        # Case 1: numpy array
        if isinstance(audio, np.ndarray):
            if audio.dtype != np.float32:
                if audio.dtype == np.int16:
                    audio = audio.astype(np.float32) / 32768.0
                else:
                    audio = audio.astype(np.float32)
            return audio

        # Case 2: speech_recognition.AudioData
        try:
            import speech_recognition as sr
            if isinstance(audio, sr.AudioData):
                pcm = np.frombuffer(audio.frame_data, dtype=np.int16).astype(np.float32) / 32768.0
                if audio.sample_rate != 16000 and len(pcm) > 0:
                    new_len = int(len(pcm) * 16000 / audio.sample_rate)
                    pcm = np.interp(
                        np.linspace(0, len(pcm) - 1, new_len),
                        np.arange(len(pcm)),
                        pcm,
                    ).astype(np.float32)
                return pcm
        except ImportError:
            pass

        # Case 3: str / Path (filepath)
        if isinstance(audio, (str, Path)):
            path_str = str(audio)
            if os.path.exists(path_str):
                return path_str

        # Case 4: raw bytes (PCM int16)
        if isinstance(audio, bytes):
            pcm = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            return pcm

        return None


def get_faster_whisper_engine() -> FasterWhisperEngine:
    """Return the global singleton FasterWhisperEngine instance."""
    engine = FasterWhisperEngine()
    if engine.status == "UNINITIALIZED":
        engine.initialize_async()
    return engine
