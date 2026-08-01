"""
JARVIS Mission Control — Core Engine.

Coordinates dozens of active tasks simultaneously, schedules them based on priority
and dependencies, manages check-pointing/telemetry, and persists records.
"""

from __future__ import annotations

import os
import json
import time
import threading
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger
from JARVIS.core.system.dependency_manager import DependencyManager

logger = get_logger("mission_control")

# Priority maps (lower number = higher priority)
PRIORITY_MAP = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "background": 5
}


class MissionControl:
    """Task coordination registry and scheduling center."""

    _instance: MissionControl | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> MissionControl:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self) -> None:
        self.lock = threading.Lock()
        self.tasks: dict[str, dict[str, Any]] = {}
        self.persistence_path = os.path.abspath(os.path.join("logs", "mission_control_state.json"))
        self.memory_path = os.path.abspath(os.path.join("logs", "mission_control_memory.json"))
        
        os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
        self._load_state()

    def create_task(self, name: str, prompt: str, agent: str, dependencies: list[str] = None, priority: str = "medium") -> str:
        """Instantiate a new task in the registry."""
        with self.lock:
            task_id = f"TASK-{int(time.time() * 1000) % 1000000:06d}"
            self.tasks[task_id] = {
                "id": task_id,
                "name": name,
                "prompt": prompt,
                "agent": agent,
                "priority": priority.lower(),
                "progress": 0,
                "dependencies": dependencies or [],
                "status": "PENDING", # PENDING (QUEUED), ACTIVE (RUNNING), WAITING (AWAITING_APPROVAL), BLOCKED, COMPLETED, FAILED, CANCELLED
                "estimated_completion": "Pending schedule",
                "logs": [f"[{time.strftime('%H:%M:%S')}] Task created."],
                "created_at": time.time(),
                "started_at": None,
                "finished_at": None,
                "retries": 0,
                "telemetry": {
                    "execution_time": 0.0,
                    "failures": 0,
                    "retries": 0,
                    "model_used": "Claude 3.5 Sonnet",
                    "tools_used": [],
                    "cpu": 0.0,
                    "ram": 0.0
                }
            }
            self._save_state()
            logger.info("Mission Control registered task: %s (priority: %s)", task_id, priority)
            return task_id

    def log_task_event(self, task_id: str, message: str) -> None:
        """Append execution log to task."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {message}")
                self._save_state()

    def set_task_status(self, task_id: str, status: str) -> None:
        """Update task status and handle transitions."""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task["status"] = status
                if status == "ACTIVE" and not task["started_at"]:
                    task["started_at"] = time.time()
                elif status in ("COMPLETED", "FAILED", "CANCELLED"):
                    task["finished_at"] = time.time()
                    if task["started_at"]:
                        task["telemetry"]["execution_time"] = round(task["finished_at"] - task["started_at"], 2)
                self._save_state()

    def set_task_progress(self, task_id: str, progress: int) -> None:
        """Update task completion percentage."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["progress"] = max(0, min(100, progress))
                self._save_state()

    def get_running_summary(self) -> str:
        """Summary of active background tasks for voice logs."""
        with self.lock:
            active = [t for t in self.tasks.values() if t["status"] == "ACTIVE"]
            pending = [t for t in self.tasks.values() if t["status"] == "PENDING"]
        
        if not active and not pending:
            return "There are no background operations active or queued at this moment, sir."
            
        summary = "Active background tasks:\n"
        for t in active:
            summary += f"- {t['name']} (ID: {t['id']}, Progress: {t['progress']}%, Agent: {t['agent']})\n"
        if pending:
            summary += f"Pending queue contains {len(pending)} task(s)."
        return summary

    def get_failed_summary(self) -> str:
        """Summary of failed tasks."""
        with self.lock:
            failed = [t for t in self.tasks.values() if t["status"] == "FAILED"]
        if not failed:
            return "No task execution failures have been logged recently, sir."
        summary = "Recent failed tasks:\n"
        for t in failed:
            summary += f"- {t['name']} (ID: {t['id']}, Retries: {t['retries']})\n"
        return summary

    def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id]["status"] == "ACTIVE":
                self.tasks[task_id]["status"] = "BLOCKED"
                self.tasks[task_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Task paused by user request.")
                self._save_state()
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """Resume a blocked task."""
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id]["status"] == "BLOCKED":
                self.tasks[task_id]["status"] = "ACTIVE"
                self.tasks[task_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Task resumed by user request.")
                self._save_state()
                return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel execution of a task."""
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id]["status"] in ("ACTIVE", "PENDING"):
                self.tasks[task_id]["status"] = "CANCELLED"
                self.tasks[task_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Task cancelled by user request.")
                self._save_state()
                return True
        return False

    def get_sorted_queue(self) -> list[dict[str, Any]]:
        """Order tasks based on priorities and topologically sorted dependencies."""
        with self.lock:
            all_tasks = list(self.tasks.values())
        
        # Sort topologically first to respect dependencies
        order = DependencyManager.get_execution_order(all_tasks)
        order_index = {tid: idx for idx, tid in enumerate(order)}

        def sort_key(t: dict[str, Any]) -> tuple[int, int]:
            # Priority first, then topological order
            p_val = PRIORITY_MAP.get(t["priority"], 3)
            topo_val = order_index.get(t["id"], 999)
            return p_val, topo_val

        return sorted(all_tasks, key=sort_key)

    # ── Internal States & Persistence ─────────────────────────────────────────

    def _save_state(self) -> None:
        try:
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error("Failed to save Mission Control state: %s", e)

    def _load_state(self) -> None:
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                logger.error("Failed to load Mission Control state: %s", e)
