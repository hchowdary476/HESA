"""Unit and integration tests for the JARVIS Tool SDK."""

import json
import os
import unittest

from tool_base import ToolBase
from tool_manager import ToolManager
from tool_result import ToolResult
from tools.windows_tools import ClipboardTool


class DummyInvalidTool(ToolBase):
    """Test helper for invalid registration."""

    def __init__(self) -> None:
        super().__init__("Dummy Invalid", "1.0")

    def validate(self, **kwargs) -> bool:
        return True

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(True, "done")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict:
        return {}

    def permissions(self) -> list:
        return []

    def metrics(self) -> dict:
        return {}

    def initialize(self) -> bool:
        return False  # Fails init

    def shutdown(self) -> bool:
        return True


class DummyStrictTool(ToolBase):
    """Test helper for strict validation and permissions."""

    def __init__(self) -> None:
        super().__init__("Dummy Strict", "1.0")

    def validate(self, **kwargs) -> bool:
        return "required_arg" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        if kwargs.get("should_fail"):
            return ToolResult(False, None, "Execution failure simulation")
        return ToolResult(True, "Success")

    def rollback(self) -> bool:
        self.rolled_back = True
        return True

    def health(self) -> dict:
        return {}

    def permissions(self) -> list:
        return ["restricted_scope"]  # Requires restricted scope

    def metrics(self) -> dict:
        return {}

    def initialize(self) -> bool:
        self.rolled_back = False
        return True

    def shutdown(self) -> bool:
        return True


class TestJARVISToolSDK(unittest.TestCase):
    """Test suite covering the Tool SDK registry and permission validation engine."""

    def setUp(self) -> None:
        self.manager = ToolManager()
        self.manager.tools.clear()
        self.manager.granted_permissions = {"filesystem", "network", "clipboard", "browser", "notifications", "settings"}

    def test_tool_registration(self) -> None:
        """Verify that tools initializing successfully are registered."""
        tool = ClipboardTool()
        self.assertTrue(self.manager.register_tool(tool))
        self.assertIn("clipboard_tool", self.manager.tools)

        invalid_tool = DummyInvalidTool()
        self.assertFalse(self.manager.register_tool(invalid_tool))

    def test_permission_denial(self) -> None:
        """Verify execution blocks when a tool requires ungranted scopes."""
        tool = DummyStrictTool()
        self.manager.register_tool(tool)

        # 'restricted_scope' is not in granted permissions list
        res = self.manager.execute_tool("Dummy Strict", required_arg=True)
        self.assertFalse(res.success)
        self.assertIn("Permission Denied", res.error)

    def test_validation_denial(self) -> None:
        """Verify execution blocks when validation logic fails."""
        tool = DummyStrictTool()
        self.manager.register_tool(tool)
        self.manager.granted_permissions.add("restricted_scope")

        # Missing 'required_arg'
        res = self.manager.execute_tool("Dummy Strict")
        self.assertFalse(res.success)
        self.assertIn("Validation Block", res.error)

    def test_execution_and_rollback(self) -> None:
        """Verify rollback triggers automatically on runtime failures."""
        tool = DummyStrictTool()
        self.manager.register_tool(tool)
        self.manager.granted_permissions.add("restricted_scope")

        res = self.manager.execute_tool("Dummy Strict", required_arg=True, should_fail=True)
        self.assertFalse(res.success)
        self.assertTrue(tool.rolled_back)

    def test_plugin_dynamic_loading(self) -> None:
        """Verify the loading framework loads files based on manifest.json."""
        manifest = {
            "name": "Mock Plugin",
            "version": "1.0",
            "plugin_entry": "plugin.py",
            "class_name": "PluginTool",
            "permissions": ["filesystem"],
        }

        # Create temp folder inside workspace for the plugin mock
        plugin_dir = "logs/mock_plugin"
        os.makedirs(plugin_dir, exist_ok=True)
        manifest_path = os.path.join(plugin_dir, "manifest.json")
        entry_path = os.path.join(plugin_dir, "plugin.py")

        plugin_code = """
from tool_base import ToolBase
from tool_result import ToolResult

class PluginTool(ToolBase):
    def __init__(self):
        super().__init__("Plugin Tool", "1.0")
    def validate(self, **kwargs): return True
    def execute(self, **kwargs): return ToolResult(True, "Loaded from plugin file")
    def rollback(self): return True
    def health(self): return {}
    def permissions(self): return ["filesystem"]
    def metrics(self): return {}
    def initialize(self): return True
    def shutdown(self): return True
"""

        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
        with open(entry_path, "w") as f:
            f.write(plugin_code)

        success = self.manager.load_plugin(manifest_path)
        self.assertTrue(success)
        self.assertIn("plugin_tool", self.manager.tools)

        # Clean up files
        try:
            os.remove(manifest_path)
            os.remove(entry_path)
            os.rmdir(plugin_dir)
        except Exception:
            pass
