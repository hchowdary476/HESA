import sys
import os

# ── Dummy stream wrapper for pythonw.exe (prevent NoneType stdout/stderr crashes) ──
class DummyStream:
    def __init__(self):
        self.encoding = "utf-8"
        self.errors = "replace"
    def write(self, s):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False
    def reconfigure(self, *args, **kwargs):
        pass

if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()
from JARVIS.core.voice import patch_microphone
import threading
import time
import ctypes
import ctypes.wintypes
from dotenv import load_dotenv
from JARVIS.core.system.utils.env_helper import find_env_file
from JARVIS.core.system.venv_resolver import get_resolved_env

# ── Crash reporter (must be imported before any other JARVIS code) ───────────
# This must be created AFTER root_dir is known; see main() below.
_crash_reporter = None

# ── UTF-8 console fix ───────────────────────────────────────────────────────
# Windows cmd/PowerShell defaults to CP1252 which cannot encode Unicode
# characters used in log output (✓ ✗ ⚙️ etc.).  Reconfigure stdout/stderr to
# UTF-8 so print() never raises UnicodeEncodeError regardless of the active
# code page.  PYTHONUTF8=1 / PYTHONIOENCODING env vars are also set so child
# processes inherit the same behaviour.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
    try:
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Add root folder to sys.path to resolve JARVIS modules
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
os.chdir(root_dir)

# Ensure PySide6 DLLs and QML plugins resolve correctly when launched via Windows autostart
try:
    import PySide6
    _pyside_dir = os.path.dirname(PySide6.__file__)
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(_pyside_dir)
        except Exception:
            pass
    if _pyside_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _pyside_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

from JARVIS.core.system.startup_manager import StartupManager
from JARVIS.core.system.environment_validator import EnvironmentValidator
from JARVIS.core.system.service_monitor import ServiceHealthMonitor
from JARVIS.gui.system_tray import SystemTrayManager
from JARVIS.gui.main_window import setup_gui_dashboard

_global_tray = None

def show_error_dialog(title, messages):
    """Simple PySide6 message dialog for errors"""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    msg_str = "\n".join(f"• {msg}" for msg in messages)
    QMessageBox.critical(
        None,
        title,
        f"JARVIS could not start due to the following errors:\n\n{msg_str}",
        QMessageBox.StandardButton.Close
    )

# ── Named-mutex single-instance guard ────────────────────────────────────────
_JARVIS_MUTEX_NAME = "Local\\JARVIS_GUI_SINGLETON_MUTEX_v2"
_jarvis_mutex_handle = None

def _acquire_named_mutex():
    """Attempt to create a named mutex. Returns handle on success, None if duplicate."""
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(
            None,   # default security
            True,   # initial owner
            _JARVIS_MUTEX_NAME
        )
        if not handle:
            return None
        # ERROR_ALREADY_EXISTS (183) means another instance owns the mutex
        if ctypes.windll.kernel32.GetLastError() == 183:
            ctypes.windll.kernel32.CloseHandle(handle)
            return None
        return handle
    except Exception:
        return None


def _bring_existing_to_focus():
    """Attempt to find and bring the existing HESA/JARVIS window to focus."""
    try:
        import ctypes
        titles = ["HESA CYBER INTERFACE", "JARVIS CYBER INTERFACE", "JARVIS", "J.A.R.V.I.S"]
        hwnd = None
        for title in titles:
            hwnd = ctypes.windll.user32.FindWindowW(None, title)
            if hwnd:
                break
        if hwnd:
            # SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        try:
            with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error focusing existing window: {e}\n")
        except Exception:
            pass
    return False


