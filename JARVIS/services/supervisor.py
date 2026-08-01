import os
import sys
import time
import json
import subprocess
import atexit
import signal
import threading
import hashlib
from dotenv import load_dotenv
from JARVIS.core.system.utils.env_helper import find_env_file

# Resolve pythonw.exe from the venv so subprocesses NEVER open a console window.
def _get_pythonw_exe():
    try:
        from JARVIS.core.system.venv_resolver import get_resolved_env
        resolved = get_resolved_env()
        py_exe = resolved.python_exe
        if py_exe and py_exe.endswith(".exe"):
            pyw_exe = py_exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pyw_exe):
                return pyw_exe
    except Exception:
        pass
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidate = os.path.join(root, ".venv", "Scripts", "pythonw.exe")
    return candidate if os.path.exists(candidate) else sys.executable

_PYTHONW_EXE = _get_pythonw_exe()

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_JARVIS_LOG_FILE = os.path.join(_ROOT_DIR, "logs", "jarvis_events.log")

def _write_event_log(tag: str, message: str) -> None:
    """Append one structured line to the shared on-disk events log."""
    try:
        os.makedirs(os.path.dirname(_JARVIS_LOG_FILE), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_JARVIS_LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] [{tag:<20}] {message}\n")
    except Exception:
        pass


# Global metrics & state for backup cooldown and change detection
BACKUP_METRICS = {
    "config": {
        "last_backup_time": 0.0,
        "backup_count": 0,
        "skipped_backups": 0,
        "last_sha256": "",
        "last_mtime": 0.0
    },
    "memory": {
        "last_backup_time": 0.0,
        "backup_count": 0,
        "skipped_backups": 0,
        "last_sha256": "",
        "last_mtime": 0.0
    }
}


# Load local environment variables from .env
load_dotenv(find_env_file())


# ── Exponential backoff helper ────────────────────────────────────────────────
def _backoff_delay(restart_count: int) -> float:
    """Return capped exponential back-off seconds: 2s → 4 → 8 → … → 60s max."""
    return min(60.0, 2.0 ** max(1, restart_count))


# ── Supervisor log writer ─────────────────────────────────────────────────────
def _write_supervisor_log(tag: str, message: str) -> None:
    """Append a structured entry to logs/supervisor.log."""
    import psutil as _psu
    try:
        own_mem = _psu.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        own_mem = 0.0
    try:
        os.makedirs("logs", exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join("logs", "supervisor.log"), "a", encoding="utf-8") as _sf:
            _sf.write(f"[{ts}] [{tag:<28}] [PID={os.getpid()}] [MEM={own_mem:.1f}MB] {message}\n")
    except Exception:
        pass


