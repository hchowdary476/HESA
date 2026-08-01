#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║          JARVIS BACKGROUND LISTENER SERVICE                         ║
║          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║  Standalone Windows background service.                             ║
║  Runs at startup — monitors microphone for:                         ║
║    • Wake words: "Jarvis", "Hey Jarvis", "Friday"                   ║
║    • Double clap  → Launch JARVIS                                   ║
║    • Triple clap  → Open Full Dashboard                             ║
║                                                                      ║
║  Usage:                                                              ║
║    python listener_service.py              # run in foreground       ║
║    python listener_service.py --hidden     # run hidden (tray icon)  ║
║    python listener_service.py --install    # register startup        ║
║    python listener_service.py --uninstall  # remove from startup     ║
║    python listener_service.py --status     # check if running        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import subprocess
import sys
import threading
import time
import winreg
from pathlib import Path

# ── Setup paths ───────────────────────────────────────────────────────────────
_THIS_DIR   = Path(__file__).parent.resolve()
_JARVIS_PY  = _THIS_DIR / "jarvis.py"
_LOG_FILE   = _THIS_DIR / "logs" / "listener_service.log"
_PID_FILE   = _THIS_DIR / "logs" / "listener.pid"
_PYTHON     = sys.executable

# ── Logging ───────────────────────────────────────────────────────────────────
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("jarvis.listener_service")

# ── Import activation engine ──────────────────────────────────────────────────
try:
    sys.path.insert(0, str(_THIS_DIR))
    from JARVIS.runtime.smart_activation import (
        ActivationState,
        SmartActivationDaemon,
        create_activation_daemon,
    )
    _ENGINE_AVAILABLE = True
except ImportError as _e:
    logger.warning("smart_activation import failed: %s — using built-in fallback", _e)
    _ENGINE_AVAILABLE = False

# ── Windows process utilities ─────────────────────────────────────────────────
def _is_jarvis_running() -> bool:
    """Return True if jarvis.py is already running as a process."""
    try:
        import psutil
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                if "jarvis.py" in cmdline or "jarvis_ui" in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        # Fallback: use tasklist
        out = subprocess.run(
            ["tasklist", "/fo", "csv"],
            capture_output=True, text=True
        ).stdout
        if "python" in out.lower():
            return True
    return False


def _bring_jarvis_to_front() -> None:
    """Attempt to bring an already-running JARVIS window to the foreground."""
    try:
        import ctypes
        import psutil

        JARVIS_TITLES = ["HESA CYBER INTERFACE", "JARVIS CYBER INTERFACE", "JARVIS", "J.A.R.V.I.S"]
        hwnd = None
        for title in JARVIS_TITLES:
            hwnd = ctypes.windll.user32.FindWindowW(None, title)
            if hwnd:
                break

        if hwnd:
            # SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            logger.info("Brought JARVIS window to foreground (hwnd=%s)", hwnd)
    except Exception as exc:
        logger.debug("bring_to_front error: %s", exc)


