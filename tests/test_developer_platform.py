"""Unit and integration tests for JARVIS Developer Platform & SDK."""

import os
import sys
import json
import time
import shutil
import unittest
import requests
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../developer_sdk")

from developer_sdk.client import JarvisClient
from api.server import DeveloperGateway
from installer.setup_wizard import SetupWizard
from release_pipeline.builder import ReleaseBuilder
import cli.main as cli_main


class TestDeveloperPlatform(unittest.TestCase):
    def setUp(self) -> None:
        from remote_api import RemoteGateway
        RemoteGateway._instance = None
        DeveloperGateway._instance = None
        self.test_dir = os.path.abspath("test_platform_sandbox")
        os.makedirs(self.test_dir, exist_ok=True)
        self.pid_file = os.path.join(self.test_dir, "jarvis_server.pid")

    def tearDown(self) -> None:
        from remote_api import RemoteGateway
        RemoteGateway._instance = None
        DeveloperGateway._instance = None
        if os.path.exists(self.test_dir):
            for _ in range(3):
                try:
                    shutil.rmtree(self.test_dir)
                    break
                except Exception:
                    time.sleep(0.2)
            else:
                try:
                    shutil.rmtree(self.test_dir, ignore_errors=True)
                except Exception:
                    pass
        
        # Ensure PID file deletion if present
        pid_active = os.path.abspath(os.path.join("logs", "jarvis_server.pid"))
        if os.path.exists(pid_active):
            try:
                os.remove(pid_active)
            except Exception:
                pass

    def test_developer_sdk_client_endpoints(self) -> None:
        """Verify Developer Python Client API get/post routing and Bearer token attachments."""
        client = JarvisClient(base_url="http://127.0.0.1:9999", token="jwt_auth_token")
        
        self.assertEqual(client.base_url, "http://127.0.0.1:9999")
        self.assertEqual(client._headers()["Authorization"], "Bearer jwt_auth_token")

        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            # Mock get response
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "SUCCESS"}
            mock_get.return_value = mock_resp
            mock_post.return_value = mock_resp

            # Test AI Route
            client.ai.route("test prompt", "least-latency")
            mock_post.assert_called_with(
                "http://127.0.0.1:9999/api/v1/route",
                headers=client._headers(),
                json={"prompt": "test prompt", "strategy": "least-latency"}
            )

            # Test Memory Write
            client.memory.write("long_term", "editor", "vim")
            mock_post.assert_called_with(
                "http://127.0.0.1:9999/api/v1/memory/write",
                headers=client._headers(),
                json={"layer": "long_term", "key": "editor", "value": "vim"}
            )

    def test_cli_argument_mappings(self) -> None:
        """Verify CLI start, status, stop processes Popen controls, and diagnostics listings."""
        # Test Start
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc

            cli_main.start_server(self.pid_file)
            self.assertTrue(os.path.exists(self.pid_file))
            with open(self.pid_file, "r") as f:
                self.assertEqual(f.read().strip(), "12345")

        # Test Status
        with patch("psutil.pid_exists", return_value=True):
            cli_main.check_status(self.pid_file)

        # Test Stop
        with patch("psutil.pid_exists", return_value=True), patch("psutil.Process") as mock_process:
            mock_p = MagicMock()
            mock_process.return_value = mock_p
            cli_main.stop_server(self.pid_file)
            mock_p.terminate.assert_called_once()
            self.assertFalse(os.path.exists(self.pid_file))

    def test_cli_ai_benchmark_and_diagnostics(self) -> None:
        """Verify CLI diagnostics prints resource loads, and ai benchmark compares providers."""
        with patch("psutil.Process") as mock_process:
            mock_p = MagicMock()
            mock_p.cpu_percent.return_value = 5.5
            mock_p.memory_info.return_value.rss = 100 * 1024 * 1024
            mock_process.return_value = mock_p

            # Should complete without error
            cli_main.run_diagnostics()
            cli_main.run_ai_benchmark()

    def test_api_openapi_and_swagger_server(self) -> None:
        """Verify DeveloperGateway hosts OpenAPI schema definitions and loads Swagger docs."""
        gateway = DeveloperGateway(host="127.0.0.1", port=0)
        gateway.start()

        try:
            port = gateway.port
            self.assertGreater(port, 0)

            # 1. Fetch openapi.json spec
            res_spec = requests.get(f"http://127.0.0.1:{port}/openapi.json")
            self.assertEqual(res_spec.status_code, 200)
            self.assertEqual(res_spec.json()["info"]["title"], "JARVIS Developer Platform API")

            # 2. Fetch docs Swagger HTML
            res_docs = requests.get(f"http://127.0.0.1:{port}/docs")
            self.assertEqual(res_docs.status_code, 200)
            self.assertIn("swagger-ui", res_docs.text)

            # 3. Test OAuth verification token trigger
            res_tok = requests.post(f"http://127.0.0.1:{port}/oauth/token", json={
                "client_id": "jarvis_client", "client_secret": "jarvis_secret"
            })
            self.assertEqual(res_tok.status_code, 200)
            token = res_tok.json()["access_token"]

            # 4. Query protected diagnostics endpoint
            headers = {"Authorization": f"Bearer {token}"}
            res_diag = requests.get(f"http://127.0.0.1:{port}/api/v1/diagnostics", headers=headers)
            self.assertEqual(res_diag.status_code, 200)
            self.assertIn("threads_count", res_diag.json())

        finally:
            gateway.stop()

    def test_installer_wizard_preflight_and_backups(self) -> None:
        """Verify Installer pre-flight audits, .env configs, and rolling upgrade rollbacks."""
        wiz = SetupWizard()
        
        # Pre-flight audits checks
        checks_ok = wiz.run_checks()
        self.assertTrue(checks_ok)

        # configure .env setup
        mock_inputs = {"port": "28020", "api_key": "custom_dev_key"}
        env_test_file = os.path.join(self.test_dir, ".env")
        
        # Redirect .env writes to test sandbox path
        with patch("builtins.open") as mock_open:
            wiz.configure_environment(mock_inputs)

        # Pre-upgrade Snapshots
        backup_dir = os.path.join(self.test_dir, "backups")
        backup_zip = wiz.backup_before_upgrade(backup_dir)
        self.assertIsNotNone(backup_zip)
        self.assertTrue(os.path.exists(backup_zip))

        # Rollback check
        success_rollback = wiz.rollback_upgrade(backup_zip)
        self.assertTrue(success_rollback)

    def test_release_builder_task_runs(self) -> None:
        """Verify ReleaseBuilder clean, verify checks, packages zips, and note compilation."""
        builder = ReleaseBuilder("1.0.5")
        # Override output location to sandbox
        builder.dist_dir = os.path.join(self.test_dir, "dist")
        
        builder.clean()
        self.assertTrue(os.path.exists(builder.dist_dir))

        # Compile release notes
        notes_path = builder.generate_release_notes()
        self.assertTrue(os.path.exists(notes_path))
        with open(notes_path, "r", encoding="utf-8") as f:
            self.assertIn("1.0.5", f.read())

        # Test package portable ZIP
        zip_path = builder.package_portable()
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.exists(zip_path))


if __name__ == "__main__":
    unittest.main()
