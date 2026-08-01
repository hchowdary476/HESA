"""
JARVIS Task Dependency Manager.

Analyzes DAG tasks to:
  - Detect circular dependencies
  - Order task execution lists correctly
  - Identify blocked tasks
"""

from __future__ import annotations

from collections import deque
from typing import Any


class DependencyManager:
    """Dependency resolver for task execution pipelines."""

    @staticmethod
    def detect_circular_dependencies(tasks: list[dict[str, Any]]) -> bool:
        """
        Returns True if a circular dependency is detected.
        Each task is dict with: 'id' (str) and 'dependencies' (list[str]).
        """
        adj: dict[str, list[str]] = {}
        all_ids = set()

        for t in tasks:
            tid = t["id"]
            all_ids.add(tid)
            adj[tid] = t.get("dependencies", [])

        # Topological sorting via DFS to detect cycles
        visited: dict[str, int] = {tid: 0 for tid in all_ids}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node: str) -> bool:
            if visited[node] == 1:
                return True  # cycle found
            if visited[node] == 2:
                return False

            visited[node] = 1
            for neighbor in adj.get(node, []):
                if neighbor in visited:  # Ignore external dependencies not in the task list
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for node in all_ids:
            if visited[node] == 0:
                if dfs(node):
                    return True
        return False

    @staticmethod
    def get_execution_order(tasks: list[dict[str, Any]]) -> list[str]:
        """
        Sorts task IDs topologically.
        If cycle is found, fallback to order defined by the list.
        """
        if DependencyManager.detect_circular_dependencies(tasks):
            return [t["id"] for t in tasks]

        in_degree: dict[str, int] = {}
        adj: dict[str, list[str]] = {}
        all_ids = [t["id"] for t in tasks]

        for tid in all_ids:
            in_degree[tid] = 0
            adj[tid] = []

        # Populate adjacency and in-degrees
        # Note: task depends on its 'dependencies', meaning dependency runs FIRST.
        # Graph edge: dependency -> task
        for t in tasks:
            tid = t["id"]
            for dep in t.get("dependencies", []):
                if dep in adj:
                    adj[dep].append(tid)
                    in_degree[tid] += 1

        queue: deque[str] = deque([tid for tid in all_ids if in_degree[tid] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append remaining nodes if incomplete
        for tid in all_ids:
            if tid not in order:
                order.append(tid)

        return order

    @staticmethod
    def identify_blocked_tasks(tasks: list[dict[str, Any]], completed_ids: set[str]) -> list[str]:
        """Returns IDs of tasks that cannot run because dependencies failed/cancelled."""
        blocked = []
        failed_or_cancelled = {t["id"] for t in tasks if t["status"] in ("FAILED", "CANCELLED")}

        for t in tasks:
            if t["status"] == "QUEUED":
                # If any dependency is failed or cancelled, this task is blocked
                if any(dep in failed_or_cancelled for dep in t.get("dependencies", [])):
                    blocked.append(t["id"])
        return blocked
