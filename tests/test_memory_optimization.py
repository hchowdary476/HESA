import json
import os
import sys
import time
import unittest
from unittest.mock import patch


class TestMemoryOptimization(unittest.TestCase):
    def setUp(self):
        # Ensure activity status file is clean before test
        from JARVIS.core.system.utils.activity_tracker import STATE_FILE

        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except Exception:
                pass

    def test_lazy_loading(self):
        # Remove dependencies if cached in sys.modules to ensure pure lazy load verification
        for mod in ["cv2", "mediapipe", "pyautogui"]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import gesture_control
        from JARVIS.runtime import gesture_control

        # Assert they are NOT loaded at module import time
        self.assertNotIn("cv2", sys.modules)
        self.assertNotIn("mediapipe", sys.modules)
        self.assertNotIn("pyautogui", sys.modules)

        # Accessing supported trigger should try to load them without crashes
        supported = gesture_control.gesture_controller.is_supported()
        self.assertIsInstance(supported, bool)

    def test_activity_tracker(self):
        from JARVIS.core.system.utils import activity_tracker

        # Initially, no activity should be active
        self.assertFalse(activity_tracker.is_activity_active("voice_recognition"))
        self.assertFalse(activity_tracker.is_any_trim_prevented())

        # Set voice recognition active
        activity_tracker.set_activity("voice_recognition", True)
        self.assertTrue(activity_tracker.is_activity_active("voice_recognition"))
        self.assertTrue(activity_tracker.is_any_trim_prevented())

        # Set it inactive
        activity_tracker.set_activity("voice_recognition", False)
        self.assertFalse(activity_tracker.is_activity_active("voice_recognition"))
        self.assertFalse(activity_tracker.is_any_trim_prevented())

    def test_memory_helper_metrics(self):
        from JARVIS.core.system.utils import memory_helper

        ram = memory_helper.get_jarvis_ram_usage()
        self.assertGreater(ram, 0.0)

        cache = memory_helper.get_cache_size_mb()
        self.assertGreaterEqual(cache, 0.0)

        threads = memory_helper.get_jarvis_active_threads()
        self.assertGreater(threads, 0)

        processes = memory_helper.get_jarvis_process_count()
        self.assertGreater(processes, 0)

        idle = memory_helper.is_system_idle()
        self.assertIsInstance(idle, bool)

    def test_trimming_rules(self):
        from JARVIS.core.system.utils import activity_tracker, memory_helper

        # 1. Trimming should be skipped if RAM <= 85%
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.percent = 80.0
            eligible = memory_helper.trim_memory_if_eligible()
            self.assertFalse(eligible)

        # 2. Trimming should be skipped if system is active (not idle)
        with patch("psutil.virtual_memory") as mock_vm, patch("JARVIS.core.system.utils.memory_helper.is_system_idle", return_value=False):
            mock_vm.return_value.percent = 90.0
            eligible = memory_helper.trim_memory_if_eligible()
            self.assertFalse(eligible)

        # 3. Trimming should be skipped if critical interaction is active
        activity_tracker.set_activity("tts_playback", True)
        with patch("psutil.virtual_memory") as mock_vm, patch("JARVIS.core.system.utils.memory_helper.is_system_idle", return_value=True):
            mock_vm.return_value.percent = 90.0
            eligible = memory_helper.trim_memory_if_eligible()
            self.assertFalse(eligible)

    def test_service_coordinator_heartbeats(self):
        import shutil
        import tempfile

        from JARVIS.services.service_coordinator import ServiceCoordinator

        coordinator = ServiceCoordinator()

        # Use temp directory to isolate test heartbeats from background process
        temp_dir = tempfile.mkdtemp()
        coordinator.hb_dir = temp_dir

        try:
            # Clear old heartbeats to avoid reading stale files
            for name in ["automation_engine", "memory_engine", "security_engine"]:
                hb_path = os.path.join(coordinator.hb_dir, f"{name}.json")
                if os.path.exists(hb_path):
                    try:
                        os.remove(hb_path)
                    except Exception:
                        pass

            # Test heartbeat writing
            coordinator.start()
            # Sleep briefly for threads to write heartbeats
            time.sleep(2.0)

            hb_dir = coordinator.hb_dir
            for name in ["automation_engine", "memory_engine", "security_engine"]:
                hb_path = os.path.join(hb_dir, f"{name}.json")
                self.assertTrue(os.path.exists(hb_path))
                with open(hb_path) as f:
                    data = json.load(f)
                    self.assertEqual(data["status"], "healthy")
                    self.assertEqual(data["pid"], os.getpid())

            coordinator.stop()
        finally:
            shutil.rmtree(temp_dir)
