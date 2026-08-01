# DEPENDENCY MANAGER SPECIFICATION

Details the task dependency verification layer of JARVIS.

---

## 1. Algorithmic Cycle Detection

Uses Depth First Search (DFS) with node coloring:
- **White** (0): Unvisited node.
- **Gray** (1): Node currently in DFS path (visiting).
- **Black** (2): Node fully visited.
- If a DFS traversal hits a gray node, a circular dependency is reported, and scheduler falls back to sequential execution.

## 2. Topological Sorting

Sorts tasks using in-degree maps (Kahn's Algorithm variant) to determine the exact order tasks must run, ensuring parents execute and finish before children are scheduled.
