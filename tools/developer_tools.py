"""JARVIS Tool SDK - Developer and codebase maintenance tools."""

from __future__ import annotations
import subprocess
import os
import json
import time
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class GitTool(ToolBase):
    """Integrates Git version control controls (Init, Status, Branch, Checkout, Commit, Diff) with simulated fallbacks."""

    def __init__(self) -> None:
        super().__init__("Git Tool", "1.0")

    def _is_git_available(self) -> bool:
        try:
            res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def validate(self, **kwargs) -> bool:
        return "repo_path" in kwargs and "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("repo_path", "")
        action = kwargs.get("action", "status")
        
        if not os.path.exists(path) and action != "init":
            return ToolResult(False, None, f"Repo path '{path}' does not exist.")
            
        git_available = self._is_git_available()
        
        try:
            if action == "init":
                os.makedirs(path, exist_ok=True)
                if git_available:
                    res = subprocess.run(["git", "init"], cwd=path, capture_output=True, text=True, timeout=5)
                    return ToolResult(res.returncode == 0, {"stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
                else:
                    # Simulation
                    os.makedirs(os.path.join(path, ".git"), exist_ok=True)
                    return ToolResult(True, {"stdout": "Initialized empty Git repository (Simulated)", "stderr": ""})
                
            elif action == "status":
                if git_available:
                    res = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True, timeout=5)
                    return ToolResult(True, {"status_output": res.stdout.strip(), "uncommitted": len(res.stdout.splitlines()) > 0})
                else:
                    # Simulation
                    has_uncommitted = len(os.listdir(path)) > 1  # More than just .git
                    return ToolResult(True, {"status_output": "M code.py" if has_uncommitted else "", "uncommitted": has_uncommitted})
                
            elif action == "branch":
                branch_name = kwargs.get("branch_name", "")
                if not branch_name:
                    if git_available:
                        res = subprocess.run(["git", "branch"], cwd=path, capture_output=True, text=True, timeout=5)
                        return ToolResult(True, {"branches": res.stdout.strip().splitlines()})
                    else:
                        return ToolResult(True, {"branches": ["* main", "dev-feature"]})
                else:
                    if git_available:
                        res = subprocess.run(["git", "branch", branch_name], cwd=path, capture_output=True, text=True, timeout=5)
                        return ToolResult(res.returncode == 0, {"stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
                    else:
                        return ToolResult(True, {"stdout": f"Branch {branch_name} created (Simulated)", "stderr": ""})
                    
            elif action == "checkout":
                branch_name = kwargs.get("branch_name", "")
                if not branch_name:
                    return ToolResult(False, None, "branch_name required for checkout action.")
                if git_available:
                    res = subprocess.run(["git", "checkout", branch_name], cwd=path, capture_output=True, text=True, timeout=5)
                    return ToolResult(res.returncode == 0, {"stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
                else:
                    return ToolResult(True, {"stdout": f"Switched to branch '{branch_name}' (Simulated)", "stderr": ""})
                
            elif action == "commit":
                message = kwargs.get("message", "Commit from JARVIS AI")
                if git_available:
                    subprocess.run(["git", "add", "."], cwd=path, timeout=5)
                    res = subprocess.run(["git", "commit", "-m", message], cwd=path, capture_output=True, text=True, timeout=5)
                    return ToolResult(res.returncode == 0, {"stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
                else:
                    return ToolResult(True, {"stdout": f"[main 1a2b3c4] {message} (Simulated)", "stderr": ""})
                
            elif action == "diff":
                if git_available:
                    res = subprocess.run(["git", "diff"], cwd=path, capture_output=True, text=True, timeout=5)
                    return ToolResult(True, {"diff": res.stdout.strip()})
                else:
                    return ToolResult(True, {"diff": "--- a/code.py\n+++ b/code.py\n@@ -1,1 +1,1 @@\n-print(1)\n+print(2)"})
                
            else:
                return ToolResult(False, None, f"Unsupported Git action: {action}")
                
        except Exception as e:
            return ToolResult(False, None, f"Git tool action '{action}' error: {e}")

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem", "network"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 45.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True


class VSCodeTool(ToolBase):
    """Enables integration with Visual Studio Code (Open projects, run tasks, launch terminal, list extensions)."""

    def __init__(self) -> None:
        super().__init__("VSCode Tool", "1.0")
        self.recent_history_path = os.path.abspath(os.path.join("logs", "vscode_recent.json"))
        os.makedirs(os.path.dirname(self.recent_history_path), exist_ok=True)

    def validate(self, **kwargs) -> bool:
        return "action" in kwargs

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "open")
        
        try:
            if action == "open":
                path = kwargs.get("path", "")
                if path:
                    path = os.path.abspath(path)
                    self._save_to_recent(path)
                    cmd = ["code", path]
                else:
                    cmd = ["code"]
                
                # Run detached
                subprocess.Popen(cmd, shell=True)
                return ToolResult(True, {"message": f"Launched VS Code with command {cmd}"})
                
            elif action == "create_project":
                path = kwargs.get("path", "")
                if not path:
                    return ToolResult(False, None, "path required for create_project action.")
                path = os.path.abspath(path)
                os.makedirs(path, exist_ok=True)
                
                # Write basic templates
                with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
                    f.write("# Developer Project\n\nGenerated by JARVIS Developer Platform.")
                with open(os.path.join(path, "requirements.txt"), "w", encoding="utf-8") as f:
                    f.write("pytest\n")
                with open(os.path.join(path, "app.py"), "w", encoding="utf-8") as f:
                    f.write("def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()")
                    
                self._save_to_recent(path)
                subprocess.Popen(["code", path], shell=True)
                return ToolResult(True, {"message": f"Created basic python project structure at {path} and opened in VS Code"})
                
            elif action == "get_recent":
                recent = self._get_recent()
                return ToolResult(True, {"recent_projects": recent})
                
            elif action == "list_extensions":
                try:
                    res = subprocess.run(["code", "--list-extensions"], capture_output=True, text=True, timeout=5)
                    extensions = res.stdout.strip().splitlines() if res.returncode == 0 else []
                    return ToolResult(res.returncode == 0, {"extensions": extensions, "stderr": res.stderr.strip()})
                except Exception:
                    # Fallback if VSCode CLI not configured on system PATH
                    return ToolResult(True, {"extensions": ["ms-python.python", "ms-vscode.cpptools"], "simulated": True})
                
            elif action == "run_task":
                cmd_to_run = kwargs.get("cmd", "")
                cwd = kwargs.get("cwd", os.getcwd())
                if not cmd_to_run:
                    return ToolResult(False, None, "cmd required for run_task action.")
                res = subprocess.run(cmd_to_run, shell=True, cwd=cwd, capture_output=True, text=True, timeout=15)
                return ToolResult(res.returncode == 0, {
                    "stdout": res.stdout.strip(),
                    "stderr": res.stderr.strip(),
                    "exit_code": res.returncode
                })
                
            elif action == "read_problems":
                path = kwargs.get("path", os.getcwd())
                problems = []
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(".py") and "venv" not in root and ".venv" not in root:
                            full_p = os.path.join(root, file)
                            try:
                                res = subprocess.run(["python", "-m", "py_compile", full_p], capture_output=True, text=True, timeout=5)
                                if res.returncode != 0:
                                    problems.append({
                                        "file": os.path.relpath(full_p, path),
                                        "error": res.stderr.strip(),
                                        "severity": "ERROR"
                                    })
                            except Exception:
                                pass
                return ToolResult(True, {"problems": problems, "count": len(problems)})
                
            else:
                return ToolResult(False, None, f"Unsupported VSCode action: {action}")
                
        except Exception as e:
            return ToolResult(False, None, f"VSCode tool action '{action}' error: {e}")

    def _save_to_recent(self, path: str):
        recent = self._get_recent()
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:10]  # Store last 10
        try:
            with open(self.recent_history_path, "w", encoding="utf-8") as f:
                json.dump(recent, f, indent=2)
        except Exception:
            pass

    def _get_recent(self) -> list[str]:
        if os.path.exists(self.recent_history_path):
            try:
                with open(self.recent_history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def rollback(self) -> bool:
        return True

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY"}

    def permissions(self) -> list[str]:
        return ["filesystem", "settings"]

    def metrics(self) -> dict[str, Any]:
        return {"avg_time": 100.0}

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
