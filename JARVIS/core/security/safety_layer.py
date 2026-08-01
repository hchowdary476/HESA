"""AI Safety Layer - Rate limiting, confirmation checks, tool restrictions, and rollback support."""

from __future__ import annotations
import os
import time
import json
import shutil
import logging
from collections import deque
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("safety_layer")

class AISafetyLayer:
    """Enforces safety restrictions, confirmation prompts, rate limits, and rollbacks."""

    _instance: AISafetyLayer | None = None

    def __new__(cls, *args, **kwargs) -> AISafetyLayer:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.rate_limit_window = 60.0  # 1 minute window
        self.max_requests_per_window = 15
        self.request_timestamps: deque[float] = deque()
        self.rollback_history: list[dict] = []
        self.safe_mode_enabled = False
        self.audit_log_path = os.path.join("logs", "safety_audit.json")
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

    def set_safe_mode(self, enabled: bool) -> None:
        """Toggle safe execution mode (restricts any script run/deletion)."""
        self.safe_mode_enabled = enabled
        logger.info("Safe mode set to %s", enabled)
        self.log_safety_event("safe_mode_toggle", {"enabled": enabled})

    def is_rate_limited(self) -> bool:
        """Check if AI requests exceed rate limits."""
        now = time.time()
        # Clean expired timestamps
        while self.request_timestamps and now - self.request_timestamps[0] > self.rate_limit_window:
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.max_requests_per_window:
            logger.warning("Rate limit exceeded! Request count: %d", len(self.request_timestamps))
            return True

        self.request_timestamps.append(now)
        return False

    def needs_confirmation(self, action: str, params: dict) -> tuple[bool, str]:
        """Determine if an action requires confirmation."""
        sensitive_actions = {
            "shutdown", "restart", "sleep", "lock_screen",
            "delete_file", "prune_memory", "write_settings",
            "git_push", "deployment", "apk_signing", "publishing"
        }
        
        # Check command run inputs for safety critical phrases
        cmd = str(params.get("command", "") or params.get("cmd", "") or "").lower()
        action_lower = action.lower()

        # Check for deleting files, git push, deployment, apk signing, publishing, restart, shutdown
        if action_lower in sensitive_actions:
            return True, f"Action '{action}' is marked sensitive."

        if "git push" in cmd:
            return True, "Operation 'git push' requires user approval."
        if "deploy" in cmd or "deployment" in cmd:
            return True, "Operation 'deployment' requires user approval."
        if "apk" in cmd or "sign" in cmd:
            return True, "Operation 'APK signing' requires user approval."
        if "publish" in cmd:
            return True, "Operation 'publishing' requires user approval."
        if "shutdown" in cmd:
            return True, "Operation 'shutdown' requires user approval."
        if "restart" in cmd or "reboot" in cmd:
            return True, "Operation 'restart' requires user approval."
        if "rm " in cmd or "del " in cmd or "rmdir" in cmd:
            return True, "Operation 'delete files' requires user approval."
            
        if self.safe_mode_enabled:
            return True, "Safe mode is active; all operations require confirmation."
            
        # Dangerous params checks
        if action in ("open_app", "run_cmd"):
            app = params.get("app", "").lower()
            dangerous_keywords = {"regedit", "format", "del", "rmdir", "rm ", "setup", "install"}
            if any(keyword in app or keyword in cmd for keyword in dangerous_keywords):
                return True, f"Dangerous command or application match detected: {app or cmd}."

        return False, ""

    def log_safety_event(self, event_type: str, details: dict) -> None:
        """Log safety checks/actions to audit file."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details
        }
        try:
            events = []
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    events = json.load(f)
            events.append(event)
            # Cap at last 500 audit logs
            if len(events) > 500:
                events = events[-500:]
            with open(self.audit_log_path, "w", encoding="utf-8") as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            logger.error("Failed to write safety audit log: %s", e)

    def create_rollback_point(self, file_path: str, action_desc: str) -> str | None:
        """Create a backup of a file before modifying it."""
        if not os.path.exists(file_path):
            return None
            
        backup_dir = os.path.join("logs", "backups", "safety_rollbacks")
        os.makedirs(backup_dir, exist_ok=True)
        backup_name = f"rollback_{int(time.time())}_{os.path.basename(file_path)}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            shutil.copy2(file_path, backup_path)
            rollback_id = f"R-{int(time.time())}"
            self.rollback_history.append({
                "id": rollback_id,
                "timestamp": time.time(),
                "file_path": os.path.abspath(file_path),
                "backup_path": os.path.abspath(backup_path),
                "description": action_desc
            })
            self.log_safety_event("rollback_point_created", {"file": file_path, "id": rollback_id})
            return rollback_id
        except Exception as e:
            logger.error("Failed to create rollback backup: %s", e)
            return None

    def rollback(self, rollback_id: str) -> bool:
        """Restore a file from a rollback point."""
        for entry in self.rollback_history:
            if entry["id"] == rollback_id:
                try:
                    shutil.copy2(entry["backup_path"], entry["file_path"])
                    self.log_safety_event("rollback_executed", {"id": rollback_id})
                    logger.info("Rollback successful for ID %s", rollback_id)
                    return True
                except Exception as e:
                    logger.error("Rollback execution failed: %s", e)
                    return False
        return False
