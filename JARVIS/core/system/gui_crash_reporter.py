"""
JARVIS GUI Crash Reporter
=========================
Central exception capture engine for all threads.

Writes:
  logs/gui_crash.log        — one-line-per-event crash summary
  logs/gui_traceback.log    — full Python tracebacks
  logs/gui_lifecycle.log    — startup / shutdown timeline
  logs/service_shutdown.log — every shutdown event with reason

Generates:
  GUI_CRASH_REPORT.md       — human-readable crash report
  GUI_RUNTIME_REPORT.md     — runtime summary (startup/shutdown timestamps)

Displays:
  Error dialog with traceback location when GUI crashes

Usage:
    from JARVIS.core.system.gui_crash_reporter import GUICrashReporter
    reporter = GUICrashReporter(root_dir)
    reporter.install_global_handlers()
"""

from __future__ import annotations

import datetime
import os
import sys
import threading
import time
import traceback

_STARTUP_TIMESTAMP = datetime.datetime.now().isoformat(timespec="seconds")


class GUICrashReporter:
    """
    Production-level crash capture for JARVIS GUI.
    Thread-safe — can be called from any thread.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.logs_dir = os.path.join(root_dir, "logs")
        self._lock = threading.Lock()
        self._start_ts = _STARTUP_TIMESTAMP
        self._shutdown_ts: str | None = None
        self._shutdown_reason: str = "unknown"
        self._crash_count: int = 0

        # Ensure log directory exists
        os.makedirs(self.logs_dir, exist_ok=True)

        # Log paths
        self.crash_log = os.path.join(self.logs_dir, "gui_crash.log")
        self.traceback_log = os.path.join(self.logs_dir, "gui_traceback.log")
        self.lifecycle_log = os.path.join(self.logs_dir, "gui_lifecycle.log")
        self.shutdown_log = os.path.join(self.logs_dir, "service_shutdown.log")
        self.crash_report = os.path.join(root_dir, "GUI_CRASH_REPORT.md")
        self.runtime_report = os.path.join(root_dir, "GUI_RUNTIME_REPORT.md")

        self._lifecycle_event("STARTUP", f"GUI process started (PID {os.getpid()})")
        self._lifecycle_event(
            "LOG_PATHS",
            f"crash={self.crash_log} | traceback={self.traceback_log} | lifecycle={self.lifecycle_log} | shutdown={self.shutdown_log}",
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def install_global_handlers(self):
        """Install exception hooks on main thread and all daemon threads."""
        # ── 1. Python faulthandler (catches C-level segfaults / SIGSEGV) ────────
        try:
            import faulthandler

            _tb_file = open(self.traceback_log, "a", encoding="utf-8")
            faulthandler.enable(file=_tb_file)
            self._lifecycle_event("FAULTHANDLER", f"faulthandler enabled → {self.traceback_log}")
        except Exception as _fe:
            self._lifecycle_event("FAULTHANDLER_FAIL", str(_fe))

        # ── 2. Qt message handler (catches Qt CRITICAL / FATAL before Python sees them)
        try:
            from PySide6.QtCore import QtMsgType, qInstallMessageHandler

            _reporter_ref = self

            def _qt_msg_handler(msg_type, context, message):
                _level_map = {
                    QtMsgType.QtDebugMsg: "QT_DEBUG",
                    QtMsgType.QtInfoMsg: "QT_INFO",
                    QtMsgType.QtWarningMsg: "QT_WARNING",
                    QtMsgType.QtCriticalMsg: "QT_CRITICAL",
                    QtMsgType.QtFatalMsg: "QT_FATAL",
                }
                level = _level_map.get(msg_type, "QT_UNKNOWN")
                loc = f"{context.file}:{context.line}" if context.file else "<unknown>"
                full_msg = f"[{level}] {loc} — {message}"
                _reporter_ref.log_qml_warning(full_msg)
                if msg_type in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
                    _reporter_ref._lifecycle_event(level, full_msg)

            qInstallMessageHandler(_qt_msg_handler)
            self._lifecycle_event("QT_MSG_HANDLER", "Qt message handler installed")
        except Exception as _qe:
            self._lifecycle_event("QT_MSG_HANDLER_FAIL", str(_qe))

        # ── 3. Main-thread Python exception hook ──────────────────────────────
        # Main thread
        original_excepthook = sys.excepthook

        def _main_excepthook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
                # SystemExit / Ctrl-C are intentional — log but don't show dialog
                reason = "KeyboardInterrupt" if issubclass(exc_type, KeyboardInterrupt) else f"SystemExit({exc_value})"
                self.log_shutdown(reason)
                original_excepthook(exc_type, exc_value, exc_tb)
                return
            self._handle_crash(
                "MAIN_THREAD",
                exc_type,
                exc_value,
                exc_tb,
                show_dialog=True,
            )

        sys.excepthook = _main_excepthook

        # All other threads (Python 3.8+)
        original_thread_excepthook = threading.excepthook

        def _thread_excepthook(args):
            if args.exc_type is None:
                return
            if issubclass(args.exc_type, SystemExit):
                self.log_shutdown(f"SystemExit in thread {args.thread.name if args.thread else 'unknown'}")
                return
            self._handle_crash(
                f"THREAD:{getattr(args.thread, 'name', 'unknown')}",
                args.exc_type,
                args.exc_value,
                args.exc_traceback,
                show_dialog=False,
            )
            original_thread_excepthook(args)

        threading.excepthook = _thread_excepthook

        self._lifecycle_event("HANDLERS", "Global exception handlers installed on main + daemon threads")

    def log_lifecycle(self, event: str, detail: str = ""):
        """Record a lifecycle event (startup, shutdown, QML load, etc.)."""
        self._lifecycle_event(event, detail)

    def log_shutdown(self, reason: str, exit_code: int = 0):
        """Record a clean or forced shutdown event."""
        self._shutdown_ts = datetime.datetime.now().isoformat(timespec="seconds")
        self._shutdown_reason = reason
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            try:
                with open(self.shutdown_log, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] SHUTDOWN | reason={reason} | exit_code={exit_code} | pid={os.getpid()}\n")
            except Exception:
                pass

        self._lifecycle_event("SHUTDOWN", f"reason={reason} | exit_code={exit_code}")
        self._generate_runtime_report(reason, exit_code)

    def log_qml_warning(self, message: str):
        """Log a QML warning or error (non-fatal)."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            try:
                with open(self.crash_log, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] QML_WARNING | {message}\n")
            except Exception:
                pass

    def log_event_loop_status(self, active: bool, detail: str = ""):
        """Record whether the Qt event loop is alive."""
        status = "ACTIVE" if active else "EXITED"
        self._lifecycle_event(f"EVENT_LOOP_{status}", detail)

    # ── Internal ───────────────────────────────────────────────────────────

    def _handle_crash(
        self,
        source: str,
        exc_type,
        exc_value,
        exc_tb,
        show_dialog: bool = False,
    ):
        """Central crash handler — writes all logs and optionally shows dialog."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        # Extract offending file / line from innermost frame
        offending_file = "unknown"
        offending_line = 0
        if exc_tb:
            import traceback as tb_mod

            frames = list(tb_mod.extract_tb(exc_tb))
            if frames:
                last = frames[-1]
                offending_file = last.filename
                offending_line = last.lineno

        self._crash_count += 1

        with self._lock:
            # gui_crash.log — one summary line
            try:
                with open(self.crash_log, "a", encoding="utf-8") as f:
                    f.write(
                        f"[{ts}] CRASH#{self._crash_count} | source={source} | "
                        f"{exc_type.__name__}: {exc_value} | "
                        f"file={offending_file}:{offending_line}\n"
                    )
            except Exception:
                pass

            # gui_traceback.log — full traceback
            try:
                with open(self.traceback_log, "a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 70}\n")
                    f.write(f"[{ts}] CRASH#{self._crash_count} SOURCE={source}\n")
                    f.write(f"{'=' * 70}\n")
                    f.write(tb_str)
                    f.write("\n")
            except Exception:
                pass

            # GUI_CRASH_REPORT.md
            self._generate_crash_report(
                ts,
                source,
                exc_type,
                exc_value,
                tb_str,
                offending_file,
                offending_line,
            )

        self._lifecycle_event("CRASH", f"source={source} | {exc_type.__name__}: {exc_value} | {offending_file}:{offending_line}")

        if show_dialog:
            self._show_crash_dialog(exc_type, exc_value, offending_file, offending_line)

    def _lifecycle_event(self, event: str, detail: str = ""):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._lock:
                with open(self.lifecycle_log, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] [{event:<24}] {detail}\n")
        except Exception:
            pass

    def _generate_crash_report(self, ts, source, exc_type, exc_value, tb_str, offending_file, offending_line):
        """Write/overwrite GUI_CRASH_REPORT.md with the latest crash info."""
        try:
            content = f"""# GUI CRASH REPORT

