"""Workflow Engine for JARVIS - Directed Acyclic Graph (DAG) workflow model definitions."""

from __future__ import annotations
import json
from typing import Any

class WorkflowNode:
    """Represents a single step in a DAG workflow, detailing tool execution, dependencies, and rollbacks."""

    def __init__(self, node_id: str, description: str, agent: str, tool: str, dependencies: list[str],
                 retry_policy: dict | None = None, rollback_action: dict | None = None, timeout: float = 30.0,
                 estimated_duration: float = 2.0, success_condition: str = "") -> None:
        self.id = node_id
        self.description = description
        self.agent = agent
        self.tool = tool
        self.dependencies = dependencies
        self.retry_policy = retry_policy or {"max_retries": 1, "delay": 1.0}
        self.rollback_action = rollback_action
        self.timeout = timeout
        self.estimated_duration = estimated_duration
        self.success_condition = success_condition
        self.status = "Pending"  # Pending, Ready, Running, Waiting, Completed, Failed, Rolled Back, Cancelled, Timed Out

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "agent": self.agent,
            "tool": self.tool,
            "dependencies": self.dependencies,
            "retry_policy": self.retry_policy,
            "rollback_action": self.rollback_action,
            "timeout": self.timeout,
            "estimated_duration": self.estimated_duration,
            "success_condition": self.success_condition,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowNode:
        node = cls(
            node_id=data["id"],
            description=data["description"],
            agent=data["agent"],
            tool=data["tool"],
            dependencies=data["dependencies"],
            retry_policy=data.get("retry_policy"),
            rollback_action=data.get("rollback_action"),
            timeout=data.get("timeout", 30.0),
            estimated_duration=data.get("estimated_duration", 2.0),
            success_condition=data.get("success_condition", "")
        )
        node.status = data.get("status", "Pending")
        return node


class Workflow:
    """DAG wrapper representing a sequence of nodes linked by execution dependencies."""

    def __init__(self, name: str, nodes: list[WorkflowNode], metadata: dict | None = None) -> None:
        self.name = name
        self.nodes = {n.id: n for n in nodes}
        self.metadata = metadata or {}
        self.status = "Pending"  # Pending, Running, Completed, Failed, Rolled Back, Cancelled

    def to_json(self) -> str:
        return json.dumps({
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "metadata": self.metadata,
            "status": self.status
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> Workflow:
        data = json.loads(json_str)
        nodes = [WorkflowNode.from_dict(n) for n in data["nodes"]]
        wf = cls(data["name"], nodes, data.get("metadata"))
        wf.status = data.get("status", "Pending")
        return wf
