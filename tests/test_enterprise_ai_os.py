"""Unit and integration tests for Phase V Enterprise AI Operating System."""

from __future__ import annotations
import os
import json
import time
import socket
import unittest
import requests
from unittest.mock import patch, MagicMock

# Import new AI OS elements
from event_bus import EventBus
from resource_manager import ResourceManager
from scheduler import GlobalScheduler, ScheduledTask
from knowledge_services import KnowledgeServices
from api_gateway import ApiGateway
from ai_kernel import AIKernel


class TestEventBus(unittest.TestCase):
    def setUp(self) -> None:
        self.eb = EventBus()
        self.eb.clear()

    def tearDown(self) -> None:
        self.eb.clear()

    def test_local_pub_sub(self) -> None:
        """Test event subscription and async callback publishing."""
        received = []
        def _callback(payload):
            received.append(payload)

        self.eb.subscribe("TestEvent", _callback)
        self.eb.publish("TestEvent", {"data": 123})
        
        # Give small window for async thread dispatch
        time.sleep(0.1)
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["data"], 123)

    def test_wildcard_subscription(self) -> None:
        """Test wildcard subscriber captures all event types."""
        received = []
        def _wildcard_callback(payload):
            received.append(payload)

        self.eb.subscribe("*", _wildcard_callback)
        self.eb.publish("EventA", {"a": 1})
        self.eb.publish("EventB", {"b": 2})
        
        time.sleep(0.1)
        
        self.assertEqual(len(received), 2)

    def test_event_history(self) -> None:
        """Verify published events list is properly cached in history."""
        self.eb.publish("EventA", {"a": 1})
        self.eb.publish("EventB", {"b": 2})
        
        history = self.eb.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["event_type"], "EventA")
        self.assertEqual(history[1]["event_type"], "EventB")


class TestResourceManager(unittest.TestCase):
    def setUp(self) -> None:
        self.rm = ResourceManager()

    def test_resource_metrics(self) -> None:
        """Verify telemetry gathers valid system metrics."""
        metrics = self.rm.get_resource_usage()
        
        self.assertIn("cpu", metrics)
        self.assertIn("ram", metrics)
        self.assertIn("disk", metrics)
        self.assertIn("threads", metrics)
        self.assertIn("gpu", metrics)
        self.assertTrue(metrics["cpu"] >= 0.0)
        self.assertTrue(metrics["ram"] >= 0.0)
        self.assertTrue(metrics["disk"] >= 0.0)

    def test_idle_limits(self) -> None:
        """Verify system idle status returns boolean value."""
        idle = self.rm.is_system_idle()
        self.assertIsInstance(idle, bool)

    def test_resource_optimization(self) -> None:
        """Test resource optimizer triggers gc and metrics update."""
        res = self.rm.optimize_resources()
        self.assertTrue(res["garbage_collected"])


