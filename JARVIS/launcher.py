"""
JARVIS/launcher.py — pre-flight launcher that runs jarvis.py in a subprocess.

Validation is now fully delegated to venv_resolver + EnvironmentValidator so that:
  * Package errors are reported by name with their pip install command.
  * The venv path is discovered via the same 5-step detection order as the main process.
  * No separate, generic "Python Packages validation failed" dialog can occur.
  * Running this file with the system python (outside the venv) still works — the
    resolver will detect the mismatch, find or create the correct venv, and report
    each missing package by name.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path before any JARVIS imports so this
# works when invoked as `python JARVIS/launcher.py` from the project root OR
# as `python -m JARVIS.launcher` from anywhere.
# ---------------------------------------------------------------------------
_JARVIS_DIR = Path(__file__).resolve().parent  # .../Open.Jarvis-main/JARVIS
_PROJECT_ROOT = _JARVIS_DIR.parent  # .../Open.Jarvis-main

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


class Launcher:
    def __init__(self):
        self.jarvis_root = _PROJECT_ROOT
        self.log_file = self.jarvis_root / "logs" / "startup.log"

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def validate_environment(self) -> bool:
        """
        Pre-flight validation delegated entirely to venv_resolver +
        EnvironmentValidator.

        Returns True when it is safe to proceed.  On any error the dialog
        lists every failing item with its name and fix command — never a
        single generic message.
        """
        self._log("=== Environment validation starting ===")

        # Step 1: resolve the venv (auto-repair if necessary)
        try:
            from JARVIS.core.system.venv_resolver import get_resolved_env

            resolved = get_resolved_env()
            self._log(f"Resolved env: {resolved.source} -> {resolved.python_exe}")
            if resolved.created:
                self._log(f"[ENV REPAIR] Virtual environment was auto-created at {resolved.venv_root}. See logs/venv_resolver.log.")
        except Exception as exc:
            self._log(f"[ERROR] venv_resolver failed: {exc}")
            self._show_error_dialog(
                "Environment Resolver Error", [f"venv_resolver raised: {exc}", "Check logs/venv_resolver.log for details."]
            )
            return False

        # Step 2: run the full EnvironmentValidator (per-package checks etc.)
        try:
            from JARVIS.core.system.environment_validator import EnvironmentValidator

            validator = EnvironmentValidator()
            ok = validator.validate_all()
            report = validator.get_report()
        except Exception as exc:
            self._log(f"[ERROR] EnvironmentValidator raised: {exc}")
            self._show_error_dialog("Validation Error", [f"EnvironmentValidator raised: {exc}"])
            return False

        # Log warnings (non-blocking)
        for warn in report.get("warnings", []):
            self._log(f"[WARN] {warn}")

        if not ok:
            errors = report.get("errors", [])
            for err in errors:
                self._log(f"[FAIL] {err}")
            self._show_error_dialog("JARVIS Environment Errors", errors)
            return False

        self._log("=== Environment validation passed ===")
        return True

    def prevent_duplicate_instance(self) -> bool:
        """Check if JARVIS GUI is already running by probing the dashboard socket port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 19106))
            s.close()
            return True  # port free — safe to launch
        except OSError:
            self._log("JARVIS GUI already running (port 19106 bound). Skipping.")
            return False

    def launch_jarvis(self) -> int:
        """
        Launch jarvis.py using the resolver-derived venv python so the
        subprocess always runs inside the correct environment.
        """
        # Derive python_exe from the resolver (same singleton used by validator)
        python_exe: Path
        try:
            from JARVIS.core.system.venv_resolver import get_resolved_env

            resolved_str = get_resolved_env().python_exe
            pyw_str = resolved_str.replace("python.exe", "pythonw.exe")
            if os.name == "nt" and os.path.exists(pyw_str):
                python_exe = Path(pyw_str)
            else:
                python_exe = Path(resolved_str)
        except Exception:
            # Absolute fallback — use whichever Python is running right now
            python_exe = Path(sys.executable)

        main_script = self.jarvis_root / "jarvis.py"

        from JARVIS.core.system.utils.gui_lifecycle_logger import log_close_reason, log_lifecycle

        log_lifecycle(
            "LAUNCHER_PRE_FLIGHT", f"Initiating launch of {main_script} using {python_exe} (current sys.executable: {sys.executable})"
        )
        self._log(f"Interpreter diagnostics: sys.executable={sys.executable}, launch_python={python_exe}")

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.jarvis_root) + os.pathsep + env.get("PYTHONPATH", "")

        process = subprocess.Popen(
            [str(python_exe), str(main_script)],
            startupinfo=startupinfo,
            cwd=str(self.jarvis_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        log_lifecycle("LAUNCHER_SUBPROCESS_STARTED", f"JARVIS process spawned with PID {process.pid}")
        self._log(f"JARVIS launched with PID {process.pid} using {python_exe}. Waiting 5 seconds to verify background startup...")
        time.sleep(5.0)

        exit_code = process.poll()
        if exit_code is not None:
            self._log(f"[CRITICAL] JARVIS process {process.pid} exited immediately with code {exit_code}.")
            log_close_reason("LAUNCHER_DETECTION_IMMEDIATE_EXIT", f"Subprocess PID {process.pid} exited immediately with code {exit_code}")
        else:
            self._log(f"JARVIS process {process.pid} is running successfully. Launcher will wait for it...")
            try:
                exit_code = process.wait()
            except KeyboardInterrupt:
                process.terminate()
                exit_code = process.wait()
            self._log(f"JARVIS process {process.pid} has exited with code {exit_code}.")
            log_close_reason("LAUNCHER_SUBPROCESS_EXITED", f"Subprocess PID {process.pid} exited with code {exit_code}")

        return process.pid

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_configs(self) -> bool:
        """Ensure .env exists; copy from .env.example if needed."""
        env_file = self.jarvis_root / ".env"
        if not env_file.exists():
            example = self.jarvis_root / ".env.example"
            if example.exists():
                import shutil

                shutil.copy2(example, env_file)
                self._log("Created .env from .env.example")
        return env_file.exists()

    def _show_error_dialog(self, title: str, messages: list[str]) -> None:
        """
        Display a non-blocking error dialog that lists every item individually.
        Falls back to console output if tkinter is unavailable.
        """
        detail = "\n\n".join(f"• {m}" for m in messages)
        full_msg = f"JARVIS could not start:\n\n{detail}"
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, full_msg)
            root.destroy()
        except Exception:
            print(f"\n[{title}]\n{full_msg}\n", file=sys.stderr)

    def _log(self, message: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line, flush=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def get_status(self) -> str:
        """
        Determine and return the current runtime status of JARVIS:
          - running
          - minimized to tray
          - crashed
          - waiting for dependencies
          - stopped
        """
        # 1. Check if waiting for dependencies
        try:
            from JARVIS.core.system.venv_resolver import get_resolved_env

            resolved = get_resolved_env()
            if resolved.missing_packages or resolved.created:
                return "waiting for dependencies"
        except Exception:
            return "waiting for dependencies"

        # 2. Check if GUI Dashboard is running (port 19106 check)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        gui_running = False
        try:
            s.bind(("127.0.0.1", 19106))
            s.close()
        except OSError:
            gui_running = True

        if gui_running:
            # Check gui_state.json to distinguish visible vs tray
            gui_state_file = self.jarvis_root / "logs" / "gui_state.json"
            if gui_state_file.exists():
                try:
                    import json

                    with open(gui_state_file, encoding="utf-8") as f:
                        state_data = json.load(f)
                    if state_data.get("window_state") == "hidden":
                        return "minimized to tray"
                except Exception:
                    pass
            return "running"

        # 3. Check if crashed recently (within last 5 minutes / 300 seconds)
        error_log = self.jarvis_root / "logs" / "error.log"
        if error_log.exists():
            try:
                mtime = os.path.getmtime(str(error_log))
                if (time.time() - mtime) < 300:
                    return "crashed"
            except Exception:
                pass

        # 4. Check if supervisor is running
        sup_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sup_running = False
        try:
            sup_s.bind(("127.0.0.1", 19100))
            sup_s.close()
        except OSError:
            sup_running = True

        if sup_running:
            return "running"

        return "stopped"

    def run(self) -> bool:
        """Execute the full startup sequence."""
        self._log("=== JARVIS Launcher Initiated ===")
        current_status = self.get_status()
        self._log(f"Current JARVIS Status: {current_status}")

        if current_status in ["running", "minimized to tray"]:
            self._log("JARVIS is already running. Skipping launch.")
            return True

        if not self.prevent_duplicate_instance():
            self._log("Launch aborted: Duplicate instance detected.")
            return False

        if not self.validate_environment():
            self._log("Launch aborted: Environment validation failed.")
            return False

        # Ensure .env exists before handing off to jarvis.py
        self._check_configs()

        pid = self.launch_jarvis()
        self._log(f"=== Startup Sequence Completed (PID: {pid}) ===")
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JARVIS Launcher")
    parser.add_argument("--status", "-s", action="store_true", help="Report current JARVIS status and exit")
    args = parser.parse_args()

    launcher = Launcher()
    if args.status:
        status = launcher.get_status()
        print(f"JARVIS Status: {status}")
        sys.exit(0)
    else:
        launcher.run()
