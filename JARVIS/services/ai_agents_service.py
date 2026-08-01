import json
import os
import threading
import time

from JARVIS.core.system.utils.service_heartbeat import wrap_service_main


def _start():

    import psutil

    from JARVIS.core.ai_router.multi_agent_system import AgentManager

    _exc_box = []

    def _run_agents():
        try:
            agent_mgr = AgentManager()
            agent_mgr.run_agent_loops()

            hb_dir = os.path.join("logs", "heartbeats")
            os.makedirs(hb_dir, exist_ok=True)
            hb_path = os.path.join(hb_dir, "ai_agents.json")
            process = psutil.Process(os.getpid())
            start_time = time.time()

            while True:
                try:
                    cpu = process.cpu_percent(interval=None)
                    ram = process.memory_info().rss / (1024 * 1024)
                    now = time.time()
                    uptime = int(now - start_time)

                    # Retrieve agent states
                    agent_telemetry = agent_mgr.get_agents_telemetry()

                    # Find the active running agent (if any is busy)
                    active_agent_name = "None"
                    active_agent_desc = "Cognitive cores idle, sir."
                    for agent in agent_telemetry:
                        if agent["status"] == "BUSY":
                            active_agent_name = agent["name"]
                            active_agent_desc = f"Executing task ({agent['pending_tasks']} enqueued)"
                            break

                    hb_data = {
                        "service_name": "ai_agents",
                        "pid": os.getpid(),
                        "status": "healthy",
                        "uptime": uptime,
                        "cpu_usage": round(cpu, 1),
                        "memory_usage": round(ram, 1),
                        "last_heartbeat": now,
                        "timestamp": now,
                        "active_agent": active_agent_name,
                        "active_agent_desc": active_agent_desc,
                        "agents": agent_telemetry,
                    }

                    with open(hb_path, "w") as f:
                        json.dump(hb_data, f)

                    # Log to logs/service_heartbeat.log
                    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    with open("logs/service_heartbeat.log", "a", encoding="utf-8") as lf:
                        lf.write(
                            f"[{timestamp_str}] Service ai_agents heartbeat: CPU={hb_data['cpu_usage']}%, RAM={hb_data['memory_usage']}MB, Uptime={uptime}s\n"
                        )
                except Exception:
                    pass
                time.sleep(2)
        except BaseException as exc:
            _exc_box.append(exc)

    worker = threading.Thread(target=_run_agents, daemon=True, name="ai-agents-main")
    worker.start()
    worker.join()

    # Re-raise so wrap_service_main can log it to service_crash.log
    if _exc_box:
        raise _exc_box[0]


if __name__ == "__main__":
    import sys

    from JARVIS.core.system.utils.port_manager import PortManager

    lock_socket = PortManager.acquire_service_lock("ai_agents_service", 19105)
    if lock_socket is None:
        print("[AI AGENTS SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        wrap_service_main("ai_agents", _start)
    except Exception:
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        import traceback

        os.makedirs("logs", exist_ok=True)
        with open("logs/service_crash.log", "a", encoding="utf-8") as cf:
            cf.write(f"[{timestamp_str}] Service ai_agents CRASHED:\n{traceback.format_exc()}\n")
        raise
    finally:
        lock_socket.close()
