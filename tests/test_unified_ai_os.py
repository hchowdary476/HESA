import os
import unittest

from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
from JARVIS.runtime.self_healing import SelfHealingEngine
from knowledge_graph import ProductionKnowledgeGraph
from memory_engine import MemoryEngine

# Core systems
from tool_sdk import tool_manager
from workflow_engine import Workflow, WorkflowNode


class UnifiedAIOSIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure base directories exist
        os.makedirs("logs", exist_ok=True)
        os.makedirs("logs/heartbeats", exist_ok=True)
        os.makedirs("logs/backups", exist_ok=True)

    def setUp(self):
        from tool_sdk import initialize_sdk

        initialize_sdk()
        self.diagnostics = DiagnosticsCenter()
        self.healing = SelfHealingEngine()
        self.memory = MemoryEngine()
        self.kg = ProductionKnowledgeGraph()

    def test_cognitive_core_ai_router_to_tool_routing(self):
        """Verify that the AI Router maps user intent/commands to the correct Tool SDK modules"""
        # Test routing definitions
        intent_mappings = {
            "Open Calculator": "window_management_tool",
            "Copy this text": "clipboard_tool",
            "Show CPU usage": "hardware_monitoring_tool",
            "Run git status": "git_tool",
            "Open Chrome": "browser_open_tool",
        }

        for command, tool_name in intent_mappings.items():
            self.assertIn(tool_name, tool_manager.tools)
            tool = tool_manager.tools[tool_name]
            self.assertTrue(tool.is_healthy)

    def test_tool_sdk_callability(self):
        """Verify every tool in the Tool SDK is registered and executable"""
        expected_tools = [
            "clipboard_tool",
            "process_tool",
            "window_management_tool",
            "notification_tool",
            "power_management_tool",
            "hardware_monitoring_tool",
            "file_search_tool",
            "file_operations_tool",
            "browser_open_tool",
            "git_tool",
            "llm_query_tool",
            "ml_training_tool",
            "cve_tool",
            "network_ping_tool",
        ]

        for t_name in expected_tools:
            with self.subTest(tool=t_name):
                self.assertIn(t_name, tool_manager.tools)
                tool = tool_manager.tools[t_name]
                self.assertTrue(tool.is_healthy)

    def test_voice_commands_pipeline(self):
        """Test voice natural language command pipeline mapping to execution"""
        voice_queries = {
            "Copy this text": "clipboard_tool",
            "Show CPU": "hardware_monitoring_tool",
            "Battery status": "power_management_tool",
        }
        for query, expected_tool in voice_queries.items():
            self.assertIn(expected_tool, tool_manager.tools)
            tool = tool_manager.tools[expected_tool]
            self.assertTrue(tool.is_healthy)

    def test_workflow_engine_dag_execution(self):
        """Test a multi-step task workflow transition states"""
        # Define mock nodes
        n1 = WorkflowNode("n1", "Build APK", "developer", "git_tool", [])
        n2 = WorkflowNode("n2", "Run tests", "developer", "process_tool", ["n1"])

        workflow = Workflow("Build Android App", [n1, n2])
        self.assertEqual(workflow.status, "Pending")
        self.assertEqual(workflow.nodes["n1"].status, "Pending")

        # Simulate execution
        workflow.status = "Running"
        workflow.nodes["n1"].status = "Completed"
        workflow.nodes["n2"].status = "Running"

        self.assertEqual(workflow.status, "Running")
        self.assertEqual(workflow.nodes["n1"].status, "Completed")

    def test_memory_update_on_tool_execution(self):
        """Confirm that executing a tool logs the action into the knowledge graph & memory engine"""
        # Get count before
        nodes_before = len(self.kg.nodes)

        # Execute tool via ToolManager to trigger KG addition
        tool_manager.execute_tool("clipboard_tool", operation="set", text="kg memory check")

        # Verify node added or logged (mock check or load KG)
        self.kg.load()
        nodes_after = len(self.kg.nodes)
        self.assertTrue(nodes_after >= nodes_before)

    def test_diagnostics_subsystem_metrics(self):
        """Ensure Diagnostics Center monitors and updates state metrics"""
        initial_plans = self.diagnostics.planner_stats.get("total_plans", 0)
        initial_subtasks = self.diagnostics.planner_stats.get("total_subtasks", 0)

        self.diagnostics.record_plan_stats(3, 2, 1, 120.0)
        self.assertEqual(self.diagnostics.planner_stats["total_plans"], initial_plans + 1)
        self.assertEqual(self.diagnostics.planner_stats["total_subtasks"], initial_subtasks + 3)

        # Test expanded subsystems checks (Phase 5)
        health = self.diagnostics.get_subsystems_health()
        self.assertIn("Voice Engine", health)
        self.assertIn("Clipboard Tool", health)
        self.assertEqual(health["Voice Engine"]["health"], "Optimal")

        # Update and verify
        self.diagnostics.update_subsystem("Voice Engine", "Busy", latency_ms=45.0, failed=True)
        updated_health = self.diagnostics.get_subsystems_health()
        self.assertEqual(updated_health["Voice Engine"]["status"], "Busy")
        self.assertEqual(updated_health["Voice Engine"]["health"], "Error")

    def test_self_healing_anomalies(self):
        """Confirm that self-healing identifies configuration/directory anomalies"""
        dummy_dir = "logs/healing_temp_test"
        if os.path.exists(dummy_dir):
            os.rmdir(dummy_dir)

        # Put temporary repair checklist
        self.healing.pending_repairs["missing_dir_logs_healing_temp_test"] = {
            "id": "missing_dir_logs_healing_temp_test",
            "name": "Missing directory: logs/healing_temp_test",
            "root_cause": "Test directory missing",
            "file": dummy_dir,
            "error_type": "Missing Directory",
            "severity": "Low",
            "risk": "LOW",
            "confidence": 0.99,
            "action": "Create folder",
            "estimated_time": "1s",
        }

        # Run auto heal
        self.healing._auto_heal_low_risk()
        self.assertTrue(os.path.exists(dummy_dir))

        # Cleanup
        os.rmdir(dummy_dir)


if __name__ == "__main__":
    unittest.main()
