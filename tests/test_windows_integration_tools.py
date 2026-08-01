import os
import unittest
from unittest.mock import patch

from tools.file_tools import FileOperationsTool
from tools.windows_tools import (
    ClipboardTool,
    HardwareMonitoringTool,
    NotificationTool,
    PowerManagementTool,
    ProcessTool,
    WindowManagementTool,
)


class TestWindowsIntegrationTools(unittest.TestCase):
    def test_clipboard_tool_history(self):
        tool = ClipboardTool()
        tool._history = []

        # Test copy string
        res = tool.execute(operation="set", text="test text 1")
        self.assertTrue(res.success)

        # Test copy another string
        tool.execute(operation="set", text="test text 2")

        # Check history
        res_hist = tool.execute(operation="history")
        self.assertTrue(res_hist.success)
        self.assertEqual(res_hist.output["history"], ["test text 2", "test text 1"])

    def test_process_tool_actions(self):
        tool = ProcessTool()

        # Test list
        res_list = tool.execute(action="list")
        self.assertTrue(res_list.success)
        self.assertIn("processes", res_list.output)

        # Test start/stop with mock
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 99999
            res_start = tool.execute(action="start", path="notepad.exe")
            self.assertTrue(res_start.success)
            self.assertEqual(res_start.output["pid"], 99999)

        # Test stop without confirmation
        res_stop_fail = tool.execute(action="stop", pid=99999, confirm=False)
        self.assertFalse(res_stop_fail.success)
        self.assertIn("confirmation required", res_stop_fail.message if hasattr(res_stop_fail, "message") else res_stop_fail.error)

    def test_window_management_tool(self):
        tool = WindowManagementTool()

        # Test monitor info
        res_mon = tool.execute(action="monitor_info")
        if os.name == "nt":
            self.assertTrue(res_mon.success)
            self.assertIn("primary_resolution", res_mon.output)
        else:
            self.assertFalse(res_mon.success)

    def test_notification_tool(self):
        tool = NotificationTool()
        with patch("subprocess.Popen") as mock_popen:
            res = tool.execute(message="Hello from unit tests!")
            self.assertTrue(res.success)
            mock_popen.assert_called_once()

    def test_power_management_tool_confirmations(self):
        tool = PowerManagementTool()

        # Test battery
        res_bat = tool.execute(action="battery")
        self.assertTrue(res_bat.success)
        self.assertIn("percent", res_bat.output)

        # Test shutdown without confirm
        res_shut = tool.execute(action="shutdown", confirm=False)
        self.assertFalse(res_shut.success)
        self.assertIn("confirm=True' is required", res_shut.message if hasattr(res_shut, "message") else res_shut.error)

    def test_hardware_monitoring_tool(self):
        tool = HardwareMonitoringTool()
        res = tool.execute()
        self.assertTrue(res.success)
        self.assertIn("cpu_percent", res.output)
        self.assertIn("ram_percent", res.output)
        self.assertIn("usb_devices", res.output)

    def test_file_operations_tool(self):
        tool = FileOperationsTool()
        test_file = "test_file_operations.txt"

        try:
            # Test write
            res_write = tool.execute(action="write", path=test_file, content="sample content")
            self.assertTrue(res_write.success)

            # Test read
            res_read = tool.execute(action="read", path=test_file)
            self.assertTrue(res_read.success)
            self.assertEqual(res_read.output["content"], "sample content")

            # Test monitor
            res_mon = tool.execute(action="monitor", path=".")
            self.assertTrue(res_mon.success)
            self.assertIn("snapshot", res_mon.output)

            # Test recycle with mock/permanent fallback
            res_recycle = tool.execute(action="recycle", path=test_file)
            self.assertTrue(res_recycle.success)
            self.assertFalse(os.path.exists(test_file))

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == "__main__":
    unittest.main()
