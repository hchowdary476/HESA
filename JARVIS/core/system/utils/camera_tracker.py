"""Centralized camera tracking and diagnostics utility for JARVIS."""

import sys
import threading
import time

# Priorities definition (lower number = higher priority)
PRIORITIES = {"Face Recognition": 1, "Security Shield": 2, "Gesture Engine": 3, "Diagnostics": 4, "Camera Probe": 5, "Unknown": 6}

# Thread-safe global stats
_lock = threading.RLock()
_total_opens = 0
_total_releases = 0
_active_handles = {}  # maps handle object ID to (handle, owner, start_time)

# Watchdog tracked variables
_current_owner = "None"
_last_open_time = 0.0
_last_release_time = 0.0
_active_duration = 0.0  # Cumulative active duration
_last_session_duration = 0.0

# Cache configurations
_last_probe_time = 0.0
_last_probe_status = "UNAVAILABLE"
_manual_test_status = "UNKNOWN"
PROBE_CACHE_COOLDOWN = 30.0  # 30 seconds cache


def has_higher_priority_owner(owner: str) -> bool:
    """Check if any currently active camera handle has a higher priority than the requesting owner."""
    req_priority = PRIORITIES.get(owner, PRIORITIES["Unknown"])
    with _lock:
        for _, active_owner, _ in _active_handles.values():
            active_priority = PRIORITIES.get(active_owner, PRIORITIES["Unknown"])
            if active_priority < req_priority:
                return True
    return False


def _acquire_lock(handle) -> bool:
    """Acquire the camera lock. Preempts active lower-priority owners if necessary."""
    global _total_opens, _current_owner, _last_open_time
    new_owner = handle.owner
    new_priority = PRIORITIES.get(new_owner, PRIORITIES["Unknown"])

    with _lock:
        # 1. Check if any active handle has a higher or equal priority
        for _, active_owner, _ in list(_active_handles.values()):
            active_priority = PRIORITIES.get(active_owner, PRIORITIES["Unknown"])
            if active_priority <= new_priority:
                # Access denied: active owner has higher or equal priority
                print(f"[CAMERA] Access denied for {new_owner}. Current owner: {active_owner} (Priority {active_priority})")
                sys.stdout.flush()
                return False

        # 2. Preempt all active handles with lower priority
        active_items = list(_active_handles.items())
        for handle_id, (active_handle, active_owner, _) in active_items:
            print(f"[CAMERA] Preempting {active_owner} (Priority {PRIORITIES.get(active_owner)}) for {new_owner} (Priority {new_priority})")
            sys.stdout.flush()
            active_handle.preempt()

        # 3. Register the new active handle
        _total_opens += 1
        _active_handles[id(handle)] = (handle, new_owner, time.time())
        _current_owner = new_owner
        _last_open_time = time.time()

        # Leak check
        if _total_opens > _total_releases:
            # We also check if this warning needs to print on open
            pass

        return True


def _register_release(handle, duration: float):
    """Register the release of a camera handle, updating stats and watchdog."""
    global _total_releases, _last_release_time, _active_duration, _last_session_duration, _current_owner
    with _lock:
        handle_id = id(handle)
        if handle_id in _active_handles:
            _total_releases += 1
            del _active_handles[handle_id]
            _last_release_time = time.time()
            _last_session_duration = duration
            _active_duration += duration

            # Update current owner
            if _active_handles:
                # Set to the most recently opened remaining handle
                remaining = sorted(_active_handles.values(), key=lambda x: x[2], reverse=True)
                _current_owner = remaining[0][1]
            else:
                _current_owner = "None"


