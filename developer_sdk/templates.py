"""Boilerplate templates for scaffolding JARVIS extensions."""

PLUGIN_TEMPLATE = """\"\"\"Custom Plugin Tool implementing ToolBase.\"\"\"

from __future__ import annotations
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class CustomPluginTool(ToolBase):
    def __init__(self) -> None:
        super().__init__(name="{name}", version="1.0.0")

    def initialize(self) -> bool:
        self.is_healthy = True
        return True

    def execute(self, **kwargs) -> ToolResult:
        import time
        t0 = time.time()
        self.run_count += 1
        
        # Implement custom execution logic
        param_value = kwargs.get("input_param", "default")
        output = f"Executed Custom Tool '{name}' with param: {{param_value}}"
        
        self.success_count += 1
        elapsed = (time.time() - t0) * 1000.0
        self.total_time_ms += elapsed
        return ToolResult(success=True, output=output, elapsed_ms=elapsed)

    def validate(self, **kwargs) -> bool:
        return True

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "is_healthy": self.is_healthy}

    def permissions(self) -> list[str]:
        return []

    def metrics(self) -> dict[str, Any]:
        return {
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_time_ms": self.total_time_ms
        }

    def shutdown(self) -> bool:
        return True
"""

WORKFLOW_TEMPLATE = """{{
  "name": "{name}",
  "nodes": [
    {{
      "id": "step_1",
      "description": "Initialize workflow node",
      "agent": "developer_agent",
      "tool": "git_tool",
      "dependencies": []
    }},
    {{
      "id": "step_2",
      "description": "Log execution data",
      "agent": "windows_system_agent",
      "tool": "clipboard_tool",
      "dependencies": ["step_1"]
    }}
  ],
  "metadata": {{
    "author": "JARVIS CLI Scaffolder"
  }}
}}
"""

AGENT_TEMPLATE = """\"\"\"Boilerplate agent skeleton structure.\"\"\"

class CustomAgent:
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role

    def process_task(self, prompt: str) -> str:
        return f"Agent [{self.role}] processed query: {{prompt}}"
"""

PROVIDER_TEMPLATE = """\"\"\"Boilerplate custom LLM model provider integration skeleton.\"\"\"

class CustomAIProvider:
    def __init__(self, name: str, api_key: str) -> None:
        self.name = name
        self.api_key = api_key

    def completions(self, prompt: str) -> str:
        return f"Response from custom provider {self.name} for prompt: {prompt}"
"""
