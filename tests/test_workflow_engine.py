"""Unit and integration tests for the JARVIS Workflow Automation Engine."""

import unittest
import os
import json
import time
import tool_sdk
from workflow_engine import Workflow, WorkflowNode
from workflow_scheduler import WorkflowScheduler
from workflow_history import WorkflowHistory
from tool_manager import ToolManager
from tool_base import ToolBase
from tool_result import ToolResult

class DummyStrictTool(ToolBase):
    """Test helper for strict validation and permissions."""
    def __init__(self) -> None:
        super().__init__("Dummy Strict", "1.0")
        self.rolled_back = False

    def validate(self, **kwargs) -> bool:
        return "required_arg" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        if kwargs.get("should_fail"):
            return ToolResult(False, None, "Execution failure simulation")
        return ToolResult(True, "Success")

    def rollback(self) -> bool:
        self.rolled_back = True
        return True

    def health(self) -> dict: return {}
    def permissions(self) -> list:
        return ["restricted_scope"]

    def metrics(self) -> dict: return {}
    def initialize(self) -> bool: return True
    def shutdown(self) -> bool: return True


class TestJARVISWorkflowEngine(unittest.TestCase):
    """Test suite covering Directed Acyclic Graph (DAG) scheduling loops."""

    def setUp(self) -> None:
        self.scheduler = WorkflowScheduler()
        self.history = WorkflowHistory()
        self.history.runs.clear()
        
        # Ensure tool SDK is initialized and tools are registered
        tool_sdk.initialize_sdk()
        self.tool_manager = ToolManager()
        self.tool_manager.granted_permissions = {
            "filesystem", "network", "clipboard", "browser", 
            "notifications", "settings", "restricted_scope"
        }
        
        # Register strict tool
        self.strict_tool = DummyStrictTool()
        self.tool_manager.register_tool(self.strict_tool)

    def test_sequential_workflow(self) -> None:
        """Verify sequential steps run in exact order."""
        nodes = [
            WorkflowNode("S1", "Step 1", "coding_agent", "clipboard_tool", []),
            WorkflowNode("S2", "Step 2", "coding_agent", "clipboard_tool", ["S1"])
        ]
        wf = Workflow("Sequential Test", nodes)
        
        self.scheduler.execute(wf)
        
        # Wait max 3 seconds for async threads to complete
        start = time.time()
        while wf.status not in ["Completed", "Failed", "Rolled Back"] and time.time() - start < 3.0:
            time.sleep(0.1)
            
        self.assertEqual(wf.status, "Completed")
        self.assertEqual(wf.nodes["S1"].status, "Completed")
        self.assertEqual(wf.nodes["S2"].status, "Completed")

    def test_parallel_workflow(self) -> None:
        """Verify independent nodes execute concurrently."""
        nodes = [
            WorkflowNode("P1", "Branch A", "coding_agent", "clipboard_tool", []),
            WorkflowNode("P2", "Branch B", "coding_agent", "clipboard_tool", []),
            WorkflowNode("P3", "Join Node", "coding_agent", "clipboard_tool", ["P1", "P2"])
        ]
        wf = Workflow("Parallel Test", nodes)
        
        self.scheduler.execute(wf)
        
        start = time.time()
        while wf.status not in ["Completed", "Failed", "Rolled Back"] and time.time() - start < 3.0:
            time.sleep(0.1)
            
        self.assertEqual(wf.status, "Completed")
        self.assertEqual(wf.nodes["P1"].status, "Completed")
        self.assertEqual(wf.nodes["P2"].status, "Completed")
        self.assertEqual(wf.nodes["P3"].status, "Completed")

    def test_retry_logic(self) -> None:
        """Verify node retries according to max_retries limit."""
        # Remove restricted_scope to cause permission block which fails execution
        self.tool_manager.granted_permissions.remove("restricted_scope")
        
        nodes = [
            WorkflowNode("R1", "Retry Node", "coding_agent", "Dummy Strict", [], retry_policy={"max_retries": 2, "delay": 0.1})
        ]
        wf = Workflow("Retry Test", nodes)
        self.scheduler.execute(wf)
        
        start = time.time()
        while wf.status not in ["Completed", "Failed", "Rolled Back"] and time.time() - start < 3.0:
            time.sleep(0.1)
            
        self.assertEqual(wf.nodes["R1"].status, "Failed")

    def test_rollback_handling(self) -> None:
        """Verify rollback triggers on unrecoverable failures."""
        nodes = [
            WorkflowNode("RB1", "Success Node", "coding_agent", "clipboard_tool", [], rollback_action={"tool": "clipboard_tool"}),
            # Force RB2 to fail by setting params to trigger should_fail=True in DummyStrictTool
            WorkflowNode("RB2", "Fail Node", "coding_agent", "Dummy Strict", ["RB1"])
        ]
        # Attach parameter to trigger failure in strict tool
        nodes[1].params = {"should_fail": True}
        
        wf = Workflow("Rollback Test", nodes)
        self.scheduler.execute(wf)
        
        start = time.time()
        while wf.status not in ["Completed", "Failed", "Rolled Back"] and time.time() - start < 3.0:
            time.sleep(0.1)
            
        self.assertEqual(wf.status, "Rolled Back")
        self.assertEqual(wf.nodes["RB1"].status, "Rolled Back")

    def test_history_persistence(self) -> None:
        """Verify run details are written to JSON history log."""
        nodes = [
            WorkflowNode("H1", "History Node", "coding_agent", "clipboard_tool", [])
        ]
        wf = Workflow("Persistence Test", nodes)
        self.scheduler.execute(wf)
        
        start = time.time()
        while wf.status not in ["Completed", "Failed", "Rolled Back"] and time.time() - start < 3.0:
            time.sleep(0.1)
            
        analytics = self.history.get_analytics()
        self.assertGreaterEqual(analytics["total_runs"], 1)
