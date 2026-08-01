"""Global Unified Scheduler for the JARVIS AI Operating System."""

from __future__ import annotations
import queue
import threading
import time
import uuid
import logging
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_os.scheduler")


class ScheduledTask:
    """Represents a job managed by the GlobalScheduler."""

    def __init__(
        self,
        task_type: str,
        payload: dict[str, Any],
        priority: str = "MEDIUM",
        timeout: float = 30.0,
        callback: Callable[[dict[str, Any]], None] | None = None
    ) -> None:
        self.id = str(uuid.uuid4())
        self.task_type = task_type
        self.payload = payload
        self.priority = priority.upper()  # HIGH, MEDIUM, LOW
        self.timeout = timeout
        self.callback = callback
        self.created_at = time.time()
        self.status = "Pending"  # Pending, Running, Completed, Failed, Cancelled
        self.result: Any = None

    def get_priority_weight(self) -> int:
        """Determines the queue ordering logic. Lower weight values resolve first."""
        if self.priority == "HIGH":
            return 1
        if self.priority == "MEDIUM":
            return 2
        return 3

    def __lt__(self, other: ScheduledTask) -> bool:
        # Priority Queue orders by priority weight first, then creation time
        if self.get_priority_weight() != other.get_priority_weight():
            return self.get_priority_weight() < other.get_priority_weight()
        return self.created_at < other.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "status": self.status,
            "result": str(self.result) if self.result else None
        }


class GlobalScheduler:
    """Orchestrates AI tasks, background jobs, tool executions, and event timelines."""

    _instance: GlobalScheduler | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> GlobalScheduler:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, resource_manager: Any = None) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.resource_manager = resource_manager
        self.task_queue: queue.PriorityQueue[ScheduledTask] = queue.PriorityQueue()
        self.active_tasks: dict[str, ScheduledTask] = {}
        self.completed_history: list[ScheduledTask] = []
        self.lock = threading.Lock()
        self.running = False
        self.paused = False
        self.worker_thread: threading.Thread | None = None
        logger.info("Global Scheduler initialized.")

    def start(self) -> None:
        """Launches background orchestration loop."""
        self.running = True
        self.worker_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Global Scheduler worker thread active.")

    def stop(self) -> None:
        """Shuts down scheduler loop."""
        self.running = False
        # Feed dummy task to wake up queue get if blocked
        self.task_queue.put(ScheduledTask("SHUTDOWN", {}))
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        logger.info("Global Scheduler stopped.")

    def pause(self) -> None:
        """Temporarily suspends executing tasks in queue."""
        self.paused = True
        logger.info("Global Scheduler paused.")

    def resume(self) -> None:
        """Resumes scheduler task execution."""
        self.paused = False
        logger.info("Global Scheduler resumed.")

    def schedule_task(
        self,
        task_type: str,
        payload: dict[str, Any],
        priority: str = "MEDIUM",
        timeout: float = 30.0,
        callback: Callable[[dict[str, Any]], None] | None = None
    ) -> str:
        """Pushes a task into the priority queue."""
        task = ScheduledTask(task_type, payload, priority, timeout, callback)
        with self.lock:
            self.active_tasks[task.id] = task
        self.task_queue.put(task)
        logger.info(f"Scheduled task {task.id} (Type: {task_type}, Priority: {priority})")
        return task.id

    def cancel_task(self, task_id: str) -> bool:
        """Marks a task as Cancelled to prevent execution if still in queue."""
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status in ["Pending", "Running"]:
                    task.status = "Cancelled"
                    logger.info(f"Cancelled task {task_id}")
                    return True
        return False

    def get_queue_status(self) -> dict[str, Any]:
        """Provides status mapping of scheduled and recently executed tasks."""
        with self.lock:
            active = [t.to_dict() for t in self.active_tasks.values() if t.status in ["Pending", "Running"]]
            history = [t.to_dict() for t in self.completed_history[-50:]]
            return {
                "queue_depth": self.task_queue.qsize(),
                "paused": self.paused,
                "active_tasks": active,
                "completed_history": history
            }

    def _scheduler_loop(self) -> None:
        """Task fetching and dispatcher worker execution loop."""
        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue

            try:
                task = self.task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if task.task_type == "SHUTDOWN":
                self.task_queue.task_done()
                break

            with self.lock:
                if task.status == "Cancelled":
                    self.task_queue.task_done()
                    continue
                task.status = "Running"

            # Telemetry checks for low-priority execution delay
            if task.priority == "LOW" and self.resource_manager:
                if not self.resource_manager.is_system_idle():
                    logger.info(f"Host under heavy load. Deferring low-priority task {task.id}...")
                    time.sleep(1.0)  # Add minor backoff delay
                    self.task_queue.put(task)  # Re-enqueue
                    self.task_queue.task_done()
                    continue

            # Process the task asynchronously
            threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()

    def _execute_task(self, task: ScheduledTask) -> None:
        """Handles task execution with timeout bounds."""
        execution_thread = threading.Thread(target=self._run_task_payload, args=(task,))
        execution_thread.start()
        execution_thread.join(timeout=task.timeout)

        if execution_thread.is_alive():
            logger.warning(f"Task {task.id} timed out after {task.timeout}s.")
            task.status = "Failed"
            task.result = "TimeoutError"
        
        # Move task to completed history
        with self.lock:
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            self.completed_history.append(task)
            if len(self.completed_history) > 500:
                self.completed_history.pop(0)

        # Trigger callback if set
        if task.callback:
            try:
                task.callback(task.to_dict())
            except Exception as e:
                logger.error(f"Error executing callback for task {task.id}: {e}")

        self.task_queue.task_done()

    def _run_task_payload(self, task: ScheduledTask) -> None:
        """Executes actual workload logic based on task_type."""
        try:
            # Simulate or route task execution based on registry
            # Real applications will hook workflows, tool runs, or AI prompts here
            task_type = task.task_type
            payload = task.payload
            
            if task_type == "AI_REQUEST":
                # Mock or delegate to CognitiveCore / Router
                logger.info(f"Processing AI Request via scheduler: {payload.get('command')}")
                # Simulate small latency
                time.sleep(0.5)
                task.result = {"response": "AI request processed successfully by scheduler."}
                task.status = "Completed"
                
            elif task_type == "TOOL_EXECUTION":
                logger.info(f"Processing Tool execution via scheduler: {payload.get('tool')}")
                time.sleep(0.2)
                task.result = {"success": True, "output": "Tool execution result."}
                task.status = "Completed"
                
            elif task_type == "WORKFLOW_TASK":
                logger.info(f"Processing Workflow node: {payload.get('node')}")
                time.sleep(0.4)
                task.result = {"node_status": "Completed"}
                task.status = "Completed"
                
            elif task_type == "BACKGROUND_JOB":
                # E.g. memory garbage cleanup
                logger.info(f"Running Background maintenance task: {payload.get('job_name')}")
                if self.resource_manager:
                    self.resource_manager.optimize_resources()
                else:
                    gc.collect()
                task.result = {"cleaned": True}
                task.status = "Completed"
                
            else:
                # Catch-all
                logger.info(f"Executing generic task block: {task_type}")
                task.status = "Completed"
                task.result = "Success"
                
        except Exception as e:
            logger.error(f"Error in task payload run: {e}")
            task.status = "Failed"
            task.result = str(e)
