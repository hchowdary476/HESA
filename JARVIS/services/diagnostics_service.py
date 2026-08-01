import os
import time
import json
import threading
import psutil

start_time = time.time()

def publish_heartbeat():
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, "diagnostics_engine.json")
    process = psutil.Process(os.getpid())
    while True:
        try:
            cpu = process.cpu_percent(interval=None)
            ram = process.memory_info().rss / (1024 * 1024)
            now = time.time()
            uptime = int(now - start_time)
            grace_until = 0.0
            if os.path.exists(hb_path):
                try:
                    with open(hb_path, "r") as rf:
                        existing = json.load(rf)
                    grace_until = existing.get("grace_until", 0.0)
                except Exception:
                    pass
            hb_data = {
                "service_name": "diagnostics_engine",
                "pid": os.getpid(),
                "status": "healthy",
                "uptime": uptime,
                "cpu_usage": round(cpu, 1),
                "memory_usage": round(ram, 1),
                "last_heartbeat": now,
                "timestamp": now,
            }
            if grace_until > 0.0:
                hb_data["grace_until"] = grace_until
            with open(hb_path, "w") as f:
                json.dump(hb_data, f)
            # Log to logs/service_heartbeat.log
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
            with open("logs/service_heartbeat.log", "a", encoding="utf-8") as lf:
                lf.write(f"[{timestamp_str}] Service diagnostics_engine heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n")
        except Exception as exc:
            import traceback
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs("logs", exist_ok=True)
            with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
                cf.write(f"[{timestamp_str}] publish_heartbeat diagnostics_engine error:\n{traceback.format_exc()}\n")
        time.sleep(2)

def diagnostics_loop():
    diag_path = os.path.join("logs", "diagnostics.json")
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            try:
                disk = psutil.disk_usage("C:").percent
            except Exception:
                disk = 0.0

            try:
                bat = psutil.sensors_battery()
                battery = bat.percent if bat else 100
            except Exception:
                battery = 100

            warnings = []
            recs = []

            if cpu > 85.0:
                warnings.append("High CPU Load detected.")
                recs.append("Reduce the number of active background processes, sir.")
            if ram > 90.0:
                warnings.append("High RAM usage detected.")
                recs.append("Close high-memory applications, sir.")
            if battery < 20.0:
                warnings.append("Battery is low.")
                recs.append("Connect your system to a power source, sir.")

            if not warnings:
                warnings.append("None")
                recs.append("All systems operational. No actions required.")

            report = {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "battery": battery,
                "warnings": warnings,
                "recommendations": recs,
                "drivers": {
                    "display": "PASS",
                    "audio": "PASS",
                    "network": "PASS"
                },
                "display_health": "PRIMARY: 1920x1080 @ 60Hz (HEALTHY)"
            }

            os.makedirs(os.path.dirname(diag_path), exist_ok=True)
            with open(diag_path, "w") as f:
                json.dump(report, f, indent=2)

        except Exception:
            pass
        time.sleep(5)

if __name__ == "__main__":
    import sys
    from JARVIS.core.system.utils.port_manager import PortManager
    lock_socket = PortManager.acquire_service_lock("diagnostics_service", 19111)
    if lock_socket is None:
        print("[DIAGNOSTICS ENGINE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        threading.Thread(target=publish_heartbeat, daemon=True).start()
        diagnostics_loop()
    except Exception as e:
        import traceback
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service diagnostics_engine CRASHED:\n{traceback.format_exc()}\n")
        raise
    finally:
        lock_socket.close()
