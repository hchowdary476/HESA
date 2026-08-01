"""Trace supervisor startup path step-by-step to find where it dies."""
import sys, os
sys.path.insert(0, os.path.abspath("."))

_log_path = os.path.join("logs", "_supervisor_trace.log")
os.makedirs("logs", exist_ok=True)

def trace(msg):
    print(msg)
    with open(_log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

trace("=== SUPERVISOR STARTUP TRACE ===")

trace("Step 1: Basic stdlib imports...")
import time, json, subprocess, atexit, signal, threading, hashlib
trace("  OK")

trace("Step 2: dotenv + env_helper...")
from dotenv import load_dotenv
from JARVIS.core.system.utils.env_helper import find_env_file
trace(f"  env_file = {find_env_file()}")

trace("Step 3: venv_resolver (this produces the log lines)...")
from JARVIS.core.system.venv_resolver import get_resolved_env
r = get_resolved_env()
trace(f"  resolved: {r.python_exe}")

trace("Step 4: load_dotenv...")
load_dotenv(find_env_file())
trace("  OK")

trace("Step 5: config paths (resolve_config_paths)...")
try:
    from JARVIS.config.paths import resolve_config_paths
    p = resolve_config_paths()
    trace(f"  settings_file = {p.settings_file}")
except Exception as e:
    trace(f"  FAILED: {e}")

trace("Step 6: psutil process_iter (stale killer simulation)...")
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
        trace(f"  process_iter error on PID {_proc.pid}: {e}")
trace(f"  iterated {_count} processes, matched {len(_matched)}: {_matched}")

trace("Step 7: PortManager import...")
from JARVIS.core.system.utils.port_manager import PortManager
trace("  OK")

trace("Step 8: acquire_service_lock('supervisor', 19100)...")
s = PortManager.acquire_service_lock("supervisor", 19100)
trace(f"  lock result: {s}")
if s:
    s.close()
    trace("  lock released")
else:
    trace("  LOCK FAILED — this is where supervisor dies silently!")

trace("=== ALL STEPS COMPLETED ===")
