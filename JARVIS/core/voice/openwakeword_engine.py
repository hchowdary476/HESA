"""
OpenWakeWord Engine for HESA / SAI Voice Subsystem.

Provides ultra-low latency (<300ms), low CPU (<5%), privacy-first local wake word detection
using custom SAI ONNX model without loading default models or requiring Picovoice access keys.

Primary Wake Word: SAI (also accepting 'Hey SAI', 'Hi SAI', 'Okay SAI')
Rejects False Positives: 'say', 'sigh', 'side', 'size', 'science', 'sai ram', 'sairam'
Logs wake events to logs/wake.log
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

import numpy as np

# Dedicated wake logger writing to logs/wake.log
WAKE_LOG_PATH = Path("logs/wake.log")
CONFIG_PATH = Path("config/wake_config.json")
DEFAULT_MODEL_PATH = Path("JARVIS/resources/models/sai.onnx")


def _setup_wake_file_logger() -> logging.Logger:
    WAKE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("hesa.wake")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(WAKE_LOG_PATH, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


wake_file_logger = _setup_wake_file_logger()


class OpenWakeWordEngine:
    """
    Singleton OpenWakeWord engine manager loading exclusively custom SAI ONNX model.
    Processes 16kHz PCM audio frames continuously without loading default models.
    """

    _instance: OpenWakeWordEngine | None = None
    _lock = threading.Lock()

    ACCEPTED_PHRASES = {"sai", "hey sai", "hi sai", "okay sai", "ok sai"}
    REJECTED_PHRASES = {"say", "sigh", "side", "size", "science", "sai ram", "sairam", "sigh ram"}

    def __new__(cls) -> OpenWakeWordEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._threshold = 0.72
                cls._instance._model_path = DEFAULT_MODEL_PATH
                cls._instance._model = None
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self) -> None:
        """Initialize OpenWakeWord loading exclusively custom SAI model configuration."""
        # Load configuration dynamically
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    cfg = json.load(f)
                    self._threshold = float(cfg.get("threshold", 0.72))
                    if not getattr(self, "_model_path", None) or self._model_path == DEFAULT_MODEL_PATH:
                        m_str = cfg.get("model", str(DEFAULT_MODEL_PATH))
                        self._model_path = Path(m_str)
            except Exception as e:
                wake_file_logger.warning("[WAKE] Error parsing config/wake_config.json: %s", e)

        print("[WAKE] Loading SAI wake model...", flush=True)
        wake_file_logger.info("[WAKE] Loading SAI wake model...")

        # Ensure custom SAI ONNX model exists
        if not self._model_path.exists():
            print("[WAKE] SAI MODEL NOT FOUND", flush=True)
            wake_file_logger.error("[WAKE] SAI MODEL NOT FOUND: %s", self._model_path)
            self._initialized = False
            return

        try:
            from openwakeword.model import Model

            # Load ONLY custom SAI model path. Never load default models.
            self._model = Model(wakeword_models=[str(self._model_path)], inference_framework="onnx")
            self._initialized = True

            print("[WAKE] Model loaded.", flush=True)
            print(f"[WAKE] Threshold = {self._threshold:.2f}", flush=True)
            print("[WAKE] Listening...", flush=True)

            wake_file_logger.info("[WAKE] Model loaded.")
            wake_file_logger.info("[WAKE] Threshold = %.2f", self._threshold)
            wake_file_logger.info("[WAKE] Listening...")
        except Exception as err:
            self._initialized = False
            wake_file_logger.error("[WAKE] OpenWakeWord initialization failed: %s", err)
            print(f"[WAKE] OpenWakeWord initialization failed: {err}", flush=True)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def process_frame(self, pcm_data: bytes | np.ndarray) -> tuple[bool, str, float]:
        """
        Process 16kHz 16-bit PCM frame data.
        Returns: (is_detected: bool, model_name: str, confidence: float)
        """
        if not self._initialized or self._model is None:
            return False, "", 0.0

        try:
            if isinstance(pcm_data, bytes):
                audio_frame = np.frombuffer(pcm_data, dtype=np.int16)
            else:
                audio_frame = pcm_data

            prediction = self._model.predict(audio_frame)

            for model_name, scores in prediction.items():
                max_score = float(np.max(scores)) if isinstance(scores, (list, np.ndarray)) else float(scores)
                if max_score >= self._threshold:
                    print("[WAKE] DETECTED: SAI", flush=True)
                    print("[VOICE] RECORDING COMMAND", flush=True)
                    print("[VOICE] STARTING WHISPER", flush=True)

                    wake_file_logger.info("[WAKE] DETECTED: SAI")
                    wake_file_logger.info("[VOICE] RECORDING COMMAND")
                    wake_file_logger.info("[VOICE] STARTING WHISPER")
                    return True, "SAI", max_score

            return False, "", 0.0
        except Exception as e:
            wake_file_logger.warning("[WAKE] Error processing audio frame: %s", e)
            return False, "", 0.0

    @classmethod
    def is_false_positive(cls, text: str) -> bool:
        """Check if transcribed text is a phonetically similar false positive."""
        if not text or not isinstance(text, str):
            return True

        normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()

        for rejected in cls.REJECTED_PHRASES:
            if normalized == rejected or normalized.startswith(rejected + " "):
                wake_file_logger.info("[WAKE] REJECTED false positive: '%s' (matches '%s')", text, rejected)
                return True

        return False


def get_openwakeword_engine() -> OpenWakeWordEngine:
    return OpenWakeWordEngine()