**Generated:** {ts}  
**PID:** {os.getpid()}  
**Startup Timestamp:** {self._start_ts}  
**Crash #:** {self._crash_count}  

---

## Crash Details

| Field | Value |
|-------|-------|
| Source Thread | `{source}` |
| Exception Type | `{exc_type.__name__}` |
| Exception Message | `{exc_value}` |
| Offending File | `{offending_file}` |
| Offending Line | `{offending_line}` |

---

## Full Traceback

```python
{tb_str.strip()}
```

---

## Recommended Fix

1. Open **`{offending_file}`** at **line {offending_line}**
2. Inspect the exception: `{exc_type.__name__}: {exc_value}`
3. Add `try/except` or null-check around the offending call
4. Check `logs/gui_traceback.log` for full history

---

*Full traceback history: `logs/gui_traceback.log`*  
*Lifecycle timeline: `logs/gui_lifecycle.log`*  
*Service events: `logs/service_shutdown.log`*  
"""
            with open(self.crash_report, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    def _generate_runtime_report(self, shutdown_reason: str, exit_code: int):
        """Write GUI_RUNTIME_REPORT.md after every shutdown."""
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            shutdown_ts = self._shutdown_ts or now

            # Compute uptime
            try:
                start = datetime.datetime.fromisoformat(self._start_ts)
                end = datetime.datetime.fromisoformat(shutdown_ts)
                uptime = str(end - start)
            except Exception:
                uptime = "unknown"

            content = f"""# GUI RUNTIME REPORT

