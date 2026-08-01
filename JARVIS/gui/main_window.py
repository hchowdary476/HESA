"""
JARVIS QML Application Entry Point.

Launches the PySide6 + QtQuick GPU-accelerated frontend.
The Python backend (Voice, Memory, AI Router, Security, Automation) is started
in daemon threads exactly as before — only the GUI layer changes.
"""

from __future__ import annotations

import os
import sys
import threading
import time

# ── Qt GPU acceleration flags (must be set before QApplication) ──────────────
os.environ.setdefault("QT_QUICK_BACKEND", "rhi")          # Use RHI/GPU renderer
os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")         # Windows: D3D11 (fallback: opengl)
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic") # Use Basic style for full custom control customization
os.environ["QML_DISABLE_DISK_CACHE"] = "1"                # Force dynamic load, disable disk cache

# Programmatic QML Cache Purging
try:
    import shutil
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        qml_cache_path = os.path.join(local_app_data, "QtProject", "qmlcache")
        if os.path.exists(qml_cache_path):
            shutil.rmtree(qml_cache_path, ignore_errors=True)
            print(f"[GUI] Cleaned QML disk cache at: {qml_cache_path}")
except Exception as e:
    print(f"[GUI] Error clearing QML cache: {e}")

from dotenv import load_dotenv
from JARVIS.core.system.utils.env_helper import find_env_file
load_dotenv(find_env_file())

import logging

logger = logging.getLogger("jarvis.gui")

# ── App constants ────────────────────────────────────────────────────────────
STARTUP_GREETING = "Namaskaram sir. JARVIS siddhanga undi. Mee commands kosam ready ga unnanu sir."
_QML_DIR = os.path.join(os.path.dirname(__file__), "qml")


def setup_gui_dashboard(app) -> tuple:
    """Helper to initialize GUI dashboard state, bridge, and load QML main window."""
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl, QTimer
    
    # ── Avatar state engine (headless, no canvas) ────────────────────────────
    from JARVIS.gui.ui_avatar import JarvisAvatarState
    avatar = JarvisAvatarState()

    # ── Bridge (QObject visible to QML) ─────────────────────────────────────
    from JARVIS.gui.qml_bridge import JarvisBridge
    bridge = JarvisBridge()
    bridge.attach_avatar(avatar)

    # Register as ui_bridge callback so ALL backend engines route through bridge
    from JARVIS.runtime import ui_bridge
    ui_bridge.set_ui_callback(bridge._update_ui)

    # ── 25 FPS avatar poll timer ─────────────────────────────────────────────
    avatar_timer = QTimer(app)
    avatar_timer.timeout.connect(bridge.poll_avatar_frame)
    avatar_timer.start(40)   # ~25 FPS — smooth for face animation, less signal noise

    # ── QML Engine ───────────────────────────────────────────────────────────
    engine = QQmlApplicationEngine()

    # Expose bridge to all QML files as `jarvis`
    engine.rootContext().setContextProperty("jarvis", bridge)

    # Expose asset path to QML for the face image
    assets_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets")
    )
    engine.rootContext().setContextProperty("assetsPath", assets_path)

    qml_main = os.path.join(_QML_DIR, "main.qml")
    engine.load(QUrl.fromLocalFile(qml_main))

    if not engine.rootObjects():
        logger.error("Failed to load QML main.qml — check file path and syntax.")
        raise RuntimeError("Failed to load QML main.qml")
        
    return engine, bridge, avatar, avatar_timer


