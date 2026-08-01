"""Unit and integration tests for JARVIS Distributed AI Platform (Phase VI)."""

import os
import json
import time
import unittest
import requests
import shutil
import socket
from unittest.mock import patch, MagicMock

from cloud_sync import CloudSyncManager
from distributed_memory import DistributedMemory
from ai_fabric import AIFabric
from service_mesh import AIServiceMesh
from remote_api import RemoteGateway
import developer_cli


class TestDistributedPlatform(unittest.TestCase):
    def setUp(self) -> None:
        # Clear all singletons for clean, independent test executions
        CloudSyncManager().clear()
        DistributedMemory().clear()
        AIFabric().clear()
        AIServiceMesh().clear()

        self.test_dir = os.path.abspath("test_sandbox")
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self) -> None:
        # Clear singletons again
        CloudSyncManager().clear()
        DistributedMemory().clear()
        AIFabric().clear()
        AIServiceMesh().clear()

        # Sweep test sandbox
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except Exception:
                pass

    def test_cloud_sync_offline_first(self) -> None:
        """Test LWW conflict resolution, queuing, and online synchronization loops."""
        sync = CloudSyncManager()
        self.assertFalse(sync.is_online())

        # Push change while offline
        v1 = sync.push_local_change("config:theme", "dark-violet")
        self.assertEqual(v1, 1)
        self.assertEqual(sync.get_value("config:theme"), "dark-violet")
        self.assertEqual(len(sync.offline_queue), 1)

        # Trigger second change offline
        v2 = sync.push_local_change("config:theme", "neon-glass")
        self.assertEqual(v2, 2)
        self.assertEqual(sync.get_value("config:theme"), "neon-glass")
        self.assertEqual(len(sync.offline_queue), 2)

        # Pre-seed Cloud state with a conflicting version (lower version)
        sync.cloud_store["config:theme"] = {
            "value": "plain-blue",
            "version": 1,
            "timestamp": time.time() - 10.0
        }

        # Toggle online status (which automatically runs sync_online)
        sync.set_online_status(True)
        self.assertTrue(sync.is_online())
        self.assertEqual(len(sync.offline_queue), 0)

        # Verify Cloud accepted the newer local LWW value
        self.assertEqual(sync.cloud_store["config:theme"]["value"], "neon-glass")
        self.assertEqual(sync.cloud_store["config:theme"]["version"], 2)

    def test_cloud_sync_lww_conflict(self) -> None:
        """Test that newer Cloud values are pulled down to local storage during sync."""
        sync = CloudSyncManager()
        
        # Pre-seed newer cloud value
        sync.cloud_store["config:theme"] = {
            "value": "remote-cloud-theme",
            "version": 10,
            "timestamp": time.time()
        }

        # Set local state to older version
        sync.local_store["config:theme"] = {
            "value": "old-local-theme",
            "version": 2,
            "timestamp": time.time() - 20.0
        }

        # Set online (runs sync)
        sync.set_online_status(True)

        # Local store should pull down the newer cloud version
        self.assertEqual(sync.get_value("config:theme"), "remote-cloud-theme")
        self.assertEqual(sync.get_version("config:theme"), 10)

    def test_distributed_memory_federation(self) -> None:
        """Test writing to federated memory scopes automatically propagates to Cloud Sync."""
        mem = DistributedMemory()
        
        # Write to non-federated layer
        success_session = mem.write_memory("session", "temp_token", "abc")
        self.assertTrue(success_session)
        self.assertEqual(mem.read_memory("session", "temp_token"), "abc")
        
        # Sync store should be untouched for session layer
        self.assertIsNone(mem.sync_manager.get_value("mem:session:temp_token"))

        # Write to federated layer (long-term)
        success_lt = mem.write_memory("long_term", "user_nickname", "JarvisMaster")
        self.assertTrue(success_lt)
        self.assertEqual(mem.read_memory("long_term", "user_nickname"), "JarvisMaster")

        # Sync store should have the value queued
        self.assertEqual(mem.sync_manager.get_value("mem:long_term:user_nickname"), "JarvisMaster")

    def test_ai_fabric_encrypted_messaging(self) -> None:
        """Test encryption routing and multi-node workflow execution DAG loop."""
        fabric = AIFabric()
        
        # Register nodes
        fabric.register_node("node-desktop", "DESKTOP", "ONLINE")
        fabric.register_node("node-mobile", "MOBILE", "ONLINE")
        
        # Assert active listing
        nodes = fabric.get_nodes()
        self.assertEqual(len(nodes), 2)
        
        # Test encrypted messaging routing
        success = fabric.send_message(
            target_node_id="node-mobile",
            sender_id="node-desktop",
            msg_type="TELEMETRY",
            payload={"cpu": 15, "ram": 40}
        )
        self.assertTrue(success)

    def test_ai_fabric_workflow_checkpoints(self) -> None:
        """Test workflow interruption saves checkpoints and resumes correctly."""
        fabric = AIFabric()
        
        fabric.register_node("node-desktop", "DESKTOP", "ONLINE")
        fabric.register_node("node-laptop", "LAPTOP", "OFFLINE")  # Offline!
        
        steps = [
            {"node_id": "node-desktop", "action": "Generate Report"},
            {"node_id": "node-laptop", "action": "Compile Codebase"}
        ]
        
        # Run workflow
        res = fabric.distribute_workflow("wf-999", steps)
        
        # Should interrupt because node-laptop is offline
        self.assertEqual(res["status"], "INTERRUPTED")
        self.assertEqual(res["last_completed_step"], 0)
        self.assertIn("wf-999", fabric.checkpoints)
        
        # Turn node-laptop ONLINE
        fabric.register_node("node-laptop", "LAPTOP", "ONLINE")
        
        # Resume workflow
        res_resume = fabric.resume_workflow("wf-999")
        self.assertEqual(res_resume["status"], "COMPLETED")
        self.assertEqual(len(res_resume["history"]), 2)

    def test_service_mesh_routing_strategies(self) -> None:
        """Test Service Mesh round-robin, least-latency, and cost-priority routing."""
        mesh = AIServiceMesh()
        
        # Check standard pre-seeded list is present
        self.assertIn("gemini", mesh.providers)
        self.assertIn("chatgpt", mesh.providers)
        self.assertIn("ollama", mesh.providers)
        
        # Verify Ollama is cheapest (cost = 0) and deepseek is cheapest remote
        cheapest = mesh.route_request("hello", strategy="cost-priority")
        self.assertIn(cheapest, ["ollama", "lm_studio"])

        # Update last latencies to see routing changes
        mesh.providers["gemini"].last_latency = 100.0
        mesh.providers["chatgpt"].last_latency = 400.0
        mesh.providers["claude"].last_latency = 800.0
        
        # Set all others offline to isolate fastest remote provider
        for p in mesh.providers.values():
            if p.name not in ["gemini", "chatgpt", "claude"]:
                p.online = False

        fastest = mesh.route_request("hello", strategy="least-latency")
        self.assertEqual(fastest, "gemini")

    def test_service_mesh_failover_execution(self) -> None:
        """Test failover sequence logic when preferred provider goes offline."""
        mesh = AIServiceMesh()
        
        # Set all online providers offline except local Ollama fallback
        for name, p in mesh.providers.items():
            if name != "ollama":
                p.online = False
                
        # Ollama is the only online node
        res = mesh.failover_execute("test prompt", strategy="least-latency")
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "ollama")
        
        # Now fail Ollama as well
        mesh.providers["ollama"].online = False
        
        # Loop attempts fallback to ollama even if offline
        res_fail = mesh.failover_execute("test prompt")
        # Ollama fails since online is false (simulating actual backend connection failure)
        self.assertFalse(res_fail["success"])

    def test_remote_api_gateway_integration(self) -> None:
        """Test dynamic gateway port binding, OAuth authentication tokens, and REST calls."""
        # Use port 0 to bind dynamically to an ephemeral port
        gateway = RemoteGateway(host="127.0.0.1", port=0)
        gateway.start()
        
        try:
            port = gateway.port
            self.assertGreater(port, 0)
            
            # 1. Access public health route
            res_health = requests.get(f"http://127.0.0.1:{port}/api/v1/health")
            self.assertEqual(res_health.status_code, 200)
            self.assertEqual(res_health.json()["status"], "HEALTHY")

            # 2. Access authenticated route with no credentials -> 401
            res_no_auth = requests.get(f"http://127.0.0.1:{port}/api/v1/nodes")
            self.assertEqual(res_no_auth.status_code, 401)

            # 3. Retrieve OAuth Bearer Token
            res_token = requests.post(
                f"http://127.0.0.1:{port}/oauth/token",
                json={
                    "client_id": "jarvis_client",
                    "client_secret": "jarvis_secret"
                }
            )
            self.assertEqual(res_token.status_code, 200)
            token_data = res_token.json()
            self.assertIn("access_token", token_data)
            token = token_data["access_token"]

            headers = {"Authorization": f"Bearer {token}"}

            # 4. Request nodes list -> Should return empty/success
            res_nodes = requests.get(f"http://127.0.0.1:{port}/api/v1/nodes", headers=headers)
            self.assertEqual(res_nodes.status_code, 200)
            self.assertIn("nodes", res_nodes.json())

            # 5. Register node via POST API
            res_reg = requests.post(
                f"http://127.0.0.1:{port}/api/v1/nodes/register",
                headers=headers,
                json={"node_id": "test-device", "device_type": "LAPTOP", "status": "ONLINE"}
            )
            self.assertEqual(res_reg.status_code, 200)
            self.assertEqual(res_reg.json()["status"], "SUCCESS")

            # 6. Verify registered node in nodes list
            res_nodes_updated = requests.get(f"http://127.0.0.1:{port}/api/v1/nodes", headers=headers)
            nodes_list = res_nodes_updated.json()["nodes"]
            self.assertEqual(len(nodes_list), 1)
            self.assertEqual(nodes_list[0]["id"], "test-device")

        finally:
            gateway.stop()

    def test_developer_cli_scaffolding_and_dag_check(self) -> None:
        """Test plugin scaffolding generation and workflow DAG cycle verifications."""
        # 1. Scaffold plugin skeleton
        developer_cli.generate_plugin("Test Plugin", self.test_dir)
        plugin_path = os.path.join(self.test_dir, "test_plugin")
        self.assertTrue(os.path.exists(plugin_path))
        self.assertTrue(os.path.exists(os.path.join(plugin_path, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(plugin_path, "plugin.py")))

        # Verify plugin loading/import compiling check passes
        check_ok = developer_cli.verify_plugin_dir(plugin_path)
        self.assertTrue(check_ok)

        # 2. Scaffold workflow JSON
        wf_path = os.path.join(self.test_dir, "test_workflow.json")
        developer_cli.generate_workflow("Test Workflow", wf_path)
        self.assertTrue(os.path.exists(wf_path))

        # Verify workflow DAG verify check passes
        dag_ok = developer_cli.verify_workflow_file(wf_path)
        self.assertTrue(dag_ok)

        # 3. Test Cycle detection (introducing a loop dependency)
        with open(wf_path, "r", encoding="utf-8") as f:
            wf_data = json.load(f)

        # Modify step_1 to depend on step_3, creating step_1 -> step_2 -> step_3 -> step_1 cycle
        for node in wf_data["nodes"]:
            if node["id"] == "step_1":
                node["dependencies"] = ["step_3"]

        cycle_wf_path = os.path.join(self.test_dir, "cycle_workflow.json")
        with open(cycle_wf_path, "w", encoding="utf-8") as f:
            json.dump(wf_data, f)

        # Verifier should fail/detect cycle
        dag_fail = developer_cli.verify_workflow_file(cycle_wf_path)
        self.assertFalse(dag_fail)


if __name__ == "__main__":
    unittest.main()
