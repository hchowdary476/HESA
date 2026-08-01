import gc
import os
import sys

import psutil

from JARVIS.core.system.utils.activity_tracker import is_any_trim_prevented


def get_jarvis_ram_usage() -> float:
    """Return total RSS memory in MB of all active JARVIS-related processes."""
    total_bytes = 0
    try:
        current_process = psutil.Process()
        total_bytes += current_process.memory_info().rss
        # Include children
        for child in current_process.children(recursive=True):
            try:
                total_bytes += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Include any other sibling processes running JARVIS components
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                if proc.pid == current_process.pid or proc.pid in [c.pid for c in current_process.children(recursive=True)]:
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(cmdline).lower()
                if "JARVIS" in cmd or any(
                    svc in cmd
                    for svc in [
                        "voice_service",
                        "gesture_service",
                        "service_coordinator",
                        "ai_agents_service",
                        "cloud_service",
                        "supervisor",
                        "ui_jarvis_os",
                    ]
                ):
                    total_bytes += proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return total_bytes / (1024 * 1024)


def get_cache_size_mb() -> float:
    """Calculate total cache size in MB (temp files, pycache, etc.)."""
    total_bytes = 0
    cache_dirs = ["groq_cache", "provider_cache", "plugin_cache", ".pytest_cache", ".ruff_cache", "build", "dist"]

    # Try to find workspace root directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Measure specific cache folders
    for d in cache_dirs:
        path = os.path.join(root_dir, d)
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        total_bytes += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass

    # Recursively collect python bytecode caches (__pycache__)
    for root, dirs, files in os.walk(root_dir):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            for sub_root, sub_dirs, sub_files in os.walk(pycache_path):
                for f in sub_files:
                    try:
                        total_bytes += os.path.getsize(os.path.join(sub_root, f))
                    except Exception:
                        pass
    return total_bytes / (1024 * 1024)


def get_jarvis_active_threads() -> int:
    """Return count of active threads across all JARVIS processes."""
    total_threads = 0
    try:
        current_process = psutil.Process()
        total_threads += current_process.num_threads()
        for child in current_process.children(recursive=True):
            try:
                total_threads += child.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                if proc.pid == current_process.pid or proc.pid in [c.pid for c in current_process.children(recursive=True)]:
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(cmdline).lower()
                if "JARVIS" in cmd or any(
                    svc in cmd
                    for svc in [
                        "voice_service",
                        "gesture_service",
                        "service_coordinator",
                        "ai_agents_service",
                        "cloud_service",
                        "supervisor",
                        "ui_jarvis_os",
                    ]
                ):
                    total_threads += proc.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return total_threads


def get_jarvis_process_count() -> int:
    """Return count of active processes running JARVIS."""
    count = 0
    try:
        current_process = psutil.Process()
        count += 1
        for child in current_process.children(recursive=True):
            try:
                if child.is_running():
                    count += 1
            except Exception:
                pass

        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                if proc.pid == current_process.pid or proc.pid in [c.pid for c in current_process.children(recursive=True)]:
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(cmdline).lower()
                if "JARVIS" in cmd or any(
                    svc in cmd
                    for svc in [
                        "voice_service",
                        "gesture_service",
                        "service_coordinator",
                        "ai_agents_service",
                        "cloud_service",
                        "supervisor",
                        "ui_jarvis_os",
                    ]
                ):
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return count


def is_system_idle() -> bool:
    """Return True if system is idle (using Windows GetLastInputInfo, or CPU usage fallback)."""
    # CPU usage check
    cpu_idle = psutil.cpu_percent(interval=None) < 15.0

    if sys.platform == "win32":
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            idle_secs = millis / 1000.0
            # Consider system idle if no user input for more than 30 seconds AND CPU is low
            return idle_secs > 30.0 and cpu_idle

    return cpu_idle


def trim_memory():
    """Trigger Python GC collection and invoke native Windows EmptyWorkingSet API to trim RAM."""
    gc.collect()
    if sys.platform == "win32":
        import ctypes

        # Trim current process
        try:
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
        except Exception:
            pass

        # Trim other active JARVIS processes
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    if proc.pid == current_pid:
                        continue
                    cmdline = proc.info.get("cmdline") or []
                    cmd = " ".join(cmdline).lower()
                    if "JARVIS" in cmd or any(
                        svc in cmd
                        for svc in [
                            "voice_service",
                            "gesture_service",
                            "service_coordinator",
                            "ai_agents_service",
                            "cloud_service",
                            "supervisor",
                            "ui_jarvis_os",
                        ]
                    ):
                        # Open process with PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION (0x0100 | 0x0400 = 0x0500)
                        h_process = ctypes.windll.kernel32.OpenProcess(0x0500, False, proc.pid)
                        if h_process:
                            ctypes.windll.psapi.EmptyWorkingSet(h_process)
                            ctypes.windll.kernel32.CloseHandle(h_process)
                except Exception:
                    pass
        except Exception:
            pass


def trim_memory_if_eligible() -> bool:
    """Run Working Set Trimming ONLY when RAM > 85% AND system is idle, and no critical tasks are active."""
    # Check physical RAM percentage
    if psutil.virtual_memory().percent <= 85.0:
        return False

    # Check if system is idle
    if not is_system_idle():
        return False

    # Check if any voice recognition, TTS, face verification, or UI interaction is active
    if is_any_trim_prevented():
        return False

    trim_memory()
    return True
