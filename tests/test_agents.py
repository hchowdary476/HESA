import json
import os
import shutil
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from JARVIS.agents.agent_base import AgentTask, AgentError
from JARVIS.agents.planner_agent import PlannerAgent
from JARVIS.agents.testing_agent import TestingAgent
from JARVIS.agents.task_queue import TaskQueue
from JARVIS.agents.orchestrator import AgentOrchestrator


class MultiAgentCoreTests(unittest.TestCase):

    def setUp(self):
        # Setup clean environment for each test
        self.test_log_dir = "test_agents_logs"
        os.makedirs(self.test_log_dir, exist_ok=True)
        self.patcher = patch("JARVIS.agents.task_queue._LOG_PATH", os.path.join(self.test_log_dir, "task_log.json"))
        self.mock_log_path = self.patcher.start()
        TaskQueue.clear()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir, ignore_errors=True)

    def test_task_queue_concurrency(self):
        """Test append_entry correctness under concurrent threads calling it rapidly."""
        num_threads = 10
        calls_per_thread = 20
        threads = []

        def worker(thread_idx):
            for i in range(calls_per_thread):
                TaskQueue.append_entry(
                    run_id="test_run",
                    agent=f"agent_{thread_idx}",
                    step=i,
                    input_text=f"input_{thread_idx}_{i}",
                    output_text=f"output_{thread_idx}_{i}",
                    elapsed_ms=10.5,
                    status="success",
                    model_used="mock_model"
                )

        for t_idx in range(num_threads):
            t = threading.Thread(target=worker, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        entries = TaskQueue.get_all()
        # Total appended entries should be num_threads * calls_per_thread
        self.assertEqual(len(entries), num_threads * calls_per_thread)

        # Assert no data corruption: JSON should load cleanly and fields must match
        for entry in entries:
            self.assertEqual(entry["run_id"], "test_run")
            self.assertEqual(entry["model_used"], "mock_model")
            self.assertEqual(entry["status"], "success")

    @patch("JARVIS.agents.agent_base.AgentBase._call_llm")
    def test_planner_agent_malformed_json_fallback(self, mock_call_llm):
        """Test PlannerAgent falls back to a single subtask on malformed JSON response."""
        # Mock _call_llm to return non-JSON text
        mock_call_llm.return_value = ("this is not json at all", 10, 50.0, "mock_model")

        agent = PlannerAgent()
        task = AgentTask(run_id="run_1", step=1, description="Create a calendar app")
        result = agent.run(task)

        # Assert status is success (due to fallback) and returns a list with 1 subtask
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.parsed), 1)
        self.assertEqual(result.parsed[0]["title"], "Implement request")
        self.assertEqual(result.parsed[0]["description"], "Create a calendar app")

    @patch("JARVIS.agents.agent_base.AgentBase._call_llm")
    def test_testing_agent_pass_fail(self, mock_call_llm):
        """Test TestingAgent correctly reports syntax pass/fail and LLM verdict."""
        # 1. Valid python syntax + LLM PASS
        mock_call_llm.return_value = (
            '{"verdict": "PASS", "issues": [], "suggestion": ""}',
            10, 50.0, "mock_model"
        )
        agent = TestingAgent()
        
        valid_code = "def get_time():\n    return '12:00'\n"
        task_pass = AgentTask(
            run_id="run_pass",
            step=1,
            description="Write a get_time function",
            context=valid_code,
            metadata={"subtask_title": "Time Subtask", "retry_count": 0}
        )
        result_pass = agent.run(task_pass)
        self.assertEqual(result_pass.status, "success")
        self.assertTrue(result_pass.parsed.passed)
        self.assertTrue(result_pass.parsed.syntax_ok)

        # 2. Syntax-broken code (py_compile should fail before LLM check is run)
        broken_code = "def get_time(\n    return '12:00'\n"
        task_fail_syntax = AgentTask(
            run_id="run_fail_syntax",
            step=1,
            description="Write a get_time function",
            context=broken_code,
            metadata={"subtask_title": "Time Subtask", "retry_count": 0}
        )
        result_fail_syntax = agent.run(task_fail_syntax)
        self.assertEqual(result_fail_syntax.status, "retry")
        self.assertFalse(result_fail_syntax.parsed.passed)
        self.assertFalse(result_fail_syntax.parsed.syntax_ok)
        self.assertIn("Syntax error", result_fail_syntax.parsed.errors)

    def test_orchestrator_concurrency_guard(self):
        """Test that calling run() concurrently returns busy status."""
        orch = AgentOrchestrator()
        
        # Lock AgentOrchestrator running state manually to simulate a running thread
        AgentOrchestrator._is_running = True
        try:
            result = orch.run("test task")
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["run_id"], "busy")
            self.assertIn("busy", result["final_output"])
        finally:
            AgentOrchestrator._is_running = False
