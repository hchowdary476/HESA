"""Personal Learning Engine - Learns application habits, working hours, and commands to predict needs."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("learning_engine")


class PersonalLearningEngine:
    """Tracks system interactions and learns user habits over time to offer recommendations."""

    _instance: PersonalLearningEngine | None = None

    def __new__(cls, *args, **kwargs) -> PersonalLearningEngine:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.learning_data_path = os.path.abspath(os.path.join("logs", "learning_data.json"))
        self.history: list[dict] = []
        self.load()

    def load(self) -> None:
        """Load user event history from disk."""
        if os.path.exists(self.learning_data_path):
            try:
                with open(self.learning_data_path, encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.error("Failed to load learning data: %s", e)
                self.history = []
        else:
            self.history = []

    def save(self) -> None:
        """Save history back to logs."""
        os.makedirs(os.path.dirname(self.learning_data_path), exist_ok=True)
        try:
            with open(self.learning_data_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error("Failed to save learning data: %s", e)

    def log_interaction(self, command: str, action: str, params: dict, success: bool = True) -> None:
        """Record an interaction for routine and preference mapping."""
        event = {
            "timestamp": time.time(),
            "time_str": datetime.now().isoformat(),
            "hour": datetime.now().hour,
            "command": command,
            "action": action,
            "params": params,
            "success": success,
        }
        self.history.append(event)
        # Cap at last 2000 events to prevent massive disk bloat
        if len(self.history) > 2000:
            self.history = self.history[-2000:]
        self.save()

    def get_frequent_apps(self) -> list[tuple[str, int]]:
        """Get the most frequently opened applications."""
        apps = [event["params"].get("app") for event in self.history if event["action"] == "open_app" and event["params"].get("app")]
        return Counter(apps).most_common(5)

    def get_frequent_commands(self) -> list[tuple[str, int]]:
        """Get the most common raw text commands."""
        cmds = [event["command"] for event in self.history if event.get("command")]
        return Counter(cmds).most_common(5)

    def get_working_hours(self) -> tuple[int, int]:
        """Estimate user working hours (start_hour, end_hour) based on interaction clusters."""
        hours = [event["hour"] for event in self.history]
        if not hours:
            return (9, 18)  # Default: 9 AM to 6 PM
        c = Counter(hours)
        active_hours = sorted(c.keys())
        if not active_hours:
            return (9, 18)
        return (active_hours[0], active_hours[-1])

    def generate_suggestions(self) -> list[dict[str, str]]:
        """Generate recommendations based on frequent actions or temporal routines."""
        suggestions = []

        # 1. App-based suggestions
        freq_apps = self.get_frequent_apps()
        if freq_apps:
            top_app = freq_apps[0][0]
            suggestions.append(
                {
                    "type": "routine",
                    "title": f"Launch {top_app.title()}",
                    "why": f"You launch {top_app.title()} frequently, sir. Would you like me to create an automatic shortcut?",
                    "command": f"open {top_app}",
                }
            )

        # 2. Time-of-day suggestions
        current_hour = datetime.now().hour
        working_start, working_end = self.get_working_hours()

        # Morning routine trigger
        if working_start <= current_hour < working_start + 2:
            suggestions.append(
                {
                    "type": "routine",
                    "title": "Morning Dev Setup",
                    "why": "It's the start of your usual work hours, sir. Shall I prepare your development environment?",
                    "command": "prepare my development environment",
                }
            )

        # 3. Model preference
        models = [event["params"].get("model") for event in self.history if event.get("params") and "model" in event["params"]]
        if models:
            fav_model = Counter(models).most_common(1)[0][0]
            if fav_model:
                suggestions.append(
                    {
                        "type": "preference",
                        "title": f"Lock {fav_model} Model",
                        "why": f"You prefer utilizing {fav_model} for queries. Shall I set it as the primary system-wide model?",
                        "command": f"use model {fav_model}",
                    }
                )

        # Default fallback recommendations if history is sparse
        if not suggestions:
            suggestions.append(
                {
                    "type": "tip",
                    "title": "System Audit Check",
                    "why": "Sir, running a regular health check helps detect performance bottlenecks early.",
                    "command": "run health check",
                }
            )
            suggestions.append(
                {
                    "type": "tip",
                    "title": "Security Log Review",
                    "why": "A quick scan of active system connections is recommended to keep your network secure.",
                    "command": "audit cybersecurity logs",
                }
            )

        return suggestions
