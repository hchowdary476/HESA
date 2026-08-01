"""Port Manager utility for port validation and single-instance locks."""

from __future__ import annotations

import socket

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("port_manager")


class PortManager:
    """Utility to check port occupancy and acquire single-instance locks."""

    @staticmethod
    def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
        """Verify port availability using socket.bind()."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return True
        except Exception:
            return False

    @staticmethod
    def get_available_port(base_port: int, host: str = "127.0.0.1", max_attempts: int = 100) -> int:
        """Find an available port starting from base_port, using socket.bind() checks."""
        port = base_port
        attempts = 0
        while attempts < max_attempts:
            if PortManager.is_port_available(port, host):
                logger.info("Port %d is available on %s and assigned.", port, host)
                return port
            logger.warning("Port %d on %s is occupied, trying fallback...", port, host)
            port += 1
            attempts += 1
        raise RuntimeError(f"Could not find an available port starting from {base_port} after {max_attempts} attempts.")

    @staticmethod
    def acquire_service_lock(service_name: str, lock_port: int) -> socket.socket | None:
        """Acquires a service-specific socket bind lock to prevent duplicate startup.

        If the lock fails, checks for a PID lockfile at ``logs/<service_name>.pid``.
        When the PID recorded there is no longer alive (stale lock from a crashed
        process), the method retries once — this prevents zombie sockets from
        permanently blocking future launches.
        """

        def _try_bind() -> socket.socket | None:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                import sys

                if sys.platform != "win32":
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", lock_port))
                s.listen(1)
                logger.info("Service lock acquired for '%s' on port %d.", service_name, lock_port)
                return s
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass
                return None

        sock = _try_bind()
        if sock is not None:
            return sock

        # Lock failed — check if the holder is still alive via PID lockfile
        import os

        pid_path = os.path.join("logs", f"{service_name}.pid")
        if os.path.exists(pid_path):
            try:
                with open(pid_path) as f:
                    old_pid = int(f.read().strip())
                # Check if that PID is still alive
                import psutil

                if not psutil.pid_exists(old_pid):
                    logger.warning(
                        "Stale lock detected for '%s': PID %d is dead. Waiting briefly for OS socket cleanup...",
                        service_name,
                        old_pid,
                    )
                    # Remove the stale PID file
                    try:
                        os.remove(pid_path)
                    except Exception:
                        pass
                    # Brief wait for the OS to release the orphaned socket
                    import time

                    time.sleep(1.5)
                    # Retry once
                    sock = _try_bind()
                    if sock is not None:
                        logger.info(
                            "Service lock recovered for '%s' on port %d (stale PID %d cleared).",
                            service_name,
                            lock_port,
                            old_pid,
                        )
                        return sock
            except Exception as e:
                logger.warning("PID lockfile check failed for '%s': %s", service_name, e)

        logger.error(
            "Failed to acquire service lock for '%s' on port %d. Service already running?",
            service_name,
            lock_port,
        )
        return None