def _launch_jarvis() -> subprocess.Popen | None:
    """Launch JARVIS.gui.main_window as a detached subprocess."""
    try:
        proc = subprocess.Popen(
            [_PYTHON, "-m", "JARVIS.gui.main_window"],
            cwd=str(_THIS_DIR),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            if platform.system() == "Windows" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Launched JARVIS.gui.main_window (PID=%d)", proc.pid)
        return proc
    except Exception as exc:
        logger.error("Failed to launch JARVIS.gui.main_window: %s", exc)
        return None


def _play_activation_sound() -> None:
    """Play a short system beep / activation sound."""
    try:
        import winsound
        winsound.Beep(880, 120)
        time.sleep(0.08)
        winsound.Beep(1320, 180)
    except Exception:
        pass


# ── Activation handler ────────────────────────────────────────────────────────
_activation_lock = threading.Lock()
_last_activation = 0.0
ACTIVATION_COOLDOWN = 8.0   # seconds between activations


def handle_activation(method: str) -> None:
    """Called when a wake event is detected (clap or wake word)."""
    global _last_activation
    with _activation_lock:
        now = time.time()
        if now - _last_activation < ACTIVATION_COOLDOWN:
            logger.debug("Activation ignored — cooldown active (%.1fs remaining)",
                         ACTIVATION_COOLDOWN - (now - _last_activation))
            return
        _last_activation = now

    logger.info("🚀 ACTIVATION via %s", method)
    _play_activation_sound()

    if _is_jarvis_running():
        logger.info("JARVIS already running — bringing to foreground")
        _bring_jarvis_to_front()
    else:
        logger.info("Launching JARVIS...")
        _launch_jarvis()
        # Give JARVIS 2 seconds to start
        time.sleep(2.0)


def handle_double_clap() -> None:
    """Double clap — open full dashboard (same as activation for now)."""
    logger.info("📊 Double clap — opening full dashboard")
    handle_activation("double_clap")


# ── Tray icon ─────────────────────────────────────────────────────────────────
def _create_tray_icon(daemon: "SmartActivationDaemon | None", stop_event: threading.Event) -> None:
    """Create a Windows system tray icon with status menu."""
    try:
        from PIL import Image, ImageDraw  # type: ignore
        import pystray  # type: ignore

        # Draw a simple cyan circle icon
        img = Image.new("RGB", (64, 64), color="#020810")
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill="#00D7FF", outline="#00FFC6", width=3)
        draw.ellipse([24, 24, 40, 40], fill="#020810")

        def _on_quit(icon, item):
            logger.info("Tray: quit requested")
            stop_event.set()
            icon.stop()

        def _on_status(icon, item):
            state = daemon.state.value if daemon else "UNKNOWN"
            clap = "✓" if (daemon and daemon.clap_available) else "✗"
            voice = "✓" if (daemon and daemon.voice_available) else "✗"
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"JARVIS Listener Status\n\nMode: {state}\nClap Detection: {clap}\nVoice Wake: {voice}\nLog: {_LOG_FILE}",
                "JARVIS Listener Service",
                0x40,
            )

        def _on_launch(icon, item):
            handle_activation("tray_manual")

        menu = pystray.Menu(
            pystray.MenuItem("JARVIS Listener — ACTIVE", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Launch JARVIS Now", _on_launch),
            pystray.MenuItem("Status", _on_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Listener", _on_quit),
        )

        icon = pystray.Icon("jarvis_listener", img, "JARVIS Listener", menu)
        icon.run()
    except ImportError:
        logger.info("pystray/Pillow not available — running without tray icon")
        stop_event.wait()
    except Exception as exc:
        logger.warning("Tray icon error: %s", exc)
        stop_event.wait()


# ── Windows Startup Registration ──────────────────────────────────────────────
_STARTUP_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_NAME  = "JarvisListenerService"


def install_startup() -> bool:
    """Register listener_service.py to run at Windows login (current user)."""
    cmd = f'"{_PYTHON}" "{Path(__file__).resolve()}" --hidden'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY,
                            access=winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _STARTUP_NAME, 0, winreg.REG_SZ, cmd)
        logger.info("✅ Startup registered: %s", cmd)
        print(f"✅ JARVIS Listener registered at Windows startup.\nCommand: {cmd}")
        return True
    except Exception as exc:
        logger.error("Failed to register startup: %s", exc)
        print(f"❌ Failed: {exc}")
        return False


def uninstall_startup() -> bool:
    """Remove listener_service.py from Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY,
                            access=winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _STARTUP_NAME)
        logger.info("✅ Startup entry removed.")
        print("✅ JARVIS Listener removed from Windows startup.")
        return True
    except FileNotFoundError:
        print("ℹ️  Not registered — nothing to remove.")
        return True
    except Exception as exc:
        logger.error("Failed to remove startup: %s", exc)
        print(f"❌ Failed: {exc}")
        return False


def check_status() -> None:
    """Print listener service status."""
    jarvis_running = _is_jarvis_running()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY) as key:
            val, _ = winreg.QueryValueEx(key, _STARTUP_NAME)
            startup_reg = f"REGISTERED\n   Command: {val}"
    except FileNotFoundError:
        startup_reg = "NOT REGISTERED"

    print(f"""
╔══════════════════════════════════════════════════╗
║        JARVIS LISTENER SERVICE STATUS            ║
╠══════════════════════════════════════════════════╣
║  JARVIS Running :  {"YES ✓" if jarvis_running else "NO  ✗"}                         ║
║  Startup Entry  :  {startup_reg[:30]:<30}  ║
║  Log File       :  {str(_LOG_FILE)[:30]:<30}  ║
╚══════════════════════════════════════════════════╝
""")


# ── Status display thread ─────────────────────────────────────────────────────
def _print_status_loop(daemon: "SmartActivationDaemon | None") -> None:
    """Print live status to console every 10 seconds."""
    while True:
        time.sleep(10)
        if daemon:
            state = daemon.state.value
            level = int(daemon.audio_level * 20)
            bar = "█" * level + "░" * (20 - level)
            clap = "✓" if daemon.clap_available else "✗"
            voice = "✓" if daemon.voice_available else "✗"
        else:
            state, bar, clap, voice = "FALLBACK", "░" * 20, "✗", "✗"
        print(
            f"\r🤖 JARVIS LISTENER | Mode:{state:9} | "
            f"Audio:[{bar}] | 👏:{clap} 🎤:{voice}",
            end="", flush=True,
        )


# ── Fallback listener (no smartactivation available) ─────────────────────────
def _run_fallback_listener(stop_event: threading.Event) -> None:
    """Minimal SpeechRecognition-only listener when smart_activation unavailable."""
    logger.info("Running fallback voice-only listener")
    try:
        import speech_recognition as sr  # type: ignore
        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        while not stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.15)
                    audio = r.listen(source, timeout=5, phrase_time_limit=4)
                text = ""
                try:
                    text = r.recognize_google(audio, language="en-US")
                except Exception:
                    pass
                if any(w in text.lower() for w in ["jarvis", "friday", "hey jarvis"]):
                    logger.info("🎤 Wake word detected: %s", text)
                    handle_activation(f"voice:{text}")
            except Exception:
                time.sleep(0.3)
    except Exception as exc:
        logger.error("Fallback listener error: %s", exc)


# ── Main entry ────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Background Listener Service")
    parser.add_argument("--hidden",    action="store_true", help="Run silently in system tray")
    parser.add_argument("--install",   action="store_true", help="Register as Windows startup item")
    parser.add_argument("--uninstall", action="store_true", help="Remove from Windows startup")
    parser.add_argument("--status",    action="store_true", help="Check service status")
    args = parser.parse_args()

    if args.install:
        return 0 if install_startup() else 1
    if args.uninstall:
        return 0 if uninstall_startup() else 1
    if args.status:
        check_status()
        return 0

    # ── Write PID file ────────────────────────────────────────────────────────
    _PID_FILE.write_text(str(os.getpid()))

    print("""
╔══════════════════════════════════════════════════╗
║        JARVIS LISTENER SERVICE                   ║
║        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║  Wake Words : Jarvis / Hey Jarvis / Friday       ║
║  Double Clap: Launch JARVIS                      ║
║  Triple Clap: Open Full Dashboard               ║
║                                                  ║
║  Press Ctrl+C to stop                            ║
╚══════════════════════════════════════════════════╝
""")

    stop_event = threading.Event()
    daemon = None

    if _ENGINE_AVAILABLE:
        daemon = create_activation_daemon(
            on_activate=handle_activation,
            on_double_clap=handle_double_clap,
        )
        daemon.start()
        logger.info("SmartActivationDaemon started — listening for wake events")
    else:
        # Fallback: simple voice recognition loop
        fb_thread = threading.Thread(
            target=_run_fallback_listener, args=(stop_event,), daemon=True
        )
        fb_thread.start()

    # Status printer
    threading.Thread(
        target=_print_status_loop, args=(daemon,), daemon=True
    ).start()

    if args.hidden:
        # Run silently with tray icon
        logger.info("Running in hidden/tray mode")
        _create_tray_icon(daemon, stop_event)
    else:
        # Console mode — wait for Ctrl+C
        logger.info("Running in console mode (Ctrl+C to stop)")
        try:
            while not stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Ctrl+C — stopping JARVIS Listener Service")
            stop_event.set()

    if daemon:
        daemon.stop()

    # Clean up PID file
    try:
        _PID_FILE.unlink()
    except Exception:
        pass

    logger.info("JARVIS Listener Service stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