class TestGlobalScheduler(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = GlobalScheduler()
        self.scheduler.start()

    def tearDown(self) -> None:
        self.scheduler.stop()

    def test_priority_ordering(self) -> None:
        """Verify priority tasks resolve by priority weight (HIGH > MEDIUM > LOW)."""
        t1 = ScheduledTask("TEST", {}, "LOW")
        t2 = ScheduledTask("TEST", {}, "HIGH")
        t3 = ScheduledTask("TEST", {}, "MEDIUM")
        
        # Test comparison operators used by PriorityQueue
        self.assertTrue(t2 < t3)  # HIGH < MEDIUM (Priority value 1 < 2)
        self.assertTrue(t3 < t1)  # MEDIUM < LOW (Priority value 2 < 3)

    def test_task_scheduling_and_cancellation(self) -> None:
        """Test task enqueuing, cancel command, and processing status updates."""
        t_id = self.scheduler.schedule_task("AI_REQUEST", {"command": "test scheduler"}, "HIGH")
        
        # Verify status exists
        status = self.scheduler.get_queue_status()
        self.assertGreaterEqual(len(status["active_tasks"]), 0)
        
        # Test cancellation
        cancelled = self.scheduler.cancel_task(t_id)
        self.assertTrue(cancelled)


class TestKnowledgeServices(unittest.TestCase):
    def setUp(self) -> None:
        self.ks = KnowledgeServices()
        self.ks.clear()

    def tearDown(self) -> None:
        self.ks.clear()

    def test_document_indexing_and_search(self) -> None:
        """Test indexing document strings and searching matching query text."""
        self.ks.add_document("doc1", "The quick brown fox jumps over the lazy dog.")
        self.ks.add_document("doc2", "Artificial Intelligence is shifting host architecture.")
        
        # Exact keyword search matches
        res = self.ks.semantic_search("artificial intelligence", top_k=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "doc2")
        self.assertTrue(res[0]["score"] > 0.0)

    def test_ranked_context_prompts(self) -> None:
        """Verify context generation includes parsed source identifiers."""
        self.ks.add_document("doc1", "Fast boot profile minimizes local boot timeouts.")
        ctx = self.ks.get_ranked_context("boot timeout")
        self.assertIn("Fast boot profile", ctx)
        self.assertIn("Source [doc1]", ctx)


class TestApiGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ApiGateway._instance = None
        cls.kernel = AIKernel()
        cls.gateway = ApiGateway(port=0)
        cls.gateway.start(cls.kernel)
        cls.port = cls.gateway.port
        
        # Wait for the HTTP server to be responsive
        for _ in range(100):
            try:
                res = requests.get(f"http://127.0.0.1:{cls.port}/api/v1/health", timeout=2.0)
                if res.status_code == 200:
                    break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.gateway.stop()
        ApiGateway._instance = None

    def test_health_endpoint(self) -> None:
        """REST GET /api/v1/health should bypass API Key authorization checks."""
        res = requests.get(f"http://127.0.0.1:{self.port}/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "HEALTHY")

    def test_unauthorized_endpoints(self) -> None:
        """REST paths other than /health should block requests lacking valid API Keys."""
        res = requests.get(f"http://127.0.0.1:{self.port}/api/v1/status")
        self.assertEqual(res.status_code, 401)

    def test_authorized_endpoints(self) -> None:
        """REST paths should accept queries containing valid Bearer headers."""
        headers = {"Authorization": "Bearer jarvis_secret_key"}
        res = requests.get(f"http://127.0.0.1:{self.port}/api/v1/status", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("kernel_status", data)

    def test_command_scheduling_endpoint(self) -> None:
        """REST POST /api/v1/command schedules input commands."""
        headers = {
            "Authorization": "Bearer jarvis_secret_key",
            "Content-Type": "application/json"
        }
        res = requests.post(
            f"http://127.0.0.1:{self.port}/api/v1/command",
            headers=headers,
            json={"command": "explain system latency", "priority": "HIGH"}
        )
        self.assertEqual(res.status_code, 202)
        data = res.json()
        self.assertEqual(data["status"], "Accepted")
        self.assertIn("task_id", data)


class TestAIKernel(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = AIKernel()

    def test_secret_encryption_flow(self) -> None:
        """Test encryption/decryption validation loops of sensitive key storage."""
        self.kernel.store_secret("TEST_OPENAI_KEY", "sk-1234567890abcdef")
        val = self.kernel.retrieve_secret("TEST_OPENAI_KEY")
        self.assertEqual(val, "sk-1234567890abcdef")

    def test_role_based_permissions(self) -> None:
        """Verify operator permissions are strictly enforced against role checks."""
        self.assertTrue(self.kernel.check_permission("admin", "any_action"))
        self.assertTrue(self.kernel.check_permission("operator", "execute_tool"))
        self.assertFalse(self.kernel.check_permission("user", "execute_tool"))

    def test_ai_router_optimizer(self) -> None:
        """Verify model routing rules switch providers depending on context lengths."""
        # Query short prompt
        route_short = self.kernel.optimize_ai_route("hi", latency_threshold_ms=500.0)
        self.assertEqual(route_short["provider"], "cloud")
        self.assertEqual(route_short["model"], "groq/llama3")
        
        # Query long context prompt
        route_long = self.kernel.optimize_ai_route("a" * 5000)
        self.assertEqual(route_long["provider"], "cloud")
        self.assertEqual(route_long["model"], "gemini-1.5-pro")


if __name__ == "__main__":
    unittest.main()
