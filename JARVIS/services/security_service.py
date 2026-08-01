import os
import time
import json
from JARVIS.core.system.utils.service_heartbeat import publish_heartbeat, wrap_service_main

def _start():
    publish_heartbeat("security_engine", "security_engine.json")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    import sys
    from JARVIS.core.system.utils.port_manager import PortManager
    lock_socket = PortManager.acquire_service_lock("security_service", 19104)
    if lock_socket is None:
        print("[SECURITY SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        wrap_service_main("security_engine", _start)
    finally:
        lock_socket.close()
