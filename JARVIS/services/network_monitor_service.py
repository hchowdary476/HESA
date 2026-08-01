import json
import os
import socket
import threading
import time

import psutil


def check_internet(host="8.8.8.8", port=53, timeout=3.0):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def get_ping_latency(host="8.8.8.8", port=53, timeout=0.5):
    try:
        start = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return round((time.perf_counter() - start) * 1000.0, 1)
    except Exception:
        return 999.0


start_time = time.time()


def publish_heartbeat():
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    hb_path = os.path.join(hb_dir, "network_monitor.json")
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
                    with open(hb_path) as rf:
                        existing = json.load(rf)
                    grace_until = existing.get("grace_until", 0.0)
                except Exception:
                    pass
            hb_data = {
                "service_name": "network_monitor",
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
                lf.write(
                    f"[{timestamp_str}] Service network_monitor heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n"
                )
        except Exception:
            pass
        time.sleep(2)


def network_loop():
    network_path = os.path.join("logs", "network_status.json")

    last_net_bytes = 0
    last_net_sent = 0
    last_net_recv = 0
    last_net_time = time.perf_counter()

    try:
        net_io = psutil.net_io_counters()
        last_net_bytes = net_io.bytes_sent + net_io.bytes_recv
        last_net_sent = net_io.bytes_sent
        last_net_recv = net_io.bytes_recv
    except Exception:
        pass

    while True:
        try:
            internet_status = "ONLINE" if check_internet() else "OFFLINE"
            latency = get_ping_latency()

            # Speed calculations
            current_time = time.perf_counter()
            net_speed_str = "0.0 KB/s"
            upload_speed_str = "0.0 KB/s"
            download_speed_str = "0.0 KB/s"

            try:
                net_io = psutil.net_io_counters()
                current_bytes = net_io.bytes_sent + net_io.bytes_recv
                time_diff = current_time - last_net_time
                if time_diff > 0:
                    net_speed = (current_bytes - last_net_bytes) / time_diff
                    sent_speed = (net_io.bytes_sent - last_net_sent) / time_diff
                    recv_speed = (net_io.bytes_recv - last_net_recv) / time_diff
                    net_speed_str = f"{round(net_speed / 1024.0, 1)} KB/s"
                    upload_speed_str = f"{round(sent_speed / 1024.0, 1)} KB/s"
                    download_speed_str = f"{round(recv_speed / 1024.0, 1)} KB/s"

                last_net_bytes = current_bytes
                last_net_sent = net_io.bytes_sent
                last_net_recv = net_io.bytes_recv
                last_net_time = current_time
            except Exception:
                pass

            report = {
                "internet_status": internet_status,
                "internet_latency": latency,
                "network_speed": net_speed_str,
                "upload_speed": upload_speed_str,
                "download_speed": download_speed_str,
                "timestamp": time.time(),
            }
            os.makedirs(os.path.dirname(network_path), exist_ok=True)
            with open(network_path, "w") as f:
                json.dump(report, f)
        except Exception:
            pass
        time.sleep(10)


if __name__ == "__main__":
    import sys

    from JARVIS.core.system.utils.port_manager import PortManager

    lock_socket = PortManager.acquire_service_lock("network_monitor_service", 19109)
    if lock_socket is None:
        print("[NETWORK MONITOR] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        threading.Thread(target=publish_heartbeat, daemon=True).start()
        network_loop()
    except Exception:
        import traceback

        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service network_monitor CRASHED:\n{traceback.format_exc()}\n")
        raise
    finally:
        lock_socket.close()
