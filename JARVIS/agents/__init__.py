"""JARVIS Multi-Agent Core — Phase 1.

Exposes the 4-agent pipeline:
  PlannerAgent → CodingAgent → TestingAgent → ReviewAgent

Public API:
    from JARVIS.agents import AgentOrchestrator
    result = AgentOrchestrator().run("add a button that shows current time")
"""

from __future__ import annotations

from JARVIS.agents.orchestrator import AgentOrchestrator
from JARVIS.agents.task_queue import TaskQueue

__all__ = ["AgentOrchestrator", "TaskQueue"]
