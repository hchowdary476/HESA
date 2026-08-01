"""JARVIS Tool SDK - Machine Learning training and dataset profiling tools."""

from __future__ import annotations
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult
from JARVIS.core.ml.ml_center import MLCenter

class MLTrainingTool(ToolBase):
    """Integrates MLCenter training sweeps and metrics evaluations."""

    def __init__(self) -> None:
        super().__init__("ML Training Tool", "1.0")
        self.ml_center = MLCenter()

    def validate(self, **kwargs) -> bool:
        return "dataset_name" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        dataset = kwargs.get("dataset_name", "")
        epochs = kwargs.get("epochs", 10)
        lr = kwargs.get("lr", 0.01)
        
        try:
            res = self.ml_center.train_model(dataset, {"epochs": epochs, "learning_rate": lr})
            return ToolResult(True, {"metrics": res.get("metrics", {}), "model_path": res.get("model_path", "")})
        except Exception as e:
            return ToolResult(False, None, f"ML training sweep error: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 400.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
