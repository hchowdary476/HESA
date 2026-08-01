"""Developer SDK CLI for JARVIS - Scaffolding generators, simulation and DAG verifiers."""

from __future__ import annotations
import os
import sys
import json
import argparse
import time
from typing import Any

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tool_base import ToolBase
from tool_result import ToolResult
from workflow_engine import Workflow, WorkflowNode
from ai_fabric import AIFabric
from service_mesh import AIServiceMesh
from cloud_sync import CloudSyncManager


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS Enterprise SDK CLI Platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. generate-plugin command
    plugin_parser = subparsers.add_parser("generate-plugin", help="Creates skeleton plugin manifests and code")
    plugin_parser.add_argument("name", help="Name of the plugin tool to create")
    plugin_parser.add_argument("--dir", default="plugins", help="Target directory directory")

    # 2. generate-workflow command
    wf_parser = subparsers.add_parser("generate-workflow", help="Scaffolds workflow configurations")
    wf_parser.add_argument("name", help="Name of the workflow template")
    wf_parser.add_argument("--output", default="", help="Custom output filepath")

    # 3. simulate command
    subparsers.add_parser("simulate", help="Runs sandbox execution mocks for distributed handoffs")

    # 4. test command
    test_parser = subparsers.add_parser("test", help="Triggers verification checks on workflows and plugins")
    test_parser.add_argument("--workflow", default="", help="Verify specific workflow JSON file path")
    test_parser.add_argument("--plugin", default="", help="Verify specific plugin directory path")

    args = parser.parse_args()

    if args.command == "generate-plugin":
        generate_plugin(args.name, args.dir)
    elif args.command == "generate-workflow":
        generate_workflow(args.name, args.output)
    elif args.command == "simulate":
        run_simulation()
    elif args.command == "test":
        run_tests(args.workflow, args.plugin)


