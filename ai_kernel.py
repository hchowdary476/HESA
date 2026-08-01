"""AI OS Kernel - The central runtime and synapses coordinator for JARVIS."""

from __future__ import annotations
import threading
import time
import os
import logging
from typing import Any
from cryptography.fernet import Fernet

# Imports from new OS modules
from event_bus import EventBus
from resource_manager import ResourceManager
from scheduler import GlobalScheduler
from knowledge_services import KnowledgeServices
from api_gateway import ApiGateway

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_os.kernel")


class AIKernel:
    """The central core runtime orchestration class for the Enterprise AI OS."""

    _instance: AIKernel | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> AIKernel:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.running = False
        self.lock = threading.Lock()
        
        # Security: Cryptographic secret manager
        self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)
        self.encrypted_secrets: dict[str, bytes] = {}
        self.role_permissions = {
            "admin": ["*"],
            "operator": ["execute_tool", "trigger_workflow", "query_rag"],
            "user": ["query_rag"]
        }

        # Subsystems references
        self.event_bus = EventBus()
        self.resource_manager = ResourceManager()
        self.scheduler = GlobalScheduler(resource_manager=self.resource_manager)
        self.knowledge = KnowledgeServices()
        self.api_gateway = ApiGateway()
        
        # Legacy/Core module imports (lazy loaded to prevent circular imports)
        self.cognitive_core = None
        self.plugin_manager = None
        self.tool_manager = None
        
        logger.info("Enterprise AI OS Kernel initialized.")

    def start(self) -> None:
        """Starts all operating system components in coordinate order."""
        with self.lock:
            if self.running:
                return
            self.running = True
            
            logger.info("Starting AI OS Kernel Synapse...")

            # 1. Initialize Event Bus TCP bridging
            self.event_bus.start_tcp_bridge(as_server=True)

            # 2. Start Resource Telemetry
            self.resource_manager.start_monitoring(self.event_bus)

            # 3. Start Global Scheduler
            self.scheduler.start()

            # 4. Bind listener to Event Bus to publish events through API stream gateway
            self.event_bus.subscribe("*", self._broadcast_event_to_gateway)

            # 5. Start API Gateway (REST + Streaming sockets)
            self.api_gateway.start(self)

            # 6. Initialize connections with legacy modules
            self._link_legacy_modules()

            # 7. Start autonomous background maintenance timer loop
            threading.Thread(target=self._run_maintenance_jobs, daemon=True).start()

            logger.info("AI OS Kernel successfully started and online.")
            self.event_bus.publish("KernelStarted", {"status": "ONLINE", "timestamp": time.time()})

    def stop(self) -> None:
        """Gracefully halts all components and threads."""
        with self.lock:
            if not self.running:
                return
            self.running = False
            
            logger.info("Initiating AI OS Kernel shutdown...")
            self.event_bus.publish("KernelShutdown", {"status": "SHUTDOWN", "timestamp": time.time()})
            
            self.api_gateway.stop()
            self.scheduler.stop()
            self.resource_manager.stop_monitoring()
            self.event_bus.clear()
            self.knowledge.clear()
            
            logger.info("AI OS Kernel offline.")

    def _link_legacy_modules(self) -> None:
        """Safely links with existing modules to ensure backwards compatibility."""
        try:
            from JARVIS.core.system.cognitive_core import CognitiveCore
            self.cognitive_core = CognitiveCore()
            logger.info("Linked with Cognitive Core module.")
        except Exception as e:
            logger.warning(f"Could not load CognitiveCore: {e}")

        try:
            from plugin_manager import PluginManager
            self.plugin_manager = PluginManager()
            logger.info("Linked with Plugin Manager module.")
        except Exception as e:
            logger.warning(f"Could not load PluginManager: {e}")

        try:
            from tool_manager import ToolManager
            self.tool_manager = ToolManager()
            logger.info("Linked with Tool Manager module.")
        except Exception as e:
            logger.warning(f"Could not load ToolManager: {e}")

    def optimize_ai_route(self, prompt: str, latency_threshold_ms: float = 1500.0) -> dict[str, Any]:
        """Automatically decides routing logic (local vs cloud) based on cost, load, latency, length."""
        prompt_len = len(prompt)
        system_load = self.resource_manager.get_resource_usage()
        
        # Decision matrix
        route_decision = {
            "provider": "local",
            "model": "ollama/llama3",
            "reason": "Default offline fallback route.",
            "cost_est": 0.0
        }

        # Check network availability
        has_network = system_load["network"]["bytes_recv"] > 0 or system_load["network"]["bytes_sent"] > 0
        
        if not has_network:
            route_decision = {
                "provider": "local",
                "model": "ollama/llama3",
                "reason": "Host offline, forcing local inference execution.",
                "cost_est": 0.0
            }
        elif prompt_len > 4000:
            route_decision = {
                "provider": "cloud",
                "model": "gemini-1.5-pro",
                "reason": "Large context length requirement, routed to Gemini.",
                "cost_est": 0.005
            }
        elif system_load["cpu"] > 80.0:
            route_decision = {
                "provider": "cloud",
                "model": "groq/llama3",
                "reason": "Local CPU overloaded, offloading inference to Groq.",
                "cost_est": 0.0001
            }
        elif latency_threshold_ms < 1000.0:
            route_decision = {
                "provider": "cloud",
                "model": "groq/llama3",
                "reason": "Ultra-low latency required, routed to Groq API.",
                "cost_est": 0.0001
            }
        else:
            route_decision = {
                "provider": "local",
                "model": "ollama/llama3",
                "reason": "Host conditions optimal, utilizing free local model.",
                "cost_est": 0.0
            }

        logger.info(f"AI Router decided optimization path: {route_decision['model']} ({route_decision['reason']})")
        self.event_bus.publish("ModelSwitched", route_decision)
        return route_decision

    def process_api_command(self, command: str, priority: str = "MEDIUM") -> str:
        """Schedules commands received from the REST gateway."""
        task_id = self.scheduler.schedule_task(
            task_type="AI_REQUEST",
            payload={"command": command},
            priority=priority,
            callback=self._on_command_task_finished
        )
        self.event_bus.publish("VoiceRecognized", {"command": command, "task_id": task_id, "priority": priority})
        return task_id

    def check_permission(self, role: str, action: str) -> bool:
        """Enforces security role limits."""
        permissions = self.role_permissions.get(role.lower(), [])
        if "*" in permissions or action in permissions:
            return True
        return False

    def store_secret(self, key_name: str, raw_secret: str) -> None:
        """Encrypts and caches sensitive credential entries (API keys)."""
        encrypted = self.cipher_suite.encrypt(raw_secret.encode("utf-8"))
        self.encrypted_secrets[key_name] = encrypted
        logger.info(f"Stored encrypted secret: {key_name}")

    def retrieve_secret(self, key_name: str) -> str | None:
        """Decrypts and returns secret values."""
        encrypted = self.encrypted_secrets.get(key_name)
        if encrypted:
            return self.cipher_suite.decrypt(encrypted).decode("utf-8")
        return None

    def get_system_status(self) -> dict[str, Any]:
        """Collects OS status block mapping."""
        metrics = self.resource_manager.get_resource_usage()
        sched_stats = self.scheduler.get_queue_status()
        
        status = {
            "kernel_status": "ONLINE" if self.running else "OFFLINE",
            "host_metrics": metrics,
            "queue_depth": sched_stats["queue_depth"],
            "active_tasks_count": len(sched_stats["active_tasks"]),
            "historical_tasks_count": len(sched_stats["completed_history"]),
            "uptime_sec": time.time() - metrics["timestamp"] if self.running else 0.0,
            "registered_vocab": self.knowledge.vocab_size()
        }
        return status

    def _broadcast_event_to_gateway(self, event: dict[str, Any]) -> None:
        """Routes published events directly down REST stream channels."""
        self.api_gateway.broadcast_event_to_clients(event["event_type"], event["payload"])

    def _on_command_task_finished(self, task_dict: dict[str, Any]) -> None:
        """Event handler callback when scheduled commands resolve."""
        logger.info(f"Task completed: {task_dict['id']}")
        self.event_bus.publish("ToolCompleted", {
            "task_id": task_dict["id"],
            "type": task_dict["task_type"],
            "status": task_dict["status"],
            "result": task_dict["result"]
        })

    def _run_maintenance_jobs(self) -> None:
        """Periodically triggers maintenance runs during host idle states."""
        while self.running:
            try:
                # Check every 10 seconds for maintenance tasks
                if self.resource_manager.is_system_idle():
                    logger.info("Host idle. Scheduling autonomous maintenance job...")
                    self.scheduler.schedule_task(
                        task_type="BACKGROUND_JOB",
                        payload={"job_name": "ResourceCleanup"},
                        priority="LOW"
                    )
            except Exception as e:
                logger.error(f"Error in background maintenance trigger: {e}")
            time.sleep(10.0)
