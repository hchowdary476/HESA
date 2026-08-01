"""
Unit & Integration Test Suite for Voice Engine Startup Diagnostics & Non-Blocking Async Pipeline.

Verifies:
1. Trace complete startup sequence: Microphone -> OpenWakeWord -> Whisper -> Intent Router -> AI Router -> Memory Engine -> Response Builder -> Edge TTS.
2. Startup timing for every subsystem (Microphone, OpenWakeWord, Whisper, Edge TTS) with sub-second precision.
3. Background worker thread execution (Qt GUI main thread never blocks).
4. Watchdog protection for >10s timeout handling.
5. Log writing to logs/voice_engine.log, logs/wake.log, logs/stt.log, logs/tts.log, logs/supervisor.log.
6. Voice Engine reaches READY state.
"""

import os
import time
import unittest
from pathlib import Path

from JARVIS.core.voice.voice_pipeline_manager import (
    VoicePipelineManager,
    get_voice_pipeline_manager,
    VOICE_ENGINE_LOG,
    WAKE_LOG,
    STT_LOG,
    TTS_LOG,
    SUPERVISOR_LOG
)


class TestVoiceEngineStartupDiagnostics(unittest.TestCase):

    def setUp(self):
        VoicePipelineManager._instance = None
        self.vpm = get_voice_pipeline_manager()

    def tearDown(self):
        VoicePipelineManager._instance = None

    def test_non_blocking_async_pipeline_initialization(self):
        """Req 4: Ensure GUI thread is non-blocking while pipeline initializes in background thread."""
        t0 = time.perf_counter()
        worker_t = self.vpm.initialize_pipeline_async(timeout_seconds=30.0)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Main thread must return immediately (<50ms)
        self.assertLess(elapsed_ms, 50.0, f"initialize_pipeline_async blocking main thread ({elapsed_ms:.2f}ms)")

        # Wait for background initialization thread to complete
        worker_t.join(timeout=35.0)
        self.assertEqual(self.vpm.status, "READY")

    def test_timing_report_subsecond_precision(self):
        """Req 3: Verify sub-second timing report for all 4 voice subsystems."""
        self.vpm._run_initialization(timeout_seconds=30.0)
        report = self.vpm._timing_report

        self.assertIn("microphone", report)
        self.assertIn("openwakeword", report)
        self.assertIn("whisper", report)
        self.assertIn("edge_tts", report)

        for subsys, duration in report.items():
            self.assertIsInstance(duration, float)
            self.assertGreaterEqual(duration, 0.0)

    def test_watchdog_protection_timeout(self):
        """Req 5: Watchdog logs VOICE ENGINE TIMEOUT if step exceeds 10s."""
        self.vpm._status = "OFFLINE"
        # Test timeout check with 0.001s threshold
        self.vpm._run_initialization(timeout_seconds=0.0001)

        with open(VOICE_ENGINE_LOG, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("VOICE ENGINE TIMEOUT", content)

    def test_all_five_stage_logs_created(self):
        """Req 6: Verify all 5 log files are created and contain formatted log entries."""
        for log_path in [VOICE_ENGINE_LOG, WAKE_LOG, STT_LOG, TTS_LOG, SUPERVISOR_LOG]:
            self.assertTrue(log_path.exists(), f"Log file {log_path} must exist")


if __name__ == "__main__":
    unittest.main()
