"""
debug_gui_launch.py — JARVIS GUI Diagnostic Launcher
=====================================================
Run this script from the project root to launch jarvis.py with full
real-time diagnostic output captured in the console window.

Usage:
    python debug_gui_launch.py

What it does:
  1. Clears stale lock / heartbeat files so no duplicate-instance false-positive
  2. Launches jarvis.py as a subprocess with stdout + stderr piped to console
  3. Monitors the process for up to 120 seconds, printing every line in real-time
  4. On exit: reads all four crash-reporter log files and prints a summary
  5. Generates GUI_RUNTIME_REPORT.md with root-cause hypothesis if the process
     exited before 10 seconds (crash detected)

Requirements: none beyond what jarvis.py already uses.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"

# ── Log file paths (same as GUICrashReporter) ───────────────────────────────
CRASH_LOG     = LOGS / "gui_crash.log"
TRACEBACK_LOG = LOGS / "gui_traceback.log"
LIFECYCLE_LOG = LOGS / "gui_lifecycle.log"
SHUTDOWN_LOG  = LOGS / "service_shutdown.log"
RUNTIME_RPT   = ROOT / "GUI_RUNTIME_REPORT.md"
CRASH_RPT     = ROOT / "GUI_CRASH_REPORT.md"

SEP = "=" * 70


def _print(msg: str) -> None:
    print(msg, flush=True)


def _read_tail(path: Path, lines: int = 40) -> str:
    """Return the last N lines of a file, or a placeholder if it doesn't exist."""
    if not path.exists():
        return f"  (not found: {path})"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return "\n".join(f"  {ln}" for ln in tail)
    except Exception as e:
        return f"  (read error: {e})"


def _clear_stale_locks() -> None:
    """Remove stale port-lock / shutdown flag files that may cause silent exits."""
    stale_files = [
        LOGS / "shutdown.flag",
        LOGS / "restart.flag",
    ]
    for f in stale_files:
        if f.exists():
            try:
                f.unlink()
                _print(f"[DEBUG] Removed stale flag: {f}")
            except Exception as e:
                _print(f"[DEBUG] Could not remove {f}: {e}")


def _stream_output(proc: subprocess.Popen, label: str) -> None:
    """Stream a subprocess pipe to stdout in a daemon thread."""
    stream = proc.stdout if label == "STDOUT" else proc.stderr
    if stream is None:
        return
    try:
        for raw_line in stream:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            _print(f"  [{label}] {line}")
    except Exception:
        pass


def _generate_crash_hypothesis(
    uptime_s: float,
    exit_code: int | None,
    lifecycle_tail: str,
) -> str:
    """Return a human-readable crash hypothesis based on collected evidence."""
    hypotheses = []

    if exit_code == 15:
        hypotheses.append(
            "EXIT CODE 15 (SIGTERM) -> An external process sent SIGTERM to the GUI. "
            "Most likely cause: the supervisor orphan-killer terminated jarvis.py. "
            "FIX: Verify the supervisor.py patch is applied (ROOT CAUSE 1)."
        )
    if exit_code == 1:
        hypotheses.append(
            "EXIT CODE 1 -> A critical service failed to initialise (StartupManager "
            "returned False) or QML failed to load. "
            "FIX: Check logs/jarvis_events.log for DEPENDENCY_FAILURE entries."
        )
    if exit_code == 0 and uptime_s < 10:
        hypotheses.append(
            "EXIT CODE 0 within <10s -> Duplicate-instance mutex or port 19106 lock "
            "detected a false positive. "
            "FIX: Ensure no stale process holds port 19106 or the named mutex."
        )
    if "ORPHAN_KILL" in lifecycle_tail:
        hypotheses.append(
            "ORPHAN_KILL event in lifecycle log -> supervisor terminated a process. "
            "FIX: Verify the supervisor.py patch is applied correctly."
        )
    if "QT_FATAL" in lifecycle_tail or "QT_CRITICAL" in lifecycle_tail:
        hypotheses.append(
            "Qt FATAL or CRITICAL message detected -> a Qt/QML-level error terminated the "
            "application before Python could catch it. "
            "FIX: Check gui_crash.log for QT_FATAL details."
        )
    if not hypotheses:
        hypotheses.append(
            "No specific pattern detected. Review gui_lifecycle.log for the last "
            "event before shutdown. The ABOUT_TO_QUIT event should include a call stack."
        )

    return "\n".join(f"  * {h}" for h in hypotheses)


