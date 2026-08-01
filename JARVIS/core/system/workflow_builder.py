"""AI Workflow Builder - Evaluates DAGs of agent executions and triggers."""

from __future__ import annotations
import json
import logging
from typing import Any
from JARVIS.core.ai_router.multi_agent_system import AgentManager
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("workflow_builder")

class WorkflowBuilder:
    """Orchestrates structured DAGs of tasks (workflows) loaded from configurations."""

    _instance: WorkflowBuilder | None = None

    def __new__(cls, *args, **kwargs) -> WorkflowBuilder:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.workflows: dict[str, dict[str, Any]] = {}
        self._load_default_workflows()

    def _load_default_workflows(self) -> None:
        # Load a default visual-voice feedback workflow
        self.workflows["voice_command_loop"] = {
            "name": "Voice Command Pipeline",
            "nodes": [
                {"id": "node_input", "type": "trigger", "value": "Voice Input"},
                {"id": "node_intent", "type": "action", "agent": "general_assistant", "prompt": "Detect Intent"},
                {"id": "node_reason", "type": "action", "agent": "coding_agent", "prompt": "Synthesize reasoning"},
                {"id": "node_execute", "type": "action", "agent": "automation_agent", "prompt": "Execute action"},
                {"id": "node_memory", "type": "action", "agent": "learning_agent", "prompt": "Update memory profile"}
            ],
            "connections": [
                {"from": "node_input", "to": "node_intent"},
                {"from": "node_intent", "to": "node_reason"},
                {"from": "node_reason", "to": "node_execute"},
                {"from": "node_execute", "to": "node_memory"}
            ]
        }

    def register_workflow(self, name: str, nodes: list, connections: list) -> str:
        """Register a visual drag-and-drop workflow configuration."""
        workflow_id = f"WF-{name.lower().replace(' ', '_')}"
        self.workflows[workflow_id] = {
            "name": name,
            "nodes": nodes,
            "connections": connections
        }
        logger.info("Registered visual workflow '%s' (ID: %s).", name, workflow_id)
        return workflow_id

    def execute_workflow(self, workflow_id: str, input_value: str) -> None:
        """Run the registered workflow step-by-step."""
        wf = self.workflows.get(workflow_id)
        if not wf:
            logger.error("Workflow %s not found.", workflow_id)
            return

        logger.info("Executing workflow '%s' with input: '%s'", wf["name"], input_value)
        agent_mgr = AgentManager()
        
        # Sequentially evaluate nodes mapping enqueued intents
        for node in wf["nodes"]:
            if node["type"] == "trigger":
                continue
            agent_key = node["agent"]
            prompt = f"{node['prompt']} related to {input_value}"
            agent = agent_mgr.get_agent(agent_key)
            if agent:
                agent.add_task(f"WF-TASK-{node['id']}", prompt)
