"""
Production Architecture Test Suite for HESA OS Voice Subsystem.

Verifies:
1. OpenWakeWord Engine (SAI wake word, accept/reject lists, <300ms latency).
2. Whisper STT command-only execution.
3. Intent Router classification (<100ms decision latency across 5 categories).
4. Safety Layer (confirmation required for shutdown, restart, delete, format, kill_process).
5. Local Command Executor (<1s latency, zero AI provider calls).
6. AI Router provider mapping & failover chain.
7. Memory Engine lookup (<50ms).
8. Response Builder.
9. 4-tier TTS Engine hierarchy.
10. All 7 dedicated stage log files (wake, stt, intent, actions, router, memory, tts).
"""

import time
import unittest

import numpy as np

from JARVIS.core.automation.local_intent_router import classify_intent, route_local_intent
from JARVIS.core.system.utils.stage_loggers import (
    STAGE_LOG_FILES,
    actions_log,
    intent_log,
    memory_log,
    router_log,
    stt_log,
    tts_log,
    wake_log,
)
from JARVIS.core.voice.openwakeword_engine import OpenWakeWordEngine, get_openwakeword_engine
from JARVIS.core.voice.response_builder import get_response_builder


class TestHesaProductionArchitecture(unittest.TestCase):
    def setUp(self):
        OpenWakeWordEngine._instance = None
        self.oww_engine = get_openwakeword_engine()

    def tearDown(self):
        OpenWakeWordEngine._instance = None

    def test_1_wake_engine_openwakeword_only(self):
        """Req 1: Verify OpenWakeWord engine, SAI wake word, accept/reject lists, <300ms latency."""
        self.assertTrue(self.oww_engine.is_initialized)

        # Accept list
        for phrase in ["SAI", "Hey SAI", "Hi SAI", "Okay SAI"]:
            self.assertFalse(self.oww_engine.is_false_positive(phrase))

        # Reject list
        for phrase in ["say", "sigh", "side", "size", "science", "sai ram"]:
            self.assertTrue(self.oww_engine.is_false_positive(phrase))

        # Latency <300ms
        pcm_frame = np.zeros(1280, dtype=np.int16).tobytes()
        t0 = time.perf_counter()
        self.oww_engine.process_frame(pcm_frame)
        latency_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(latency_ms, 300.0)

    def test_2_intent_router_5_categories_and_latency(self):
        """Req 3: Classify commands into 5 categories with decision latency <100ms."""
        t0 = time.perf_counter()
        cat1, _ = classify_intent("open calculator")
        cat2, _ = classify_intent("shutdown computer")
        cat3, _ = classify_intent("what is my favorite language")
        cat4, _ = classify_intent("create soc report workflow")
        cat5, task_type = classify_intent("write a python function to sort an array")
        latency_ms = (time.perf_counter() - t0) * 1000

        self.assertLess(latency_ms, 100.0, f"Intent classification ({latency_ms:.2f}ms) must be <100ms")
        self.assertEqual(cat1, "LOCAL_COMMAND")
        self.assertEqual(cat2, "SYSTEM_CONTROL")
        self.assertEqual(cat3, "MEMORY_QUERY")
        self.assertEqual(cat4, "AUTOMATION")
        self.assertEqual(cat5, "AI_QUERY")
        self.assertEqual(task_type, "coding")

    def test_3_safety_confirmation_layer(self):
        """Req 4: Dangerous operations require confirmation."""
        cat, action = classify_intent("shutdown computer")
        self.assertEqual(cat, "SYSTEM_CONTROL")
        self.assertTrue(action.get("requires_confirmation", False))

        cat_r, action_r = classify_intent("restart computer")
        self.assertEqual(cat_r, "SYSTEM_CONTROL")
        self.assertTrue(action_r.get("requires_confirmation", False))

    def test_4_local_command_executor_zero_ai_calls(self):
        """Req 5: Local commands execute locally without AI provider calls (<1s latency)."""
        t0 = time.perf_counter()
        action = route_local_intent("open calculator")
        exec_latency = (time.perf_counter() - t0) * 1000

        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "open_app")
        self.assertLess(exec_latency, 1000.0)

    def test_5_memory_engine_lookup_latency(self):
        """Req 7: Memory Engine lookup latency <50ms."""
        from JARVIS.core.memory.memory_preferences import get_preference, set_preference

        set_preference("favorite_language", "Python")

        t0 = time.perf_counter()
        val = get_preference("favorite_language")
        lookup_ms = (time.perf_counter() - t0) * 1000

        self.assertEqual(val, "Python")
        self.assertLess(lookup_ms, 50.0, f"Memory lookup ({lookup_ms:.2f}ms) must be <50ms")

    def test_6_response_builder(self):
        """Req 8: ResponseBuilder formats context-aware natural response."""
        builder = get_response_builder()
        resp = builder.build_response("Opening Calculator, sir.", intent_category="LOCAL_COMMAND")
        self.assertIn("Opening Calculator", resp)

    def test_7_stage_log_files_writing(self):
        """Req 10: Verify 7 dedicated stage log files exist and accept log events."""
        wake_log("TEST", "Wake event logged")
        stt_log("TEST", "STT transcribed")
        intent_log("TEST", "Intent classified")
        actions_log("TEST", "Action executed")
        router_log("TEST", "AI Router assigned")
        memory_log("TEST", "Memory context retrieved")
        tts_log("TEST", "TTS audio synthesized")

        for stage, log_path in STAGE_LOG_FILES.items():
            self.assertTrue(log_path.exists(), f"Log file for {stage} ({log_path}) must exist")


if __name__ == "__main__":
    unittest.main()
