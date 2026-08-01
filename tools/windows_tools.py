"""JARVIS Tool SDK - Windows administrative and system automation tools."""

from __future__ import annotations
import os
import subprocess
import time
import ctypes
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

# Windows ctypes helpers
EnumWindows = ctypes.windll.user32.EnumWindows if hasattr(ctypes.windll, "user32") else None
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int) if hasattr(ctypes.windll, "user32") else None
GetWindowText = ctypes.windll.user32.GetWindowTextW if hasattr(ctypes.windll, "user32") else None
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW if hasattr(ctypes.windll, "user32") else None
IsWindowVisible = ctypes.windll.user32.IsWindowVisible if hasattr(ctypes.windll, "user32") else None

class ClipboardTool(ToolBase):
    """Integrates clipboard copy/paste controls and maintains a history of the last 10 copied strings."""
    _history = []

    def __init__(self) -> None:
        super().__init__("Clipboard Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "text" in kwargs or kwargs.get("operation") in ["get", "history"]

    def execute(self, **kwargs) -> ToolResult:
        import pyperclip
        op = kwargs.get("operation", "set")
        if op == "get":
            text = pyperclip.paste() or ""
            return ToolResult(True, {"text": text})
        elif op == "history":
            return ToolResult(True, {"history": self._history})
        else:
            text = kwargs.get("text", "")
            pyperclip.copy(text)
            # Prepend to history, keep last 10 items unique
            if text and (not self._history or self._history[0] != text):
                self._history.insert(0, text)
                if len(self._history) > 10:
                    self._history.pop()
            return ToolResult(True, "Copied text to clipboard.")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["clipboard"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 2.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class ProcessTool(ToolBase):
    """List running processes, start, stop, monitor health, and check responding status."""

    def __init__(self) -> None:
        super().__init__("Process Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        import psutil
        action = kwargs.get("action", "list")
        
        if action == "list":
            procs = []
            cpu_cores = psutil.cpu_count() or 1
            for p in list(psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]))[:100]:
                try:
                    info = p.info.copy()
                    if "cpu_percent" in info and info["cpu_percent"] is not None:
                        info["cpu_percent"] = round(info["cpu_percent"] / cpu_cores, 1)
                    procs.append(info)
                except Exception:
                    pass
            # Sort by CPU usage
            procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
            return ToolResult(True, {"processes": procs})
            
        elif action == "start":
            path = kwargs.get("path")
            if not path:
                return ToolResult(False, None, "Missing 'path' parameter to start process.")
            try:
                proc = subprocess.Popen(path, shell=True)
                return ToolResult(True, {"pid": proc.pid, "status": "started"})
            except Exception as e:
                return ToolResult(False, None, f"Failed to start process: {e}")
                
        elif action == "stop":
            pid = kwargs.get("pid")
            confirm = kwargs.get("confirm", False)
            if not pid:
                return ToolResult(False, None, "Missing 'pid' parameter to stop process.")
            if not confirm:
                return ToolResult(False, None, "Stop process aborted: user confirmation required. Set 'confirm=True'.")
            try:
                p = psutil.Process(int(pid))
                p.terminate()
                return ToolResult(True, f"Process {pid} terminated successfully.")
            except Exception as e:
                return ToolResult(False, None, f"Failed to stop process {pid}: {e}")
                
        elif action == "monitor":
            pid = kwargs.get("pid")
            if not pid:
                return ToolResult(False, None, "Missing 'pid' parameter to monitor.")
            try:
                p = psutil.Process(int(pid))
                cpu_cores = psutil.cpu_count() or 1
                cpu = p.cpu_percent(interval=0.1)
                normalized_cpu = round(cpu / cpu_cores, 1)
                mem = p.memory_info().rss / (1024 * 1024)
                status = p.status()
                
                # Check responding status via PowerShell
                responding = True
                try:
                    res = subprocess.check_output(
                        ["powershell", "-Command", f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).Responding"],
                        text=True
                    ).strip()
                    responding = (res == "True")
                except Exception:
                    pass
                    
                return ToolResult(True, {
                    "pid": pid,
                    "name": p.name(),
                    "cpu_percent": normalized_cpu,
                    "memory_mb": round(mem, 2),
                    "status": status,
                    "responding": responding
                })
            except Exception as e:
                return ToolResult(False, None, f"Failed to monitor process {pid}: {e}")
        else:
            return ToolResult(False, None, f"Unknown action: {action}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["settings"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 15.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class WindowManagementTool(ToolBase):
    """Enables listing, focusing, closing, and resizing GUI application windows natively on Windows OS."""

    def __init__(self) -> None:
        super().__init__("Window Management Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        if os.name != "nt" or EnumWindows is None:
            return ToolResult(False, None, "Window Management Tool is only supported on Windows.")

        action = kwargs.get("action", "list")
        
        if action == "list":
            windows = []
            def callback(hwnd, extra):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLength(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buffer, length + 1)
                        windows.append({"hwnd": hwnd, "title": buffer.value})
                return True
            EnumWindows(EnumWindowsProc(callback), 0)
            return ToolResult(True, {"windows": windows})
            
        elif action == "focus":
            hwnd = kwargs.get("hwnd")
            if hwnd is None:
                return ToolResult(False, None, "Missing 'hwnd' parameter to focus window.")
            try:
                ctypes.windll.user32.ShowWindow(int(hwnd), 9) # SW_RESTORE
                success = ctypes.windll.user32.SetForegroundWindow(int(hwnd)) != 0
                return ToolResult(success, "Window focused successfully." if success else "Failed to focus window.")
            except Exception as e:
                return ToolResult(False, None, f"Error focusing window: {e}")
                
        elif action == "close":
            hwnd = kwargs.get("hwnd")
            if hwnd is None:
                return ToolResult(False, None, "Missing 'hwnd' parameter to close window.")
            try:
                success = ctypes.windll.user32.PostMessageW(int(hwnd), 0x0010, 0, 0) != 0
                return ToolResult(success, "Close message sent." if success else "Failed to close window.")
            except Exception as e:
                return ToolResult(False, None, f"Error closing window: {e}")
                
        elif action == "move_resize":
            hwnd = kwargs.get("hwnd")
            x = kwargs.get("x", 100)
            y = kwargs.get("y", 100)
            w = kwargs.get("width", 800)
            h = kwargs.get("height", 600)
            if hwnd is None:
                return ToolResult(False, None, "Missing 'hwnd' parameter.")
            try:
                success = ctypes.windll.user32.SetWindowPos(int(hwnd), 0, int(x), int(y), int(w), int(h), 0x0040) != 0
                return ToolResult(success, "Window coordinates updated." if success else "Failed to update window position.")
            except Exception as e:
                return ToolResult(False, None, f"Error positioning window: {e}")
                
        elif action == "monitor_info":
            try:
                width = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = ctypes.windll.user32.GetSystemMetrics(1) # SM_CYSCREEN
                count = ctypes.windll.user32.GetSystemMetrics(80) # SM_CMONITORS
                return ToolResult(True, {"primary_resolution": f"{width}x{height}", "monitor_count": count})
            except Exception as e:
                return ToolResult(False, None, f"Failed to get monitor metrics: {e}")
        else:
            return ToolResult(False, None, f"Unknown action: {action}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["settings"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 10.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class NotificationTool(ToolBase):
    """Sends native Windows balloon notifications and structures user alerts."""

    def __init__(self) -> None:
        super().__init__("Notification Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "message" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title", "JARVIS Notification")
        message = kwargs.get("message", "")
        
        powershell_command = (
            f'[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
            f'$notification = New-Object System.Windows.Forms.NotifyIcon; '
            f'$notification.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$notification.BalloonTipIcon = "Info"; '
            f'$notification.BalloonTipTitle = "{title.replace("\"", "`\"")}"; '
            f'$notification.BalloonTipText = "{message.replace("\"", "`\"")}"; '
            f'$notification.Visible = $True; '
            f'$notification.ShowBalloonTip(5000);'
        )
        try:
            subprocess.Popen(["powershell", "-Command", powershell_command], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, "Native notification sent successfully.")
        except Exception as e:
            return ToolResult(False, None, f"Failed to send notification: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["notifications"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 5.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class PowerManagementTool(ToolBase):
    """Queries battery level, monitors power status, and triggers system shutdown or restarts."""

    def __init__(self) -> None:
        super().__init__("Power Management Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        import psutil
        action = kwargs.get("action")
        
        if action == "battery":
            try:
                bat = psutil.sensors_battery()
                if bat:
                    return ToolResult(True, {
                        "percent": bat.percent,
                        "power_plugged": bat.power_plugged,
                        "secsleft": bat.secsleft
                    })
                return ToolResult(True, {"percent": 100.0, "power_plugged": True, "secsleft": -1})
            except Exception as e:
                return ToolResult(False, None, f"Failed to query battery status: {e}")
                
        elif action in ["shutdown", "restart"]:
            confirm = kwargs.get("confirm", False)
            if not confirm:
                return ToolResult(False, None, f"System {action} aborted: confirmation 'confirm=True' is required.")
            try:
                flag = "/s" if action == "shutdown" else "/r"
                subprocess.Popen(["shutdown", flag, "/t", "10", "/c", "JARVIS-triggered reboot"], shell=True)
                return ToolResult(True, f"System {action} sequence initiated (10s delay).")
            except Exception as e:
                return ToolResult(False, None, f"Failed to execute {action}: {e}")
        else:
            return ToolResult(False, None, f"Unknown action: {action}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["settings"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 8.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class HardwareMonitoringTool(ToolBase):
    """Reads system resources (CPU, RAM, Disk), lists hardware USB/Bluetooth devices, and checks audio setups."""

    def __init__(self) -> None:
        super().__init__("Hardware Monitoring Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return True

    def execute(self, **kwargs) -> ToolResult:
        import psutil
        
        # 1. Fetch core CPU and memory usage
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        try:
            disk = psutil.disk_usage("C:").percent
        except Exception:
            disk = 0.0
            
        # 2. Fetch list of USB devices via PowerShell
        usb_devices = []
        try:
            res = subprocess.check_output(
                ["powershell", "-Command", "Get-PnpDevice -Class USB -Status OK -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FriendlyName"],
                text=True
            ).strip().split("\n")
            usb_devices = [x.strip() for x in res if x.strip()]
        except Exception:
            pass
            
        # 3. Fetch Bluetooth devices
        bt_devices = []
        try:
            res = subprocess.check_output(
                ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FriendlyName"],
                text=True
            ).strip().split("\n")
            bt_devices = [x.strip() for x in res if x.strip()]
        except Exception:
            pass
            
        # 4. Fetch Audio devices
        audio_setups = []
        try:
            res = subprocess.check_output(
                ["powershell", "-Command", "Get-AudioDevice -List -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name"],
                text=True
            ).strip().split("\n")
            audio_setups = [x.strip() for x in res if x.strip()]
        except Exception:
            pass
            
        return ToolResult(True, {
            "cpu_percent": cpu,
            "ram_percent": mem,
            "disk_percent": disk,
            "usb_devices": usb_devices[:20],
            "bluetooth_devices": bt_devices[:20],
            "audio_devices": audio_setups[:20]
        })

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["settings"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 20.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
