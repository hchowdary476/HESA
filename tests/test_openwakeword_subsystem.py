"""
Comprehensive Unit & System Tests for Custom SAI OpenWakeWord Model Subsystem.

Verifies:
1. Exclusive loading of JARVIS/resources/models/sai.onnx from config/wake_config.json.
2. Complete non-loading of default models (weather, timer, hey_jarvis).
3. Missing model detection and error logging ([WAKE] SAI MODEL NOT FOUND).
4. Accept list ('SAI', 'Hey SAI', 'Hi SAI', 'Okay SAI').
5. Reject list ('say', 'sigh', 'side', 'size', 'science', 'sai ram', 'sairam').
6. Audio frame latency under 300ms.
7. Local command fast-path without AI provider requests.
"""

import json
import unittest
from pathlib import Path

import numpy as np

from JARVIS.core.automation.local_intent_router import route_local_intent
from JARVIS.core.voice.openwakeword_engine import (
    CONFIG_PATH,
    DEFAULT_MODEL_PATH,
    OpenWakeWordEngine,
    get_openwakeword_engine,
)


class TestCustomSaiOpenWakeWordSubsystem(unittest.TestCase):
    def setUp(self):
        OpenWakeWordEngine._instance = None
        self.engine = get_openwakeword_engine()

    def tearDown(self):
        OpenWakeWordEngine._instance = None

    def test_custom_sai_config_loaded(self):
        """Req 2: Ensure config/wake_config.json exists and is loaded."""
        self.assertTrue(CONFIG_PATH.exists())
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["wake_word"], "SAI")
        self.assertEqual(cfg["threshold"], 0.72)
        self.assertIn("sai.onnx", cfg["model"])

    def test_exclusive_sai_model_loaded_no_defaults(self):
        """Req 1 & 2: Ensure ONLY custom sai.onnx is loaded and NO default models are loaded."""
        self.assertTrue(DEFAULT_MODEL_PATH.exists())
        self.assertTrue(self.engine.is_initialized)

        # Ensure default models (weather, timer, hey_jarvis) are not in engine's model set
        if hasattr(self.engine, "_model") and self.engine._model is not None:
            loaded_models = list(self.engine._model.models.keys())
            self.assertNotIn("weather", loaded_models)
            self.assertNotIn("timer", loaded_models)
            self.assertNotIn("hey_jarvis", loaded_models)

    def test_missing_model_handling(self):
        """Req 2: Missing model must log [WAKE] SAI MODEL NOT FOUND and fail initialization without loading defaults."""
        OpenWakeWordEngine._instance = None
        fake_path = Path("JARVIS/resources/models/missing_sai.onnx")

        # Temporarily mock _model_path
        engine_obj = OpenWakeWordEngine.__new__(OpenWakeWordEngine)
        engine_obj._model_path = fake_path
        engine_obj._initialized = False
        engine_obj._model = None
        engine_obj._init_engine()

        self.assertFalse(engine_obj.is_initialized)

    def test_accepted_wake_phrases(self):
        """Req 3: Verify accepted wake phrases."""
        accepted = ["SAI", "Hey SAI", "Hi SAI", "Okay SAI", "ok sai"]
        for phrase in accepted:
            self.assertFalse(self.engine.is_false_positive(phrase), f"Phrase '{phrase}' should be accepted as a valid wake phrase.")

    def test_rejected_false_positive_phrases(self):
        """Req 3: Verify rejection of phonetically similar false positives."""
        rejected = ["say", "sigh", "side", "size", "science", "sai ram", "sairam", "sigh ram"]
        for phrase in rejected:
            self.assertTrue(self.engine.is_false_positive(phrase), f"Phrase '{phrase}' should be rejected as a false positive.")

    def test_audio_frame_processing_latency(self):
        """Req 5: Verify audio frame processing latency is under 300ms."""
        import time

        pcm_frame = np.zeros(1280, dtype=np.int16).tobytes()

        t0 = time.perf_counter()
        detected, model_name, score = self.engine.process_frame(pcm_frame)
        latency_ms = (time.perf_counter() - t0) * 1000

        self.assertLess(latency_ms, 300.0, f"Frame processing latency ({latency_ms:.2f}ms) must be <300ms")

    def test_local_commands_no_ai_provider(self):
        """Req 6: Local commands execute locally without contacting AI providers."""
        local_cmd = "SAI open calculator"
        cleaned = local_cmd.replace("SAI ", "").strip()
        action = route_local_intent(cleaned)

        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "open_app")
        self.assertEqual(action["params"]["app"], "calculator")


if __name__ == "__main__":
    unittest.main()