def main() -> int:
    _print(SEP)
    _print("  JARVIS GUI DIAGNOSTIC LAUNCHER")
    _print(f"  Root: {ROOT}")
    _print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    _print(SEP)

    # Ensure logs directory exists
    LOGS.mkdir(exist_ok=True)

    # Clear stale flags
    _clear_stale_locks()

    # Find the correct Python interpreter
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    _print(f"\n[DEBUG] Using Python: {python_exe}")
    _print(f"[DEBUG] Launching: {ROOT / 'jarvis.py'}\n")
    _print(SEP)

    start_ts = time.time()

    try:
        proc = subprocess.Popen(
            [python_exe, str(ROOT / "jarvis.py")],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
        )
    except Exception as e:
        _print(f"[FATAL] Could not launch jarvis.py: {e}")
        return 1

    _print(f"[DEBUG] PID: {proc.pid}\n")

    # Stream stdout + stderr in background threads
    t_out = threading.Thread(target=_stream_output, args=(proc, "STDOUT"), daemon=True)
    t_err = threading.Thread(target=_stream_output, args=(proc, "STDERR"), daemon=True)
    t_out.start()
    t_err.start()

    # Monitor process (120-second window)
    MAX_WAIT = 120
    try:
        while True:
            elapsed = time.time() - start_ts
            rc = proc.poll()
            if rc is not None:
                break
            if elapsed > MAX_WAIT:
                _print(f"\n[DEBUG] Process still alive after {MAX_WAIT}s — detaching monitor.")
                _print("[DEBUG] GUI is running normally. Close it manually to see shutdown report.")
                t_out.join(timeout=2)
                t_err.join(timeout=2)
                return 0
            time.sleep(0.5)
    except KeyboardInterrupt:
        _print("\n[DEBUG] Ctrl-C pressed — sending SIGTERM to GUI process...")
        proc.terminate()
        proc.wait(timeout=5)

    uptime_s = time.time() - start_ts
    exit_code = proc.returncode

    t_out.join(timeout=3)
    t_err.join(timeout=3)

    _print(f"\n{SEP}")
    _print("  GUI PROCESS EXITED")
    _print(f"  Uptime  : {uptime_s:.2f}s")
    _print(f"  Exit code: {exit_code}")
    _print(SEP)

    # Read all four crash-reporter log files
    lifecycle_tail = _read_tail(LIFECYCLE_LOG)

    _print("\n-- gui_lifecycle.log (last 40 lines) --")
    _print(lifecycle_tail)

    _print("\n-- gui_crash.log (last 40 lines) --")
    _print(_read_tail(CRASH_LOG))

    _print("\n-- gui_traceback.log (last 40 lines) --")
    _print(_read_tail(TRACEBACK_LOG))

    _print("\n-- service_shutdown.log (last 20 lines) --")
    _print(_read_tail(SHUTDOWN_LOG, lines=20))

    if CRASH_RPT.exists():
        _print("\n-- GUI_CRASH_REPORT.md --")
        _print(_read_tail(CRASH_RPT, lines=60))

    # Root-cause hypothesis
    hypothesis = _generate_crash_hypothesis(uptime_s, exit_code, lifecycle_tail)

    _print(f"\n{SEP}")
    _print("  ROOT CAUSE HYPOTHESIS")
    _print(SEP)
    _print(hypothesis)

    # Write GUI_RUNTIME_REPORT.md
    startup_ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_ts))
    shutdown_ts_str = time.strftime("%Y-%m-%d %H:%M:%S")

    last_lifecycle = ""
    if LIFECYCLE_LOG.exists():
        try:
            lines = LIFECYCLE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            last_lifecycle = "\n".join(lines[-10:]) if lines else "(empty)"
        except Exception:
            last_lifecycle = "(read error)"

    report_md = f"""# GUI RUNTIME REPORT - Diagnostic Launch

**Generated by:** debug_gui_launch.py
**Startup Timestamp:** {startup_ts_str}
**Shutdown Timestamp:** {shutdown_ts_str}
**Uptime:** {uptime_s:.2f}s
**PID:** {proc.pid}
**Exit Code:** {exit_code}

---

## Shutdown Details

| Field | Value |
|-------|-------|
| Uptime | {uptime_s:.2f}s |
| Exit Code | {exit_code} |
| Crash Detected | {"YES - uptime < 30s" if uptime_s < 30 else "NO - normal lifetime"} |

---

## Root Cause Hypothesis

{hypothesis}

---

## Last Lifecycle Events

```
{last_lifecycle}
```

---

## Log Locations

| Log File | Purpose |
|----------|---------|
| logs/gui_crash.log | One-line crash summaries |
| logs/gui_traceback.log | Full exception tracebacks |
| logs/gui_lifecycle.log | Full startup/shutdown timeline |
| logs/service_shutdown.log | Service stop/crash events |
| GUI_CRASH_REPORT.md | Latest crash detail report |

---

Generated at {shutdown_ts_str} by debug_gui_launch.py
"""
    try:
        RUNTIME_RPT.write_text(report_md, encoding="utf-8")
        _print(f"\n[DEBUG] GUI_RUNTIME_REPORT.md written to: {RUNTIME_RPT}")
    except Exception as e:
        _print(f"[DEBUG] Could not write report: {e}")

    _print(f"\n{SEP}")
    _print("  DIAGNOSTIC COMPLETE")
    _print(f"  Review: {RUNTIME_RPT}")
    _print(f"  Log:    {LIFECYCLE_LOG}")
    _print(SEP)

    return 0 if exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
