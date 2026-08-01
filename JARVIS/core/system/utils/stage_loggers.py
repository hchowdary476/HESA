"""
Dedicated Stage Loggers for HESA OS Production Voice Assistant Architecture.

Manages 7 dedicated log files:
- logs/wake.log
- logs/stt.log
- logs/intent.log
- logs/actions.log
- logs/router.log
- logs/memory.log
- logs/tts.log
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

STAGE_LOG_FILES: Dict[str, Path] = {
    "wake": LOG_DIR / "wake.log",
    "stt": LOG_DIR / "stt.log",
    "intent": LOG_DIR / "intent.log",
    "actions": LOG_DIR / "actions.log",
    "router": LOG_DIR / "router.log",
    "memory": LOG_DIR / "memory.log",
    "tts": LOG_DIR / "tts.log",
}

_loggers: Dict[str, logging.Logger] = {}


def get_stage_logger(stage: str) -> logging.Logger:
    """Get or create dedicated logger for a pipeline stage."""
    key = stage.lower().strip()
    if key in _loggers:
        return _loggers[key]

    log_path = STAGE_LOG_FILES.get(key, LOG_DIR / f"{key}.log")
    logger = logging.getLogger(f"hesa.{key}")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    _loggers[key] = logger
    return logger


def log_stage_event(stage: str, tag: str, message: str = "") -> None:
    """Write formatted event to dedicated stage log and print to stdout."""
    logger = get_stage_logger(stage)
    formatted = f"[{tag.upper()}] {message}".strip()
    logger.info(formatted)
    print(f"[{stage.upper()}] {formatted}", flush=True)


# Conveniences
wake_log = lambda tag, msg="": log_stage_event("wake", tag, msg)
stt_log = lambda tag, msg="": log_stage_event("stt", tag, msg)
intent_log = lambda tag, msg="": log_stage_event("intent", tag, msg)
actions_log = lambda tag, msg="": log_stage_event("actions", tag, msg)
router_log = lambda tag, msg="": log_stage_event("router", tag, msg)
memory_log = lambda tag, msg="": log_stage_event("memory", tag, msg)
tts_log = lambda tag, msg="": log_stage_event("tts", tag, msg)