def generate_plugin(name: str, base_dir: str) -> None:
    """Generates plugin structure and tool code."""
    safe_name = name.lower().replace(" ", "_")
    p_dir = os.path.join(base_dir, safe_name)
    os.makedirs(p_dir, exist_ok=True)

    manifest = {
        "name": name,
        "version": "1.0.0",
        "author": "JARVIS Developer CLI",
        "plugin_entry": "plugin.py",
        "class_name": "PluginTool",
        "permissions": []
    }

    manifest_path = os.path.join(p_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    plugin_code = f"""\"\"\"Generated plugin skeleton for {name}.\"\"\"

from __future__ import annotations
from typing import Any
from tool_base import ToolBase
from tool_result import ToolResult

class PluginTool(ToolBase):
    \"\"\"Generated custom JARVIS Tool implementing ToolBase.\"\"\"

    def __init__(self) -> None:
        super().__init__(name="{name}", version="1.0.0")

    def initialize(self) -> bool:
        \"\"\"Runs startup dependency mapping check hooks.\"\"\"
        self.is_healthy = True
        return True

    def execute(self, **kwargs) -> ToolResult:
        \"\"\"Run custom tool business logic.\"\"\"
        import time
        t0 = time.time()
        self.run_count += 1
        
        # User defined code block
        param = kwargs.get("param", "Default Action")
        output = f"Hello from {name}! Received parameter: '{{param}}'"
        
        self.success_count += 1
        elapsed = (time.time() - t0) * 1000.0
        self.total_time_ms += elapsed
        
        return ToolResult(success=True, output=output, elapsed_ms=elapsed)

    def validate(self, **kwargs) -> bool:
        \"\"\"Validates input parameters before trigger execution runs.\"\"\"
        return True

    def rollback(self) -> bool:
        \"\"\"Reverts state changes on exception or cancellation triggers.\"\"\"
        return True

    def health(self) -> dict[str, Any]:
        \"\"\"Reports metrics telemetry check values.\"\"\"
        return {{"status": "HEALTHY", "is_healthy": self.is_healthy}}

    def permissions(self) -> list[str]:
        \"\"\"Declares runtime security boundaries.\"\"\"
        return []

    def metrics(self) -> dict[str, Any]:
        \"\"\"Reports run counts and cumulative latency stats.\"\"\"
        return {{
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_time_ms": self.total_time_ms
        }}

    def shutdown(self) -> bool:
        \"\"\"Cleans up active connections and handlers on system shutdown.\"\"\"
        return True
"""

    code_path = os.path.join(p_dir, "plugin.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(plugin_code)

    print(f"SUCCESS: Generated plugin '{name}' under '{p_dir}'")
    print(f"  - Manifest: {manifest_path}")
    print(f"  - Entry Code: {code_path}")


def generate_workflow(name: str, output_path: str) -> None:
    """Scaffolds workflow definition templates."""
    safe_name = name.lower().replace(" ", "_")
    if not output_path:
        output_path = f"{safe_name}_workflow.json"

    # Define a default workflow layout
    nodes = [
        WorkflowNode(
            node_id="step_1",
            description="Fetch data metrics from target",
            agent="research_agent",
            tool="browser_open_tool",
            dependencies=[]
        ),
        WorkflowNode(
            node_id="step_2",
            description="Process data inputs in sandbox",
            agent="developer_agent",
            tool="git_tool",
            dependencies=["step_1"]
        ),
        WorkflowNode(
            node_id="step_3",
            description="Report execution results metrics",
            agent="windows_system_agent",
            tool="clipboard_tool",
            dependencies=["step_2"]
        )
    ]

    wf = Workflow(name, nodes, metadata={"author": "JARVIS Developer CLI"})
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(wf.to_json())

    print(f"SUCCESS: Scaffolded workflow '{name}' in path '{output_path}'")


def run_simulation() -> None:
    """Runs mock sandbox simulation for distributed nodes execution."""
    print("-----------------------------------------------------------------")
    print("      JARVIS Distributed fabric execution simulation engine       ")
    print("-----------------------------------------------------------------")
    time.sleep(0.3)
    
    # 1. Instantiate modules
    fabric = AIFabric()
    mesh = AIServiceMesh()
    sync = CloudSyncManager()
    
    # 2. Seed simulated nodes cluster
    print("[Simulator] Seeding virtual platform nodes...")
    fabric.register_node("host-desktop", "DESKTOP", "ONLINE")
    fabric.register_node("host-mobile", "MOBILE", "ONLINE")
    fabric.register_node("cloud-mesh", "CLOUD", "ONLINE")
    fabric.register_node("laptop-dev", "LAPTOP", "OFFLINE")
    time.sleep(0.2)
    
    # 3. Create simulated multi-node workflow DAG
    print("[Simulator] Compiling distributed workflow nodes...")
    steps = [
        {"node_id": "host-desktop", "action": "Generate system prompt"},
        {"node_id": "cloud-mesh", "action": "Route query through model load-balancer"},
        {"node_id": "host-mobile", "action": "Broadcast status notification alert"}
    ]
    time.sleep(0.2)
    
    # 4. Execute workflow
    print("[Simulator] Launching workflow execution handoff loop:")
    res = fabric.distribute_workflow("simulation-wf-101", steps)
    print(f"[Simulator] Execution finished with status: {res['status']}")
    for step in res.get("history", []):
        print(f"  - Step {step['step']}: '{step['action']}' completed on '{step['node_id']}'")
        
    if res['status'] == "COMPLETED":
        print("[Simulator] Distributed task completed successfully.")
        
    print("-----------------------------------------------------------------")
    print("Simulation complete.")


def run_tests(workflow_file: str, plugin_dir: str) -> None:
    """Runs DAG validation verification checks on workflows or imports plugins."""
    print("[Verifier] Running verification tests...")
    
    if workflow_file:
        verify_workflow_file(workflow_file)
    if plugin_dir:
        verify_plugin_dir(plugin_dir)

    if not workflow_file and not plugin_dir:
        # Scan current dir for any .json files and check if they look like workflows
        print("[Verifier] Scanning workspace root for workflows and plugins...")
        found_wfs = 0
        found_plugs = 0
        for entry in os.listdir("."):
            if entry.endswith("_workflow.json"):
                verify_workflow_file(entry)
                found_wfs += 1
        
        plugins_root = "plugins"
        if os.path.exists(plugins_root):
            for entry in os.listdir(plugins_root):
                p_path = os.path.join(plugins_root, entry)
                if os.path.isdir(p_path) and os.path.exists(os.path.join(p_path, "manifest.json")):
                    verify_plugin_dir(p_path)
                    found_plugs += 1
                    
        print(f"[Verifier] System verification check: validated {found_wfs} workflows, tested {found_plugs} plugins.")


def verify_workflow_file(path: str) -> bool:
    """Verifies that a workflow JSON file exists and has no dependency loops (DAG check)."""
    if not os.path.exists(path):
        print(f"[Verifier] ERROR: File '{path}' does not exist.")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        nodes = data.get("nodes", [])
        # Build dependency graph
        adj: dict[str, list[str]] = {}
        for n in nodes:
            nid = n.get("id")
            deps = n.get("dependencies", [])
            adj[nid] = deps

        # Check for cycles using standard DFS (3-color coloring)
        visited = {}  # 0 = unvisited, 1 = visiting, 2 = visited
        for nid in adj:
            visited[nid] = 0

        def has_cycle(u: str) -> bool:
            visited[u] = 1
            for v in adj.get(u, []):
                if v not in visited:
                    # Missing dependency error
                    print(f"[Verifier] WARNING: Node '{u}' depends on missing node '{v}'")
                    continue
                if visited[v] == 1:
                    return True
                if visited[v] == 0:
                    if has_cycle(v):
                        return True
            visited[u] = 2
            return False

        cycle_found = False
        for nid in adj:
            if visited[nid] == 0:
                if has_cycle(nid):
                    cycle_found = True
                    break

        if cycle_found:
            print(f"[Verifier] FAILURE: Loop cycle detected in workflow DAG config: '{path}'")
            return False
        else:
            print(f"[Verifier] SUCCESS: Workflow DAG validated successfully: '{path}'")
            return True

    except Exception as e:
        print(f"[Verifier] FAILURE parsing workflow '{path}': {e}")
        return False


def verify_plugin_dir(path: str) -> bool:
    """Verifies manifest schema and loads the entry python module code."""
    manifest_path = os.path.join(path, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"[Verifier] FAILURE: manifest.json missing in '{path}'")
        return False

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        required = {"name", "version", "author", "plugin_entry", "class_name"}
        if not required.issubset(manifest.keys()):
            print(f"[Verifier] FAILURE: missing required keys in manifest: {manifest_path}")
            return False

        entry_file = os.path.join(path, manifest["plugin_entry"])
        if not os.path.exists(entry_file):
            print(f"[Verifier] FAILURE: entry file '{entry_file}' not found.")
            return False

        # Attempt basic compilation syntax check
        with open(entry_file, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, entry_file, "exec")

        print(f"[Verifier] SUCCESS: Plugin '{manifest['name']}' manifest and code verified: '{path}'")
        return True
    except Exception as e:
        print(f"[Verifier] FAILURE verifying plugin '{path}': {e}")
        return False


if __name__ == "__main__":
    main()
