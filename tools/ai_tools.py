"""JARVIS Tool SDK - AI LLM Query and routing tools."""

from __future__ import annotations
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult
from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator

class LLMQueryTool(ToolBase):
    """Integrates multi-model query and reasoning routing capabilities."""

    def __init__(self) -> None:
        super().__init__("LLM Query Tool", "1.0")
        self.orchestrator = AIOrchestrator()

    def validate(self, **kwargs) -> bool:
        return "prompt" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        prompt = kwargs.get("prompt", "")
        provider = kwargs.get("provider")
        model = kwargs.get("model")
        
        try:
            if provider and model:
                # Custom selection overrides
                self.orchestrator.active_ai = provider
                self.orchestrator.active_model = model
            
            res = self.orchestrator.query_with_failover(prompt)
            return ToolResult(True, {"response": res, "provider": self.orchestrator.active_ai, "model": self.orchestrator.active_model})
        except Exception as e:
            return ToolResult(False, None, f"Orchestrator query error: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["network"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 180.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
