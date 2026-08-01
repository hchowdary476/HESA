"""Unit and integration tests for the JARVIS Plugin Ecosystem."""

import json
import os
import shutil
import time
import unittest

from plugin_manager import PluginManager
from plugin_registry import PluginRegistry
from plugin_sandbox import PluginSandbox
from tool_manager import ToolManager


class TestJARVISPluginEcosystem(unittest.TestCase):
    """Test suite covering dynamic plugin loads, sandboxed timeouts, and market installs."""

    def setUp(self) -> None:
        self.manager = PluginManager(plugins_root="logs/test_plugins")
        self.registry = PluginRegistry()
        self.registry.registry.clear()

        # Ensure default permissions are whitelisted
        self.tool_manager = ToolManager()
        self.tool_manager.tools.clear()
        self.tool_manager.granted_permissions = {"filesystem", "network"}

    def tearDown(self) -> None:
        if os.path.exists("logs/test_plugins"):
            shutil.rmtree("logs/test_plugins")

    def test_manifest_validation(self) -> None:
        """Verify dynamic loader blocks plugins missing standard manifest keys."""
        src_dir = "logs/test_source_plugin"
        os.makedirs(src_dir, exist_ok=True)
        manifest_path = os.path.join(src_dir, "manifest.json")

        # Manifest missing name/version
        bad_manifest = {"author": "Dev", "plugin_entry": "plugin.py"}
        with open(manifest_path, "w") as f:
            json.dump(bad_manifest, f)

        success = self.manager.install_plugin(src_dir)
        self.assertFalse(success)

        # Cleanup
        shutil.rmtree(src_dir)

    def test_permission_denial(self) -> None:
        """Verify dynamic loader blocks plugins requesting ungranted permissions."""
        src_dir = "logs/test_source_perm_plugin"
        os.makedirs(src_dir, exist_ok=True)
        manifest_path = os.path.join(src_dir, "manifest.json")

        # Requires 'restricted_scope' which is not granted
        manifest = {
            "name": "Perm Plugin",
            "version": "1.0",
            "author": "Dev",
            "plugin_entry": "plugin.py",
            "permissions": ["restricted_scope"],
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        success = self.manager.install_plugin(src_dir)
        self.assertFalse(success)

        # Cleanup
        shutil.rmtree(src_dir)

    def test_sandbox_crash_containment(self) -> None:
        """Verify sandbox catches exceptions and prevents core crashes."""

        def bad_function():
            raise ValueError("Interrupted runtime error simulation")

        res = PluginSandbox.execute_safely(bad_function)
        self.assertFalse(res.success)
        self.assertIn("Exception Intercepted", res.error)

    def test_sandbox_timeout(self) -> None:
        """Verify sandbox terminates execution when limits are exceeded."""

        def hanging_function():
            time.sleep(1.0)
            return "done"

        res = PluginSandbox.execute_safely(hanging_function, timeout=0.1)
        self.assertFalse(res.success)
        self.assertIn("timed out", res.error)

    def test_plugin_installation_and_removal(self) -> None:
        """Verify file copying, loader execution, and complete purges."""
        src_dir = "logs/test_install_plugin"
        os.makedirs(src_dir, exist_ok=True)

        manifest = {
            "name": "Integration Plugin",
            "version": "1.0",
            "author": "Dev",
            "plugin_entry": "plugin.py",
            "class_name": "IntegrationTool",
            "permissions": ["filesystem"],
        }
        plugin_code = """
from tool_base import ToolBase
from tool_result import ToolResult

class IntegrationTool(ToolBase):
    def __init__(self):
        super().__init__("Integration Plugin", "1.0")
    def validate(self, **kwargs): return True
    def execute(self, **kwargs): return ToolResult(True, "Working")
    def rollback(self): return True
    def health(self): return {}
    def permissions(self): return ["filesystem"]
    def metrics(self): return {}
    def initialize(self): return True
    def shutdown(self): return True
"""
        with open(os.path.join(src_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)
        with open(os.path.join(src_dir, "plugin.py"), "w") as f:
            f.write(plugin_code)

        # Install
        success = self.manager.install_plugin(src_dir)
        self.assertTrue(success)
        self.assertIn("integration_plugin", self.tool_manager.tools)

        # Verify metrics
        metrics = self.manager.get_plugin_metrics()
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "Integration Plugin")

        # Remove
        removed = self.manager.remove_plugin("Integration Plugin")
        self.assertTrue(removed)
        self.assertNotIn("integration_plugin", self.tool_manager.tools)

        # Cleanup source
        shutil.rmtree(src_dir)
