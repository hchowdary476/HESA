import os
import sys
import time
import json
import threading
from JARVIS.core.ai_router.cloud.server import start_cloud_server
from JARVIS.core.system.utils.port_manager import PortManager

DEFAULT_CLOUD_PORT = 8008
LOCK_PORT = 19106


def main():
    # 1. Prevent duplicate startup using socket lock
    lock_socket = PortManager.acquire_service_lock("cloud_service", LOCK_PORT)
    if lock_socket is None:
        print("[CLOUD SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)

    # 2. Get available port
    base_port = int(os.environ.get("JARVIS_CLOUD_PORT", str(DEFAULT_CLOUD_PORT)))
    try:
        port = PortManager.get_available_port(base_port)
    except Exception as e:
        print(f"[CLOUD SERVICE] Port allocation failed: {e}")
        sys.exit(1)
        
    # 3. Start Server in a daemon thread
    server_thread = threading.Thread(target=start_cloud_server, args=(port,), daemon=True, name="cloud_server_thread")
    server_thread.start()
    
    # 4. Maintain supervisor heartbeat
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, "cloud_service.json")
    
    print(f"[CLOUD SERVICE] Service fully initialized on port {port}. Starting heartbeat loop.")
    sys.stdout.flush()

    try:
        while True:
            # Write heartbeat payload
            try:
                with open(hb_path, "w", encoding="utf-8") as f:
                    json.dump({"pid": os.getpid(), "timestamp": time.time(), "status": "healthy", "port": port}, f)
            except Exception:
                pass
            time.sleep(8.0)
    except (KeyboardInterrupt, SystemExit):
        print("[CLOUD SERVICE] Shutting down...")
    finally:
        if lock_socket:
            lock_socket.close()


if __name__ == "__main__":
    main()
