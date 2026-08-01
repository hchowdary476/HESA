"""Unit and integration tests for JARVIS AI Operating System (AI OS 3.0)."""

import os
import json
import time
import unittest
from unittest.mock import patch, MagicMock

from JARVIS.core.system.cognitive_core import CognitiveCore
from JARVIS.core.security.safety_layer import AISafetyLayer
from JARVIS.core.memory.knowledge_graph import KnowledgeGraph
from JARVIS.core.learning.learning_engine import PersonalLearningEngine
from JARVIS.core.system.predictive_intelligence import PredictiveIntelligence
from JARVIS.core.ai_router.multi_agent_system import AgentManager
from JARVIS.core.system.task_planner import TaskPlanner
from JARVIS.core.system.workflow_builder import WorkflowBuilder
from JARVIS.core.ml.ml_center import MLCenter


class TestAIOSCore(unittest.TestCase):
    def setUp(self) -> None:
        self.safety = AISafetyLayer()
        self.kg = KnowledgeGraph()
        self.learning = PersonalLearningEngine()
        self.predictor = PredictiveIntelligence()
        self.agent_mgr = AgentManager()
        self.planner = TaskPlanner()
        self.workflow = WorkflowBuilder()
        self.ml = MLCenter()

        # Use test database locations to avoid polluting production logs
        self.safety.audit_log_path = os.path.abspath("logs/test_safety_audit.json")
        self.kg.graph_path = os.path.abspath("logs/test_knowledge_graph.json")
        self.learning.learning_data_path = os.path.abspath("logs/test_learning_data.json")
        self.predictor.prediction_path = os.path.abspath("logs/test_predictions.json")
        self.ml.experiments_path = os.path.abspath("logs/test_experiments.json")

    def tearDown(self) -> None:
        # Clean up files created during testing
        for p in [
            self.safety.audit_log_path,
            self.kg.graph_path,
            self.learning.learning_data_path,
            self.predictor.prediction_path,
            self.ml.experiments_path
        ]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def test_cognitive_core_routing(self) -> None:
        """Test Cognitive Core request coordinator routing."""
        core = CognitiveCore()
        
        # Mock orchestrator failover query
        with patch.object(core.orchestrator, "query_with_failover", return_value="Test response from AI OS."):
            res = core.process_request("hello jarvis")
            self.assertIn("response", res)
            self.assertEqual(res["response"], "Test response from AI OS.")
            self.assertIn("explanation", res)
            self.assertEqual(res["explanation"]["confidence"], 0.98)

    def test_safety_rate_limiting_and_confirmation(self) -> None:
        """Test rate limit checks, sensitive action triggers, and file rollback creation."""
        self.safety.request_timestamps.clear()
        
        # Test rate limiting enqueues (threshold is 15)
        for _ in range(15):
            self.assertFalse(self.safety.is_rate_limited())
        self.assertTrue(self.safety.is_rate_limited())

        # Reset rate limit timestamps for other tests
        self.safety.request_timestamps.clear()

        # Sensitive action confirmation checks
        confirm, reason = self.safety.needs_confirmation("shutdown", {})
        self.assertTrue(confirm)
        self.assertIn("sensitive", reason)

        confirm_safe, _ = self.safety.needs_confirmation("talk", {})
        self.assertFalse(confirm_safe)

        # Rollback point test
        test_file = "logs/test_dummy_file.txt"
        with open(test_file, "w") as f:
            f.write("Original content")
        
        r_id = self.safety.create_rollback_point(test_file, "Pre-test backup")
        self.assertIsNotNone(r_id)
        
        # Modify file
        with open(test_file, "w") as f:
            f.write("Modified content")
            
        # Rollback
        success = self.safety.rollback(r_id)
        self.assertTrue(success)
        
        with open(test_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "Original content")
        
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_knowledge_graph(self) -> None:
        """Test entity addition and search traversal inside Knowledge Graph."""
        self.kg.add_node("note_1", "note", "Project Alpha Launch", {"content": "Launch timeline is set."})
        self.kg.add_node("task_1", "task", "Prepare setup", {"status": "pending"})
        self.kg.add_edge("note_1", "task_1", "depends_on")

        # Query Node
        node = self.kg.get_node("note_1")
        self.assertIsNotNone(node)
        self.assertEqual(node["label"], "Project Alpha Launch")

        # Semantic Search
        res = self.kg.semantic_search("timeline")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "note_1")

        # Relationship retrieval
        related = self.kg.get_related_nodes("note_1")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0][0]["label"], "Prepare setup")

    def test_predictive_intelligence(self) -> None:
        """Test linear trend metric forecasting and alerts generation."""
        # Feed decreasing battery levels to trigger depletion alert
        for i in range(10):
            self.predictor.add_metrics(
                cpu=15.0,
                ram=30.0,
                disk=40.0,
                battery=80.0 - (5.0 * i),  # steep drop
                net_kbps=10.0
            )
        
        preds = self.predictor.get_predictions()
        self.assertIn("alerts", preds)
        self.assertTrue(len(preds["alerts"]) > 0)
        self.assertEqual(preds["alerts"][0]["metric"], "battery")

    def test_multi_agent_loops(self) -> None:
        """Test Agent manager routing, tasks enqueuing, and health telemetry."""
        agent_key = self.agent_mgr.route_command("write a python script to parse logs")
        self.assertEqual(agent_key, "coding_agent")

        agent = self.agent_mgr.get_agent(agent_key)
        self.assertIsNotNone(agent)
        
        # Enqueue task
        task_report = None
        def _callback(r):
            nonlocal task_report
            task_report = r

        agent.add_task("test-task-1", "write a hello world script", _callback)
        agent.execute_next_task()

        self.assertIsNotNone(task_report)
        self.assertTrue(task_report["success"])
        self.assertIn("Completed task", task_report["result"])

    def test_task_planner_and_workflows(self) -> None:
        """Test task decomposition planner and workflow execution."""
        plan_id = self.planner.create_plan("Prepare my development environment")
        self.assertIsNotNone(plan_id)
        
        plan = self.planner.get_plan_status(plan_id)
        self.assertEqual(len(plan["subtasks"]), 4)
        self.assertEqual(plan["status"], "QUEUED")

        # Execute Plan
        self.planner.execute_plan(plan_id)
        # Verify planner enqueued tasks correctly
        plan_updated = self.planner.get_plan_status(plan_id)
        self.assertEqual(plan_updated["status"], "RUNNING")

        # Test workflow builder config
        self.assertIn("voice_command_loop", self.workflow.workflows)
        self.workflow.execute_workflow("voice_command_loop", "music")

    def test_ml_center(self) -> None:
        """Test Model Hub benchmarks and simulated parameter sweeps."""
        # Benchmark Ollama
        bench = self.ml.run_benchmark("ollama")
        self.assertIn("results", bench)
        self.assertEqual(bench["results"]["status"], "LOCAL_FAST")

        # Train model
        sweep = self.ml.train_model("system_telemetry", {"epochs": 15, "learning_rate": 0.05})
        self.assertIn("metrics", sweep)
        self.assertTrue(sweep["metrics"]["r2_score"] > 0.8)
        self.assertEqual(len(self.ml.get_experiments()), 1)


if __name__ == "__main__":
    unittest.main()