**Generated:** {now}  
**PID:** {os.getpid()}  

---

## Timeline

| Event | Timestamp |
|-------|-----------|
| Startup | `{self._start_ts}` |
| Shutdown | `{shutdown_ts}` |
| Uptime | `{uptime}` |

---

## Shutdown Details

| Field | Value |
|-------|-------|
| Shutdown Reason | `{shutdown_reason}` |
| Exit Code | `{exit_code}` |
| Crash Count | `{self._crash_count}` |

---

## Log Locations

| Log File | Purpose |
|----------|---------|
| `logs/gui_crash.log` | One-line crash summaries |
| `logs/gui_traceback.log` | Full exception tracebacks |
| `logs/gui_lifecycle.log` | Full startup/shutdown timeline |
| `logs/service_shutdown.log` | Service stop/crash events |
| `GUI_CRASH_REPORT.md` | Latest crash detail report |

---

## Status

{"✅ Clean shutdown — no crashes recorded." if self._crash_count == 0 else f"❌ {self._crash_count} crash(es) recorded — see GUI_CRASH_REPORT.md"}
"""
            with open(self.runtime_report, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    def _show_crash_dialog(self, exc_type, exc_value, offending_file, offending_line):
        """Show an error dialog with traceback location. Falls back to stderr."""
        message = (
            f"HESA GUI encountered an unhandled exception:\n\n"
            f"Exception: {exc_type.__name__}: {exc_value}\n\n"
            f"File: {offending_file}\n"
            f"Line: {offending_line}\n\n"
            f"Full traceback written to:\n"
            f"  logs/gui_crash.log\n"
            f"  logs/gui_traceback.log\n\n"
            f"Crash report: GUI_CRASH_REPORT.md"
        )
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance()
            if app:
                msg = QMessageBox()
                msg.setWindowTitle("HESA — Unhandled Exception")
                msg.setIcon(QMessageBox.Critical)
                msg.setText(message)
                msg.exec()
                return
        except Exception:
            pass
        # Fallback: keep console open with the error
        print(f"\n{'=' * 60}", file=sys.stderr)
        print("HESA GUI CRASH DETECTED", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(message, file=sys.stderr)
        print(f"{'=' * 60}\n", file=sys.stderr)
        input("Press ENTER to close this window...")
