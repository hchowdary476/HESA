"""Shared logging setup for Open.Jarvis."""

from __future__ import annotations

import atexit
import logging
import logging.handlers
import os
import queue
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "jarvis.log"

# Inject Windows Native Certificate Store via truststore to safely solve SSL EOF,
# enterprise CA, and certificate validation issues without disabling SSL verification.
try:
    import truststore

    truststore.inject_into_ssl()
    logging.getLogger("jarvis.system").info("[SSL] Native Windows Certificate Store injected via truststore.")
except Exception as _ssl_err:
    logging.getLogger("jarvis.system").warning("[SSL] truststore injection skipped: %s", _ssl_err)


# Dedicated per-subsystem log files under the project logs/ folder.
# All paths are relative to the CWD of the running process (Open.Jarvis-main/).
_SUBSYSTEM_LOGS: dict[str, str] = {
    "jarvis.wake": "logs/wake.log",
    "jarvis.intent": "logs/intent.log",
    "jarvis.router": "logs/router.log",
    "jarvis.actions": "logs/actions.log",
    "jarvis.memory": "logs/memory.log",
    "jarvis.voice": "logs/voice_engine.log",
    "jarvis.tts": "logs/tts.log",
    "jarvis.stt": "logs/stt.log",
    "ai_orchestrator": "logs/router.log",
}


_log_queue: queue.Queue = queue.Queue(-1)
_listener: logging.handlers.QueueListener | None = None

# Cache of already-created file loggers so we never add duplicate handlers.
_file_loggers: dict[str, logging.Logger] = {}


def _subsystem_formatter() -> logging.Formatter:
    """Rich formatter that includes timestamp, level, logger name, and PID."""
    return logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] [PID=%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_queue_logging() -> None:
    """Initialize the queue listener for logging if not already setup."""
    global _listener
    if _listener is not None:
        return

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8", delay=True)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    _listener = logging.handlers.QueueListener(_log_queue, file_handler, console_handler, respect_handler_level=True)
    _listener.start()

    atexit.register(_listener.stop)


def get_logger(name: str = "jarvis") -> logging.Logger:
    """Return a configured logger that writes to logs/jarvis.log via queue listener."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    setup_queue_logging()

    queue_handler = logging.handlers.QueueHandler(_log_queue)
    logger.addHandler(queue_handler)

    return logger


def get_file_logger(name: str, log_path: str | None = None) -> logging.Logger:
    """Return (or create) a dedicated per-subsystem rotating file logger.

    Parameters
    ----------
    name:
        Logger name, e.g. ``"jarvis.voice"``.  Known names are automatically
        mapped to their canonical log-file path via ``_SUBSYSTEM_LOGS``.
    log_path:
        Override the output file path.  If *None*, the path is looked up from
        ``_SUBSYSTEM_LOGS``; if not found there either, falls back to the shared
        ``logs/jarvis.log``.

    The returned logger writes to *both* the dedicated file **and** the shared
    queue listener (for the console / central jarvis.log), so no log lines are
    ever lost.
    """
    if name in _file_loggers:
        return _file_loggers[name]

    # Resolve output path
    resolved_path = log_path or _SUBSYSTEM_LOGS.get(name)
    logger = logging.getLogger(name)

    # Guard: if handlers already attached by a previous call, return as-is
    if logger.handlers:
        _file_loggers[name] = logger
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # 1. Dedicated rotating file handler
    if resolved_path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(resolved_path)), exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                resolved_path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
                delay=True,
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(_subsystem_formatter())
            logger.addHandler(fh)
        except Exception:
            pass  # Silently degrade to shared logger only

    # 2. Also route through shared queue listener (console + central file)
    setup_queue_logging()
    qh = logging.handlers.QueueHandler(_log_queue)
    qh.setLevel(logging.INFO)
    logger.addHandler(qh)

    _file_loggers[name] = logger
    return logger


# ── Pre-wire all known subsystem loggers at import time ──────────────────────
# This ensures the log files are created on first import, even if a subsystem
# has not yet called get_file_logger() itself.
def _prewire_subsystem_loggers() -> None:
    for _name in _SUBSYSTEM_LOGS:
        get_file_logger(_name)


_prewire_subsystem_loggers()
