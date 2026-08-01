"""Workflow History for JARVIS - Records execution runs and aggregates performance statistics."""

from __future__ import annotations
import os
import json
import time
from typing import Any
from workflow_engine import Workflow

class WorkflowHistory:
    """Manages locally persisted execution records and runs performance analytics."""

    _instance: WorkflowHistory | None = None

    def __new__(cls, *args, **kwargs) -> WorkflowHistory:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.history_path = os.path.abspath(os.path.join("logs", "workflow_history.json"))
        self.runs: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    self.runs = json.load(f)
            except Exception:
                self.runs = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.runs, f, indent=2)
        except Exception:
            pass

    def record_run(self, wf: Workflow) -> None:
        """Append workflow run record details."""
        run_record = {
            "name": wf.name,
            "timestamp": time.time(),
            "status": wf.status,
            "steps_count": len(wf.nodes),
            "completed_steps": sum(1 for n in wf.nodes.values() if n.status == "Completed"),
            "failed_steps": sum(1 for n in wf.nodes.values() if n.status == "Failed"),
            "rolled_back_steps": sum(1 for n in wf.nodes.values() if n.status == "Rolled Back"),
            "steps": [n.to_dict() for n in wf.nodes.values()]
        }
        self.runs.append(run_record)
        self.save()

        # Log to ProductionKnowledgeGraph
        try:
            from knowledge_graph import ProductionKnowledgeGraph
            kg = ProductionKnowledgeGraph()
            wf_run_id = f"wf_run_{int(run_record['timestamp'])}"
            kg.add_node(wf_run_id, "WORKFLOW", wf.name, {"status": wf.status})
            
            for node in wf.nodes.values():
                step_node_id = f"wf_step_{node.id}_{int(run_record['timestamp'])}"
                kg.add_node(step_node_id, "TASK", node.description, {
                    "agent": node.agent, 
                    "tool": node.tool, 
                    "status": node.status
                })
                kg.add_edge(wf_run_id, step_node_id, "USES")
                
                for dep in node.dependencies:
                    dep_node_id = f"wf_step_{dep}_{int(run_record['timestamp'])}"
                    kg.add_edge(step_node_id, dep_node_id, "DEPENDS_ON")
        except Exception:
            pass

    def get_analytics(self) -> dict[str, Any]:
        """Aggregate execution metrics across all runs."""
        total = len(self.runs)
        if total == 0:
            return {"success_rate": 100.0, "total_runs": 0, "failures": 0, "retries": 0, "rollback_frequency": 0}
            
        successes = sum(1 for r in self.runs if r["status"] == "Completed")
        failures = sum(1 for r in self.runs if r["status"] in ["Failed", "Rolled Back"])
        
        return {
            "total_runs": total,
            "success_rate": round((successes / total) * 100.0, 1),
            "failures": failures,
            "retries": sum(r["failed_steps"] for r in self.runs),
            "rollback_frequency": sum(r["rolled_back_steps"] for r in self.runs)
        }