def get_cached_camera_status(force_probe: bool = False) -> str:
    """Return camera readiness.
    If force_probe is False, it NEVER opens the camera and returns the active owner status or the manual test status (defaulting to UNKNOWN).
    If force_probe is True, it performs a physical probe, updates manual test status, and returns it.
    """
    global _manual_test_status, _last_probe_time, _last_probe_status

    # If a module (like Gesture Engine) already owns the camera, it is active and READY
    with _lock:
        if _active_handles:
            return "READY"

    if not force_probe:
        with _lock:
            return _manual_test_status

    now = time.time()
    with _lock:
        if now - _last_probe_time < PROBE_CACHE_COOLDOWN:
            return _last_probe_status

    # Perform a tracked probe
    try:
        cap = TrackedVideoCapture(0, owner="Camera Probe")
        if cap.isOpened():
            ret, _ = cap.read()
            status = "READY" if ret else "UNAVAILABLE"
        else:
            status = "UNAVAILABLE"
        cap.release()
    except Exception:
        status = "UNAVAILABLE"

    with _lock:
        _manual_test_status = status
        _last_probe_time = now
        _last_probe_status = status

    return status


def get_diagnostics_report() -> dict:
    """Return the Camera Diagnostics Report."""
    with _lock:
        # Determine continuous monitoring status (e.g. Gesture Engine is active)
        continuous_monitoring = "INACTIVE"
        for _, owner, _ in _active_handles.values():
            if owner == "Gesture Engine":
                continuous_monitoring = "ACTIVE"
                break

        # Handle leak check
        if _total_opens > _total_releases:
            print("[CAMERA WARNING] Unreleased camera handle detected")
            sys.stdout.flush()

        return {
            "current_owner": _current_owner,
            "total_opens": _total_opens,
            "total_releases": _total_releases,
            "unreleased_handles": len(_active_handles),
            "continuous_monitoring": continuous_monitoring,
            "last_open_time": _last_open_time,
            "last_release_time": _last_release_time,
            "active_duration": _active_duration,
            "last_session_duration": _last_session_duration,
        }


def generate_startup_report() -> str:
    """Generate and return Camera Health Report for JARVIS startup without opening the device."""
    status = "READY"
    owner = "None"

    with _lock:
        open_handles = len(_active_handles)
        if _active_handles:
            remaining = sorted(_active_handles.values(), key=lambda x: x[2], reverse=True)
            owner = remaining[0][1]
            status = "BUSY"

    report = f"""CAMERA HEALTH REPORT:
Status: {status}
Owner: {owner}
Open Handles: {open_handles}"""
    return report


class TrackedVideoCapture:
    """Wrapper around cv2.VideoCapture to track camera lifecycle and duration."""

    def __init__(self, index, owner="Unknown"):
        self.owner = owner
        self.index = index
        self.start_time = time.time()
        self.preempted = False
        self.cap = None

        # Try to acquire lock
        if not _acquire_lock(self):
            # Could not acquire (higher/equal priority active owner)
            return

        import cv2

        if self.owner != "Camera Probe":
            print(f"[CAMERA] Opened by {self.owner}")
            sys.stdout.flush()

        self.cap = cv2.VideoCapture(index)

    def isOpened(self) -> bool:
        if self.preempted or self.cap is None:
            return False
        return self.cap.isOpened()

    def read(self):
        if self.preempted or self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.preempted:
            return

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        duration = time.time() - self.start_time
        _register_release(self, duration)
        if self.owner != "Camera Probe":
            print(f"[CAMERA] Released by {self.owner}")
            print(f"[CAMERA] Active duration: {duration:.2f} seconds")
            sys.stdout.flush()

    def preempt(self):
        """Preempt this handle, closing its connection and updating registration."""
        self.preempted = True
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        duration = time.time() - self.start_time
        _register_release(self, duration)
        if self.owner != "Camera Probe":
            print(f"[CAMERA] Preempted: {self.owner} released camera connection")
            print(f"[CAMERA] Active duration: {duration:.2f} seconds")
            sys.stdout.flush()

    def __del__(self):
        """Destructor to ensure cleanup and check for leaks."""
        if hasattr(self, "cap") and self.cap is not None:
            print("[CAMERA WARNING] Unreleased camera handle detected")
            sys.stdout.flush()
            self.release()
