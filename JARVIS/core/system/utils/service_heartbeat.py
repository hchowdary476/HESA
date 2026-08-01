import os
import time
import json
import traceback
import psutil
import threading
import sys

def publish_heartbeat(service_name: str, filename: str, interval: float = 2.0):
    """
    Spawns a daemon thread that writes a compliant heartbeat every `interval` seconds.
    Complies with Requirement 4 (fields: service_name, pid, status, uptime, cpu_usage, memory_usage, last_heartbeat).
    Also writes logs to logs/service_heartbeat.log on every heartbeat update.
    """
    hb_dir = os.path.abspath(os.path.join("logs", "heartbeats"))
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, filename)
    
    start_time = time.time()
    process = psutil.Process(os.getpid())
    
    # Pre-warm cpu percent check
    process.cpu_percent(interval=None)

    def _loop():
        while True:
            try:
                cpu = process.cpu_percent(interval=None)
                ram = process.memory_info().rss / (1024 * 1024)
                now = time.time()
                uptime = int(now - start_time)
                
                hb_data = {
                    "service_name": service_name,
                    "pid": os.getpid(),
                    "status": "healthy",
                    "uptime": uptime,
                    "cpu_usage": round(cpu, 1),
                    "memory_usage": round(ram, 1),
                    "last_heartbeat": now,
                    "timestamp": now  # Keep timestamp for supervisor backwards-compatibility
                }
                
                # Write heartbeat json
                with open(hb_path, "w") as f:
                    json.dump(hb_data, f)
                
                # Log to logs/service_heartbeat.log
                os.makedirs("logs", exist_ok=True)
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                with open("logs/service_heartbeat.log", "a", encoding="utf-8") as lf:
                    lf.write(f"[{timestamp_str}] Service {service_name} heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n")
                    
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t

def wrap_service_main(service_name: str, main_func, *args, **kwargs):
    """
    Wraps the main loop execution of a service to capture unhandled exceptions and log tracebacks to logs/service_crash.log.
    """
    try:
        main_func(*args, **kwargs)
    except BaseException as e:
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        # Log to service_crash.log
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service {service_name} CRASHED:\n{traceback.format_exc()}\n")
        # Notify Diagnostics Center of the failure
        try:
            from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
            DiagnosticsCenter().update_subsystem(service_name, "Failed", failed=True)
        except Exception:
            pass
        raise e

def update_subcomponent_heartbeat(subcomponent_name: str, status: str = "healthy", details: dict | None = None):
    """
    Writes a heartbeat file for voice pipeline subcomponents: voice_listener, wake_listener, audio_stream, speech_backend.
    """
    try:
        hb_dir = os.path.abspath(os.path.join("logs", "heartbeats"))
        os.makedirs(hb_dir, exist_ok=True)
        hb_path = os.path.join(hb_dir, f"{subcomponent_name}.json")
        now = time.time()
        
        hb_data = {
            "subcomponent_name": subcomponent_name,
            "pid": os.getpid(),
            "status": status,
            "last_heartbeat": now,
            "timestamp": now,
            "details": details or {}
        }
        with open(hb_path, "w") as f:
            json.dump(hb_data, f)
    except Exception:
        pass
