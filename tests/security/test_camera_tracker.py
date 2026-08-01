"""Unit tests for Camera Resource Management and Tracker."""

import time
from unittest import mock
import pytest

from JARVIS.core.system.utils import camera_tracker
from JARVIS.core.system.utils.camera_tracker import TrackedVideoCapture, PRIORITIES

@pytest.fixture(autouse=True)
def reset_camera_tracker():
    """Reset the global variables in the camera tracker before each test."""
    with camera_tracker._lock:
        camera_tracker._total_opens = 0
        camera_tracker._total_releases = 0
        camera_tracker._active_handles.clear()
        camera_tracker._current_owner = "None"
        camera_tracker._last_open_time = 0.0
        camera_tracker._last_release_time = 0.0
        camera_tracker._active_duration = 0.0
        camera_tracker._last_session_duration = 0.0
        camera_tracker._last_probe_time = 0.0
        camera_tracker._last_probe_status = "UNAVAILABLE"
        camera_tracker._manual_test_status = "UNKNOWN"
    yield

def test_camera_priorities_exist():
    """Verify priorities are defined for key modules."""
    assert "Face Recognition" in PRIORITIES
    assert "Security Shield" in PRIORITIES
    assert "Gesture Engine" in PRIORITIES
    assert "Diagnostics" in PRIORITIES
    assert PRIORITIES["Face Recognition"] < PRIORITIES["Gesture Engine"]

def test_single_owner_and_preemption():
    """Verify that a higher priority module preempts a lower priority one."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        mock_cap = mock.Mock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap
        
        # 1. Gesture Engine (Priority 3) opens camera
        gesture_cap = TrackedVideoCapture(0, owner="Gesture Engine")
        assert gesture_cap.isOpened() is True
        assert camera_tracker._current_owner == "Gesture Engine"
        
        # 2. Face Recognition (Priority 1) opens camera, should preempt Gesture Engine
        face_cap = TrackedVideoCapture(0, owner="Face Recognition")
        assert face_cap.isOpened() is True
        assert gesture_cap.preempted is True
        assert gesture_cap.isOpened() is False
        assert camera_tracker._current_owner == "Face Recognition"
        
        # 3. Clean up
        face_cap.release()
        assert camera_tracker._current_owner == "None"

def test_access_denied_higher_priority_active():
    """Verify that a lower priority module cannot acquire camera if a higher priority one holds it."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        mock_cap = mock.Mock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap
        
        # 1. Face Recognition (Priority 1) opens camera
        face_cap = TrackedVideoCapture(0, owner="Face Recognition")
        assert face_cap.isOpened() is True
        
        # 2. Gesture Engine (Priority 3) tries to open camera, should be denied
        gesture_cap = TrackedVideoCapture(0, owner="Gesture Engine")
        assert gesture_cap.isOpened() is False
        assert gesture_cap.cap is None
        
        # 3. Clean up
        face_cap.release()

def test_handle_leak_warning(capsys):
    """Verify handle leak warning is printed when opens exceed releases on garbage collection/diagnostics."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        mock_cap = mock.Mock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap
        
        # Open handle but don't release it (simulate leak)
        cap = TrackedVideoCapture(0, owner="Diagnostics")
        # Direct deletion without calling release()
        cap.__del__()
        
        captured = capsys.readouterr()
        assert "[CAMERA WARNING] Unreleased camera handle detected" in captured.out

def test_dashboard_cached_status():
    """Verify dashboard cache policy avoids repeated VideoCapture calls."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        mock_cap = mock.Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, None)
        mock_vc.return_value = mock_cap
        
        # Call get_cached_camera_status twice with force_probe=True
        status1 = camera_tracker.get_cached_camera_status(force_probe=True)
        status2 = camera_tracker.get_cached_camera_status(force_probe=True)
        
        assert status1 == "READY"
        assert status2 == "READY"
        
        # VideoCapture should have been called only once due to the cache cooldown
        assert mock_vc.call_count == 1

def test_watchdog_tracking():
    """Verify camera watchdog tracks metrics correctly."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        mock_cap = mock.Mock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap
        
        cap = TrackedVideoCapture(0, owner="Diagnostics")
        time.sleep(0.01)
        cap.release()
        
        report = camera_tracker.get_diagnostics_report()
        assert report["total_opens"] == 1
        assert report["total_releases"] == 1
        assert report["current_owner"] == "None"
        assert report["active_duration"] > 0

def test_default_unknown_status():
    """Verify status defaults to UNKNOWN without calling VideoCapture when force_probe=False."""
    with mock.patch("cv2.VideoCapture") as mock_vc:
        status = camera_tracker.get_cached_camera_status(force_probe=False)
        assert status == "UNKNOWN"
        assert mock_vc.call_count == 0
