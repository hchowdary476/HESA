import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

# venv_resolver is the single source of truth for the active Python interpreter.
# StartupManager reads from the same module-level singleton that
# EnvironmentValidator uses — this prevents the two-path divergence bug.
from JARVIS.core.system.venv_resolver import get_resolved_env

logger = logging.getLogger("startup_manager")

# Paths resolved from __file__ so they work regardless of CWD
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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


# Per-service startup timeout (seconds).  Tune individually here.
_SERVICE_TIMEOUTS = {
    "ai_router": 40,  # orchestration layer — most dependencies
    "memory_engine": 30,
    "knowledge_graph": 30,
    "voice_engine": 25,  # hardware-dependent; may take longer
    "workflow_engine": 20,
    "diagnostics": 20,
    "automation_engine": 20,
    "plugin_manager": 20,
}
_DEFAULT_TIMEOUT = 30


class StartupManager:
    def __init__(self):
        self.startup_log = []
        self.start_time = time.time()
        self.service_status = {}  # {name: "READY"|"FAILED"|"TIMEOUT"|"RETRY"}
        self.services = {}  # {name: instance}

        # ── Canonical startup sequence ─────────────────────────────────────────
        # Each entry: (service_name, is_critical)
        # is_critical=True  → failure aborts the entire startup
        # is_critical=False → failure is logged; startup continues
        #
        # Order matches spec: AI Router → Memory → Knowledge → Voice →
        #                     Workflow → Diagnostics → optional services → GUI
        # ──────────────────────────────────────────────────────────────────────
        self.startup_sequence = [
            ("ai_router", True),  # 1. AI Router  — orchestration first
            ("memory_engine", True),  # 2. Memory Engine
            ("knowledge_graph", True),  # 3. Knowledge Graph (memory layer)
            ("voice_engine", False),  # 4. Voice Engine  — hardware-dep; optional
            ("workflow_engine", True),  # 5. Workflow Engine
            ("diagnostics", True),  # 6. Diagnostics
            ("automation_engine", False),  # 7. Automation (optional)
            ("plugin_manager", False),  # 8. Plugin Manager (optional)
        ]

        # Derived convenience lists (kept for backwards compat)
        self.critical_services = [s for s, c in self.startup_sequence if c]
        self.optional_services = [s for s, c in self.startup_sequence if not c]

    # ── Public API ─────────────────────────────────────────────────────────────

    def initialize_all_services(self) -> bool:
        """Initialize every service in startup_sequence order."""
        self._log("Initiating zero-touch service startup sequence...")
        _write_event_log("STARTUP", "Service initialization sequence started")

        for service_name, is_critical in self.startup_sequence:
            ok = self._initialize_service(service_name)
            if not ok:
                if is_critical:
                    msg = f"Critical service '{service_name}' failed — startup aborted"
                    self._log(f"CRITICAL FAILURE: {msg}")
                    _write_event_log("DEPENDENCY_FAILURE", msg)
                    return False
                else:
                    msg = f"Optional service '{service_name}' failed — continuing"
                    self._log(msg)
                    _write_event_log("DEPENDENCY_FAILURE", msg)

        self._log("All services initialized.")
        _write_event_log("STARTUP", f"All services initialized in {self.get_startup_duration():.2f}s")
        return True

    def is_ready_for_gui_launch(self) -> bool:
        """GUI may launch only after all critical services are READY."""
        return all(self.service_status.get(svc) == "READY" for svc in self.critical_services)

    def get_startup_duration(self) -> float:
        return time.time() - self.start_time

    def generate_diagnostics(self) -> dict:
        return {
            "startup_duration": self.get_startup_duration(),
            "service_status": self.service_status,
            "failed_services": [s for s, st in self.service_status.items() if st in ("FAILED", "TIMEOUT")],
            "startup_log": self.startup_log,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _initialize_service(self, service_name: str) -> bool:
        """Init a single service with timeout; retry once on first failure."""
        from JARVIS.core.system.utils.gui_lifecycle_logger import log_lifecycle

        timeout = _SERVICE_TIMEOUTS.get(service_name, _DEFAULT_TIMEOUT)
        self._log(f"Initializing {service_name} (timeout={timeout}s)...")

        for attempt in range(1, 3):  # up to 2 attempts
            log_lifecycle("SERVICE_INIT_ATTEMPT", f"Service: {service_name}, Attempt: {attempt}, Timeout: {timeout}s")
            result = self._run_with_timeout(service_name, timeout)

            if result is True:
                self.service_status[service_name] = "READY"
                msg = f"{service_name} ready (attempt {attempt}, {self.get_startup_duration():.2f}s elapsed)"
                self._log(f"✓ {msg}")
                _write_event_log("STARTUP", msg)
                log_lifecycle(
                    "SERVICE_INIT_SUCCESS", f"Service: {service_name}, Attempt: {attempt}, Duration: {self.get_startup_duration():.2f}s"
                )
                return True

            if result == "TIMEOUT":
                self.service_status[service_name] = "TIMEOUT"
                msg = f"{service_name} timed out after {timeout}s (attempt {attempt})"
                self._log(f"✗ {msg}")
                _write_event_log("SERVICE_TIMEOUT", msg)
                log_lifecycle("SERVICE_INIT_TIMEOUT", f"Service: {service_name}, Attempt: {attempt}")
            else:
                self.service_status[service_name] = "RETRY" if attempt == 1 else "FAILED"
                msg = f"{service_name} error: {result} (attempt {attempt})"
                self._log(f"✗ {msg}")
                _write_event_log("DEPENDENCY_FAILURE", msg)
                log_lifecycle("SERVICE_INIT_FAILURE", f"Service: {service_name}, Attempt: {attempt}, Error: {result}")

            if attempt == 1:
                self._log(f"  → Retrying {service_name}...")

        self.service_status[service_name] = "FAILED"
        _write_event_log("DEPENDENCY_FAILURE", f"{service_name} failed after 2 attempts")
        log_lifecycle("SERVICE_INIT_ABORT", f"Service: {service_name} failed all startup attempts")
        return False

    def _run_with_timeout(self, service_name: str, timeout: float):
        """
        Run service instantiation in a worker thread with a hard timeout.
        Returns: True | "TIMEOUT" | error_string
        """
        exc_holder: list[str] = []

        def _target():
            try:
                instance = self._init_service_instance(service_name)
                self.services[service_name] = instance
            except Exception as exc:
                exc_holder.append(str(exc))

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_target)
            try:
                future.result(timeout=timeout)
            except FutureTimeoutError:
                return "TIMEOUT"
            except Exception as exc:
                return str(exc)

        return exc_holder[0] if exc_holder else True

    def _init_service_instance(self, service_name: str):
        """Import and instantiate the service engine for service_name."""
        root_dir = _ROOT_DIR
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        # Keep the resolved interpreter reference accessible for diagnostics.
        # No path logic lives here — resolution is owned by venv_resolver.
        _resolved_python = get_resolved_env().python_exe  # noqa: F841

        if service_name == "ai_router":
            from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

            return AIOrchestrator()
        elif service_name == "memory_engine":
            from memory_engine import MemoryEngine

            return MemoryEngine()
        elif service_name == "knowledge_graph":
            from knowledge_graph import ProductionKnowledgeGraph

            return ProductionKnowledgeGraph()
        elif service_name == "voice_engine":
            from JARVIS.core.voice.ses_motoru import VoiceEngine

            return VoiceEngine()
        elif service_name == "workflow_engine":
            import workflow_engine

            return workflow_engine
        elif service_name == "diagnostics":
            from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

            return DiagnosticsCenter()
        elif service_name == "automation_engine":
            from tool_manager import ToolManager

            return ToolManager()
        elif service_name == "plugin_manager":
            from plugin_manager import PluginManager

            pm = PluginManager()
            pm.discover_plugins()
            return pm
        else:
            raise ValueError(f"Unknown service: {service_name}")

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.startup_log.append(entry)
        # Also write to disk so pythonw.exe (no stdout) doesn't lose this
        _write_event_log("STARTUP_LOG", message)
        try:
            print(entry)
            sys.stdout.flush()
        except UnicodeEncodeError:
            # Fallback for CP1252 / non-UTF-8 consoles — strip or escape unencodable chars
            safe = entry.encode(sys.stdout.encoding or "ascii", errors="backslashreplace").decode(sys.stdout.encoding or "ascii")
            print(safe)
            sys.stdout.flush()
