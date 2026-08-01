import time

from JARVIS.core.system.utils.service_heartbeat import publish_heartbeat, wrap_service_main


def _start():
    publish_heartbeat("automation_engine", "automation_engine.json")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    import sys

    from JARVIS.core.system.utils.port_manager import PortManager

    lock_socket = PortManager.acquire_service_lock("automation_service", 19103)
    if lock_socket is None:
        print("[AUTOMATION SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        wrap_service_main("automation_engine", _start)
    finally:
        lock_socket.close()
