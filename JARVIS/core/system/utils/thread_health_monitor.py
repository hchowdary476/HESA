"""Thread Health Monitor for tracking active threads, leaks, and lifetimes."""

from __future__ import annotations

import threading
import time
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("thread_health_monitor")


class ThreadHealthMonitor:
    """Monitors thread count, lifetimes, potential leaks, and dead threads."""

    _instance: ThreadHealthMonitor | None = None

    def __new__(cls, *args, **kwargs) -> ThreadHealthMonitor:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, limit: int = 40):
        # Prevent re-initialization if already initialized
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.limit = limit
        self.started_times: dict[int, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def check_health(self) -> dict[str, Any]:
        """Inspect threads and return health analytics."""
        current_threads = threading.enumerate()
        active_count = len(current_threads)
        now = time.time()

        with self.lock:
            # Clean up tracking for threads that are no longer active
            active_idents = {t.ident for t in current_threads if t.ident is not None}
            dead_idents = set(self.started_times.keys()) - active_idents
            for ident in dead_idents:
                self.started_times.pop(ident, None)

            # Record newly detected threads
            for t in current_threads:
                if t.ident is not None and t.ident not in self.started_times:
                    self.started_times[t.ident] = {
                        "name": t.name,
                        "start_time": now,
                        "daemon": t.daemon,
                    }

        # Analyze thread metadata
        thread_details = []
        name_counts: dict[str, int] = {}
        for t in current_threads:
            if t.ident is None:
                continue
            name_counts[t.name] = name_counts.get(t.name, 0) + 1
            info = self.started_times.get(t.ident, {"name": t.name, "start_time": now, "daemon": t.daemon})
            lifetime = now - info["start_time"]
            thread_details.append(
                {
                    "ident": t.ident,
                    "name": t.name,
                    "daemon": t.daemon,
                    "lifetime_seconds": lifetime,
                }
            )

        # Detect potential leaks (excluding standard background loops or workers)
        leaked_threads = []
        for name, count in name_counts.items():
            if count > 5 and not any(k in name.lower() for k in ["pool", "process", "queue", "thread"]):
                leaked_threads.append(name)

        status = "healthy"
        if active_count > self.limit or leaked_threads:
            status = "warning"
            logger.warning(
                "Thread limit or leak warning: count=%d (limit=%d), leak names=%s",
                active_count,
                self.limit,
                leaked_threads,
            )

        return {
            "status": status,
            "active_count": active_count,
            "limit": self.limit,
            "leaked_threads": leaked_threads,
            "thread_details": thread_details,
        }