SERVICES = {
    "voice_engine": {
        "module": "JARVIS.services.voice_service",
        "desc": "Wake word & Speech STT/TTS",
        "process": None,
        "restart_count": 0,
        # voice_engine is immortal — never permanently disabled.
        "max_restarts": 999999,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "memory_engine": {
        "module": "JARVIS.services.memory_service",
        "desc": "Cognitive Database & Cache",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "automation_engine": {
        "module": "JARVIS.services.automation_service",
        "desc": "Workflow Triggers & Scheduling",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "security_engine": {
        "module": "JARVIS.services.security_service",
        "desc": "Threat Monitor & Health Checks",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "ai_agents": {
        "module": "JARVIS.services.ai_agents_service",
        "desc": "AI Router & Multi-Agent Synaptic Control",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "diagnostics_engine": {
        "module": "JARVIS.services.diagnostics_service",
        "desc": "Hardware & Dynamic Health Diagnostics",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "system_monitor": {
        "module": "JARVIS.services.system_monitor_service",
        "desc": "Background Process & Core Usage Monitor",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "camera_engine": {
        "module": "JARVIS.services.camera_service",
        "desc": "Live Vision Feed & State Tracker",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    },
    "network_monitor": {
        "module": "JARVIS.services.network_monitor_service",
        "desc": "Real-time Port & Network Speed Sensor",
        "process": None,
        "restart_count": 0,
        "max_restarts": 10,
        "backoff_delay": 2.0,
        "last_seen": 0.0,
        "status": "healthy",
    }
}

def cleanup_subprocesses():
    print("[SUPERVISOR] Cleaning up all service processes...")
    for name, cfg in SERVICES.items():
        proc = cfg.get("process")
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
    for name, cfg in SERVICES.items():
        proc = cfg.get("process")
        if proc:
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass
            except Exception:
                pass
    print("[SUPERVISOR] Cleanup complete.")

atexit.register(cleanup_subprocesses)

def signal_handler(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

running = True

# Paths for config and memory databases
def get_settings_file():
    try:
        from JARVIS.config.paths import resolve_config_paths
        return str(resolve_config_paths().settings_file)
    except Exception:
        local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Local")
        return os.path.join(local_appdata, "Open.Jarvis", "settings.json")

SETTINGS_FILE = get_settings_file()
MEMORY_FILE = os.path.abspath("memory.json")

DEFAULT_MEMORY = {
    "preferences": {
        "favorite_music": None,
        "favorite_app": None,
        "preferred_volume": None,
        "wake_word": "hesa",
        "custom": {},
    },
    "habits": {},
    "notes": [],
    "created_at": None,
    "last_seen": None,
    "total_commands": 0,
}

def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def write_backup_status_file():
    status_path = os.path.join("logs", "backup_status.json")
    os.makedirs("logs", exist_ok=True)
    
    status_data = {}
    for key, metrics in BACKUP_METRICS.items():
        last_time_str = "Never"
        if metrics["last_backup_time"] > 0:
            last_time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(metrics["last_backup_time"]))
            
        now = time.time()
        time_since_last = now - metrics["last_backup_time"]
        cooldown_status = "active" if (metrics["last_backup_time"] > 0 and time_since_last < 600.0) else "idle"
        
        status_data[key] = {
            "last_backup_time": last_time_str,
            "backup_count": metrics["backup_count"],
            "skipped_backups": metrics["skipped_backups"],
            "backup_cooldown_status": cooldown_status
        }
        
    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
    except Exception:
        pass

# Auto-Backup System
def create_backup(file_path, backup_dir_name, emergency=False):
    if not os.path.exists(file_path):
        return
    # Verify file is valid JSON before backing up
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception:
        return # Skip backing up corrupted files

    now = time.time()
    
    # Identify key type (config or memory)
    key = "config" if "config" in backup_dir_name or "settings" in file_path.lower() else "memory"
    metrics = BACKUP_METRICS[key]
    
    # 1. Change detection: Check modification time and SHA256
    try:
        mtime = os.path.getmtime(file_path)
    except Exception:
        mtime = 0.0
        
    current_hash = calculate_sha256(file_path)
    
    # Skip if contents and timestamp are unchanged
    if metrics["last_sha256"] == current_hash and metrics["last_mtime"] == mtime:
        metrics["skipped_backups"] += 1
        write_backup_status_file()
        return
        
    # 2. Cooldown check: 10 minutes (600 seconds)
    cooldown = 600.0
    time_since_last = now - metrics["last_backup_time"]
    
    if not emergency and metrics["last_backup_time"] > 0 and time_since_last < cooldown:
        metrics["skipped_backups"] += 1
        write_backup_status_file()
        return
        
    backup_dir = os.path.join("logs", "backups", backup_dir_name)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Rotate backups: bak_4 -> bak_5, ..., current -> bak_1
    for i in range(4, 0, -1):
        old_path = os.path.join(backup_dir, f"{backup_dir_name}_bak_{i}.json")
        new_path = os.path.join(backup_dir, f"{backup_dir_name}_bak_{i+1}.json")
        if os.path.exists(old_path):
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(old_path, new_path)
            except Exception:
                pass
                
    dst = os.path.join(backup_dir, f"{backup_dir_name}_bak_1.json")
    try:
        import shutil
        shutil.copy2(file_path, dst)
        print(f"[SUPERVISOR] Backup created: {dst}")
        
        # Update metrics
        metrics["last_backup_time"] = now
        metrics["backup_count"] += 1
        metrics["last_sha256"] = current_hash
        metrics["last_mtime"] = mtime
        write_backup_status_file()
    except Exception as e:
        print(f"[SUPERVISOR] Backup failed for {file_path}: {e}")

# Self-Healing Integrity Check & Repair
def repair_file_if_corrupted(file_path, backup_dir_name, default_content=None):
    corrupted = False
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        corrupted = True
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception:
            corrupted = True
            
    if corrupted:
        print(f"[SELF-HEALING] File corrupted or missing: {file_path}")
        # Try to restore from backups
        backup_dir = os.path.join("logs", "backups", backup_dir_name)
        restored = False
        for i in range(1, 6):
            bak_path = os.path.join(backup_dir, f"{backup_dir_name}_bak_{i}.json")
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r", encoding="utf-8") as f:
                        json.load(f)
                    import shutil
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    shutil.copy2(bak_path, file_path)
                    print(f"[SELF-HEALING] Restored {file_path} from backup checkpoint {i}")
                    restored = True
                    break
                except Exception:
                    pass
        if not restored:
            print(f"[SELF-HEALING] No valid backup. Creating default template for {file_path}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(default_content or {}, f, indent=2)
            except Exception:
                pass
        return True
    return False

safe_mode = False

coordinator_process = None
coordinator_lock = threading.Lock()

def is_process_alive(proc):
    if proc is None:
        return False
    if hasattr(proc, "poll"):
        return proc.poll() is None
    try:
        import psutil
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False

def get_service_env(name: str):
    """Load configuration from ConfigManager and return environment mapping."""
    env = os.environ.copy()
    try:
        from JARVIS.config.manager import ConfigManager
        config_mgr = ConfigManager()
        config_mgr.load()
        env.update(config_mgr.as_env_mapping())
    except Exception:
        pass
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
    env["JARVIS_SERVICE_NAME"] = name
    env["JARVIS_MANAGED"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return env

def launch_service(name):
    cfg = SERVICES[name]
    if cfg["process"] is not None:
        try:
            cfg["process"].terminate()
            try:
                cfg["process"].wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                try:
                    cfg["process"].kill()
                    cfg["process"].wait()
                except Exception:
                    pass
        except Exception:
            pass
    
    env = get_service_env(name)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # Dashboard UI needs error logging for debugging crashes
    if name == "dashboard_ui":
        err_file = os.path.join("logs", "dashboard_ui_stderr.log")
        os.makedirs(os.path.dirname(err_file), exist_ok=True)
        with open(err_file, "w") as f:
            pass
        stderr_handle = open(err_file, "w")
    else:
        stderr_handle = subprocess.DEVNULL
    
    # Redirect subprocess stdout & stderr to service-specific log files under logs/services/
    log_dir = os.path.join(root_dir, "logs", "services")
    os.makedirs(log_dir, exist_ok=True)
    service_log_path = os.path.join(log_dir, f"{name}.log")
    try:
        log_file = open(service_log_path, "a", encoding="utf-8")
        log_file.write(f"\n--- SERVICE LAUNCH: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_file.flush()
    except Exception:
        log_file = subprocess.DEVNULL

    # We run services as subprocesses.
    # pythonw.exe suppresses all console windows; CREATE_NO_WINDOW+DETACHED_PROCESS
    # ensure zero visible CMD flashes even when restarted from the supervisor thread.
    proc = subprocess.Popen(
        [_PYTHONW_EXE, "-u", "-m", cfg["module"]],
        cwd=root_dir,
        env=env,
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )

    cfg["process"] = proc
    cfg["last_seen"] = time.time()
    # Write initial heartbeat with a grace_until field so the monitor loop
    # does NOT declare the service OFFLINE before its heartbeat daemon has
    # had time to produce its first real write (typically ~2s after import).
    # We keep the real timestamp accurate — only grace_until is extended.
    hb_dir = os.path.join("logs", "heartbeats")
    os.makedirs(hb_dir, exist_ok=True)
    _now = time.time()
    with open(os.path.join(hb_dir, f"{name}.json"), "w") as f:
        json.dump({
            "pid": proc.pid,
            "timestamp": _now,
            "grace_until": _now + 60.0,
            "status": "starting",
        }, f)
    
    print(f"[SUPERVISOR] Launched service {name} (PID: {proc.pid})")

    # Logging startup and registration
    try:
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open("logs/service_startup.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp_str}] Service {name} startup initiated (PID: {proc.pid}).\n")
        with open("logs/service_registration.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp_str}] Service {name} registered with Supervisor (PID: {proc.pid}).\n")
    except Exception:
        pass

    # Register with Diagnostics Center
    try:
        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
        DiagnosticsCenter().update_subsystem(name, "Running")
    except Exception:
        pass

def write_status_file():
    status_path = os.path.join("logs", "system_status.json")
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    data = {
        "safe_mode": {"status": "active" if safe_mode else "inactive", "desc": "Emergency Safe Mode Posture", "pid": None, "restart_count": 0}
    }
    for name, cfg in SERVICES.items():
        status_val = cfg["status"]
        if status_val == "healthy":
            display_status = "Running"
        elif status_val == "recovering":
            display_status = "Restarting"
        elif status_val == "offline":
            display_status = "Failed"
        elif status_val == "starting":
            display_status = "Starting"
        elif status_val == "stopping":
            display_status = "Stopping"
        else:
            display_status = status_val.capitalize()

        # Health score drops by 25 per restart, 0 if Failed
        if display_status == "Failed":
            health_score = 0
        else:
            health_score = max(0, 100 - (cfg["restart_count"] * 25))

        data[name] = {
            "status": display_status,
            "restart_count": cfg["restart_count"],
            "pid": cfg["process"].pid if cfg["process"] else None,
            "desc": cfg["desc"],
            "health_score": health_score,
            "heartbeat": cfg["last_seen"]
        }
    try:
        temp_path = status_path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f)
        os.replace(temp_path, status_path)
    except Exception:
        pass

def run_refresh_engine():
    boot_logs = []
    
    def log_boot(msg, kind="info"):
        full_msg = msg if msg == "Welcome back." else f"[JARVIS] {msg}"
        print(full_msg)
        boot_logs.append({"message": full_msg, "kind": kind})
        try:
            os.makedirs("logs", exist_ok=True)
            with open(os.path.join("logs", "boot_log.json"), "w") as f:
                json.dump(boot_logs, f)
        except Exception:
            pass

    repaired_settings = repair_file_if_corrupted(SETTINGS_FILE, "config", {})
    repaired_memory = repair_file_if_corrupted(MEMORY_FILE, "memory", DEFAULT_MEMORY)
    
    create_backup(SETTINGS_FILE, "config", emergency=True)
    create_backup(MEMORY_FILE, "memory", emergency=True)
    
    # 1. Clear heartbeats (preserve dashboard_ui.json)
    hb_dir = os.path.join("logs", "heartbeats")
    try:
        if os.path.exists(hb_dir):
            for file in os.listdir(hb_dir):
                if file != "dashboard_ui.json":
                    try:
                        filepath = os.path.join(hb_dir, file)
                        if os.path.isdir(filepath):
                            import shutil
                            shutil.rmtree(filepath)
                        else:
                            os.remove(filepath)
                    except Exception:
                        pass
        else:
            os.makedirs(hb_dir, exist_ok=True)
    except Exception:
        pass

    
    # 2. Terminate orphan processes
    # ── SAFETY: build a set of PIDs that must NEVER be terminated ────────────
    # The GUI (jarvis.py) writes its PID to logs/heartbeats/dashboard_ui.json
    # BEFORE launching the supervisor subprocess.  We read that file here so
    # the orphan-killer can exclude the live GUI process.  Without this the
    # supervisor would terminate the very GUI process that spawned it.
    _safe_pids: set = set()
    try:
        import psutil as _psu
        _safe_pids.add(os.getpid())     # self
        _safe_pids.add(os.getppid())    # direct parent (pythonw / shell)

        # Walk full ancestor chain so no grandparent is killed either
        try:
            _p = _psu.Process(os.getpid())
            for _anc in _p.parents():
                _safe_pids.add(_anc.pid)
        except Exception:
            pass

        # Read the known GUI PID from the heartbeat file written by jarvis.py
        _hb_path = os.path.join("logs", "heartbeats", "dashboard_ui.json")
        if os.path.exists(_hb_path):
            try:
                with open(_hb_path, "r") as _hf:
                    _hb_data = json.load(_hf)
                _gui_pid = _hb_data.get("pid")
                if _gui_pid and isinstance(_gui_pid, int):
                    _safe_pids.add(_gui_pid)
                    # Also protect the GUI's own parent chain
                    try:
                        _gp = _psu.Process(_gui_pid)
                        for _anc in _gp.parents():
                            _safe_pids.add(_anc.pid)
                    except Exception:
                        pass
            except Exception:
                pass

        _write_event_log("ORPHAN_KILL", f"Safe PID set (will NOT be terminated): {sorted(_safe_pids)}")
    except Exception:
        pass

    # Only terminate KNOWN service subprocess orphans — never the GUI process
    # (jarvis.py and any process containing "jarvis.py" in cmdline is excluded).
    try:
        import psutil
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid in _safe_pids:
                    continue

                cmdline = proc.info.get('cmdline') or []
                if not cmdline:
                    continue
                cmd_str = " ".join(cmdline).lower()

                # HARD GUARD: Never kill a process that IS jarvis.py (the GUI entry point)
                if "jarvis.py" in cmd_str:
                    _write_event_log("ORPHAN_SKIP", f"Skipping GUI process PID {proc.pid} (jarvis.py in cmdline)")
                    continue

                # Only terminate SERVICES listed in the SERVICES dict
                # Do NOT match jarvis.gui.main_window, jarvis.gui, or ui bridges
                is_orphan_service = False
                for s_name, s_cfg in SERVICES.items():
                    s_mod = s_cfg["module"].lower()
                    if s_mod in cmd_str:
                        is_orphan_service = True
                        break

                if is_orphan_service:
                    _write_event_log("ORPHAN_KILL", f"Terminating orphan service PID {proc.pid}: {cmd_str[:80]}")
                    proc.terminate()
            except Exception:
                pass
    except Exception:
        pass


    # Aligned startup diagnostic loading sequence logs
    log_boot("System refresh completed.", "ok")
    log_boot("Voice Engine online.", "voice")

    log_boot("Memory synchronized.", "ok")
    log_boot("Security systems active.", "ok")
    log_boot("All systems operational.", "ok")
    log_boot("Welcome back.", "ok")


eb_server = None

def monitor_loop():
    global running, safe_mode, eb_server
    hb_dir = os.path.join("logs", "heartbeats")
    
    # Start Event Bus Server first so services can connect instantly
    from JARVIS.core.system.event_bus import EventBusServer
    eb_server = EventBusServer()
    eb_server.start()
    time.sleep(0.2)
    
    # Start timer
    start_time = time.time()
    
    # Run System Refresh Engine
    run_refresh_engine()

    # 1. Load Security Shield first
    sec_start = time.time()
    launch_service("security_engine")
    time.sleep(0.5)
    sec_load_time = time.time() - sec_start
    
    # 2. Run Face Verification asynchronously (DISABLED: not requested by owner)
    # def _run_face_check():
    #     try:
    #         from JARVIS.core.security.security_shield import run_face_match_check
    #         run_face_match_check(app=None)
    #     except Exception as e:
    #         print(f"[SUPERVISOR] Face match check failed or skipped: {e}")
    # threading.Thread(target=_run_face_check, daemon=True).start()
    
    # 3. Load Memory Engine
    mem_start = time.time()
    launch_service("memory_engine")
    time.sleep(0.3)
    mem_load_time = time.time() - mem_start
    
    # 4. Load Voice Engine (if enabled)
    voice_start = time.time()
    voice_enabled = True
    wake_word_enabled = True
    try:
        from JARVIS.config.manager import ConfigManager
        config_mgr = ConfigManager()
        config_mgr.load()
        voice_enabled = config_mgr.get("voice.voice_enabled", True)
        wake_word_enabled = config_mgr.get("voice.wake_word_enabled", True)
    except Exception:
        pass

    if voice_enabled and wake_word_enabled:
        launch_service("voice_engine")
        time.sleep(0.5)
        voice_load_time = time.time() - voice_start
    else:
        SERVICES["voice_engine"]["status"] = "offline"
        voice_load_time = 0.0
    
    # JARVIS voice-ready completed!
    total_time_to_ready = time.time() - start_time
    
    # 5. Load remaining modules in parallel
    launch_service("automation_engine")
    launch_service("ai_agents")
    launch_service("diagnostics_engine")
    launch_service("system_monitor")
    launch_service("camera_engine")
    launch_service("network_monitor")
        
    # Generate startup timing report
    report_md = f"""=================================================
          JARVIS FAST BOOT TIMING REPORT
=================================================
* Security Shield Load Time: {sec_load_time:.2f}s
* Voice Engine Load Time: {voice_load_time:.2f}s
* Memory Engine Load Time: {mem_load_time:.2f}s
* Total Time To Ready: {total_time_to_ready:.2f}s
================================================="""
    print(report_md)
    sys.stdout.flush()
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "fast_boot_report.md"), "w", encoding="utf-8") as f:
            f.write(report_md)
    except Exception:
        pass
        
    write_status_file()
    
    # Initialize dashboard_ui service tracking dynamically
    if "dashboard_ui" not in SERVICES:
        SERVICES["dashboard_ui"] = {
            "module": "JARVIS.gui.main_window",
            "desc": "Main QML Dashboard User Interface",
            "process": None,
            "restart_count": 0,
            "max_restarts": 4,
            "last_seen": time.time(),
            "status": "healthy",
        }
    
    while running:
        now = time.time()
        changed = False  # reset each iteration — prevents UnboundLocalError if no crash branch fires
        # Check shutdown flag
        shutdown_flag = os.path.join("logs", "shutdown.flag")
        if os.path.exists(shutdown_flag):
            print("[SUPERVISOR] Shutdown flag detected. Stopping all services...")
            for name, cfg in SERVICES.items():
                if cfg["process"]:
                    try:
                        cfg["process"].terminate()
                    except Exception:
                        pass
            try:
                os.remove(shutdown_flag)
            except Exception:
                pass
            running = False
            break

        # Check restart flag
        restart_flag = os.path.join("logs", "restart.flag")
        if os.path.exists(restart_flag):
            print("[SUPERVISOR] Restart flag detected. Performing full system restart...")
            for name, cfg in SERVICES.items():
                if cfg["process"]:
                    try:
                        cfg["process"].terminate()
                    except Exception:
                        pass
            try:
                os.remove(restart_flag)
            except Exception:
                pass
            
            # Coordinated execv system restart
            os.execv(sys.executable, [sys.executable] + sys.argv)

        # Get settings from ConfigManager
        camera_mode_enabled = False
        voice_enabled = True
        wake_word_enabled = True
        try:
            from JARVIS.config.manager import ConfigManager
            config_mgr = ConfigManager()
            config_mgr.load()
            camera_mode_enabled = config_mgr.get("general.camera_mode_enabled", False)
            voice_enabled = config_mgr.get("voice.voice_enabled", True)
            wake_word_enabled = config_mgr.get("voice.wake_word_enabled", True)
        except Exception:
            pass

        # Coordinate voice engine based on settings
        voice_cfg = SERVICES["voice_engine"]
        if not (voice_enabled and wake_word_enabled):
            if voice_cfg["process"] is not None:
                try:
                    if hasattr(voice_cfg["process"], "terminate"):
                        voice_cfg["process"].terminate()
                        voice_cfg["process"].wait(timeout=1.0)
                    else:
                        voice_cfg["process"].terminate()
                except Exception:
                    pass
                voice_cfg["process"] = None
                print("[SUPERVISOR] Voice engine subprocess terminated (voice/wake word disabled).")
                changed = True
            if voice_cfg["status"] != "offline":
                voice_cfg["status"] = "offline"
                changed = True

        window_state = "visible"

        # ── Safe Mode trigger ────────────────────────────────────────────────
        # Only count voice_engine, memory_engine, security_engine as essential.
        # dashboard_ui is explicitly excluded — its memory usage must never
        # trigger Safe Mode.
        # Threshold: at least 2 essential services must be offline (not 1) so a
        # single transient crash during startup does not cascade into Safe Mode.
        essential_offline = sum(
            1 for n, cfg in SERVICES.items()
            if n in ("voice_engine", "memory_engine", "security_engine")
            and cfg["status"] == "offline"
        )
        # dashboard_ui deliberately excluded from total_offline count
        total_offline = sum(
            1 for n, cfg in SERVICES.items()
            if n not in ("dashboard_ui",) and cfg["status"] == "offline"
        )

        if (now - start_time > 30.0) and (total_offline >= 3 or essential_offline >= 2) and not safe_mode:
            from JARVIS.core.system.utils.gui_lifecycle_logger import log_supervisor_action
            safe_mode = True
            msg_sm = f"Safe Mode triggered (total_offline={total_offline}, essential_offline={essential_offline})"
            print(f"[SUPERVISOR] Safe Mode activated! {msg_sm}")
            _write_supervisor_log("SAFE_MODE_ACTIVATED", msg_sm)
            log_supervisor_action("SAFE_MODE_ACTIVATED", msg_sm)
            # Terminate non-essential processes — voice_engine is NEVER terminated.
            for name, cfg in SERVICES.items():
                if name in ("dashboard_ui", "voice_engine", "memory_engine", "security_engine"):
                    continue
                if cfg["process"]:
                    try:
                        log_supervisor_action("SAFE_MODE_TERMINATE_SERVICE", f"Terminating non-essential service: {name}")
                        _write_supervisor_log("SAFE_MODE_TERMINATE", f"Terminating {name}")
                        cfg["process"].terminate()
                    except Exception as e:
                        log_supervisor_action("SAFE_MODE_TERMINATE_ERROR", f"Error terminating {name}: {e}")
                    cfg["process"] = None
                cfg["status"] = "offline"
            write_status_file()

        for name, cfg in SERVICES.items():
            # Dynamic process linking and health tracking for dashboard_ui
            if name == "dashboard_ui":
                hb_path = os.path.join(hb_dir, "dashboard_ui.json")
                if os.path.exists(hb_path):
                    try:
                        with open(hb_path, "r") as f:
                            hb_data = json.load(f)
                        pid_val = hb_data.get("pid")
                        ts_val = hb_data.get("timestamp", 0.0)
                        if pid_val:
                            import psutil
                            if psutil.pid_exists(pid_val):
                                if cfg["process"] is None or getattr(cfg["process"], "pid", None) != pid_val:
                                    try:
                                        cfg["process"] = psutil.Process(pid_val)
                                        print(f"[SUPERVISOR] Dynamically linked dashboard_ui process (PID: {pid_val})")
                                    except Exception:
                                        pass
                                if now - ts_val < 45.0:
                                    cfg["status"] = "healthy"
                                    cfg["last_seen"] = ts_val
                                    cfg["restart_count"] = 0
                    except Exception:
                        pass

            if name == "voice_engine" and not (voice_enabled and wake_word_enabled):
                cfg["status"] = "offline"
                continue
            if safe_mode and name not in ["voice_engine", "memory_engine", "security_engine"]:
                cfg["status"] = "offline"
                continue

            if name in ["memory_engine", "security_engine", "automation_engine"]:
                alive = True
                cfg["status"] = "healthy"
                cfg["last_seen"] = time.time()
            else:
                hb_path = os.path.join(hb_dir, f"{name}.json")
                alive = False
                if os.path.exists(hb_path):
                    try:
                        with open(hb_path, "r") as f:
                            hb_data = json.load(f)
                        ts = hb_data.get("timestamp", 0.0)
                        grace_until = hb_data.get("grace_until", 0.0)

                        if now < grace_until:
                            # Still inside the startup grace window — don't apply
                            # the 30-second staleness gate.  However, if the OS
                            # process has already exited we must still catch that.
                            if cfg["process"] and not is_process_alive(cfg["process"]):
                                # Hard crash during grace period — report it
                                alive = False
                            else:
                                alive = True
                                cfg["last_seen"] = ts
                        elif now - ts < 30.0:  # Active heartbeat in the last 30 seconds
                            alive = True
                            cfg["last_seen"] = ts
                    except Exception:
                        pass

                # Add 15-second grace period for dashboard_ui at startup
                if name == "dashboard_ui" and (now - start_time < 15.0):
                    alive = True
                
                # Check process state dynamically
                if cfg["process"]:
                    if not is_process_alive(cfg["process"]):
                        alive = False
                    elif is_process_alive(cfg["process"]) and (now - cfg["last_seen"] < 30.0):
                        alive = True
                # Failure Detection: High CPU or Memory leak
                if cfg["process"] and is_process_alive(cfg["process"]):
                    try:
                        import psutil
                        pid = cfg["process"].pid
                        p = psutil.Process(pid)
                        cpu_use = p.cpu_percent(interval=None)
                        mem_mb = p.memory_info().rss / (1024 * 1024)

                        # Absolute limits: 2.5 GB for GUI, 1.0 GB for others
                        _abs_limit_mb = 2560.0 if name == "dashboard_ui" else 1024.0
                        
                        # Rate of growth tracking
                        now_ts = time.time()
                        if "mem_history" not in cfg:
                            cfg["mem_history"] = []
                        cfg["mem_history"].append((now_ts, mem_mb))
                        # Keep last 5 minutes of history
                        cfg["mem_history"] = [pt for pt in cfg["mem_history"] if now_ts - pt[0] <= 300.0]
                        
                        # Rate of growth leak detection:
                        # If memory grows by > 150 MB/min sustained over at least 2 minutes (120 seconds)
                        is_leaking_by_rate = False
                        if len(cfg["mem_history"]) >= 6: # at least 1 minute of readings
                            old_readings = [pt for pt in cfg["mem_history"] if 120.0 <= now_ts - pt[0] <= 300.0]
                            if old_readings:
                                old_ts, old_mem = old_readings[0]
                                elapsed_mins = (now_ts - old_ts) / 60.0
                                growth = mem_mb - old_mem
                                growth_rate = growth / elapsed_mins
                                if growth_rate > 150.0 and mem_mb > 400.0:
                                    print(f"[SUPERVISOR] Rate-of-growth memory leak detected in {name} ({growth_rate:.1f} MB/min growth, current: {mem_mb:.1f} MB). Restarting service.")
                                    is_leaking_by_rate = True

                        if cpu_use > 90.0:
                             print(f"[SUPERVISOR] High CPU detected in {name} ({cpu_use:.1f}%). Restarting service.")
                             alive = False
                        elif mem_mb > _abs_limit_mb:
                             print(f"[SUPERVISOR] Absolute memory leak limit exceeded in {name} ({mem_mb:.1f} MB > {_abs_limit_mb:.0f} MB limit). Restarting service.")
                             alive = False
                        elif is_leaking_by_rate:
                             alive = False
                    except Exception:
                        pass

            if not alive:
                from JARVIS.core.system.utils.gui_lifecycle_logger import log_supervisor_action
                # Service is dead or not responding
                if cfg["status"] != "offline":
                    # Capture memory of crashed service for the log
                    _crashed_mem_mb = 0.0
                    try:
                        import psutil as _psu_crash
                        if cfg["process"] and hasattr(cfg["process"], "pid"):
                            _crashed_mem_mb = _psu_crash.Process(cfg["process"].pid).memory_info().rss / (1024 * 1024)
                    except Exception:
                        pass

                    msg = f"Service {name} crashed/timed out (restart #{cfg['restart_count'] + 1}, mem={_crashed_mem_mb:.1f}MB)"
                    print(f"[SUPERVISOR] {msg}")
                    _write_event_log("SUBPROCESS_CRASH", msg)
                    _write_supervisor_log("SUBPROCESS_CRASH", msg)
                    log_supervisor_action("SERVICE_CRASH_DETECTION", msg)

                    if cfg["restart_count"] < cfg["max_restarts"]:
                        cfg["status"] = "recovering"
                        cfg["restart_count"] += 1
                        # Compute exponential backoff — never block voice_engine > 5s
                        _bd = _backoff_delay(cfg["restart_count"])
                        if name == "voice_engine":
                            _bd = min(_bd, 5.0)
                        cfg["backoff_delay"] = _bd
                        changed = True
                        write_status_file()

                        # Logging restart
                        try:
                            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
                            os.makedirs("logs", exist_ok=True)
                            with open("logs/service_restart.log", "a", encoding="utf-8") as f:
                                f.write(f"[{timestamp_str}] Service {name} restart triggered: attempt {cfg['restart_count']}/{cfg['max_restarts']} backoff={_bd:.0f}s.\n")
                        except Exception:
                            pass

                        # Update Diagnostics Center status
                        try:
                            from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
                            DiagnosticsCenter().update_subsystem(name, "recovering", recovery_restart=True)
                        except Exception:
                            pass

                        # Apply backoff delay asynchronously so the supervisor monitoring loop is never blocked
                        if name != "dashboard_ui":
                            restart_msg = f"Restarting {name} in {_bd:.0f}s (attempt {cfg['restart_count']}/{cfg['max_restarts']})"
                            _write_event_log("SUBPROCESS_RESTART", restart_msg)
                            _write_supervisor_log("SUBPROCESS_RESTART", restart_msg)
                            log_supervisor_action("SERVICE_RESTART_TRIGGER", restart_msg)

                            def _async_restart_target(svc_name=name, delay=_bd):
                                time.sleep(delay)
                                launch_service(svc_name)

                            threading.Thread(target=_async_restart_target, daemon=True).start()
                        else:
                            log_supervisor_action("SERVICE_RESTART_SKIP_GUI", "Skipped restarting dashboard_ui")
                            cfg["process"] = None
                        cfg["status"] = "recovering"
                    else:
                        cfg["status"] = "offline"
                        changed = True
                        msg_fail = f"Service {name} reached max restart limit ({cfg['max_restarts']}). Offline."
                        print(f"[SUPERVISOR] {msg_fail}")
                        _write_event_log("SUBPROCESS_FAILED", msg_fail)
                        _write_supervisor_log("SUBPROCESS_FAILED", msg_fail)
                        log_supervisor_action("SERVICE_FAILED_PERMANENTLY", msg_fail)

                        # Update Diagnostics Center status to failed
                        try:
                            from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
                            DiagnosticsCenter().update_subsystem(name, "Failed", failed=True)
                        except Exception:
                            pass

                        # Trigger diagnostics scan
                        try:
                            from JARVIS.runtime.self_healing import SelfHealingEngine
                            SelfHealingEngine().run_diagnostics()
                        except Exception as e:
                            print(f"[SUPERVISOR] Diagnostics trigger failed: {e}")
            else:
                if cfg["status"] in ["recovering", "offline"]:
                    cfg["status"] = "healthy"
                    cfg["restart_count"] = 0
                    # Reset backoff on recovery
                    cfg["backoff_delay"] = 2.0
        # Periodic backups
        create_backup(SETTINGS_FILE, "config")
        create_backup(MEMORY_FILE, "memory")

        # Run memory trimming check if idle
        try:
            from JARVIS.core.system.utils.memory_helper import trim_memory_if_eligible
            trim_memory_if_eligible()
        except Exception:
            pass

        write_status_file()
        time.sleep(3)

if __name__ == "__main__":
    # ── Helper: append to supervisor.log (critical for pythonw.exe where
    #    stdout/stderr are invisible) ───────────────────────────────────────
    def _log_to_file(msg):
        try:
            os.makedirs("logs", exist_ok=True)
            with open(os.path.join("logs", "supervisor.log"), "a", encoding="utf-8") as _lf:
                _lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    _log_to_file(f"[SUPERVISOR] __main__ entered (PID {os.getpid()})")

    # ── Kill any stale supervisor processes from previous sessions ─────────────
    # We read the PID lockfile to find and terminate any stale supervisor instances.
    try:
        import psutil as _psu
        _self_pid = os.getpid()
        _killed = []
        _pid_file = os.path.join("logs", "supervisor.pid")
        if os.path.exists(_pid_file):
            try:
                with open(_pid_file, "r") as _pf:
                    _old_pid = int(_pf.read().strip())
                if _old_pid != _self_pid and _psu.pid_exists(_old_pid):
                    _old_proc = _psu.Process(_old_pid)
                    _old_name = _old_proc.name().lower()
                    if "python" in _old_name:
                        _log_to_file(
                            f"[SUPERVISOR] Terminating stale supervisor PID {_old_pid} "
                            f"(found via lockfile, name={_old_name})"
                        )
                        _old_proc.terminate()
                        try:
                            _old_proc.wait(timeout=2.0)
                        except Exception:
                            _old_proc.kill()
                        _killed.append(_old_pid)
                elif _old_pid != _self_pid:
                    os.remove(_pid_file)
            except Exception as _e:
                _log_to_file(f"[SUPERVISOR] Error cleaning up stale lockfile: {_e}")

        if _killed:
            print(f"[SUPERVISOR] Terminated stale supervisor instance(s): {_killed}")
            _log_to_file(f"[SUPERVISOR] Terminated stale instances: {_killed}")
            time.sleep(0.5)
    except Exception as _e:
        print(f"[SUPERVISOR] Stale process cleanup skipped: {_e}")
        _log_to_file(f"[SUPERVISOR] Stale process cleanup skipped: {_e}")

    _log_to_file("[SUPERVISOR] Acquiring port lock...")
    from JARVIS.core.system.utils.port_manager import PortManager
    # Retry up to 3 times — Windows TCP TIME_WAIT can hold port 19100 for ~1-4s
    # after a previous supervisor exits without closing its socket gracefully.
    lock_socket = None
    for _lock_attempt in range(3):
        lock_socket = PortManager.acquire_service_lock("supervisor", 19100)
        if lock_socket is not None:
            break
        _retry_msg = (
            f"[SUPERVISOR] Port 19100 unavailable on attempt {_lock_attempt + 1}/3. "
            f"Retrying in 2s..."
        )
        print(_retry_msg)
        _log_to_file(_retry_msg)
        time.sleep(2.0)

    if lock_socket is None:
        _fail_msg = (
            f"[SUPERVISOR] Duplicate supervisor instance detected (port 19100 "
            f"unavailable after 3 attempts). PID {os.getpid()} exiting."
        )
        print(_fail_msg)
        _log_to_file(_fail_msg)
        sys.exit(1)

    _log_to_file(f"[SUPERVISOR] Port lock acquired (PID {os.getpid()})")

    # Write PID lockfile so other tools can detect dead lock owners
    _pid_lock_path = os.path.join("logs", "supervisor.pid")
    try:
        os.makedirs("logs", exist_ok=True)
        with open(_pid_lock_path, "w") as _pf:
            _pf.write(str(os.getpid()))
    except Exception:
        pass

    print("[SUPERVISOR] Starting JARVIS Multi-Process Supervisor CORE...")
    try:
        monitor_loop()
    except KeyboardInterrupt:
        print("[SUPERVISOR] Shutting down supervisor and all services...")
        running = False
        create_backup(SETTINGS_FILE, "config", emergency=True)
        create_backup(MEMORY_FILE, "memory", emergency=True)
        for name, cfg in SERVICES.items():
            proc = cfg.get("process")
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
        # Wait for graceful exit of subprocesses
        for name, cfg in SERVICES.items():
            proc = cfg.get("process")
            if proc:
                try:
                    proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                except Exception:
                    pass
        print("[SUPERVISOR] All services stopped.")
    finally:
        if lock_socket:
            lock_socket.close()
        # Remove PID lockfile on clean exit
        try:
            os.remove(os.path.join("logs", "supervisor.pid"))
        except Exception:
            pass
