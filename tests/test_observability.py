"""Unit and integration tests for JARVIS Phase III Observability and diagnostics center."""

import unittest
from unittest.mock import MagicMock, patch
import json
from JARVIS.core.system.cognitive_core import CognitiveCore
from JARVIS.core.system.diagnostics_center import DiagnosticsCenter

class TestJARVISObservability(unittest.TestCase):
    """Test suite covering Phase III observability models and metrics."""

    def setUp(self) -> None:
        self.diagnostics = DiagnosticsCenter()
        self.diagnostics.reset()

    def test_timeline_profiling(self) -> None:
        """Verify timeline timings are recorded correctly for all 12 stages."""
        timings = {
            "intent_detection": 5.2,
            "context_retrieval": 12.4,
            "memory_lookup": 8.1,
            "goal_planning": 15.6,
            "agent_selection": 4.2,
            "ai_model_selection": 3.1,
            "tool_selection": 2.5,
            "safety_evaluation": 11.2,
            "execution": 120.5,
            "learning": 6.3,
            "memory_update": 14.2
        }
        self.diagnostics.record_timeline(timings)
        timeline = self.diagnostics.get_cognitive_timeline()
        self.assertEqual(timeline["intent_detection"], 5.2)
        self.assertEqual(timeline["execution"], 120.5)

    def test_agent_analytics(self) -> None:
        """Verify agent analytics returns enriched task metrics."""
        analytics = self.diagnostics.get_agent_analytics()
        self.assertGreater(len(analytics), 0)
        first_agent = analytics[0]
        self.assertIn("name", first_agent)
        self.assertIn("tasks_executed", first_agent)
        self.assertIn("success_rate", first_agent)

    def test_model_analytics(self) -> None:
        """Verify model performance logging and stats calculation."""
        self.diagnostics.record_model_query("Google", 110.0, 0.0012, 500, True)
        self.diagnostics.record_model_query("Google", 130.0, 0.0013, 600, True)
        
        analytics = self.diagnostics.get_model_analytics()
        google_stats = next(a for a in analytics if a["provider"] == "Google")
        self.assertEqual(google_stats["avg_latency_ms"], 120.0)
        self.assertEqual(google_stats["success_rate"], 100.0)

    def test_planner_metrics(self) -> None:
        """Verify planner DAG and execution metrics."""
        self.diagnostics.record_plan_stats(subtask_count=5, depth=4, parallel=3, planning_time_ms=30.0)
        self.diagnostics.record_task_outcome(success=True)
        self.diagnostics.record_task_outcome(success=False, rollback_triggered=True)
        
        planner = self.diagnostics.get_planner_analytics()
        self.assertEqual(planner["avg_dag_depth"], 4)
        self.assertEqual(planner["parallel_task_count"], 3)
        self.assertEqual(planner["rollback_count"], 1)

    def test_failure_reports(self) -> None:
        """Verify failure analysis report logging."""
        self.diagnostics.failures.clear()
        self.diagnostics.record_failure(
            stage="execution",
            agent="coding_agent",
            model="ChatGPT 4o",
            tool="linter",
            exception="SyntaxError: invalid syntax",
            rollback=True
        )
        failures = self.diagnostics.failures
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["failed_stage"], "execution")
        self.assertTrue(failures[0]["rollback_triggered"])

    def test_learning_metrics(self) -> None:
        """Verify learning event counts and frequencies."""
        self.diagnostics.record_learning_event("successful_workflow", "goal: Prepare workspace")
        self.diagnostics.record_learning_event("user_correction", "goal: Compile project")
        
        learning = self.diagnostics.get_learning_analytics()
        self.assertEqual(learning["user_corrections"], 1)
        self.assertIn("Prepare workspace", learning["frequent_goals"])

    def test_self_improvement_engine(self) -> None:
        """Verify heuristic-based recommendation builder suggestions."""
        recs = self.diagnostics.get_self_improvement_recommendations()
        self.assertGreater(len(recs), 0)
        self.assertIn("category", recs[0])
        self.assertIn("recommendation", recs[0])
