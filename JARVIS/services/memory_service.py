"""Memory Engine Service — Persistent heartbeat daemon with retry on transient load errors."""

import logging
import sys
import time

logger = logging.getLogger("jarvis.memory_service")


def _start():
    from JARVIS.core.system.utils.service_heartbeat import publish_heartbeat

    # Start heartbeat first so supervisor doesn't time out during memory init
    publish_heartbeat("memory_engine", "memory_engine.json")

    # Attempt to initialize memory backend with exponential backoff
    _max_retries = 5
    _backoff = 1.0
    for _attempt in range(1, _max_retries + 1):
        try:
            # Import core memory modules — may fail transiently on first launch
            from JARVIS.core.memory import memory_preferences  # noqa: F401

            logger.info("[MEMORY] Memory backend initialised on attempt %d", _attempt)
            print(f"[MEMORY] Memory backend initialised (attempt {_attempt})", flush=True)
            break
        except Exception as exc:
            if _attempt < _max_retries:
                logger.warning(
                    "[MEMORY] Transient load error (attempt %d/%d): %s — retrying in %.1fs",
                    _attempt,
                    _max_retries,
                    exc,
                    _backoff,
                )
                print(
                    f"[MEMORY] Transient load error (attempt {_attempt}/{_max_retries}): {exc} — retrying in {_backoff:.1f}s",
                    flush=True,
                )
                time.sleep(_backoff)
                _backoff = min(_backoff * 2, 15.0)
            else:
                logger.error("[MEMORY] Memory backend failed to initialise after %d attempts: %s", _max_retries, exc)
                print(f"[MEMORY] Memory backend failed after {_max_retries} attempts: {exc}", flush=True)

    # Keep process alive — heartbeat published in background daemon thread
    while True:
        time.sleep(1)


if __name__ == "__main__":
    from JARVIS.core.system.utils.port_manager import PortManager
    from JARVIS.core.system.utils.service_heartbeat import wrap_service_main

    lock_socket = PortManager.acquire_service_lock("memory_service", 19102)
    if lock_socket is None:
        print("[MEMORY SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        wrap_service_main("memory_engine", _start)
    finally:
        lock_socket.close()
