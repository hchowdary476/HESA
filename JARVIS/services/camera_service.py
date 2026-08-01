import os
import time
import json
import threading
import psutil

start_time = time.time()

def publish_heartbeat():
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, "camera_engine.json")
    process = psutil.Process(os.getpid())
    while True:
        try:
            cpu = process.cpu_percent(interval=None)
            ram = process.memory_info().rss / (1024 * 1024)
            now = time.time()
            uptime = int(now - start_time)
            hb_data = {
                "service_name": "camera_engine",
                "pid": os.getpid(),
                "status": "healthy",
                "uptime": uptime,
                "cpu_usage": round(cpu, 1),
                "memory_usage": round(ram, 1),
                "last_heartbeat": now,
                "timestamp": now
            }
            with open(hb_path, "w") as f:
                json.dump(hb_data, f)
            # Log to logs/service_heartbeat.log
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
            with open("logs/service_heartbeat.log", "a", encoding="utf-8") as lf:
                lf.write(f"[{timestamp_str}] Service camera_engine heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n")
        except Exception:
            pass
        time.sleep(2)

def camera_loop():
    camera_path = os.path.join("logs", "camera_status.json")
    while True:
        try:
            # Check camera device state
            status = "STANDBY"
            try:
                from JARVIS.core.system.utils.camera_tracker import get_cached_camera_status
                status = get_cached_camera_status()
            except Exception:
                pass
                
            report = {
                "status": status,
                "timestamp": time.time()
            }
            os.makedirs(os.path.dirname(camera_path), exist_ok=True)
            with open(camera_path, "w") as f:
                json.dump(report, f)
        except Exception:
            pass
        time.sleep(5)

if __name__ == "__main__":
    import sys
    from JARVIS.core.system.utils.port_manager import PortManager
    lock_socket = PortManager.acquire_service_lock("camera_service", 19108)
    if lock_socket is None:
        print("[CAMERA ENGINE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        threading.Thread(target=publish_heartbeat, daemon=True).start()
        camera_loop()
    except Exception as e:
        import traceback
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service camera_engine CRASHED:\n{traceback.format_exc()}\n")
        raise
    finally:
        lock_socket.close()
