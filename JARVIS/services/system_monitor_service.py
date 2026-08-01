import os
import time
import json
import threading
import psutil

start_time = time.time()

def publish_heartbeat():
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, "system_monitor.json")
    process = psutil.Process(os.getpid())
    while True:
        try:
            cpu = process.cpu_percent(interval=None)
            ram = process.memory_info().rss / (1024 * 1024)
            now = time.time()
            uptime = int(now - start_time)
            hb_data = {
                "service_name": "system_monitor",
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
                lf.write(f"[{timestamp_str}] Service system_monitor heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n")
        except Exception:
            pass
        time.sleep(2)

def monitor_loop():
    monitor_path = os.path.join("logs", "system_monitor.json")
    from JARVIS.core.system.predictive_intelligence import PredictiveIntelligence
    predictor = PredictiveIntelligence()
    
    # Track network metrics locally to compute network rate (kbps)
    last_net_bytes = 0
    last_time = time.time()
    try:
        last_net_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    except Exception:
        pass

    while True:
        try:
            # 1. Fetch current global metrics
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            try:
                disk = psutil.disk_usage("C:").percent
            except Exception:
                disk = 0.0
                
            try:
                bat = psutil.sensors_battery()
                battery = bat.percent if bat else 100.0
            except Exception:
                battery = 100.0
                
            # Net throughput
            net_kbps = 0.0
            now = time.time()
            try:
                curr_net = psutil.net_io_counters()
                curr_bytes = curr_net.bytes_sent + curr_net.bytes_recv
                time_diff = now - last_time
                if time_diff > 0:
                    net_kbps = ((curr_bytes - last_net_bytes) / 1024.0) / time_diff
                last_net_bytes = curr_bytes
                last_time = now
            except Exception:
                pass
                
            # Feed metrics to the predictor
            predictor.add_metrics(cpu, ram, disk, battery, net_kbps)

            processes = []
            cpu_cores = psutil.cpu_count() or 1
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    info = proc.info
                    status_raw = (info.get('status') or 'running').lower()
                    status_map = {
                        'running': 'RUNNING', 'sleeping': 'SLEEPING', 'idle': 'IDLE',
                        'stopped': 'STOPPED', 'zombie': 'ZOMBIE', 'dead': 'DEAD',
                        'disk-sleep': 'DISK-SLP', 'tracing-stop': 'TRACED'
                    }
                    status_display = status_map.get(status_raw, status_raw.upper()[:8])
                    
                    # Normalize CPU percentage by core count to ensure it does not exceed 100%
                    raw_cpu = info.get('cpu_percent') or 0.0
                    normalized_cpu = raw_cpu / cpu_cores
                    
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'] or "Unknown",
                        "cpu": round(normalized_cpu, 1),
                        "ram": round(info['memory_percent'] or 0.0, 1),
                        "status": status_display
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            
            report = {
                "active_processes": len(psutil.pids()),
                "processes_list": processes[:30]
            }

            os.makedirs(os.path.dirname(monitor_path), exist_ok=True)
            with open(monitor_path, "w") as f:
                json.dump(report, f)
        except Exception:
            pass
        interval = float(os.getenv("JARVIS_PROCESS_MONITOR_INTERVAL", "5.0"))
        time.sleep(interval)

if __name__ == "__main__":
    import sys
    from JARVIS.core.system.utils.port_manager import PortManager
    lock_socket = PortManager.acquire_service_lock("system_monitor_service", 19107)
    if lock_socket is None:
        print("[SYSTEM MONITOR] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        threading.Thread(target=publish_heartbeat, daemon=True).start()
        monitor_loop()
    except Exception as e:
        import traceback
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service system_monitor CRASHED:\n{traceback.format_exc()}\n")
        raise
    finally:
        lock_socket.close()
