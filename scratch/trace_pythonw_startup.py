"""Trace supervisor startup under pythonw.exe — writes ALL output to a log file
since pythonw has no console."""
import sys, os

# Redirect stdout/stderr to a file immediately — pythonw.exe has no console
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(_root)
sys.path.insert(0, _root)

_log_path = os.path.join("logs", "_pythonw_trace.log")
os.makedirs("logs", exist_ok=True)
_log_fh = open(_log_path, "w", encoding="utf-8")

def trace(msg):
    _log_fh.write(msg + "\n")
    _log_fh.flush()

trace(f"=== PYTHONW SUPERVISOR TRACE (pid={os.getpid()}) ===")
trace(f"sys.executable = {sys.executable}")
trace(f"cwd = {os.getcwd()}")

try:
    trace("Step 1: Basic stdlib imports...")
    import time, json, subprocess, atexit, signal, threading, hashlib
    trace("  OK")

    trace("Step 2: dotenv + env_helper...")
    from dotenv import load_dotenv
    from JARVIS.core.system.utils.env_helper import find_env_file
    trace(f"  env_file = {find_env_file()}")

    trace("Step 3: venv_resolver (get_resolved_env)...")
    from JARVIS.core.system.venv_resolver import get_resolved_env
    r = get_resolved_env()
    trace(f"  resolved: {r.python_exe}")

    trace("Step 4: load_dotenv...")
    load_dotenv(find_env_file())
    trace("  OK")

    trace("Step 5: psutil process_iter (stale killer simulation)...")
    import psutil
    _self_pid = os.getpid()
    _count = 0
    _matched = []
    for _proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            _count += 1
            if _proc.pid == _self_pid:
                continue
            _cmdline = " ".join(_proc.info.get('cmdline') or []).lower()
            if "jarvis.services.supervisor" in _cmdline or (
                "supervisor.py" in _cmdline and "jarvis" in _cmdline
            ):
                _matched.append((_proc.pid, _cmdline[:80]))
        except Exception as e:
            trace(f"  process_iter error on PID {getattr(_proc, 'pid', '?')}: {e}")
    trace(f"  iterated {_count} processes, matched {len(_matched)}: {_matched}")

    trace("Step 6: PortManager import...")
    from JARVIS.core.system.utils.port_manager import PortManager
    trace("  OK")

    trace("Step 7: acquire_service_lock('supervisor', 19100)...")
    s = PortManager.acquire_service_lock("supervisor", 19100)
    trace(f"  lock result: {s}")
    if s:
        s.close()
        trace("  lock released")
    else:
        trace("  !!! LOCK FAILED — THIS IS THE BUG !!!")

    trace("=== ALL STEPS COMPLETED ===")

except Exception as exc:
    import traceback
    trace(f"\n!!! EXCEPTION: {exc}")
    trace(traceback.format_exc())

finally:
    _log_fh.close()