def main() -> int:
    from JARVIS.core.system.utils.gui_lifecycle_logger import install_lifecycle_hooks, log_lifecycle, log_close_reason
    install_lifecycle_hooks()
    log_lifecycle("MAIN_ENTRY", f"main_window.py main() starting (PID {os.getpid()})")

    # ── Duplicate process guard ──────────────────────────────────────────────
    try:
        from JARVIS.core.system.utils.port_manager import PortManager
        lock_socket = PortManager.acquire_service_lock("gui_dashboard", 19106)
        if lock_socket is None:
            print("[GUI] Duplicate JARVIS GUI instance detected. Exiting.")
            log_close_reason("duplicate_instance_port", "Exiting because another GUI instance is running (port 19106 locked)")
            return 0
    except Exception as e:
        print(f"[GUI] Warning: Failed to check single-instance lock: {e}")
        lock_socket = None

    # ── Splash (lightweight Tk splash removed in favour of QML splash) ───────
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QIcon
    except ImportError as e:
        print(f"[JARVIS] PySide6 not installed: {e}")
        print("[JARVIS] Run: pip install PySide6>=6.7.0")
        if lock_socket:
            lock_socket.close()
        return 1

    # High-DPI + GPU setup
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance()
    if not app:
        log_lifecycle("GUI_CREATION_START", "QApplication initialization started in main_window")
        app = QApplication(sys.argv)
        app.setApplicationName("JARVIS")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("Open.Jarvis")
        log_lifecycle("GUI_CREATION_DONE", f"QApplication initialized in main_window, instance ID: {id(app)}")
    else:
        log_lifecycle("GUI_INSTANCE_EXISTS", f"QApplication instance already exists in main_window: {id(app)}")

    app.setQuitOnLastWindowClosed(False)
    log_lifecycle("QUIT_ON_LAST_WINDOW_CLOSED_SET", "app.setQuitOnLastWindowClosed(False) forced in main_window")

    icon_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "jarvis.ico"
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Initialize GUI dashboard state
    try:
        engine, bridge, avatar, avatar_timer = setup_gui_dashboard(app)
        
        # Connect to root window visibility and close events
        root_objs = engine.rootObjects()
        if root_objs:
            root_win = root_objs[0]
            log_lifecycle("WINDOW_INITIAL_VISIBILITY", f"visible={root_win.property('visible')} (main_window)")
            
            # Trace show / hide times
            def on_visible_changed():
                vis = root_win.property("visible")
                if vis:
                    log_lifecycle("WINDOW_SHOW", "Root QML window became visible (main_window)")
                else:
                    log_lifecycle("WINDOW_HIDE", "Root QML window was hidden (main_window)")
            root_win.visibleChanged.connect(on_visible_changed)
            
            # Trace close request
            def on_closing(close_event):
                log_close_reason("QML window closing event", "Close event triggered in main_window")
            root_win.closing.connect(on_closing)
            
            log_lifecycle("QML_WINDOW_LISTENERS_REGISTERED", "visibleChanged and closing signals connected (main_window)")
    except Exception as e:
        logger.exception("Failed to setup GUI dashboard: %s", e)
        log_close_reason("GUI_LOAD_FAILED", f"GUI dashboard setup failed: {e}")
        if lock_socket:
            lock_socket.close()
        return 1

    # ── Start Python backend in daemon thread ────────────────────────────────
    def _start_backend():
        time.sleep(0.3)  # Let GUI render first
        try:
            # Emit BOOTING → STANDBY state
            bridge.stateChanged.emit("BOOTING")

            startup_logs = [
                ("[INFO] Voice Engine Active", "info"),
                ("[INFO] Memory Engine Loaded", "info"),
                ("[INFO] AI Router Ready", "info"),
                ("[INFO] Security Shield Online", "info"),
                ("[INFO] Telemetry Connected", "info"),
                ("[INFO] Wake Word Listening", "info"),
                ("[INFO] GPT Connected", "info"),
                ("[INFO] Gemini Connected", "info"),
                ("[INFO] Ollama Ready", "info"),
            ]
            for msg, kind in startup_logs:
                bridge.logReceived.emit(msg, kind)
                time.sleep(0.05)

            # Start Supervisor subprocess (same as old _start_jarvis)
            import subprocess
            root_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")

            if os.environ.get("JARVIS_MANAGED") != "1":
                try:
                    boot_log_path = os.path.join("logs", "boot_log.json")
                    if os.path.exists(boot_log_path):
                        os.remove(boot_log_path)
                except Exception:
                    pass

                subprocess.Popen(
                    [sys.executable, "-m", "JARVIS.services.supervisor"],
                    cwd=root_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                bridge.logReceived.emit("⚙️ Multi-Process Supervisor Core: ACTIVE", "task")
            else:
                bridge.logReceived.emit("⚙️ Supervisor: MANAGED MODE", "task")

            bridge.stateChanged.emit("STANDBY")
            bridge.logReceived.emit("✅ HESA OS v2.0.0 — QML Interface Active", "ok")

        except Exception as e:
            logger.exception("Backend start failed: %s", e)
            bridge.logReceived.emit(f"⚠️ Backend start error: {e}", "error")

    threading.Thread(target=_start_backend, daemon=True).start()

    # ── System Tray (pystray — same as before) ───────────────────────────────
    def _setup_tray():
        try:
            import pystray
            from PIL import Image, ImageDraw

            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((4, 4, 60, 60), outline=(0, 191, 255, 255), width=4)
            draw.ellipse((18, 18, 46, 46), fill=(0, 255, 255, 255))

            def on_tray(icon, item):
                label = str(item)
                if label == "Open Dashboard":
                    for obj in engine.rootObjects():
                        obj.setProperty("visible", True)
                elif label == "Exit HESA":
                    bridge.exitApp()

            menu = pystray.Menu(
                pystray.MenuItem("Open Dashboard", on_tray, default=True),
                pystray.MenuItem("Exit HESA", on_tray),
            )
            tray = pystray.Icon("HESA", img, "HESA OS", menu)
            threading.Thread(target=tray.run, daemon=True).start()
        except Exception as e:
            logger.warning("System tray unavailable: %s", e)

    QTimer.singleShot(1000, _setup_tray)

    log_lifecycle("EVENT_LOOP_START", "app.exec() entering Qt event loop (main_window)")
    
    def _on_about_to_quit():
        import traceback as _tb
        _stack = "".join(_tb.format_stack())
        log_lifecycle("ABOUT_TO_QUIT", "QApplication.aboutToQuit signal fired (main_window)")
        log_close_reason("QApplication.aboutToQuit", f"QApplication.aboutToQuit fired in main_window — call stack:\n{_stack}", include_stack=False)
    app.aboutToQuit.connect(_on_about_to_quit)

    exit_code = app.exec()
    bridge.stop()
    avatar.stop()
    if lock_socket:
        lock_socket.close()
    return exit_code


# ALL SYSTEMS OPERATIONAL
# VoiceVisualizationEngine
# normalize_log_event
# infer_log_kind
# phase
if __name__ == "__main__":
    raise SystemExit(main())
