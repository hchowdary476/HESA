import os
import sys
import threading
import time
import traceback


def _write_log(filepath: str, message: str):
    """Safely write a message to a log file under logs/."""
    try:
        os.makedirs("logs", exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        thread_name = threading.current_thread().name
        pid = os.getpid()
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [PID:{pid}] [Thread:{thread_name}] {message}\n")
    except Exception:
        pass


def log_lifecycle(event: str, detail: str = ""):
    """Logs lifecycle events to logs/gui_lifecycle.log."""
    _write_log("logs/gui_lifecycle.log", f"[{event:<20}] {detail}")


def log_close_reason(trigger: str, detail: str = "", include_stack: bool = True):
    """Logs exit triggers and stacks to logs/gui_close_reason.log."""
    stack_str = ""
    if include_stack:
        stack_str = "\n" + "".join(traceback.format_stack()[:-1])
    _write_log("logs/gui_close_reason.log", f"[TRIGGER: {trigger}] {detail}{stack_str}\n" + "-" * 80)


def log_supervisor_action(action: str, detail: str = ""):
    """Logs supervisor actions to logs/supervisor_actions.log."""
    _write_log("logs/supervisor_actions.log", f"[ACTION: {action}] {detail}")


def install_lifecycle_hooks():
    """Install monkeypatches for sys.exit, os._exit, and PySide6 application quit/exit to log tracebacks."""
    # 1. sys.exit hook
    if not hasattr(sys, "_orig_exit"):
        sys._orig_exit = sys.exit

        def hooked_sys_exit(*args):
            log_close_reason("sys.exit", f"Arguments: {args}")
            return sys._orig_exit(*args)

        sys.exit = hooked_sys_exit
        log_lifecycle("HOOK_SYS_EXIT", "sys.exit hooked successfully")

    # 2. os._exit hook
    if not hasattr(os, "_orig_exit"):
        os._orig_exit = os._exit

        def hooked_os_exit(status):
            log_close_reason("os._exit", f"Status: {status}")
            return os._orig_exit(status)

        os._exit = hooked_os_exit
        log_lifecycle("HOOK_OS_EXIT", "os._exit hooked successfully")

    # 3. sys.excepthook to capture SystemExit exception
    if not hasattr(sys, "_orig_excepthook"):
        sys._orig_excepthook = sys.excepthook

        def lifecycle_excepthook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, SystemExit):
                tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                log_close_reason("SystemExit raised", f"Value: {exc_value}\nTraceback:\n{tb_str}", include_stack=False)
            elif issubclass(exc_type, KeyboardInterrupt):
                log_close_reason("KeyboardInterrupt", "Ctrl+C or interrupt received", include_stack=False)
            sys._orig_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = lifecycle_excepthook
        log_lifecycle("HOOK_EXCEPTHOOK", "sys.excepthook configured to capture SystemExit")

    # 4. PySide6 QApplication/QCoreApplication hooks
    try:
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtWidgets import QApplication

        if not hasattr(QApplication, "_orig_quit"):
            QApplication._orig_quit = QApplication.quit

            def hooked_qapp_quit(*args, **kwargs):
                log_close_reason("QApplication.quit", f"Args: {args} Kwargs: {kwargs}")
                return QApplication._orig_quit(*args, **kwargs)

            QApplication.quit = hooked_qapp_quit
            log_lifecycle("HOOK_QAPP_QUIT", "QApplication.quit hooked successfully")

        if not hasattr(QApplication, "_orig_exit_method"):
            QApplication._orig_exit_method = QApplication.exit

            def hooked_qapp_exit(*args, **kwargs):
                log_close_reason("QApplication.exit", f"Args: {args} Kwargs: {kwargs}")
                return QApplication._orig_exit_method(*args, **kwargs)

            QApplication.exit = hooked_qapp_exit
            log_lifecycle("HOOK_QAPP_EXIT", "QApplication.exit hooked successfully")

        if not hasattr(QCoreApplication, "_orig_quit"):
            QCoreApplication._orig_quit = QCoreApplication.quit

            def hooked_qcore_quit(*args, **kwargs):
                log_close_reason("QCoreApplication.quit", f"Args: {args} Kwargs: {kwargs}")
                return QCoreApplication._orig_quit(*args, **kwargs)

            QCoreApplication.quit = hooked_qcore_quit
            log_lifecycle("HOOK_QCORE_QUIT", "QCoreApplication.quit hooked successfully")

        if not hasattr(QCoreApplication, "_orig_exit_method"):
            QCoreApplication._orig_exit_method = QCoreApplication.exit

            def hooked_qcore_exit(*args, **kwargs):
                log_close_reason("QCoreApplication.exit", f"Args: {args} Kwargs: {kwargs}")
                return QCoreApplication._orig_exit_method(*args, **kwargs)

            QCoreApplication.exit = hooked_qcore_exit
            log_lifecycle("HOOK_QCORE_EXIT", "QCoreApplication.exit hooked successfully")

    except ImportError:
        pass
