import logging
import os
import threading
import time

logger = logging.getLogger("service_monitor")

# Log file path — resolved from __file__ so it works regardless of CWD
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_JARVIS_LOG_FILE = os.path.join(_ROOT_DIR, "logs", "jarvis_events.log")


def _write_event_log(tag: str, message: str) -> None:
    """Append one structured line to the shared on-disk events log."""
    try:
        os.makedirs(os.path.dirname(_JARVIS_LOG_FILE), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_JARVIS_LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] [{tag:<20}] {message}\n")
    except Exception:
        pass


class ServiceHealthMonitor:
    """
    In-process health monitor for instantiated JARVIS service objects.

    Design:
    - Runs on a background daemon thread (no exit guard needed).
    - Calls service.is_alive() or service.health_check() every check_interval seconds.
    - On crash: tries restart up to max_retries times, then marks PERMANENTLY_FAILED.
    - Calls notify_callback(service_name, new_status) on every state transition so
      the system tray can show balloon notifications without the GUI exiting.
    - All crash/restart/recovery events are written to logs/jarvis_events.log.

    States emitted via notify_callback:
        "RESTARTING"  — restart attempt in progress (attempt N / max_retries)
        "RECOVERING"  — restart call returned without exception
        "RECOVERED"   — service is_alive() returned True again after a crash
        "FAILED"      — permanently failed (max_retries exhausted), JARVIS keeps running
    """

    def __init__(self):
        self.services = {}  # {name: {instance, status, last_seen, crash_count}}
        self.retry_count = {}  # {name: int}
        self.max_retries = 3  # After 3 failures → PERMANENTLY_FAILED
        self.check_interval = 5  # Seconds between health sweeps
        self.running = False
        self._lock = threading.Lock()

        # Optional callback: notify_callback(service_name: str, status: str) -> None
        self.notify_callback = None

    # ── Public API ──────────────────────────────────────────────────────────────

    def set_notify_callback(self, callback) -> None:
        """Wire in the tray/GUI notification function after init."""
        self.notify_callback = callback

    def register_service(self, service_name: str, service_instance) -> None:
        """Register a service for health monitoring."""
        with self._lock:
            self.services[service_name] = {
                "instance": service_instance,
                "status": "UNKNOWN",
                "last_seen": time.time(),
                "crash_count": 0,
            }
            self.retry_count[service_name] = 0

    def monitor_loop(self) -> None:
        """Continuous monitoring loop — call on a daemon thread."""
        self.running = True
        while self.running:
            with self._lock:
                items = list(self.services.items())
            for service_name, service_info in items:
                self._check_service_health(service_name, service_info)
            time.sleep(self.check_interval)

    def stop(self) -> None:
        self.running = False

    def get_service_status(self, service_name: str) -> str:
        return self.services.get(service_name, {}).get("status", "UNKNOWN")

    def get_all_status(self) -> dict:
        return {name: info["status"] for name, info in self.services.items()}

    # ── Internal ────────────────────────────────────────────────────────────────

    def _check_service_health(self, service_name: str, service_info: dict) -> None:
        try:
            service = service_info["instance"]
            is_alive: bool

            if hasattr(service, "is_alive"):
                is_alive = service.is_alive()
            elif hasattr(service, "health_check"):
                is_alive = service.health_check()
            else:
                # No health method → assume alive (avoids false alarms)
                is_alive = True

            if is_alive:
                prev = service_info["status"]
                service_info["status"] = "HEALTHY"
                service_info["crash_count"] = 0
                service_info["last_seen"] = time.time()
                self.retry_count[service_name] = 0

                if prev in ("RESTARTING", "RECOVERING"):
                    _write_event_log("RECOVERY", f"{service_name} is back online after {service_info['crash_count']} crash(es)")
                    self._notify(service_name, "RECOVERED")
            else:
                self._handle_service_crash(service_name, service_info)

        except Exception as exc:
            logger.warning(f"[ServiceMonitor] Exception checking {service_name}: {exc}")
            service_info["status"] = "ERROR"

    def _handle_service_crash(self, service_name: str, service_info: dict) -> None:
        service_info["crash_count"] += 1
        self.retry_count[service_name] += 1
        attempt = self.retry_count[service_name]

        if attempt <= self.max_retries:
            service_info["status"] = "RESTARTING"
            msg = f"{service_name} crashed — restart attempt {attempt}/{self.max_retries}"
            logger.warning(f"[ServiceMonitor] {msg}")
            _write_event_log("CRASH", msg)
            self._notify(service_name, "RESTARTING")

            try:
                service = service_info["instance"]
                if hasattr(service, "restart"):
                    service.restart()
                elif hasattr(service, "initialize"):
                    service.initialize()

                service_info["status"] = "RECOVERING"
                _write_event_log("RESTART", f"{service_name} restart call returned (attempt {attempt})")
                self._notify(service_name, "RECOVERING")
                logger.info(f"[ServiceMonitor] {service_name} recovery triggered (attempt {attempt})")
            except Exception as exc:
                _write_event_log("RESTART", f"{service_name} restart failed: {exc}")
                logger.error(f"[ServiceMonitor] Failed to restart {service_name}: {exc}")
                service_info["status"] = "RESTARTING"
        else:
            prev = service_info["status"]
            service_info["status"] = "PERMANENTLY_FAILED"
            if prev != "PERMANENTLY_FAILED":
                msg = f"{service_name} permanently failed after {self.max_retries} retries — JARVIS continues running"
                logger.error(f"[ServiceMonitor] {msg}")
                _write_event_log("FAILED", msg)
                self._notify(service_name, "FAILED")

    def _notify(self, service_name: str, status: str) -> None:
        """Fire the tray notification callback; errors are swallowed so the monitor never crashes."""
        if self.notify_callback:
            try:
                self.notify_callback(service_name, status)
            except Exception as exc:
                logger.warning(f"[ServiceMonitor] notify_callback raised: {exc}")
