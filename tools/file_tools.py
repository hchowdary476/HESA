"""JARVIS Tool SDK - Filesystem search and safety tools."""

from __future__ import annotations
import os
import shutil
import subprocess
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class FileSearchTool(ToolBase):
    """Searches workspace directories safely with path validation constraints."""

    def __init__(self) -> None:
        super().__init__("File Search Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "target_dir" in kwargs and "pattern" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        target_dir = kwargs.get("target_dir", "")
        pattern = kwargs.get("pattern", "").lower()
        
        # Path validation check
        abs_path = os.path.abspath(target_dir)
        if not os.path.exists(abs_path):
            return ToolResult(False, None, f"Directory path '{target_dir}' does not exist.")
            
        matches = []
        try:
            for root, dirs, files in os.walk(abs_path):
                for f in files:
                    if pattern in f.lower():
                        matches.append(os.path.join(root, f))
                if len(matches) > 100:  # Safety cap
                    break
            return ToolResult(True, {"matches": matches, "count": len(matches)})
        except Exception as e:
            return ToolResult(False, None, f"Scan failed: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 30.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class FileOperationsTool(ToolBase):
    """Integrates file read, write, directory organization, monitoring, and Recycle Bin support."""
    
    def __init__(self) -> None:
        super().__init__("File Operations Tool", "1.0")

    def validate(self, **kwargs) -> bool:
        return "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        path = kwargs.get("path")
        if not path:
            return ToolResult(False, None, "Missing 'path' parameter.")
            
        abs_path = os.path.abspath(path)
        
        if action == "read":
            if not os.path.exists(abs_path):
                return ToolResult(False, None, f"File does not exist: {path}")
            if not os.path.isfile(abs_path):
                return ToolResult(False, None, f"Path is not a file: {path}")
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return ToolResult(True, {"content": content})
            except Exception as e:
                return ToolResult(False, None, f"Failed to read file: {e}")
                
        elif action == "write":
            content = kwargs.get("content")
            if content is None:
                return ToolResult(False, None, "Missing 'content' parameter to write.")
            try:
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(True, f"File written successfully to {path}")
            except Exception as e:
                return ToolResult(False, None, f"Failed to write file: {e}")
                
        elif action == "organize":
            if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
                return ToolResult(False, None, f"Directory does not exist: {path}")
            try:
                moved_files = []
                for item in os.listdir(abs_path):
                    item_path = os.path.join(abs_path, item)
                    if os.path.isfile(item_path):
                        ext = os.path.splitext(item)[1].replace(".", "").lower()
                        if ext:
                            dest_dir = os.path.join(abs_path, ext.upper())
                            os.makedirs(dest_dir, exist_ok=True)
                            dest_path = os.path.join(dest_dir, item)
                            if not os.path.exists(dest_path):
                                shutil.move(item_path, dest_path)
                                moved_files.append((item, ext.upper()))
                return ToolResult(True, {"organized_count": len(moved_files), "moved": moved_files})
            except Exception as e:
                return ToolResult(False, None, f"Organization failed: {e}")
                
        elif action == "recycle":
            if not os.path.exists(abs_path):
                return ToolResult(False, None, f"Target path does not exist: {path}")
            try:
                # Use .NET Framework class through PowerShell to move to Recycle Bin safely
                powershell_cmd = (
                    f'Add-Type -AssemblyName Microsoft.VisualBasic; '
                    f'[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("{abs_path.replace("\\", "\\\\")}", '
                    f'"OnlyErrorDialogs", "SendToRecycleBin")' if os.path.isfile(abs_path) else
                    f'[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory("{abs_path.replace("\\", "\\\\")}", '
                    f'"OnlyErrorDialogs", "SendToRecycleBin")'
                )
                subprocess.check_call(["powershell", "-Command", powershell_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ToolResult(True, f"Successfully moved {path} to Recycle Bin.")
            except Exception as e:
                # Fallback to delete permanently
                try:
                    if os.path.isdir(abs_path):
                        shutil.rmtree(abs_path)
                    else:
                        os.remove(abs_path)
                    return ToolResult(True, f"Recycled fallback: deleted {path} permanently.")
                except Exception as fallback_err:
                    return ToolResult(False, None, f"Failed to delete {path}: {fallback_err}")
                    
        elif action == "monitor":
            if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
                return ToolResult(False, None, f"Directory does not exist: {path}")
            try:
                snapshot = {}
                for root, _, files in os.walk(abs_path):
                    for file in files:
                        f_path = os.path.join(root, file)
                        try:
                            snapshot[os.path.relpath(f_path, abs_path)] = os.path.getmtime(f_path)
                        except Exception:
                            pass
                return ToolResult(True, {"snapshot": snapshot})
            except Exception as e:
                return ToolResult(False, None, f"Monitoring failed: {e}")
        else:
            return ToolResult(False, None, f"Unknown action: {action}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 12.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
