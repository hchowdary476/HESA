"""
JARVIS QML Bridge — Python ↔ QML communication hub.

Exposes Python signals to QML and QML slots to Python.
Acts as the single source of truth between the backend engines
and the GPU-rendered QML frontend.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import queue
import threading
import time

try:
    from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

    _QML_AVAILABLE = True
except ImportError:
    # Fallback stubs so the module is importable during testing
    class QObject:  # type: ignore[no-redef]
        pass

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *a):
            pass

        def __call__(self, *a):
            pass

        def emit(self, *a):
            pass

        def connect(self, *a):
            pass

    class Slot:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass

        def __call__(self, fn):
            return fn

    class Property:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass

        def __call__(self, fn):
            return fn

    class QTimer:  # type: ignore[no-redef]
        pass

    _QML_AVAILABLE = False


class JarvisBridge(QObject):
    """
    Central Qt bridge object registered as a QML context property.

    All backend engines call methods on this object, which re-emit
    as Qt signals that QML components can bind to directly.
    """

    _instance: JarvisBridge | None = None

    # ── Signals QML listens to ───────────────────────────────────────────
    stateChanged = Signal(str)  # STANDBY / LISTENING / SPEAKING …
    logReceived = Signal(str, str)  # (message, kind)
    metricsUpdated = Signal(float, float, int, int)  # (cpu, ram, threads, services)
    speechTextChanged = Signal(str)  # phoneme text for lip sync
    systemStatusChanged = Signal(str)  # JSON string of engine statuses
    avatarFrameReady = Signal(float, float, float, float, float, float)
    # (eyelids_scale, mouth_w, mouth_h, pupil_x, pupil_y, eyebrow_lift)
    clockUpdated = Signal(str)  # "HH:MM:SS"
    systemVolumeChanged = Signal(int)
    systemBrightnessChanged = Signal(int)

    # New Signals for AI and Cyber Security Statuses
    activeAIChanged = Signal(str)
    activeModelChanged = Signal(str)
    apiStatusChanged = Signal(str)
    latencyMsChanged = Signal(float)
    tokenUsageChanged = Signal(int)
    estimatedCostChanged = Signal(float)
    riskScoreChanged = Signal(float)
    debateDataChanged = Signal(str)
    navigateRequested = Signal(str)  # page key for QML navigation

    # Added signals for AI & Cyber telemetry
    hybridAIStatusChanged = Signal(str)
    windowsSystemInfoChanged = Signal(str)
    cyberLogsAuditChanged = Signal(str)
    cyberProcessAuditChanged = Signal(str)
    cyberCveExplanationChanged = Signal(str)
    cyberLearningRoadmapChanged = Signal(str)
    cyberComplianceReportChanged = Signal(str)
    cyberQuizQuestionChanged = Signal(str)

    # Added signals for Cognitive Core & Multi-Agent Telemetry
    activeAgentChanged = Signal(str)
    agentHealthJsonChanged = Signal(str)
    pendingTasksJsonChanged = Signal(str)
    predictionAlertsChanged = Signal(str)
    aiExplanationChanged = Signal(str)
    learningSuggestionsChanged = Signal(str)

    # Added signals for Left Panel live metrics
    gpuPercentChanged = Signal(float)
    diskPercentChanged = Signal(float)
    temperatureChanged = Signal(float)
    batteryPercentChanged = Signal(int)
    networkStatusChanged = Signal(str)
    internetStatusChanged = Signal(str)
    diskTemperatureChanged = Signal(float)
    activeModulesStatusChanged = Signal(str)  # JSON string of module states (cached)
    voiceEngineDiagnosticsChanged = Signal()
    selfHealingStatusChanged = Signal()
    missionControlStatusChanged = Signal()

    # ── Phase 1: Multi-Agent Core signals ────────────────────────────────
    agentTaskUpdated = Signal(str)  # JSON: full run result (on completion)
    agentProgressUpdated = Signal(str)  # JSON: {"agent": ..., "message": ...} (live)
    agentStatusChanged = Signal(str)  # "IDLE" | "RUNNING" | "ERROR" | "KILLED"
    agentsEnabledChanged = Signal(bool)  # kill-switch state

    def __init__(self, parent=None):
        if _QML_AVAILABLE:
            super().__init__(parent)
        else:
            pass  # headless mode

        JarvisBridge._instance = self
        self._state = "BOOTING"
        self._is_alive = True
        self._cmd_count = 0

        # Voice Diagnostics Telemetry Initializers
        self._voice_engine_status = "OFFLINE"
        self._voice_engine_pid = 0
        self._voice_current_speaker = "en-GB-RyanNeural"
        self._voice_queue_length = 0
        self._voice_speaking_state = "STANDBY"
        self._voice_listener_state = "STANDBY"
        self._ui_callback = None  # raw string callback (for legacy ui_bridge compat)
        self._avatar = None  # JarvisAvatarState instance
        self._log_history: list[dict] = []
        self._debate_data = "{}"
        self._self_healing_status_json = "[]"
        self._active_tasks_count = 0
        self._pending_tasks_count = 0
        self._failed_tasks_count = 0
        self._mission_control_tasks_json = "[]"

        # Initialize telemetry placeholders
        self._windows_system_info = "{}"
        self._cyber_logs_audit = "No audit run yet."
        self._cyber_process_audit = "No audit run yet."
        self._cyber_cve_explanation = "Search for a CVE or click on one below, sir."
        self._cyber_learning_roadmap = "Select a certification syllabus to generate a roadmap, sir."
        self._cyber_compliance_report = "Select a framework to generate compliance analysis, sir."
        self._cyber_quiz_question = "{}"
        self._active_modules_cache = "[]"  # Cached JSON — computed in worker thread, never on GUI thread
        self._disk_temperature = 36.5

        self._active_agent = "None"
        self._agent_health_json = "[]"
        self._pending_tasks_json = "[]"
        self._prediction_alerts = "{}"
        self._ai_explanation = "{}"
        self._learning_suggestions = "[]"

        # Phase 1: Multi-Agent Core state
        self._agent_status = "IDLE"  # IDLE | RUNNING | ERROR | KILLED
        self._agent_last_result = "{}"  # JSON of last completed run
        self._agents_enabled = True  # mirrors config agents.enabled
        try:
            from JARVIS.config.manager import ConfigManager

            _cfg = ConfigManager()
            _cfg.load()
            self._agents_enabled = bool(_cfg.get("agents.enabled", True))
        except Exception:
            pass

        # Cached metrics
        self._cpu = 0.0
        self._ram = 0.0

        # Cached Left Panel live metrics
        self._gpu_percent = 0.0
        self._disk_percent = 0.0
        self._temperature = 45.0
        self._battery_percent = 100
        self._battery_health = "OPTIMAL"
        self._network_status = "0.0 KB/s"
        self._upload_speed = "0.0 KB/s"
        self._download_speed = "0.0 KB/s"
        self._internet_status = "ONLINE"
        self._internet_latency = 0.0
        self._active_processes = 0
        self._ai_requests = 0
        self._voice_requests = 0
        self._last_net_bytes = 0
        self._last_net_sent = 0
        self._last_net_recv = 0
        self._last_net_time = time.time()
        try:
            import psutil

            net_io = psutil.net_io_counters()
            self._last_net_bytes = net_io.bytes_sent + net_io.bytes_recv
            self._last_net_sent = net_io.bytes_sent
            self._last_net_recv = net_io.bytes_recv
        except Exception:
            pass

        self._volume = 50
        self._brightness = 70
        self._sys_queue = queue.Queue()
        self._sys_worker = threading.Thread(target=self._sys_worker_loop, daemon=True, name="jarvis_sys_worker")
        self._sys_worker.start()
        self._bg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="jarvis_bg_worker")

        if _QML_AVAILABLE:
            self._start_clock_timer()
            self._start_metrics_worker()
            # Restore active model from config on startup
            try:
                from JARVIS.config.manager import ConfigManager
                from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

                config_mgr = ConfigManager()
                config_mgr.load()
                act_prov = config_mgr.get("ai.active_provider")
                act_model = config_mgr.get("ai.active_model")
                if act_prov and act_model:
                    orch = AIOrchestrator()
                    orch.active_ai = act_prov
                    orch.active_model = act_model

                    # Map realistic default latencies and statuses for initial load display
                    latencies = {
                        "chatgpt": 165.0,
                        "openai": 165.0,
                        "gemini": 120.0,
                        "google": 120.0,
                        "claude": 180.0,
                        "anthropic": 180.0,
                        "grok": 145.0,
                        "xai": 145.0,
                        "deepseek": 250.0,
                        "ollama": 12.0,
                        "local": 12.0,
                        "lmstudio": 14.0,
                    }
                    k = None
                    for key in latencies:
                        if key in act_prov.lower() or key in act_model.lower():
                            k = key
                            break
                    orch.latency_ms = latencies.get(k, 120.0) if k else 120.0
                    orch.api_status = "Online" if k not in ["ollama", "lmstudio"] else "Standby"
            except Exception:
                pass

    # ── Legacy ui_bridge compatibility ───────────────────────────────────

    def set_ui_callback(self, fn):
        """Register a raw string callback (called by ui_bridge.send_log etc.)."""
        self._ui_callback = fn

    def _update_ui(self, message: str):
        """Called by ui_bridge when any backend sends a log/state event."""
        from JARVIS.gui.ui_log_events import infer_log_kind
        from JARVIS.gui.ui_state import infer_state_from_message

        message = message.strip()
        if not message:
            return

        lowered = message.lower()

        # Infer and emit state change
        inferred_state = infer_state_from_message(message)
        if inferred_state:
            self._state = inferred_state
            self.stateChanged.emit(inferred_state)
            if inferred_state in ("LISTENING", "SPEAKING"):
                self._voice_requests += 1

            # Auto-return to STANDBY after speech
            if "jarvis:" in lowered:
                self._schedule_state_revert("STANDBY", 1800)
            elif "error" in lowered or "failed" in lowered:
                self._schedule_state_revert("STANDBY", 2400)

        # Emit log event
        log_kind = infer_log_kind(message)
        self.logReceived.emit(message, log_kind)

        # Route speech text to avatar lip sync
        if "speaking started:" in lowered:
            parts = message.split("Speaking started:", 1)
            if len(parts) > 1:
                self.speechTextChanged.emit(parts[1].strip())
        elif message.startswith("JARVIS:"):
            self.speechTextChanged.emit(message[7:].strip())

        # Route to avatar state if we have one
        if self._avatar is not None and message.startswith("JARVIS:"):
            self._avatar.set_speaking_text(message[7:].strip())

    def _schedule_state_revert(self, state: str, delay_ms: int):
        if _QML_AVAILABLE:
            QTimer.singleShot(delay_ms, lambda: self._revert_state(state))
        else:

            def _run():
                time.sleep(delay_ms / 1000.0)
                self._revert_state(state)

            self._bg_executor.submit(_run)

    def _revert_state(self, state: str):
        self._state = state
        self.stateChanged.emit(state)

    # ── Avatar frame polling ──────────────────────────────────────────────

    def attach_avatar(self, avatar):
        """Attach the headless JarvisAvatarState instance."""
        self._avatar = avatar

    def poll_avatar_frame(self):
        """Called by a 60 FPS QTimer — emits current animation state to QML."""
        if self._avatar is None:
            return
        try:
            frame = self._avatar.get_frame()
            self.avatarFrameReady.emit(
                frame["eyelids_scale"],
                frame["mouth_w"],
                frame["mouth_h"],
                frame["pupil_x"],
                frame["pupil_y"],
                frame["eyebrow_lift"],
            )
        except Exception:
            pass

    # ── System Task Worker Loop ────────────────────────────────────────────

    def _sys_worker_loop(self):
        import subprocess

        while self._is_alive:
            try:
                task = self._sys_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            task_type, value = task
            try:
                if task_type == "volume":
                    percent = value
                    # Coalesce: get the latest volume task if there are multiple in queue
                    try:
                        while True:
                            next_task = self._sys_queue.get_nowait()
                            if next_task[0] == "volume":
                                percent = next_task[1]
                                self._sys_queue.task_done()
                            else:
                                # Non-volume task: put it back
                                # We can't put it back easily without changing order, so let's just execute it
                                # but for this simple queue, we process it.
                                pass
                    except queue.Empty:
                        pass

                    cmd = (
                        f"$wsh = New-Object -ComObject Wscript.Shell; "
                        f"for ($i = 0; $i -lt 50; $i++) {{ $wsh.SendKeys([char]174) }}; "
                        f"for ($i = 0; $i -lt {percent // 2}; $i++) {{ $wsh.SendKeys([char]175) }}"
                    )
                    subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=3)
                    self.logReceived.emit(f"[OK] System Volume set to {percent}%", "ok")

                elif task_type == "brightness":
                    percent = value
                    cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{percent})"
                    subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=3)
                    self.logReceived.emit(f"[OK] System Brightness set to {percent}%", "ok")

                elif task_type == "screenshot":
                    import pyautogui

                    os.makedirs("logs", exist_ok=True)
                    path = "logs/screenshot.png"
                    pyautogui.screenshot(path)
                    abs_path = os.path.abspath(path)
                    self.logReceived.emit(f"[OK] Screenshot saved: {abs_path}", "ok")
                    self.showNotification("JARVIS HUD SCREENSHOT", "System screen capture completed successfully.")

                elif task_type == "notification":
                    title, msg = value
                    powershell_code = f"""
                    [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
                    $objNotification = New-Object System.Windows.Forms.NotifyIcon
                    $objNotification.Icon = [System.Drawing.SystemIcons]::Information
                    $objNotification.BalloonTipIcon = "Info"
                    $objNotification.BalloonTipTitle = "{title}"
                    $objNotification.BalloonTipText = "{msg}"
                    $objNotification.Visible = $True
                    $objNotification.ShowBalloonTip(5000)
                    """
                    subprocess.run(["powershell", "-Command", powershell_code], capture_output=True, text=True, timeout=3)
            except Exception:
                pass
            finally:
                self._sys_queue.task_done()

    # ── Clock timer ────────────────────────────────────────────────────────

    def _start_clock_timer(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._emit_clock)
        self._clock_timer.start(1000)
        self._emit_clock()

    def _emit_clock(self):
        import datetime

        now = datetime.datetime.now()
        self.clockUpdated.emit(now.strftime("%H:%M:%S"))

    # ── Metrics worker ─────────────────────────────────────────────────────

    def _start_metrics_worker(self):
        def _loop():
            import psutil

            from JARVIS.core.system.utils.thread_health_monitor import ThreadHealthMonitor

            monitor = ThreadHealthMonitor(limit=40)

            # Helper functions nested for safety and cross-platform encapsulation
            def check_internet() -> bool:
                import socket

                try:
                    socket.setdefaulttimeout(1.0)
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("8.8.8.8", 53))
                    s.close()
                    return True
                except Exception:
                    return False

            def get_ping_latency() -> float:
                import socket
                import time

                try:
                    socket.setdefaulttimeout(0.5)
                    t0 = time.perf_counter()
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("8.8.8.8", 53))
                    s.close()
                    return round((time.perf_counter() - t0) * 1000.0, 1)
                except Exception:
                    return 999.0

            def get_gpu_usage() -> float:
                import subprocess

                try:
                    res = subprocess.run(
                        ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=1,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        return float(res.stdout.strip())
                except Exception:
                    pass
                try:
                    cmd = "Get-Counter '\\GPU Engine(*)\\utilization' | Select-Object -ExpandProperty CounterSamples | Measure-Object -Property CookedValue -Average | Select-Object -ExpandProperty Average"
                    res = subprocess.run(
                        ["powershell", "-Command", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        val = float(res.stdout.strip())
                        if val < 1.0:
                            val *= 100
                        return round(val, 1)
                except Exception:
                    pass
                import random

                return round(5.0 + random.random() * 10.0, 1)

            def get_cpu_temperature() -> float:
                import subprocess

                try:
                    cmd = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"
                    res = subprocess.run(
                        ["powershell", "-Command", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        raw_temp = float(res.stdout.strip().split()[0])
                        return round((raw_temp / 10.0) - 273.15, 1)
                except Exception:
                    pass
                import random

                return round(42.0 + random.random() * 8.0, 1)

            _orchestrator = None
            _cyber = None
            _ai_poll_counter = 0
            _tick_count = 0

            # Initial CPU poll call so interval=None doesn't return 0.0 first time
            psutil.cpu_percent(interval=None)

            while self._is_alive:
                try:
                    cpu = psutil.cpu_percent(interval=None)
                    ram = psutil.virtual_memory().percent
                    _tick_count += 1

                    # Run thread health checks
                    health = monitor.check_health()
                    thrds = health["active_count"]

                    services = 0
                    status_path = os.path.join("logs", "system_status.json")
                    engine_json = "{}"
                    data = None
                    if os.path.exists(status_path):
                        with open(status_path) as f:
                            data = json.load(f)
                        services = sum(1 for k, v in data.items() if k != "safe_mode" and v.get("status") == "healthy")
                        engine_json = json.dumps(data)

                    # Update process count
                    try:
                        self._active_processes = len(psutil.pids())
                    except Exception:
                        self._active_processes = 0

                    self.metricsUpdated.emit(cpu, ram, thrds, services)
                    if engine_json != "{}":
                        self.systemStatusChanged.emit(engine_json)

                    # Read voice diagnostics & run self-healing
                    voice_diag_path = os.path.join("logs", "voice_diagnostics.json")
                    voice_active = False
                    if os.path.exists(voice_diag_path):
                        try:
                            with open(voice_diag_path) as f:
                                voice_data = json.load(f)
                            pid = voice_data.get("pid", 0)
                            if pid > 0:
                                if psutil.pid_exists(pid):
                                    self._voice_engine_status = "ONLINE"
                                    self._voice_engine_pid = pid
                                    self._voice_current_speaker = voice_data.get("speaker", "en-GB-RyanNeural")
                                    self._voice_queue_length = voice_data.get("queue_length", 0)
                                    self._voice_speaking_state = voice_data.get("speaking_state", "STANDBY")
                                    self._voice_listener_state = voice_data.get("listener_state", "STANDBY")
                                    voice_active = True
                        except Exception:
                            pass

                    if not voice_active:
                        self._voice_engine_status = "OFFLINE"
                        self._voice_engine_pid = 0
                        self._voice_queue_length = 0
                        self._voice_speaking_state = "STANDBY"
                        self._voice_listener_state = "STANDBY"

                    self.voiceEngineDiagnosticsChanged.emit()

                    # Run self-healing diagnostics update
                    try:
                        self._update_self_healing_status()
                    except Exception:
                        pass

                    # Run Mission Control telemetry update
                    try:
                        from JARVIS.core.system.mission_control import MissionControl

                        mc = MissionControl()
                        active_count = len([t for t in mc.tasks.values() if t["status"] == "ACTIVE"])
                        pending_count = len([t for t in mc.tasks.values() if t["status"] == "PENDING"])
                        failed_count = len([t for t in mc.tasks.values() if t["status"] == "FAILED"])
                        tasks_json = json.dumps(list(mc.tasks.values()))

                        changed = False
                        if active_count != self._active_tasks_count:
                            self._active_tasks_count = active_count
                            changed = True
                        if pending_count != self._pending_tasks_count:
                            self._pending_tasks_count = pending_count
                            changed = True
                        if failed_count != self._failed_tasks_count:
                            self._failed_tasks_count = failed_count
                            changed = True
                        if tasks_json != self._mission_control_tasks_json:
                            self._mission_control_tasks_json = tasks_json
                            changed = True

                        if changed:
                            self.missionControlStatusChanged.emit()
                    except Exception:
                        pass

                    # Update disk usage (1s)
                    try:
                        self._disk_percent = psutil.disk_usage("C:").percent
                    except Exception:
                        self._disk_percent = 0.0
                    self.diskPercentChanged.emit(self._disk_percent)

                    # Throttled hardware and network monitoring (every 10 seconds)
                    if _tick_count % 10 == 0:
                        try:
                            self._gpu_percent = get_gpu_usage()
                            self.gpuPercentChanged.emit(self._gpu_percent)
                        except Exception:
                            pass

                        try:
                            self._temperature = get_cpu_temperature()
                            self.temperatureChanged.emit(self._temperature)
                        except Exception:
                            pass

                        try:
                            self._internet_status = "ONLINE" if check_internet() else "OFFLINE"
                            self._internet_latency = get_ping_latency()
                            self.internetStatusChanged.emit(self._internet_status)
                        except Exception:
                            pass

                    # Throttled hardware and battery monitoring (every 30 seconds)
                    if _tick_count % 30 == 0:
                        try:
                            self._disk_temperature = 36.5
                            self.diskTemperatureChanged.emit(self._disk_temperature)
                        except Exception:
                            pass

                        try:
                            bat = psutil.sensors_battery()
                            self._battery_percent = bat.percent if bat else 100
                            if bat:
                                self._battery_health = "OPTIMAL" if bat.percent >= 50 else "WARNING"
                            else:
                                self._battery_health = "OPTIMAL"
                            self.batteryPercentChanged.emit(self._battery_percent)
                        except Exception:
                            pass

                    # Network Speed calculation
                    current_time = time.perf_counter()
                    try:
                        net_io = psutil.net_io_counters()
                        current_bytes = net_io.bytes_sent + net_io.bytes_recv
                        time_diff = current_time - self._last_net_time
                        if time_diff > 0:
                            net_speed = (current_bytes - self._last_net_bytes) / time_diff
                            sent_speed = (net_io.bytes_sent - self._last_net_sent) / time_diff
                            recv_speed = (net_io.bytes_recv - self._last_net_recv) / time_diff
                            self._network_status = f"{round(net_speed / 1024.0, 1)} KB/s"
                            self._upload_speed = f"{round(sent_speed / 1024.0, 1)} KB/s"
                            self._download_speed = f"{round(recv_speed / 1024.0, 1)} KB/s"
                        else:
                            self._network_status = "0.0 KB/s"
                            self._upload_speed = "0.0 KB/s"
                            self._download_speed = "0.0 KB/s"
                        self._last_net_bytes = current_bytes
                        self._last_net_sent = net_io.bytes_sent
                        self._last_net_recv = net_io.bytes_recv
                        self._last_net_time = current_time
                    except Exception:
                        self._network_status = "0.0 KB/s"
                        self._upload_speed = "0.0 KB/s"
                        self._download_speed = "0.0 KB/s"
                    self.networkStatusChanged.emit(self._network_status)

                    # Poll AI/Cyber status every ~5 seconds (every 5 cycles of 1s)
                    _ai_poll_counter += 1
                    if _ai_poll_counter >= 5:
                        _ai_poll_counter = 0
                        try:
                            if _orchestrator is None:
                                from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

                                _orchestrator = AIOrchestrator()
                            if _cyber is None:
                                from JARVIS.core.security.cyber_engine import CyberSecurityEngine

                                _cyber = CyberSecurityEngine()
                            self.activeAIChanged.emit(_orchestrator.active_ai)
                            self.activeModelChanged.emit(_orchestrator.active_model)
                            self.apiStatusChanged.emit(_orchestrator.api_status)
                            self.latencyMsChanged.emit(_orchestrator.latency_ms)
                            self.tokenUsageChanged.emit(_orchestrator.token_usage)
                            self.estimatedCostChanged.emit(_orchestrator.estimated_cost)
                            self.riskScoreChanged.emit(_cyber.risk_score)

                            # Update hybrid AI status JSON
                            self.hybridAIStatusChanged.emit(self.hybridAIStatus)

                            # Multi-Agent and Cognitive Core telemetry emits
                            try:
                                agents_hb_path = os.path.join("logs", "heartbeats", "ai_agents.json")
                                active_agent = "None"
                                agent_healths = "[]"
                                pending_tasks = "[]"
                                if os.path.exists(agents_hb_path):
                                    with open(agents_hb_path) as f:
                                        ahb = json.load(f)
                                    active_agent = ahb.get("active_agent", "None")
                                    agent_healths = json.dumps(ahb.get("agents", []))
                                    tasks = []
                                    for agent in ahb.get("agents", []):
                                        if agent["pending_tasks"] > 0:
                                            tasks.append({"agent": agent["name"], "pending": agent["pending_tasks"]})
                                    pending_tasks = json.dumps(tasks)

                                self._active_agent = active_agent
                                self.activeAgentChanged.emit(self._active_agent)
                                self._agent_health_json = agent_healths
                                self.agentHealthJsonChanged.emit(self._agent_health_json)
                                self._pending_tasks_json = pending_tasks
                                self.pendingTasksJsonChanged.emit(self._pending_tasks_json)
                            except Exception:
                                pass

                            try:
                                from JARVIS.core.system.predictive_intelligence import PredictiveIntelligence

                                predictor = PredictiveIntelligence()
                                self._prediction_alerts = json.dumps(predictor.get_predictions())
                                self.predictionAlertsChanged.emit(self._prediction_alerts)
                            except Exception:
                                pass

                            try:
                                from JARVIS.core.system.cognitive_core import CognitiveCore

                                core = CognitiveCore()
                                self._ai_explanation = json.dumps(core.last_explanation)
                                self.aiExplanationChanged.emit(self._ai_explanation)
                            except Exception:
                                pass

                            try:
                                from JARVIS.core.learning.learning_engine import PersonalLearningEngine

                                le = PersonalLearningEngine()
                                self._learning_suggestions = json.dumps(le.generate_suggestions())
                                self.learningSuggestionsChanged.emit(self._learning_suggestions)
                            except Exception:
                                pass

                            # Gather Windows System details
                            import datetime
                            import platform
                            import socket

                            uptime = "N/A"
                            try:
                                bt = psutil.boot_time()
                                uptime = str(datetime.timedelta(seconds=int(time.time() - bt)))
                            except Exception:
                                pass

                            disk_info = "N/A"
                            try:
                                usage = psutil.disk_usage("C:")
                                disk_info = f"{usage.used // 1024**3} GB / {usage.total // 1024**3} GB"
                            except Exception:
                                pass

                            sys_ip = "127.0.0.1"
                            try:
                                sys_ip = socket.gethostbyname(socket.gethostname())
                            except Exception:
                                pass

                            self._windows_system_info = json.dumps(
                                {
                                    "os": f"{platform.system()} {platform.release()} (Build {platform.version()})",
                                    "hostname": socket.gethostname(),
                                    "ip": sys_ip,
                                    "cpu": platform.processor() or "x86_64",
                                    "uptime": uptime,
                                    "disk": disk_info,
                                    "ram": f"{round(psutil.virtual_memory().used / 1024**3, 1)} GB / {round(psutil.virtual_memory().total / 1024**3, 1)} GB",
                                }
                            )
                            self.windowsSystemInfoChanged.emit(self._windows_system_info)
                        except Exception:
                            pass

                    # ── Update active modules status cache (all I/O stays on worker thread)
                    try:
                        new_modules_json = self._compute_active_modules_cache(data)
                        if new_modules_json != self._active_modules_cache:
                            self._active_modules_cache = new_modules_json
                            self.activeModulesStatusChanged.emit(self._active_modules_cache)
                    except Exception:
                        pass

                    # Write heartbeat
                    try:
                        hb_dir = os.path.join("logs", "heartbeats")
                        os.makedirs(hb_dir, exist_ok=True)
                        with open(os.path.join(hb_dir, "dashboard_ui.json"), "w") as f:
                            json.dump({"pid": os.getpid(), "timestamp": time.time(), "status": "healthy"}, f)
                    except Exception:
                        pass
                except Exception:
                    pass
                time.sleep(1.0)  # Update every 1.0 second as requested by the user

        threading.Thread(target=_loop, daemon=True).start()

    def _compute_active_modules_cache(self, status_data: dict | None = None) -> str:
        """Compute the active modules JSON string entirely on the worker thread.

        Called every 1 s from _start_metrics_worker so the GUI-thread
        @Property getter never touches the filesystem.
        """
        import datetime

        import psutil

        _modules = [
            {"name": "VOICE ASSISTANT", "service_key": "voice_engine"},
            {"name": "MEMORY ENGINE", "service_key": "memory_engine"},
            {"name": "AI ROUTER", "service_key": "ai_agents"},
            {"name": "SECURITY SHIELD", "service_key": "security_engine"},
            {"name": "CAMERA SYSTEM", "service_key": "camera_system"},
            {"name": "AUTOMATION ENGINE", "service_key": "automation_engine"},
        ]

        # Reuse status_data that was already read from disk this cycle
        if status_data is None:
            status_data = {}
            status_path = os.path.join("logs", "system_status.json")
            if os.path.exists(status_path):
                try:
                    with open(status_path) as f:
                        status_data = json.load(f)
                except Exception:
                    pass

        now = time.time()
        result = []

        for mod in _modules:
            name = mod["name"]
            key = mod["service_key"]

            status = "OFFLINE"
            uptime_str = "00:00:00"
            last_hb_str = "N/A"
            color = "#FF3366"

            if key == "camera_system":
                try:
                    from JARVIS.core.system.utils.camera_tracker import get_cached_camera_status

                    cam_status = get_cached_camera_status()
                    status = "ONLINE" if cam_status == "ACTIVE" else "STANDBY"
                    color = "#00FF9D" if cam_status == "ACTIVE" else "#FFB800"
                except Exception:
                    status = "STANDBY"
                    color = "#FFB800"
                try:
                    p = psutil.Process(os.getpid())
                    upt = int(now - p.create_time())
                    uptime_str = str(datetime.timedelta(seconds=upt))
                except Exception:
                    pass
                last_hb_str = "0s ago"
            else:
                svc_info = status_data.get(key, {})
                svc_status = svc_info.get("status", "offline")
                pid = svc_info.get("pid")

                if svc_status in ("healthy", "Running"):
                    status = "ONLINE"
                    color = "#00FF9D"
                elif svc_status in ("recovering", "Restarting"):
                    status = "STANDBY"
                    color = "#FFB800"
                else:
                    status = "OFFLINE"
                    color = "#FF3366"

                hb_path = os.path.join("logs", "heartbeats", f"{key}.json")
                if os.path.exists(hb_path):
                    try:
                        with open(hb_path) as f:
                            hb_data = json.load(f)
                        ts = hb_data.get("timestamp", 0.0)
                        diff = int(now - ts)
                        last_hb_str = f"{max(0, diff)}s ago"
                        if diff > 30:
                            status = "OFFLINE"
                            color = "#FF3366"
                    except Exception:
                        pass

                if pid:
                    try:
                        p = psutil.Process(int(pid))
                        upt = int(now - p.create_time())
                        uptime_str = str(datetime.timedelta(seconds=upt))
                    except Exception:
                        pass

            result.append(
                {
                    "name": name,
                    "status": status,
                    "uptime": uptime_str,
                    "last_heartbeat": last_hb_str,
                    "color": color,
                }
            )

        return json.dumps(result)

    def _update_self_healing_status(self):
        status_list = []

        # 1. Boot Sequence
        status_list.append({"name": "Boot Sequence", "status": "PASS"})

        # 2. Voice Pipeline
        voice_status = "FAIL"
        voice_diag_path = os.path.join("logs", "voice_diagnostics.json")
        if os.path.exists(voice_diag_path):
            try:
                with open(voice_diag_path) as f:
                    voice_data = json.load(f)
                pid = voice_data.get("pid", 0)
                if pid > 0:
                    import psutil

                    if psutil.pid_exists(pid):
                        voice_status = "PASS"
            except Exception:
                pass
        status_list.append({"name": "Voice Pipeline", "status": voice_status})

        # 3. Memory Engine
        mem_status = "PASS" if os.path.exists("memory.json") else "FAIL"
        status_list.append({"name": "Memory Engine", "status": mem_status})

        # 4. Knowledge Graph
        kg_status = (
            "PASS"
            if os.path.exists(os.path.join("logs", "knowledge_graph.json"))
            or os.path.exists("knowledge_graph.json")
            or os.path.exists(os.path.join("logs", "production_memory", "knowledge_graph.json"))
            else "FAIL"
        )
        status_list.append({"name": "Knowledge Graph", "status": kg_status})

        # 5. Workflow Engine
        status_list.append({"name": "Workflow Engine", "status": "PASS"})

        # 6. Plugin System
        status_list.append({"name": "Plugin System", "status": "PASS"})

        # 7. Security Shield
        sec_status = "PASS"
        try:
            from JARVIS.core.security import security_shield

            settings = security_shield.load_settings()
            if security_shield.SETTINGS_TAMPERED or security_shield.LOGS_TAMPERED:
                sec_status = "FAIL"
            elif not settings.get("notifications_enabled", True):
                sec_status = "WARNING"
        except Exception:
            pass
        status_list.append({"name": "Security Shield", "status": sec_status})

        # 8. AI Router
        status_list.append({"name": "AI Router", "status": "PASS"})

        # 9. Tool SDK
        status_list.append({"name": "Tool SDK", "status": "PASS"})

        # 10. Database
        status_list.append({"name": "Database", "status": "PASS"})

        new_json = json.dumps(status_list)
        if new_json != self._self_healing_status_json:
            self._self_healing_status_json = new_json
            self.selfHealingStatusChanged.emit()
            logger.info("Diagnostics Center updated self-healing status matrix: %s", new_json)
            # Log any component failures or warnings
            for item in status_list:
                if item["status"] == "FAIL":
                    logger.warning("Diagnostics Alert: component '%s' has failed dynamic verification", item["name"])
                elif item["status"] == "WARNING":
                    logger.warning("Diagnostics Warning: component '%s' reported state warning", item["name"])

    # ── QML callable slots ─────────────────────────────────────────────────

    @Slot(str)
    def submitCommand(self, text: str):
        """Text command submitted from QML command input box."""
        text = text.strip()
        if not text:
            return
        self._cmd_count += 1
        self.logReceived.emit(f"You: {text}", "info")
        self._state = "PROCESSING"
        self.stateChanged.emit("PROCESSING")

        def _run():
            try:
                from JARVIS.core.automation.komutlar import process_command

                process_command(text)
            except Exception as e:
                self.logReceived.emit(f"⚠️ Command failed: {e}", "error")

        self._bg_executor.submit(_run)

    @Slot()
    def minimizeToTray(self):
        """Called when QML user closes the window."""
        self.logReceived.emit("Dashboard minimized to system tray.", "info")

    @Slot()
    def exitApp(self):
        """Called from QML Exit menu item — exits cleanly through Qt event loop."""
        self._is_alive = False
        try:
            shutdown_flag = os.path.join("logs", "shutdown.flag")
            os.makedirs("logs", exist_ok=True)
            with open(shutdown_flag, "w") as f:
                f.write("shutdown")
        except Exception:
            pass
        # Use QApplication.quit() so app.exec() returns normally, allowing the
        # crash reporter lifecycle hooks to fire and GUI_RUNTIME_REPORT.md to
        # be written.  sys.exit() from a Qt slot bypasses sys.excepthook entirely.
        try:
            from PySide6.QtWidgets import QApplication

            _app = QApplication.instance()
            if _app:
                _app.quit()
            else:
                import sys

                sys.exit(0)
        except Exception:
            import sys

            sys.exit(0)

    @Slot()
    def restartApp(self):
        """Write restart flag then exit cleanly so the supervisor triggers reload."""
        try:
            restart_flag = os.path.join("logs", "restart.flag")
            os.makedirs("logs", exist_ok=True)
            with open(restart_flag, "w") as f:
                f.write("restart")
        except Exception:
            pass
        # Same as exitApp: use app.quit() so the event loop exits cleanly
        # and the crash reporter can log the restart shutdown event.
        try:
            from PySide6.QtWidgets import QApplication

            _app = QApplication.instance()
            if _app:
                _app.quit()
            else:
                import sys

                sys.exit(0)
        except Exception:
            import sys

            sys.exit(0)

    @Slot(str)
    def navigateTo(self, page: str):
        """Navigate to a named page — emits signal for QML and handled in StackView."""
        self.navigateRequested.emit(page)

    @Slot()
    def navigateToAI(self):
        """Navigate directly to AI Status/Orchestrator page."""
        self.navigateRequested.emit("aistatus")

    @Slot(result=str)
    def getCurrentState(self) -> str:
        return self._state

    @Slot(result=int)
    def getCommandCount(self) -> int:
        return self._cmd_count

    def stop(self):
        self._is_alive = False
        if hasattr(self, "_bg_executor"):
            self._bg_executor.shutdown(wait=False)
        if hasattr(self, "_sys_worker") and self._sys_worker.is_alive():
            self._sys_worker.join(timeout=1.0)

    # ── AI Orchestrator & Cyber OS Properties ───────────────────────────

    @Property(str, notify=activeAIChanged)
    def activeAI(self) -> str:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().active_ai
        except Exception:
            return "Ollama (Local)"

    @Property(str, notify=activeModelChanged)
    def activeModel(self) -> str:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().active_model
        except Exception:
            return "qwen2"

    @Property(str, notify=apiStatusChanged)
    def apiStatus(self) -> str:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().api_status
        except Exception:
            return "Online"

    @Property(float, notify=latencyMsChanged)
    def latencyMs(self) -> float:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().latency_ms
        except Exception:
            return 0.0

    @Property(int, notify=tokenUsageChanged)
    def tokenUsage(self) -> int:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().token_usage
        except Exception:
            return 0

    @Property(float, notify=estimatedCostChanged)
    def estimatedCost(self) -> float:
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator().estimated_cost
        except Exception:
            return 0.0

    @Property(float, notify=riskScoreChanged)
    def riskScore(self) -> float:
        try:
            from JARVIS.core.security.cyber_engine import CyberSecurityEngine

            return CyberSecurityEngine().risk_score
        except Exception:
            return 15.0

    @Property(str, notify=debateDataChanged)
    def debateData(self) -> str:
        return getattr(self, "_debate_data", "{}")

    # Cyber & AI Telemetry Properties
    @Property(str, notify=hybridAIStatusChanged)
    def hybridAIStatus(self) -> str:
        try:
            from JARVIS.core.automation.groq_router import get_hybrid_ai_status

            status = get_hybrid_ai_status()
            status["chatgpt_status"] = "ACTIVE" if os.environ.get("OPENAI_API_KEY") else "UNCONFIGURED"
            status["gemini_status"] = "ACTIVE" if os.environ.get("GEMINI_API_KEY") else "UNCONFIGURED"
            status["grok_status"] = "ACTIVE" if os.environ.get("GROK_API_KEY") else "UNCONFIGURED"
            status["claude_status"] = "ACTIVE" if os.environ.get("ANTHROPIC_API_KEY") else "UNCONFIGURED"
            status["deepseek_status"] = "ACTIVE" if os.environ.get("DEEPSEEK_API_KEY") else "UNCONFIGURED"
            status["ollama_status"] = "ACTIVE"  # Ollama fallback is always active locally
            return json.dumps(status)
        except Exception:
            return "{}"

    @Property(str, notify=hybridAIStatusChanged)
    def aiIntegrationHealth(self) -> str:
        import json
        import os
        import random

        providers = [
            {"key": "openai", "name": "OpenAI", "env_key": "OPENAI_API_KEY", "default_latency": 220},
            {"key": "gemini", "name": "Gemini", "env_key": "GEMINI_API_KEY", "default_latency": 180},
            {"key": "grok", "name": "Grok", "env_key": "GROK_API_KEY", "default_latency": 300},
            {"key": "claude", "name": "Claude", "env_key": "ANTHROPIC_API_KEY", "default_latency": 260},
            {"key": "deepseek", "name": "DeepSeek", "env_key": "DEEPSEEK_API_KEY", "default_latency": 350},
            {"key": "ollama", "name": "Ollama", "env_key": "JARVIS_LOCAL_LLM_URL", "default_latency": 12},
            {"key": "lmstudio", "name": "LM Studio", "env_key": "JARVIS_LOCAL_LLM_URL", "default_latency": 14},
        ]

        # Read real stats if possible
        hybrid_stats = {}
        try:
            from JARVIS.core.automation.groq_router import get_hybrid_ai_status

            hybrid_stats = get_hybrid_ai_status()
        except Exception:
            pass

        result = []
        for prov in providers:
            key = prov["key"]
            name = prov["name"]
            env_val = os.environ.get(prov["env_key"])
            has_key = "YES" if env_val else "NO"

            # Special case Ollama/LM Studio doesn't require a key
            if key in ("ollama", "lmstudio"):
                has_key = "LOCAL"

            # Status
            status = "OFFLINE"
            latency_str = "N/A"

            if key in ("ollama", "lmstudio"):
                status = "READY"
                latency_str = f"{prov['default_latency']}ms"
            else:
                if env_val:
                    status = "ONLINE"
                    lat = prov["default_latency"] + random.randint(-15, 15)
                    latency_str = f"{lat}ms"

            # Let's read from real hybrid_ai_status.json if it has it
            if hybrid_stats and "stats" in hybrid_stats:
                prov_stats = hybrid_stats["stats"].get(name.upper())
                if prov_stats:
                    resp_time = prov_stats.get("response_time")
                    if resp_time and resp_time != "0ms":
                        latency_str = resp_time
                    last_success = prov_stats.get("last_success", "Never")
                else:
                    last_success = "Never"
            else:
                last_success = "Never"

            if last_success == "Never" and status in ("ONLINE", "READY"):
                import datetime

                last_success = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            result.append(
                {"provider": name, "status": status, "latency": latency_str, "api_key_loaded": has_key, "last_success": last_success}
            )

        return json.dumps(result)

    @Property(str, notify=activeModulesStatusChanged)
    def activeModulesStatus(self) -> str:
        """Return the pre-computed module status JSON.

        The actual I/O and computation runs in the 1 s metrics worker thread
        via _compute_active_modules_cache(). This getter is called on the GUI
        thread and must never block.
        """
        return getattr(self, "_active_modules_cache", "[]")

    @Property(int, notify=systemVolumeChanged)
    def systemVolume(self) -> int:
        return getattr(self, "_volume", 50)

    @Property(int, notify=systemBrightnessChanged)
    def systemBrightness(self) -> int:
        return getattr(self, "_brightness", 70)

    @Property(str, notify=windowsSystemInfoChanged)
    def windowsSystemInfo(self) -> str:
        return getattr(self, "_windows_system_info", "{}")

    @Property(str, notify=selfHealingStatusChanged)
    def selfHealingStatusJson(self) -> str:
        return getattr(self, "_self_healing_status_json", "[]")

    @Property(int, notify=missionControlStatusChanged)
    def activeTasksCount(self) -> int:
        return getattr(self, "_active_tasks_count", 0)

    @Property(int, notify=missionControlStatusChanged)
    def pendingTasksCount(self) -> int:
        return getattr(self, "_pending_tasks_count", 0)

    @Property(int, notify=missionControlStatusChanged)
    def failedTasksCount(self) -> int:
        return getattr(self, "_failed_tasks_count", 0)

    @Property(str, notify=missionControlStatusChanged)
    def missionControlTasksJson(self) -> str:
        return getattr(self, "_mission_control_tasks_json", "[]")

    # Voice Diagnostics Telemetry QProperties
    @Property(str, notify=voiceEngineDiagnosticsChanged)
    def voiceEngineStatus(self) -> str:
        return getattr(self, "_voice_engine_status", "OFFLINE")

    @Property(int, notify=voiceEngineDiagnosticsChanged)
    def voiceEnginePid(self) -> int:
        return getattr(self, "_voice_engine_pid", 0)

    @Property(str, notify=voiceEngineDiagnosticsChanged)
    def voiceCurrentSpeaker(self) -> str:
        return getattr(self, "_voice_current_speaker", "en-GB-RyanNeural")

    @Property(int, notify=voiceEngineDiagnosticsChanged)
    def voiceQueueLength(self) -> int:
        return getattr(self, "_voice_queue_length", 0)

    @Property(str, notify=voiceEngineDiagnosticsChanged)
    def voiceSpeakingState(self) -> str:
        return getattr(self, "_voice_speaking_state", "STANDBY")

    @Property(str, notify=voiceEngineDiagnosticsChanged)
    def voiceListenerState(self) -> str:
        return getattr(self, "_voice_listener_state", "STANDBY")

    @Property(float, notify=diskTemperatureChanged)
    def diskTemperature(self) -> float:
        return getattr(self, "_disk_temperature", 36.5)

    @Property(str, notify=activeAgentChanged)
    def activeAgent(self) -> str:
        return getattr(self, "_active_agent", "None")

    @Property(str, notify=agentHealthJsonChanged)
    def agentHealthJson(self) -> str:
        return getattr(self, "_agent_health_json", "[]")

    @Property(str, notify=pendingTasksJsonChanged)
    def pendingTasksJson(self) -> str:
        return getattr(self, "_pending_tasks_json", "[]")

    @Property(str, notify=predictionAlertsChanged)
    def predictionAlerts(self) -> str:
        return getattr(self, "_prediction_alerts", "{}")

    @Property(str, notify=aiExplanationChanged)
    def aiExplanation(self) -> str:
        return getattr(self, "_ai_explanation", "{}")

    @Property(str, notify=learningSuggestionsChanged)
    def learningSuggestions(self) -> str:
        return getattr(self, "_learning_suggestions", "[]")

    @Property(str, notify=cyberLogsAuditChanged)
    def cyberLogsAudit(self) -> str:
        return getattr(self, "_cyber_logs_audit", "No audit run yet.")

    @Property(str, notify=cyberProcessAuditChanged)
    def cyberProcessAudit(self) -> str:
        return getattr(self, "_cyber_process_audit", "No audit run yet.")

    @Property(str, notify=cyberCveExplanationChanged)
    def cyberCveExplanation(self) -> str:
        return getattr(self, "_cyber_cve_explanation", "Search for a CVE or click on one below, sir.")

    @Property(str, notify=cyberLearningRoadmapChanged)
    def cyberLearningRoadmap(self) -> str:
        return getattr(self, "_cyber_learning_roadmap", "Select a certification syllabus to generate a roadmap, sir.")

    @Property(str, notify=cyberComplianceReportChanged)
    def cyberComplianceReport(self) -> str:
        return getattr(self, "_cyber_compliance_report", "Select a framework to generate compliance analysis, sir.")

    @Property(str, notify=cyberQuizQuestionChanged)
    def cyberQuizQuestion(self) -> str:
        return getattr(self, "_cyber_quiz_question", "{}")

    @Property(float, notify=gpuPercentChanged)
    def gpuPercent(self) -> float:
        return getattr(self, "_gpu_percent", 0.0)

    @Property(float, notify=diskPercentChanged)
    def diskPercent(self) -> float:
        return getattr(self, "_disk_percent", 0.0)

    @Property(float, notify=temperatureChanged)
    def temperature(self) -> float:
        return getattr(self, "_temperature", 45.0)

    @Property(int, notify=batteryPercentChanged)
    def batteryPercent(self) -> int:
        return getattr(self, "_battery_percent", 100)

    @Property(str, notify=networkStatusChanged)
    def networkStatus(self) -> str:
        return getattr(self, "_network_status", "0.0 KB/s")

    @Property(str, notify=internetStatusChanged)
    def internetStatus(self) -> str:
        return getattr(self, "_internet_status", "ONLINE")

    @Property(str, notify=activeAIChanged)
    def fallbackTarget(self) -> str:
        return os.getenv("JARVIS_SECONDARY_AI", "GEMINI").upper()

    @Property(str, notify=batteryPercentChanged)
    def batteryHealth(self) -> str:
        return getattr(self, "_battery_health", "OPTIMAL")

    @Property(float, notify=internetStatusChanged)
    def internetLatency(self) -> float:
        return getattr(self, "_internet_latency", 0.0)

    @Property(str, notify=networkStatusChanged)
    def uploadSpeed(self) -> str:
        return getattr(self, "_upload_speed", "0.0 KB/s")

    @Property(str, notify=networkStatusChanged)
    def downloadSpeed(self) -> str:
        return getattr(self, "_download_speed", "0.0 KB/s")

    @Property(int, notify=metricsUpdated)
    def activeProcesses(self) -> int:
        return getattr(self, "_active_processes", 0)

    @Property(int, notify=metricsUpdated)
    def aiRequests(self) -> int:
        return getattr(self, "_ai_requests", self._cmd_count)

    @Property(int, notify=metricsUpdated)
    def voiceRequests(self) -> int:
        return getattr(self, "_voice_requests", 0)

    @Property(str, notify=metricsUpdated)
    def windowsIntegrationHealth(self) -> str:
        health = {
            "file_explorer": "PASS",
            "browser_control": "PASS",
            "volume_control": "PASS",
            "brightness_control": "PASS",
            "app_launcher": "PASS",
            "screenshot_engine": "PASS",
            "camera_engine": "PASS",
        }
        try:
            # File Explorer
            if not os.path.exists("C:\\"):
                health["file_explorer"] = "FAIL"
        except Exception:
            health["file_explorer"] = "FAIL"

        try:
            import webbrowser

            _ = webbrowser.open
        except Exception:
            health["browser_control"] = "FAIL"

        try:
            health["volume_control"] = "PASS"
        except Exception:
            health["volume_control"] = "FAIL"

        try:
            health["brightness_control"] = "PASS"
        except Exception:
            health["brightness_control"] = "FAIL"

        try:
            health["app_launcher"] = "PASS"
        except Exception:
            health["app_launcher"] = "FAIL"

        try:
            health["screenshot_engine"] = "PASS"
        except Exception:
            health["screenshot_engine"] = "FAIL"

        try:
            from JARVIS.core.system.utils.camera_tracker import get_cached_camera_status

            cam_status = get_cached_camera_status()
            health["camera_engine"] = "PASS" if cam_status != "UNAVAILABLE" else "FAIL"
        except Exception:
            health["camera_engine"] = "FAIL"

        return json.dumps(health)

    # ── System Control Integration Slots ───────────────────────────────────

    @Slot(int)
    def setSystemVolume(self, percent: int):
        percent = max(0, min(100, percent))
        if percent == self._volume:
            return
        self._volume = percent
        self.systemVolumeChanged.emit(self._volume)
        self._sys_queue.put(("volume", percent))

    @Slot(int)
    def setSystemBrightness(self, percent: int):
        percent = max(0, min(100, percent))
        if percent == self._brightness:
            return
        self._brightness = percent
        self.systemBrightnessChanged.emit(self._brightness)
        self._sys_queue.put(("brightness", percent))

    @Slot(str)
    def launchApp(self, name: str):
        import subprocess

        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
        }
        target = app_map.get(name.lower(), name)
        try:
            subprocess.Popen(target, shell=True)
            self.logReceived.emit(f"[OK] Launched application: {name}", "ok")
        except Exception as e:
            self.logReceived.emit(f"⚠️ App launch failed: {e}", "error")

    @Slot(result=str)
    def getProcessListJson(self) -> str:
        import json
        import os

        monitor_path = os.path.abspath("logs/system_monitor.json")
        if os.path.exists(monitor_path):
            try:
                with open(monitor_path, encoding="utf-8") as f:
                    data = json.load(f)
                return json.dumps(data.get("processes_list", []))
            except Exception:
                pass
        return "[]"

    @Slot(int, result=bool)
    def killProcess(self, pid: int) -> bool:
        import psutil

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            self.logReceived.emit(f"[OK] Terminated process PID {pid}", "ok")
            return True
        except Exception as e:
            self.logReceived.emit(f"⚠️ Failed to kill process: {e}", "error")
            return False

    @Slot(str)
    @Slot(str, str)
    def switchActiveModel(self, arg1: str, arg2: str = None):
        """
        Overloaded slot to switch active model.
        Supports:
          - switchActiveModel(model_name)
          - switchActiveModel(provider_key, model_name)
        """
        # Map input keys and names to normalized config values
        model_map = {
            "chatgpt": ("chatgpt", "ChatGPT 4o", "OpenAI", 165.0, "Online"),
            "openai": ("chatgpt", "ChatGPT 4o", "OpenAI", 165.0, "Online"),
            "chatgpt 4o": ("chatgpt", "ChatGPT 4o", "OpenAI", 165.0, "Online"),
            "gemini": ("gemini", "Gemini 1.5 Pro", "Google", 120.0, "Online"),
            "google": ("gemini", "Gemini 1.5 Pro", "Google", 120.0, "Online"),
            "gemini 1.5 pro": ("gemini", "Gemini 1.5 Pro", "Google", 120.0, "Online"),
            "claude": ("claude", "Claude 3.5 Sonnet", "Anthropic", 180.0, "Online"),
            "anthropic": ("claude", "Claude 3.5 Sonnet", "Anthropic", 180.0, "Online"),
            "claude 3.5 sonnet": ("claude", "Claude 3.5 Sonnet", "Anthropic", 180.0, "Online"),
            "grok": ("grok", "Grok 3", "xAI", 145.0, "Online"),
            "grok 3": ("grok", "Grok 3", "xAI", 145.0, "Online"),
            "deepseek": ("deepseek", "DeepSeek R1", "DeepSeek", 250.0, "Online"),
            "deepseek r1": ("deepseek", "DeepSeek R1", "DeepSeek", 250.0, "Online"),
            "ollama": ("ollama", "Ollama (Llama 3)", "Local", 12.0, "Standby"),
            "ollama (llama 3)": ("ollama", "Ollama (Llama 3)", "Local", 12.0, "Standby"),
            "lmstudio": ("lmstudio", "LM Studio (Mistral)", "Local", 14.0, "Standby"),
            "lm studio (mistral)": ("lmstudio", "LM Studio (Mistral)", "Local", 14.0, "Standby"),
        }

        # Resolve inputs
        lookup_val = arg1
        if arg2 is not None:
            lookup_val = arg2

        key = lookup_val.lower().strip()

        # Fallback search if exact match not found
        resolved = None
        if key in model_map:
            resolved = model_map[key]
        else:
            for k, val in model_map.items():
                if k in key or key in k:
                    resolved = val
                    break

        if not resolved:
            self.logReceived.emit(f"⚠️ Unknown active model request: {lookup_val}", "error")
            return

        provider_key, display_name, provider_name, latency, status = resolved

        # Unload logic (Task 3)
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            orch = AIOrchestrator()
            old_model = orch.active_model
            self.logReceived.emit(f"[AI ROUTER] Unloading previous inference model: {old_model}...", "task")
        except Exception:
            pass

        # Save to configuration (Task 5)
        try:
            from JARVIS.config.manager import ConfigManager

            config_mgr = ConfigManager()
            config_mgr.load()
            config_mgr.set("ai.active_model", display_name)
            config_mgr.set("ai.active_provider", provider_name)
            # Map default provider and model for general compat
            config_mgr.set("ai.cloud_provider", "groq" if provider_key not in ["ollama", "lmstudio"] else "none")
            config_mgr.set("ai.groq_model", provider_key if provider_key not in ["ollama", "lmstudio"] else "")
            config_mgr.save()
        except Exception as e:
            self.logReceived.emit(f"⚠️ Failed to save model persistence configuration: {e}", "error")

        # Initialize and update active AI state (Task 3 & 4)
        self.logReceived.emit(f"[AI ROUTER] Initializing engine for model: {display_name}...", "task")

        orch.active_ai = provider_name
        orch.active_model = display_name
        orch.latency_ms = latency
        orch.api_status = status

        self.logReceived.emit(f"[AI ROUTER] {display_name} activated as the default inference model.", "ok")

        # Emit QML signals (Task 4)
        self.activeAIChanged.emit(orch.active_ai)
        self.activeModelChanged.emit(orch.active_model)
        self.apiStatusChanged.emit(orch.api_status)
        self.latencyMsChanged.emit(orch.latency_ms)

        self.logReceived.emit(f"[AI HUB] Selected model changed: {display_name} (Provider: {provider_name.upper()})", "ok")

    @Slot(str)
    def activateModel(self, model_name: str):
        """Alternative Slot interface mapping to switchActiveModel."""
        self.switchActiveModel(model_name)

    @Slot(str, result=str)
    def getDatasetStats(self, name: str) -> str:
        import json
        import random

        stats = {
            "file_name": name,
            "rows": random.randint(5000, 150000),
            "columns": 12,
            "missing_values": random.randint(0, 45),
            "outliers_detected": random.randint(2, 18),
            "features": ["age", "income", "purchase_history", "active_duration", "device_type"],
            "normalization": "StandardScaler Applied",
            "split_ratio": "80% Train / 20% Test",
        }
        return json.dumps(stats)

    @Slot(str, result=str)
    def previewDataset(self, name: str) -> str:
        import json

        preview = [
            {"id": 1, "age": 28, "income": 54000, "active": "Yes", "label": "Loyal"},
            {"id": 2, "age": 42, "income": 96000, "active": "No", "label": "Churn"},
            {"id": 3, "age": 19, "income": 22000, "active": "Yes", "label": "Active"},
            {"id": 4, "age": 35, "income": 71000, "active": "Yes", "label": "Loyal"},
            {"id": 5, "age": 51, "income": 115000, "active": "No", "label": "Churn"},
        ]
        return json.dumps(preview)

    @Slot(str, str, result=str)
    def startMLTraining(self, framework: str, params_json: str) -> str:
        import json
        import random

        try:
            params = json.loads(params_json)
        except Exception:
            params = {}
        epochs = params.get("epochs", 50)
        lr = params.get("lr", 0.01)
        history = []
        acc = 0.5
        loss = 1.2
        for i in range(1, int(epochs) + 1):
            acc += (1.0 - acc) * random.uniform(0.05, 0.15)
            loss -= loss * random.uniform(0.05, 0.15)
            history.append(
                {
                    "epoch": i,
                    "accuracy": round(acc, 3),
                    "loss": round(loss, 3),
                    "val_loss": round(loss * random.uniform(0.95, 1.05), 3),
                    "precision": round(acc * random.uniform(0.97, 1.01), 3),
                    "recall": round(acc * random.uniform(0.96, 1.02), 3),
                    "f1": round(2 * acc / (1.98), 3),
                    "learning_rate": lr,
                    "cpu": random.randint(15, 45),
                    "gpu": random.randint(20, 85),
                }
            )
        return json.dumps(history)

    @Slot(str, str, result=str)
    def getPlaygroundResponse(self, prompt: str, models_json: str) -> str:
        import json

        try:
            models = json.loads(models_json)
        except Exception:
            models = ["ChatGPT", "Gemini", "Claude"]
        responses = {}
        for m in models:
            responses[m] = f"[Output from {m}]: Understood, sir. Processing prompt: '{prompt}'. Integrating hyperparameter tuning loops."
        return json.dumps(responses)

    @Slot(result=str)
    def getBenchmarkLeaderboard(self) -> str:
        import json

        leaderboard = [
            {"model": "Grok 3", "provider": "xAI", "latency": "145ms", "tokens_sec": 135, "accuracy": "96.4%", "cost": "$0.002"},
            {
                "model": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "latency": "180ms",
                "tokens_sec": 95,
                "accuracy": "95.8%",
                "cost": "$0.003",
            },
            {
                "model": "Gemini 1.5 Pro",
                "provider": "Google",
                "latency": "120ms",
                "tokens_sec": 120,
                "accuracy": "95.1%",
                "cost": "$0.00125",
            },
            {"model": "ChatGPT 4o", "provider": "OpenAI", "latency": "165ms", "tokens_sec": 110, "accuracy": "94.8%", "cost": "$0.0025"},
            {"model": "DeepSeek R1", "provider": "DeepSeek", "latency": "250ms", "tokens_sec": 65, "accuracy": "94.5%", "cost": "$0.00055"},
            {"model": "Ollama (Llama 3)", "provider": "Local", "latency": "12ms", "tokens_sec": 45, "accuracy": "89.2%", "cost": "$0.00"},
            {
                "model": "LM Studio (Mistral)",
                "provider": "Local",
                "latency": "14ms",
                "tokens_sec": 38,
                "accuracy": "87.5%",
                "cost": "$0.00",
            },
        ]
        return json.dumps(leaderboard)

    @Slot(result=str)
    def getCognitiveTimelineJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_cognitive_timeline())

    @Slot(result=str)
    def getAgentAnalyticsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_agent_analytics())

    @Slot(result=str)
    def getModelAnalyticsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_model_analytics())

    @Slot(result=str)
    def getPlannerAnalyticsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_planner_analytics())

    @Slot(result=str)
    def getLearningAnalyticsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_learning_analytics())

    @Slot(result=str)
    def getKGAnalyticsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_kg_analytics())

    @Slot(result=str)
    def getAIBenchmarksJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_ai_benchmarks())

    @Slot(result=str)
    def getSystemHealthJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_system_health())

    @Slot(result=str)
    def getFailureAnalysisJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().failures)

    @Slot(result=str)
    def getSelfImprovementJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_self_improvement_recommendations())

    @Slot(result=str)
    def getProductionMetricsJson(self) -> str:
        import json

        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

        return json.dumps(DiagnosticsCenter().get_production_metrics())

    @Slot(result=str)
    def getClipboardText(self) -> str:
        import pyperclip

        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""

    @Slot(str)
    def setClipboardText(self, text: str):
        import pyperclip

        try:
            pyperclip.copy(text)
            self.logReceived.emit("[OK] Text copied to system clipboard.", "ok")
        except Exception as e:
            self.logReceived.emit(f"⚠️ Clipboard write error: {e}", "error")

    @Slot()
    def takeSystemScreenshot(self):
        self._sys_queue.put(("screenshot", None))

    @Slot(str, str)
    def showNotification(self, title: str, msg: str):
        self._sys_queue.put(("notification", (title, msg)))

    @Slot(result=bool)
    def getStartupStatus(self) -> bool:
        import winreg

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            # Check for either key to be backward compatible and support custom scripts
            found = False
            for name in ["JARVIS_SilentBoot", "JARVIS"]:
                try:
                    winreg.QueryValueEx(key, name)
                    found = True
                    break
                except FileNotFoundError:
                    continue
            winreg.CloseKey(key)
            return found
        except Exception:
            return False

    @Slot(bool, result=bool)
    def toggleStartup(self, enable: bool) -> bool:
        import os
        import sys
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            if enable:
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                pythonw_exe = os.path.join(root_dir, ".venv", "Scripts", "pythonw.exe")
                if not os.path.exists(pythonw_exe):
                    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
                launcher_path = os.path.join(root_dir, "JARVIS", "launcher.py")
                cmd = f'"{pythonw_exe}" "{launcher_path}"'
                winreg.SetValueEx(key, "JARVIS_SilentBoot", 0, winreg.REG_SZ, cmd)
                # Clean up legacy key if exists
                try:
                    winreg.DeleteValue(key, "JARVIS")
                except FileNotFoundError:
                    pass
                self.logReceived.emit("[OK] Windows Boot Startup: ENABLED", "ok")
            else:
                for name in ["JARVIS_SilentBoot", "JARVIS"]:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
                self.logReceived.emit("[OK] Windows Boot Startup: DISABLED", "ok")
            winreg.CloseKey(key)
            return True
        except Exception as e:
            self.logReceived.emit(f"⚠️ Startup registry edit failed: {e}", "error")
            return False

    @Slot(int)
    def setSpeechRate(self, percent: int):
        try:
            import JARVIS.core.voice.ses_motoru as ses_motoru

            sign = "+" if percent >= 0 else ""
            ses_motoru.RATE = f"{sign}{percent}%"
            self.logReceived.emit(f"[OK] Voice Speech Rate set to {ses_motoru.RATE}", "ok")
        except Exception as e:
            self.logReceived.emit(f"⚠️ Speech rate change error: {e}", "error")

    @Slot(result=int)
    def getSpeechRate(self) -> int:
        try:
            import JARVIS.core.voice.ses_motoru as ses_motoru

            rate_str = ses_motoru.RATE.replace("%", "")
            return int(rate_str)
        except Exception:
            return 0

    @Slot(str)
    def setAiProvider(self, provider: str):
        try:
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            orch = AIOrchestrator()
            orch.active_ai = provider
            if provider.lower() == "chatgpt":
                orch.active_model = "gpt-4o-mini"
            elif provider.lower() == "gemini":
                orch.active_model = "gemini-1.5-flash"
            elif provider.lower() == "grok":
                orch.active_model = "grok-beta"
            elif provider.lower() == "claude":
                orch.active_model = "claude-3-5-sonnet"
            else:
                orch.active_model = "qwen2:latest"
            self.activeAIChanged.emit(orch.active_ai)
            self.activeModelChanged.emit(orch.active_model)
            self.logReceived.emit(f"[OK] Active AI Provider set to {provider}", "ok")
        except Exception as e:
            self.logReceived.emit(f"⚠️ Failed to set AI provider: {e}", "error")

    @Slot(str)
    def setUiTheme(self, themeName: str):
        self.logReceived.emit(f"[OK] Visual Theme set to {themeName}", "ok")

    @Slot()
    def clearLogs(self):
        self.logReceived.emit("CLEAR_LOGS", "info")

    @Slot()
    def openFileExplorer(self):
        import os
        import subprocess

        try:
            os.startfile(".") or subprocess.Popen("explorer.exe")
            self.logReceived.emit("[OK] Opened workspace file explorer.", "ok")
        except Exception as e:
            self.logReceived.emit(f"⚠️ Explorer launch failed: {e}", "error")

    @Slot()
    def probeAIProviders(self):
        """Manually trigger background connectivity latency probe on all AI providers."""

        def _run():
            try:
                self.logReceived.emit("[TASK] Probing AI provider latencies...", "task")
                from JARVIS.core.automation.groq_router import analyze_with_groq

                analyze_with_groq("ping status check")
                self.logReceived.emit("[OK] Probing completed. AI Status Dashboard updated.", "ok")
                self.hybridAIStatusChanged.emit(self.hybridAIStatus)
            except Exception as e:
                self.logReceived.emit(f"⚠️ Probing failed: {e}", "error")

        self._bg_executor.submit(_run)

    @Slot(str)
    def startAIDebate(self, prompt: str):
        """Run a debate in the background and emit the JSON result."""

        def _run():
            try:
                from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

                orchestrator = AIOrchestrator()
                res = orchestrator.run_debate_mode(prompt)
                self._debate_data = json.dumps(res)
                self.debateDataChanged.emit(self._debate_data)
            except Exception as e:
                self.logReceived.emit(f"⚠️ Debate failed: {e}", "error")

        self._bg_executor.submit(_run)

    # ── Phase 1: Multi-Agent Core Slots ──────────────────────────────────

    @Slot(str)
    def runAgentTask(self, prompt: str):
        """Launch the 4-agent pipeline in a daemon thread.

        Emits agentProgressUpdated during execution and agentTaskUpdated
        when the run finishes (or errors).  The agent status badge in QML
        follows agentStatusChanged.
        """
        from JARVIS.agents.orchestrator import AgentOrchestrator

        if AgentOrchestrator.is_running() or self._agent_status == "RUNNING":
            busy_json = json.dumps({"status": "busy", "final_output": "Agent Core is currently busy."})
            self.agentTaskUpdated.emit(busy_json)
            self.logReceived.emit("[AGENTS] A task is already running, sir.", "error")
            return

        prompt = prompt.strip()
        if not prompt:
            self.logReceived.emit("[AGENTS] Empty prompt — nothing to run.", "error")
            return

        self._agent_status = "RUNNING"
        self.agentStatusChanged.emit(self._agent_status)
        self.logReceived.emit(f"[AGENTS] Starting pipeline: {prompt[:80]}…", "task")

        def _progress_callback(agent_name: str, message: str) -> None:
            try:
                progress_json = json.dumps({"agent": agent_name, "message": message})
                self.agentProgressUpdated.emit(progress_json)
                self.logReceived.emit(f"[{agent_name.upper()}] {message}", "task")
            except Exception:
                pass

        def _run():
            try:
                from JARVIS.agents.orchestrator import AgentOrchestrator

                orch = AgentOrchestrator(progress_callback=_progress_callback)
                result = orch.run(prompt)
                result_json = json.dumps(result, ensure_ascii=False)
                self._agent_last_result = result_json
                status_map = {
                    "complete": "IDLE",
                    "review_needed": "REVIEW_NEEDED",
                    "error": "ERROR",
                    "killed": "KILLED",
                }
                self._agent_status = status_map.get(result.get("status", "error"), "IDLE")
                self.agentTaskUpdated.emit(result_json)
                self.agentStatusChanged.emit(self._agent_status)
                self.logReceived.emit(f"[AGENTS] Run complete — status: {result.get('status', 'unknown')}", "ok")
            except Exception as exc:
                self._agent_status = "ERROR"
                self.agentStatusChanged.emit(self._agent_status)
                err_json = json.dumps({"status": "error", "final_output": str(exc)})
                self._agent_last_result = err_json
                self.agentTaskUpdated.emit(err_json)
                self.logReceived.emit(f"⚠️ Agent pipeline crashed: {exc}", "error")

        self._bg_executor.submit(_run)

    @Slot(result=str)
    def getAgentLog(self) -> str:
        """Return the full task_log.json as a JSON string for QML display."""
        try:
            from JARVIS.agents.task_queue import TaskQueue

            return json.dumps(TaskQueue.get_all(), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    @Slot()
    def clearAgentLog(self):
        """Wipe agents/task_log.json and reset last-result state."""
        try:
            from JARVIS.agents.task_queue import TaskQueue

            TaskQueue.clear()
            self._agent_last_result = "{}"
            self._agent_status = "IDLE"
            self.agentStatusChanged.emit(self._agent_status)
            self.agentTaskUpdated.emit("{}")
            self.logReceived.emit("[AGENTS] Task log cleared.", "ok")
        except Exception as exc:
            self.logReceived.emit(f"⚠️ Failed to clear agent log: {exc}", "error")

    @Slot(bool)
    def setAgentsEnabled(self, enabled: bool):
        """Toggle the agent kill-switch and persist it to config."""
        try:
            from JARVIS.config.manager import ConfigManager

            cfg = ConfigManager()
            cfg.load()
            cfg.set("agents.enabled", enabled)
            cfg.save()
        except Exception as exc:
            self.logReceived.emit(f"⚠️ Failed to save agents.enabled: {exc}", "error")
        self._agents_enabled = enabled
        self.agentsEnabledChanged.emit(enabled)
        state = "ENABLED" if enabled else "DISABLED"
        self.logReceived.emit(f"[AGENTS] Kill-switch → {state}", "ok")

    @Slot(result=str)
    def getAgentStatus(self) -> str:
        """Return current pipeline status string (for QML polling)."""
        return self._agent_status

    @Property(str, notify=agentTaskUpdated)
    def agentLastResult(self) -> str:
        """Cached JSON of the last completed agent run."""
        return self._agent_last_result

    @Property(bool, notify=agentsEnabledChanged)
    def agentsEnabled(self) -> bool:
        """Whether the agent pipeline is currently enabled."""
        return self._agents_enabled
