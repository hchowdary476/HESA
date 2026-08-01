"""
Unit and Integration Tests for Supervisor, Diagnostics, UI State Disambiguation, and Voice Health.
"""

import socket
import unittest

from JARVIS.core.voice.voice_pipeline_manager import get_voice_pipeline_manager
from JARVIS.gui.ui_state import infer_state_from_message
from JARVIS.services.network_monitor_service import check_internet, get_ping_latency


class TestSupervisorAndDiagnostics(unittest.TestCase):
    def test_infer_state_from_message_filters_system_messages(self):
        # Service status / supervisor messages with "failed" or "error" must return None or non-ERROR
        sys_msgs = [
            "Service 'diagnostics_engine': FAILED",
            "Service 'network_monitor': FAILED",
            "[SUPERVISOR] Service voice_engine crashed/timed out",
            "[ServiceMonitor] Exception checking diagnostics: Error",
            "[ENV ERROR] Missing package",
            "⚙️ Multi-Process Supervisor Core: ACTIVE",
            "✓ Service 'ai_router': HEALTHY",
        ]
        for msg in sys_msgs:
            state = infer_state_from_message(msg)
            self.assertNotEqual(state, "ERROR", f"System message '{msg}' improperly set cockpit state to ERROR!")

    def test_infer_state_from_message_handles_actual_command_failure(self):
        # Explicit user command failure should set state to ERROR
        cmd_msgs = [
            "COMMAND FAILED: Unable to open file",
            "[command_error] Failed to execute target process",
            "User command error occurred",
        ]
        for msg in cmd_msgs:
            state = infer_state_from_message(msg)
            self.assertEqual(state, "ERROR")

    def test_socket_timeout_safety(self):
        # Verify socket.getdefaulttimeout() is NOT modified by network checks
        orig_timeout = socket.getdefaulttimeout()
        check_internet("8.8.8.8", 53, timeout=0.1)
        get_ping_latency("8.8.8.8", 53, timeout=0.1)
        current_timeout = socket.getdefaulttimeout()
        self.assertEqual(orig_timeout, current_timeout, "global socket timeout was altered!")

    def test_voice_pipeline_health_diagnostics(self):
        mgr = get_voice_pipeline_manager()
        diag = mgr.get_health_diagnostics()
        self.assertIn("overall_status", diag)
        self.assertIn("microphone", diag)
        self.assertIn("wakeword", diag)
        self.assertIn("vad", diag)
        self.assertIn("stt_whisper", diag)
        self.assertIn("ai_router", diag)
        self.assertIn("pronunciation_engine", diag)
        self.assertIn("edge_tts", diag)
        self.assertIn("speaker", diag)


if __name__ == "__main__":
    unittest.main()