def main() -> int:
    global _jarvis_mutex_handle, _crash_reporter

    # ── Register atexit handler to ensure supervisor terminates background services ──
    import atexit
    def _write_supervisor_shutdown_flag():
        try:
            os.makedirs("logs", exist_ok=True)
            with open(os.path.join("logs", "shutdown.flag"), "w") as sf:
                sf.write(str(time.time()))
        except Exception:
            pass
    atexit.register(_write_supervisor_shutdown_flag)

    # ── Crash Reporter + Lifecycle Logger ────────────────────────────────────
    os.makedirs("logs", exist_ok=True)
    from JARVIS.core.system.utils.gui_lifecycle_logger import install_lifecycle_hooks, log_lifecycle, log_close_reason
    install_lifecycle_hooks()
    
    from JARVIS.core.system.gui_crash_reporter import GUICrashReporter
    _crash_reporter = GUICrashReporter(root_dir)
    _crash_reporter.install_global_handlers()
    log_lifecycle("MAIN_ENTRY", f"jarvis.py main() starting (PID {os.getpid()})")

    with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] jarvis.py main() starting...\n")

    # ── Primary: Windows named mutex (process-safe, no port collision) ────────
    _jarvis_mutex_handle = _acquire_named_mutex()
    if _jarvis_mutex_handle is None:
        _bring_existing_to_focus()
        with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exiting: Another instance is already running (named mutex locked).\n")
        _crash_reporter.log_shutdown("duplicate_instance_mutex", exit_code=0)
        log_close_reason("duplicate_instance_mutex", "Exiting because another instance is already running (mutex locked)")
        return 0

    # ── Secondary: port lock (keeps compatibility with supervisor/launcher) ────
    lock_socket = None
    try:
        from JARVIS.core.system.utils.port_manager import PortManager
        lock_socket = PortManager.acquire_service_lock("gui_dashboard", 19106)
        if lock_socket is None:
            _bring_existing_to_focus()
            with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exiting: Another instance is already running (port 19106 locked).\n")
            _crash_reporter.log_shutdown("duplicate_instance_port", exit_code=0)
            log_close_reason("duplicate_instance_port", "Exiting because another instance is already running (port 19106 locked)")
            if _jarvis_mutex_handle:
                ctypes.windll.kernel32.CloseHandle(_jarvis_mutex_handle)
                _jarvis_mutex_handle = None
            return 0
    except Exception as pe:
        with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Port lock check exception (non-fatal): {pe}\n")

    # ── Environment & Service Startup ────────────────────────────────────────
    validator = EnvironmentValidator()
    startup_mgr = StartupManager()
    
    validation_ok = validator.validate_all()
    report = validator.get_report()
    
    if not validation_ok:
        diag = startup_mgr.generate_diagnostics()
        if diag["failed_services"]:
            show_error_dialog("Service Initialization Failed", diag["failed_services"])
            if lock_socket:
                lock_socket.close()
            return 1
            
    ok = startup_mgr.initialize_all_services()
    if not ok:
        diag = startup_mgr.generate_diagnostics()
        if diag["failed_services"]:
            show_error_dialog("Service Initialization Failed", diag["failed_services"])
            if lock_socket:
                lock_socket.close()
            return 1

    # Step 1: Initialize PySide6 Application settings
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication.instance()
    if not app:
        log_lifecycle("GUI_CREATION_START", "QApplication initialization started")
        app = QApplication(sys.argv)
        app.setApplicationName("HESA")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("Open.Jarvis")
        log_lifecycle("GUI_CREATION_DONE", f"QApplication initialized, instance ID: {id(app)}")
    else:
        log_lifecycle("GUI_INSTANCE_EXISTS", f"QApplication instance already exists: {id(app)}")

    app.setQuitOnLastWindowClosed(False)
    log_lifecycle("QUIT_ON_LAST_WINDOW_CLOSED_SET", "app.setQuitOnLastWindowClosed(False) forced")
        
    icon_path = os.path.join(root_dir, "jarvis.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Step 4: Setup GUI Dashboard QML context
    _crash_reporter.log_lifecycle("GUI_LOAD_START", "Loading QML engine and main window")
    print("[4/4] Launching GUI Dashboard...")
    try:
        engine, bridge, avatar, avatar_timer = setup_gui_dashboard(app)
        # Anchor all top-level QML components to app to prevent Python GC
        app._engine = engine
        app._bridge = bridge
        app._avatar = avatar
        app._avatar_timer = avatar_timer
        
        # Connect to root window visibility and close events
        root_objs = engine.rootObjects()
        if root_objs:
            root_win = root_objs[0]
            log_lifecycle("WINDOW_INITIAL_VISIBILITY", f"visible={root_win.property('visible')}")
            
            # Trace show / hide times
            def on_visible_changed():
                vis = root_win.property("visible")
                if vis:
                    log_lifecycle("WINDOW_SHOW", "Root QML window became visible")
                else:
                    log_lifecycle("WINDOW_HIDE", "Root QML window was hidden")
            root_win.visibleChanged.connect(on_visible_changed)
            log_lifecycle("QML_WINDOW_LISTENERS_REGISTERED", "visibleChanged signal connected")
    except Exception as e:
        import traceback as _tb
        _crash_reporter.log_lifecycle("GUI_LOAD_FAILED", f"{e}")
        _crash_reporter.log_shutdown(f"QML load failed: {e}", exit_code=1)
        log_close_reason("GUI_LOAD_FAILED", f"QML load failed: {e}")
        show_error_dialog("GUI Dashboard Loading Failed", [str(e)])
        if lock_socket:
            lock_socket.close()
        return 1

    # ── QML warning/error capture ────────────────────────────────────────────
    def _on_qml_warning(warnings):
        for w in warnings:
            msg = f"{w.url().toString()}:{w.line()} — {w.description()}"
            _crash_reporter.log_qml_warning(msg)
            print(f"[QML WARNING] {msg}")
    engine.warnings.connect(_on_qml_warning)

    _crash_reporter.log_lifecycle("GUI_LOAD_DONE", "QML engine loaded, root objects present")

    # Step 5: Setup system tray integration
    global _global_tray
    _global_tray = SystemTrayManager(app)
    app.tray_icon = _global_tray
    tray = _global_tray
    
    # Connect tray signals to QML engine and system controls
    def on_open_dashboard():
        for obj in engine.rootObjects():
            obj.setProperty("visible", True)
            try:
                obj.showNormal()
                obj.raise_()
                obj.requestActivate()
            except Exception:
                pass
            
    def on_voice_toggle(enabled):
        # Write preferences configuration via ConfigManager dynamically if possible
        try:
            from JARVIS.config.manager import ConfigManager
            config_mgr = ConfigManager()
            config_mgr.load()
            config_mgr.set("voice.voice_enabled", enabled)
            config_mgr.save()
        except Exception:
            pass
        bridge.logReceived.emit(f"⚙️ Voice toggled to: {'ON' if enabled else 'OFF'}", "task")
        
    def on_restart():
        restart_flag = os.path.join("logs", "restart.flag")
        try:
            os.makedirs("logs", exist_ok=True)
            with open(restart_flag, "w") as f:
                f.write(str(time.time()))
            bridge.logReceived.emit("⚙️ Full system restart triggered...", "task")
        except Exception:
            pass
            
    def on_reload_plugins():
        try:
            pm = startup_mgr.services.get("plugin_manager")
            if pm:
                count = pm.discover_plugins()
                bridge.logReceived.emit(f"🔌 Reloaded plugins. Found: {count}", "ok")
        except Exception as e:
            bridge.logReceived.emit(f"⚠️ Reloading plugins failed: {str(e)}", "error")
            
    def on_show_diagnostics():
        diag = startup_mgr.generate_diagnostics()
        msg = f"Startup Duration: {diag['startup_duration']:.2f}s\n\nService Status:\n"
        for svc, status in diag['service_status'].items():
            msg += f"• {svc}: {status}\n"
        QMessageBox.information(None, "JARVIS Diagnostics & Status", msg)

    tray.sig_open_dashboard.connect(on_open_dashboard)
    tray.sig_voice_toggle.connect(on_voice_toggle)
    tray.sig_restart_jarvis.connect(on_restart)
    tray.sig_reload_plugins.connect(on_reload_plugins)
    tray.sig_show_diagnostics.connect(on_show_diagnostics)
    tray.sig_exit_completely.connect(bridge.exitApp)

    # Step 6: Setup health monitoring with tray notification callback
    monitor = ServiceHealthMonitor()
    for name, instance in startup_mgr.services.items():
        monitor.register_service(name, instance)
        # Set initial healthy state so tray shows green for all started services
        tray.update_service_status(name, "HEALTHY")

    from PySide6.QtCore import QObject, Signal

    class HealthSignalHelper(QObject):
        sig_health_event = Signal(str, str)

    health_helper = HealthSignalHelper()

    def _on_service_health_event(service_name, status):
        """Called from the monitor daemon thread — routes to tray via Qt signal."""
        health_helper.sig_health_event.emit(service_name, status)

    def _handle_health_event_gui(service_name, status):
        tray.update_service_status(service_name, status)
        # Also reflect in the GUI log panel
        status_icons = {
            "RESTARTING":  ("⟳", "task"),
            "RECOVERING":  ("↻", "task"),
            "RECOVERED":   ("✓", "ok"),
            "FAILED":      ("✗", "error"),
        }
        icon, kind = status_icons.get(status, ("•", "task"))
        bridge.logReceived.emit(
            f"{icon} Service '{service_name}': {status}", kind
        )

    health_helper.sig_health_event.connect(_handle_health_event_gui)
    monitor.set_notify_callback(_on_service_health_event)

    # Start health monitor daemon thread
    threading.Thread(target=monitor.monitor_loop, daemon=True).start()

    # Step 6.5: Periodically poll supervisor subprocess status from system_status.json
    # to bridge the multi-process supervisor state directly to the system tray.
    _supervisor_state_cache = {}

    def poll_supervisor_status():
        import json
        status_path = os.path.join(root_dir, "logs", "system_status.json")
        if not os.path.exists(status_path):
            return
        try:
            # Staleness check — if supervisor hasn't updated the file
            # in >30s, it's dead; treat all services as FAILED.
            _file_age = time.time() - os.path.getmtime(status_path)
            _is_stale = _file_age > 30.0

            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return  # grace/skip if file is locked or temporarily incomplete
        
        for name, info in data.items():
            if name == "safe_mode" or name.startswith("_"):
                continue
            if not isinstance(info, dict):
                continue

            if _is_stale:
                mapped = "FAILED"
            else:
                status_val = info.get("status", "Unknown").lower()
                
                # Map supervisor status to tray state
                if status_val == "running":
                    mapped = "HEALTHY"
                elif status_val == "recovering":
                    mapped = "RECOVERING"
                elif status_val in ("failed", "offline"):
                    mapped = "FAILED"
                elif status_val == "starting":
                    mapped = "RESTARTING"
                elif status_val == "stopping":
                    mapped = "FAILED"
                else:
                    mapped = "HEALTHY"

            prev = _supervisor_state_cache.get(name)
            if prev != mapped:
                _supervisor_state_cache[name] = mapped
                # Update tray + bridge logs
                _on_service_health_event(name, mapped)

    # Set up polling QTimer (every 2.5 seconds)
    status_timer = QTimer(app)
    status_timer.timeout.connect(poll_supervisor_status)
    status_timer.start(2500)
    # Store reference to prevent garbage collection
    app._status_timer = status_timer

    # ── Dedicated heartbeat QTimer (every 5s) — FIXES heartbeat race ────────
    # The metrics worker has a 1s startup delay and exception guard; this
    # dedicated timer guarantees dashboard_ui.json stays fresh regardless.
    def _write_gui_heartbeat():
        try:
            import json
            hb_dir = os.path.join("logs", "heartbeats")
            os.makedirs(hb_dir, exist_ok=True)
            with open(os.path.join(hb_dir, "dashboard_ui.json"), "w") as _hf:
                json.dump(
                    {"pid": os.getpid(), "timestamp": time.time(), "status": "healthy"},
                    _hf,
                )
        except Exception:
            pass

    _hb_timer = QTimer(app)
    _hb_timer.timeout.connect(_write_gui_heartbeat)
    _hb_timer.start(5000)   # every 5 seconds
    app._hb_timer = _hb_timer   # prevent GC
    _write_gui_heartbeat()  # write immediately so supervisor sees it at once


    # Step 7: Start multi-process supervisor core in background if it's not managed
    if os.environ.get("JARVIS_MANAGED") != "1":
        import subprocess, json
        env = os.environ.copy()
        env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
        # Set dashboard UI heartbeat initially so supervisor detects it running immediately
        hb_dir = os.path.join("logs", "heartbeats")
        os.makedirs(hb_dir, exist_ok=True)
        try:
            with open(os.path.join(hb_dir, "dashboard_ui.json"), "w") as f:
                json.dump({"pid": os.getpid(), "timestamp": time.time(), "status": "healthy"}, f)
        except Exception:
            pass

        # ── Write GUI heartbeat BEFORE launching supervisor ───────────────────
        # The supervisor's run_refresh_engine() orphan-killer reads this file to
        # learn which PID is the live GUI and must NOT be terminated.
        hb_dir = os.path.join("logs", "heartbeats")
        os.makedirs(hb_dir, exist_ok=True)
        try:
            import json as _json
            _hb_payload = {"pid": os.getpid(), "timestamp": time.time(), "status": "healthy"}
            _hb_file = os.path.join(hb_dir, "dashboard_ui.json")
            with open(_hb_file, "w") as f:
                _json.dump(_hb_payload, f)
            _crash_reporter.log_lifecycle(
                "GUI_PID_WRITTEN",
                f"GUI PID {os.getpid()} written to {_hb_file} before supervisor launch",
            )
        except Exception as _hb_err:
            _crash_reporter.log_lifecycle("GUI_PID_WRITE_FAIL", str(_hb_err))

        # Prefer pythonw.exe so the supervisor process never opens a console window.
        # Use the shared venv_resolver singleton — same path that EnvironmentValidator resolved.
        _resolved = get_resolved_env()
        _venv_root = _resolved.venv_root
        _venv_pythonw = (
            os.path.join(str(_venv_root), "Scripts", "pythonw.exe")
            if _venv_root else None
        )
        _supervisor_exe = (
            _venv_pythonw
            if _venv_pythonw and os.path.exists(_venv_pythonw)
            else _resolved.python_exe
        )

        supervisor_log = os.path.join(root_dir, "logs", "supervisor.log")
        try:
            os.makedirs(os.path.dirname(supervisor_log), exist_ok=True)
            sup_file = open(supervisor_log, "a", encoding="utf-8")
            sup_file.write(f"\n--- SUPERVISOR LAUNCH: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            sup_file.flush()
        except Exception:
            sup_file = subprocess.DEVNULL

        subprocess.Popen(
            [_supervisor_exe, "-m", "JARVIS.services.supervisor"],
            cwd=root_dir,
            env=env,
            stdout=sup_file,
            stderr=sup_file,
            # Fully detach from the parent console — no CMD window ever appears
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        bridge.logReceived.emit("⚙️ Multi-Process Supervisor Core: ACTIVE", "task")
    else:
        bridge.logReceived.emit("⚙️ Supervisor: MANAGED MODE", "task")

    # ── Supervisor watchdog ───────────────────────────────────────────────
    # Fires every 15 s.  If system_status.json is >45 s stale the supervisor
    # process has died; we relaunch it automatically without restarting the GUI.
    _watchdog_ss_path = os.path.join(root_dir, "logs", "system_status.json")

    def _relaunch_supervisor():
        """Re-spawn the supervisor subprocess (identical args to the initial launch)."""
        try:
            _resolved_wd = get_resolved_env()
            _venv_root_wd = _resolved_wd.venv_root
            _venv_pythonw_wd = (
                os.path.join(str(_venv_root_wd), "Scripts", "pythonw.exe")
                if _venv_root_wd else None
            )
            _sup_exe_wd = (
                _venv_pythonw_wd
                if _venv_pythonw_wd and os.path.exists(_venv_pythonw_wd)
                else get_resolved_env().python_exe
            )
            env_wd = os.environ.copy()
            env_wd["PYTHONPATH"] = root_dir + os.pathsep + env_wd.get("PYTHONPATH", "")
            sup_log_wd = os.path.join(root_dir, "logs", "supervisor.log")
            try:
                sup_fh_wd = open(sup_log_wd, "a", encoding="utf-8")
                sup_fh_wd.write(f"\n--- WATCHDOG RELAUNCH: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                sup_fh_wd.flush()
            except Exception:
                sup_fh_wd = subprocess.DEVNULL
            subprocess.Popen(
                [_sup_exe_wd, "-m", "JARVIS.services.supervisor"],
                cwd=root_dir,
                env=env_wd,
                stdout=sup_fh_wd,
                stderr=sup_fh_wd,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            )
        except Exception as _wd_err:
            bridge.logReceived.emit(f"⚠️ Watchdog relaunch failed: {_wd_err}", "error")

    _watchdog_last_relaunch = [0.0]  # mutable cell for closure

    def _supervisor_watchdog():
        """Check system_status.json age; relaunch supervisor if stale >45 s."""
        if os.environ.get("JARVIS_MANAGED") == "1":
            return  # managed mode — supervisor is an external orchestrator
        try:
            if not os.path.exists(_watchdog_ss_path):
                return  # not yet created at first boot
            ss_age = time.time() - os.path.getmtime(_watchdog_ss_path)
            if ss_age > 45.0:
                # Avoid relaunching more than once every 30 s
                if time.time() - _watchdog_last_relaunch[0] < 30.0:
                    return
                _watchdog_last_relaunch[0] = time.time()
                bridge.logReceived.emit(
                    f"⚙️ Supervisor stale ({ss_age:.0f}s). Auto-relaunching...",
                    "task",
                )
                _relaunch_supervisor()
        except Exception:
            pass

    _sup_watchdog_timer = QTimer(app)
    _sup_watchdog_timer.timeout.connect(_supervisor_watchdog)
    _sup_watchdog_timer.start(15_000)   # check every 15 seconds
    app._sup_watchdog_timer = _sup_watchdog_timer  # prevent GC

    tray.show()

    # ── Lifecycle: GUI fully ready ───────────────────────────────────────────
    _crash_reporter.log_lifecycle("GUI_READY", "Tray shown, event loop about to start")
    _crash_reporter.log_lifecycle("QAPPLICATION_EXISTS", f"QApplication instance: {id(app)}")
    root_objs = engine.rootObjects()
    _crash_reporter.log_lifecycle(
        "ROOT_OBJECTS",
        f"count={len(root_objs)} visible={root_objs[0].property('visible') if root_objs else 'N/A'}",
    )

    # Emit readiness state on bridge
    bridge.stateChanged.emit("STANDBY")

    # Surface any environment validation events in the GUI log panel (non-blocking)
    if report.get("venv_created"):
        bridge.logReceived.emit(
            f"⚙️ ENV REPAIR: virtual environment auto-created at "
            f"{report['venv_root']} (source: {report['venv_source']}). "
            f"See logs/venv_resolver.log",
            "task",
        )
    for warn in report.get("warnings", []):
        bridge.logReceived.emit(f"⚠️ ENV: {warn}", "task")
    if not report.get("valid"):
        for err in report.get("errors", []):
            bridge.logReceived.emit(f"✗ ENV ERROR: {err}", "error")

    bridge.logReceived.emit("✅ JARVIS Zero-Touch Startup complete. Ready, sir.", "ok")
    
    print("✓ JARVIS Ready")
    sys.stdout.flush()

    # Start Wake Word Listener Thread with Auto-Recovery
    from JARVIS.runtime.wake_listener import listen_for_wake_word
    from JARVIS.runtime.ui_bridge import send_log
    import logging

    def run_wake_listener_with_recovery():
        logger = logging.getLogger("jarvis.voice")
        while True:
            try:
                listen_for_wake_word(logger=logger, send_log=send_log)
            except BaseException as e:
                import traceback
                tb = traceback.format_exc()
                logger.error("Wake listener crashed: %s\n%s", e, tb)
                print(f"[ERROR] Wake listener crashed: {e}", flush=True)
                print(tb, flush=True)
            time.sleep(3)

    threading.Thread(
        target=run_wake_listener_with_recovery,
        daemon=True,
        name="WakeListener"
    ).start()

    log_lifecycle("EVENT_LOOP_START", "app.exec() entering Qt event loop")
    _crash_reporter.log_lifecycle("EVENT_LOOP_START", "app.exec() entering Qt event loop")
    _crash_reporter.log_event_loop_status(True, "app.exec() called")

    # ── aboutToQuit hook — logs every Qt-initiated shutdown ─────────────────
    def _on_about_to_quit():
        import traceback as _tb
        _stack = "".join(_tb.format_stack())
        log_lifecycle("ABOUT_TO_QUIT", "QApplication.aboutToQuit signal fired")
        log_close_reason("QApplication.aboutToQuit", f"QApplication.aboutToQuit fired — call stack:\n{_stack}", include_stack=False)
        _crash_reporter.log_lifecycle(
            "ABOUT_TO_QUIT",
            f"QApplication.aboutToQuit fired — call stack:\n{_stack}",
        )
        _crash_reporter.log_shutdown("aboutToQuit_signal", exit_code=0)
    app.aboutToQuit.connect(_on_about_to_quit)

    # ── Post-startup window visibility check ─────────────────────────────────
    # Fires 3 seconds after the event loop starts.  If the root QML window is
    # no longer visible at that point it means something hid it silently — we
    # log the anomaly and force it back to visible so the user sees the GUI.
    def _verify_window_visible():
        root_objs = engine.rootObjects()
        if not root_objs:
            _crash_reporter.log_lifecycle(
                "WINDOW_LOST",
                "ALERT: No root QML objects found 3s after event loop start!",
            )
            bridge.logReceived.emit(
                "⚠️ ALERT: Root QML window lost — attempting recovery", "error"
            )
            return
        win = root_objs[0]
        visible = win.property("visible")
        _crash_reporter.log_lifecycle(
            "WINDOW_CHECK",
            f"Post-startup visibility check: visible={visible}",
        )
        if not visible:
            _crash_reporter.log_lifecycle(
                "WINDOW_HIDDEN",
                "ALERT: Root window is NOT visible 3s after startup — forcing visible=True",
            )
            win.setProperty("visible", True)
            bridge.logReceived.emit(
                "⚠️ Root window was hidden — forced back to visible", "error"
            )
    QTimer.singleShot(3000, _verify_window_visible)

    exit_code = app.exec()

    _crash_reporter.log_event_loop_status(False, f"app.exec() returned exit_code={exit_code}")

    # Cleanup
    bridge.stop()
    avatar.stop()
    tray.hide()
    if lock_socket:
        lock_socket.close()
    # Release the named mutex so a fresh restart can acquire it
    if _jarvis_mutex_handle:
        ctypes.windll.kernel32.ReleaseMutex(_jarvis_mutex_handle)
        ctypes.windll.kernel32.CloseHandle(_jarvis_mutex_handle)
        _jarvis_mutex_handle = None

    with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] jarvis.py exited normally with code {exit_code}.\n")

    _crash_reporter.log_shutdown(f"clean_exit_code_{exit_code}", exit_code=exit_code)
    return exit_code

if __name__ == "__main__":
    # Ensure logs folder exists
    os.makedirs("logs", exist_ok=True)
    with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] jarvis.py main process execution started.\n")
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        err_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CRASH: {e}\n{traceback.format_exc()}"
        with open(os.path.join("logs", "startup.log"), "a", encoding="utf-8") as f:
            f.write(err_msg + "\n")
        with open(os.path.join("logs", "error.log"), "a", encoding="utf-8") as f:
            f.write(err_msg + "\n")
        sys.exit(1)
